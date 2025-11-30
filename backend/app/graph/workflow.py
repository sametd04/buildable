"""The compiled StateGraph workflow."""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import (
    node_conversation_agent,
    node_style_optimizer,
    node_planner,
    node_inventory_clerk,
    node_prompt_engineer,
    node_flux_generator,
)


def check_conversation_status(state: AgentState) -> Literal["workflow", "conversation"]:
    """
    Conditional function to determine if we should proceed to workflow or continue conversation.
    
    Logic:
    - If ready_for_workflow is True or skip_conversation is True: proceed to workflow
    - Otherwise: continue conversation
    
    Args:
        state: Current AgentState
        
    Returns:
        Next node name
    """
    if state.get("ready_for_workflow", False) or state.get("skip_conversation", False):
        return "workflow"  # Proceed to style optimizer
    return "conversation"  # Continue conversation


def check_inventory_status(state: AgentState) -> Literal["agent_c", "agent_a", "end_fail"]:
    """
    Conditional function to determine the next step after Agent B (Inventory Clerk).
    
    Logic:
    - If clerk was successful: proceed to Agent C (Prompt Engineer)
    - If retry_count >= 3: give up and end with failure
    - Otherwise: loop back to Agent A (Planner) for revision
    
    Args:
        state: Current AgentState
        
    Returns:
        Next node name or END
    """
    if state.get("is_clerk_successful", False):
        return "agent_c"  # Proceed to Prompt Engineering
    
    retry_count = state.get("retry_count", 0)
    if retry_count >= 1:
        return "end_fail"  # Give up after 1 retry
    
    return "agent_a"  # Loop back to Planner


def set_failure_status(state: AgentState) -> dict:
    """
    Set the status to failed_no_parts when giving up after retries.
    
    Args:
        state: Current AgentState
        
    Returns:
        Dictionary with updated status
    """
    return {
        "status": "failed_no_parts",
    }


def increment_retry_count(state: AgentState) -> dict:
    """
    Helper function to increment retry_count when looping back to Planner.
    
    Args:
        state: Current AgentState
        
    Returns:
        Dictionary with updated retry_count
    """
    current_count = state.get("retry_count", 0)
    return {
        "retry_count": current_count + 1,
        "status": "processing",
    }




def create_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow with feedback loop.
    
    The workflow includes:
    START -> Conversation Agent -> (conditional) -> Style Optimizer -> Planner -> Inventory Clerk -> 
    (conditional) -> Prompt Engineer -> Flux Generator -> END
                                                                                |
                                                                                v (if failed)
                                                                            Planner (retry)
    
    Note: The retry loop goes back to Planner (not Style Optimizer) to maintain the style while revising materials.
    Assembly manual generation is handled separately via a dedicated endpoint after user confirmation.
    
    Returns:
        Compiled StateGraph ready for execution with Langfuse tracing.
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("conversation_agent", node_conversation_agent)
    workflow.add_node("style_optimizer", node_style_optimizer)
    workflow.add_node("planner", node_planner)
    workflow.add_node("inventory_clerk", node_inventory_clerk)
    workflow.add_node("prompt_engineer", node_prompt_engineer)
    workflow.add_node("flux_generator", node_flux_generator)
    
    # Add helper nodes
    workflow.add_node("increment_retry", increment_retry_count)
    workflow.add_node("set_failure_status", set_failure_status)
    
    # Define the flow
    workflow.set_entry_point("conversation_agent")
    
    # Conditional edge from conversation_agent
    workflow.add_conditional_edges(
        "conversation_agent",
        check_conversation_status,
        {
            "workflow": "style_optimizer",  # Proceed to workflow
            "conversation": END,  # Stop and wait for user input (conversation mode)
        }
    )
    
    workflow.add_edge("style_optimizer", "planner")
    workflow.add_edge("planner", "inventory_clerk")
    
    # Conditional edge from inventory_clerk
    workflow.add_conditional_edges(
        "inventory_clerk",
        check_inventory_status,
        {
            "agent_c": "prompt_engineer",  # Success - proceed
            "agent_a": "increment_retry",   # Retry - increment counter first
            "end_fail": "set_failure_status",  # Set failure status before ending
        }
    )
    
    # After incrementing retry, go back to planner
    workflow.add_edge("increment_retry", "planner")
    
    # After setting failure status, end
    workflow.add_edge("set_failure_status", END)
    
    # Continue with normal flow after success - generate product image only
    # Assembly manual generation is handled separately via a dedicated endpoint
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

