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
    
    Fetches inventory from MongoDB, initializes the Graph with user_query and inventory,
    and returns the final state (Plan, Selected Items, and Image URL).
    """
    try:
        # Fetch inventory from MongoDB
        inventory_data = get_inventory()
        
        # Initialize state
        initial_state: AgentState = {
            "user_query": request.user_query,
            "inventory_data": inventory_data,
            "construction_plan": None,
            "selected_item_ids": [],
            "flux_prompt": None,
            "final_image_url": None,
        }
        
        # Get workflow and execute
        workflow = get_workflow()
        final_state = workflow.invoke(initial_state)
        
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

