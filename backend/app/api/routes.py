"""API routes for triggering graph execution."""
from fastapi import APIRouter, HTTPException
from app.api.schemas import BuildRequest, BuildResponse
from app.core.database import get_inventory, get_inventory_item_by_id
from app.graph.workflow import get_workflow
from app.graph.state import AgentState
import traceback


router = APIRouter(prefix="/api/v1", tags=["build"])


@router.post("/build", response_model=BuildResponse)
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
            "construction_plan": None,
            "selected_item_ids": [],
            "flux_prompt": None,
            "final_image_url": None,
            "retry_count": 0,
            "clerk_feedback": None,
            "status": "processing",
            "is_clerk_successful": False,
        }
        
        # Get workflow and execute
        workflow = get_workflow()
        final_state = workflow.invoke(initial_state)
        
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

