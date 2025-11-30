"""API routes for triggering graph execution."""
from fastapi import APIRouter, HTTPException
from app.api.schemas import (
    BuildRequest, 
    BuildResponse, 
    FluxTestRequest, 
    FluxTestResponse,
    GenerateAssemblyManualRequest,
    GenerateAssemblyManualResponse,
)
from app.core.database import get_inventory, get_inventory_item_by_id
from app.core.config import settings
from app.graph.workflow import get_workflow
from app.graph.state import AgentState
from app.graph.nodes import (
    node_assembly_manual_prompt_engineer,
    node_assembly_manual_generator,
)
from app.services.flux_service import generate_image
from langfuse import observe
import traceback


router = APIRouter(prefix="/api/v1", tags=["build"])


@router.get("/inventory")
async def get_all_inventory():
    """
    GET /inventory endpoint.
    
    Returns all inventory items from MongoDB.
    """
    try:
        items = get_inventory()
        return {"success": True, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch inventory: {str(e)}")


@router.delete("/inventory/{item_id}")
async def delete_inventory_item(item_id: str):
    """
    DELETE /inventory/{item_id} endpoint.
    
    Deletes an inventory item from MongoDB.
    """
    try:
        from app.core.database import get_database
        db = get_database()
        collection = db.inventory
        
        # Try to delete by 'id' field first
        result = collection.delete_one({"id": item_id})
        
        # If not found, try by _id (ObjectId)
        if result.deleted_count == 0:
            from bson import ObjectId
            try:
                result = collection.delete_one({"_id": ObjectId(item_id)})
            except Exception:
                pass
        
        if result.deleted_count > 0:
            return {"success": True, "message": f"Item {item_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")


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
            "style_description": request.previous_style_description or "",  # Use previous or empty
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
            style_description=final_state.get("style_description"),
            construction_plan=final_state.get("construction_plan"),
            selected_item_ids=final_state.get("selected_item_ids", []),
            selected_items=selected_items,
            flux_prompt=final_state.get("flux_prompt"),
            final_image_url=final_state.get("final_image_url"),
            assembly_manual_prompts=[],  # Assembly manual not generated in workflow
            assembly_manual_images=[],  # Assembly manual not generated in workflow
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


@router.post("/generate-assembly-manual", response_model=GenerateAssemblyManualResponse)
@observe(name="generate_assembly_manual_endpoint")
async def generate_assembly_manual(request: GenerateAssemblyManualRequest) -> GenerateAssemblyManualResponse:
    """
    POST /generate-assembly-manual endpoint.
    
    Generates an assembly manual for a confirmed product design.
    This endpoint is called after the user confirms they're happy with the final product image.
    
    Takes the construction plan and selected item IDs, then generates step-by-step
    assembly instructions with images.
    """
    try:
        # Create a minimal state with only the data needed for assembly manual generation
        state: AgentState = {
            "user_query": "",  # Not needed for assembly manual
            "style_description": "",  # Not needed for assembly manual
            "construction_plan": request.construction_plan,
            "selected_item_ids": request.selected_item_ids,
            "flux_prompt": None,  # Not needed for assembly manual
            "final_image_url": request.final_image_url,  # Use confirmed product image for consistency
            "assembly_manual_prompts": [],
            "assembly_manual_images": [],
            "retry_count": 0,
            "clerk_feedback": None,
            "status": "processing",
            "is_clerk_successful": True,  # Assume success since items were already selected
        }
        
        # Generate assembly manual prompts
        prompt_state = node_assembly_manual_prompt_engineer(state)
        state.update(prompt_state)
        
        # Generate assembly manual images
        image_state = node_assembly_manual_generator(state)
        state.update(image_state)
        
        return GenerateAssemblyManualResponse(
            success=True,
            assembly_manual_prompts=state.get("assembly_manual_prompts", []),
            assembly_manual_images=state.get("assembly_manual_images", []),
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        return GenerateAssemblyManualResponse(
            success=False,
            assembly_manual_prompts=[],
            assembly_manual_images=[],
            error=f"Assembly manual generation failed: {str(e)}\n\nTraceback:\n{error_trace}",
        )
