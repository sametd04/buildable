"""API routes for triggering graph execution."""
from fastapi import APIRouter, HTTPException
from app.api.schemas import BuildRequest, BuildResponse, FluxTestRequest, FluxTestResponse
from app.core.database import get_inventory, get_inventory_item_by_id
from app.core.config import settings
from app.graph.workflow import get_workflow
from app.graph.state import AgentState
from app.services.flux_service import generate_image
from langfuse import observe
import traceback


router = APIRouter(prefix="/api/v1", tags=["build"])


@router.post("/build", response_model=BuildResponse)
@observe(name="build_endpoint")
async def build(request: BuildRequest) -> BuildResponse:
    """
    POST /build endpoint.
    
    Initializes the Graph with user_query (inventory is accessed via vector search),
    and returns the final state (Plan, Selected Items, and Image URL).
    """
    try:
        # Initialize state (no need to load inventory into memory)
        initial_state: AgentState = {
            "user_query": request.user_query,
            "style_description": "",  # Will be set by style_optimizer node
            "construction_plan": None,
            "selected_item_ids": [],
            "flux_prompt": None,
            "final_image_url": None,
            "assembly_manual_prompts": [],
            "assembly_manual_images": [],
            "retry_count": 0,
            "clerk_feedback": None,
            "status": "processing",
            "is_clerk_successful": False,
        }
        
        # Get workflow and execute with Langfuse callback if configured
        workflow = get_workflow()
        
        # Add Langfuse callback handler for LangGraph tracing
        config = {}
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            from langfuse.langchain import CallbackHandler
            # Explicitly pass credentials to CallbackHandler
            # Try base_url first, fallback to host if that doesn't work
            import os
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url
            """
            try:
                langfuse_handler = CallbackHandler(
                    public_key=settings.langfuse_public_key,
                    # secret_key=settings.langfuse_secret_key,
                    # base_url=settings.langfuse_base_url,
                )
            except TypeError:
                # If base_url doesn't work, try host parameter
                langfuse_handler = CallbackHandler(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    base_url=settings.langfuse_base_url,
                )"""
            langfuse_handler = CallbackHandler()
            config["callbacks"] = [langfuse_handler]
        
        final_state = workflow.invoke(initial_state, config=config if config else None)
        
        # Check if the workflow failed due to missing parts
        status = final_state.get("status", "processing")
        if status == "failed_no_parts" or (not final_state.get("is_clerk_successful", False) and final_state.get("retry_count", 0) >= 3):
            return BuildResponse(
                success=False,
                user_query=final_state["user_query"],
                construction_plan=final_state.get("construction_plan"),
                selected_item_ids=[],
                selected_items=[],
                flux_prompt=None,
                final_image_url=None,
                assembly_manual_prompts=[],
                assembly_manual_images=[],
                error="We couldn't find the specific parts for your request. Please try a different design or use more common materials.",
            )
        
        # Get full details of selected items
        selected_items = [
            get_inventory_item_by_id(item_id)
            for item_id in final_state.get("selected_item_ids", [])
            if get_inventory_item_by_id(item_id) is not None
        ]
        
        return BuildResponse(
            success=True,
            user_query=final_state["user_query"],
            construction_plan=final_state.get("construction_plan"),
            selected_item_ids=final_state.get("selected_item_ids", []),
            selected_items=selected_items,
            flux_prompt=final_state.get("flux_prompt"),
            final_image_url=final_state.get("final_image_url"),
            assembly_manual_prompts=final_state.get("assembly_manual_prompts", []),
            assembly_manual_images=final_state.get("assembly_manual_images", []),
        )
        
    except ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB connection error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        error_trace = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Build failed: {str(e)}\n\nTraceback:\n{error_trace}"
        )



@router.post("/test-flux", response_model=FluxTestResponse)
async def test_flux(request: FluxTestRequest) -> FluxTestResponse:
    """
    POST /test-flux endpoint.
    
    Test the FLUX image generation service directly with custom parameters.
    Useful for debugging and testing the FLUX API integration.
    
    Supports two modes:
    1. Initial generation: Only provide prompt and material_image_url
    2. Iterative editing: Also provide previous_image_url to edit an existing image
    """
    try:
        image_url = generate_image(
            prompt=request.prompt,
            material_image_url=request.material_image_url,
            previous_image_url=request.previous_image_url,
            width=request.width,
            height=request.height,
            seed=request.seed,
        )
        
        if image_url:
            return FluxTestResponse(
                success=True,
                image_url=image_url,
            )
        else:
            return FluxTestResponse(
                success=False,
                error="Image generation failed. Check server logs for details.",
            )
            
    except Exception as e:
        error_trace = traceback.format_exc()
        return FluxTestResponse(
            success=False,
            error=f"FLUX test failed: {str(e)}\n\nTraceback:\n{error_trace}",
        )
