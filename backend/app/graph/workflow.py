"""The compiled StateGraph workflow."""
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import (
    node_planner,
    node_inventory_clerk,
    node_prompt_engineer,
    node_flux_generator,
)


def create_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow.
    
    The workflow is linear:
    START -> Planner -> Inventory Clerk -> Prompt Engineer -> Flux Generator -> END
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", node_planner)
    workflow.add_node("inventory_clerk", node_inventory_clerk)
    workflow.add_node("prompt_engineer", node_prompt_engineer)
    workflow.add_node("flux_generator", node_flux_generator)
    
    # Define the linear flow
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "inventory_clerk")
    workflow.add_edge("inventory_clerk", "prompt_engineer")
    workflow.add_edge("prompt_engineer", "flux_generator")
    workflow.add_edge("flux_generator", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# Create a singleton instance
_workflow_instance = None


def get_workflow() -> StateGraph:
    """Get or create the workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = create_workflow()
    return _workflow_instance

