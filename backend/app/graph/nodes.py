"""Node logic for Agent A (Planner), B (Inventory Clerk), C (Prompt Engineer), and D (Flux Generator)."""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph.state import AgentState


# Initialize LLM based on configuration
def get_llm():
    """Get the configured LLM instance."""
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not set. Set ANTHROPIC_API_KEY in .env")
        return ChatAnthropic(
            model=settings.llm_model if settings.llm_model.startswith("claude") else "claude-3-5-sonnet-20241022",
            api_key=settings.anthropic_api_key,
            temperature=0.7,
        )
    else:
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not set. Set OPENAI_API_KEY in .env")
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )


def node_planner(state: AgentState) -> Dict[str, Any]:
    """
    Agent A: Planner Node
    
    Receives user_query + inventory_data and generates a detailed construction plan.
    Updates construction_plan in state.
    """
    llm = get_llm()
    
    # Format inventory items for context
    inventory_summary = "\n".join([
        f"- {item.get('name', 'Unknown')} ({item.get('id', 'N/A')}): {item.get('description', 'No description')}"
        for item in state["inventory_data"]
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert construction planner. Your task is to create a detailed, 
        step-by-step construction plan based on a user's vague idea, using ONLY items from the provided inventory.
        
        Be specific about:
        - What materials will be used
        - How they will be assembled
        - The final structure's appearance and function
        
        Make the plan practical and achievable with the available inventory items."""),
        ("human", """User's idea: {user_query}

Available inventory items:
{inventory_summary}

Generate a detailed construction plan that uses items from this inventory to realize the user's idea.
The plan should be specific, actionable, and reference items by their names."""),
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "user_query": state["user_query"],
        "inventory_summary": inventory_summary,
    })
    
    construction_plan = response.content
    
    return {
        "construction_plan": construction_plan,
    }


class ItemSelection(BaseModel):
    """Pydantic model for structured output from Inventory Clerk."""
    selected_item_ids: List[str] = Field(
        description="List of item IDs from the inventory that are needed for the construction plan. "
        "Only include IDs that exist in the provided inventory."
    )


def node_inventory_clerk(state: AgentState) -> Dict[str, Any]:
    """
    Agent B: Inventory Clerk Node
    
    Receives construction_plan and uses structured output to return a list of item IDs.
    Updates selected_item_ids in state.
    """
    llm = get_llm()
    
    # Get all available item IDs for validation context
    available_ids = [item.get("id") for item in state["inventory_data"] if item.get("id")]
    available_items = "\n".join([
        f"- ID: {item.get('id')}, Name: {item.get('name')}"
        for item in state["inventory_data"]
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an inventory clerk. Your task is to analyze a construction plan 
        and identify which specific inventory items (by their IDs) are needed.
        
        You MUST only return item IDs that exist in the provided inventory list.
        Be precise and only select items that are actually mentioned or implied in the construction plan."""),
        ("human", """Construction Plan:
{construction_plan}

Available Inventory Items:
{available_items}

Analyze the construction plan and return ONLY the item IDs that are needed for this project.
Return an empty list if no items match."""),
    ])
    
    # Use structured output to ensure we get a list of IDs
    structured_llm = llm.with_structured_output(ItemSelection)
    chain = prompt | structured_llm
    
    result = chain.invoke({
        "construction_plan": state["construction_plan"],
        "available_items": available_items,
    })
    
    # Validate that all IDs exist in inventory
    valid_ids = [
        item_id for item_id in result.selected_item_ids
        if item_id in available_ids
    ]
    
    return {
        "selected_item_ids": valid_ids,
    }


def node_prompt_engineer(state: AgentState) -> Dict[str, Any]:
    """
    Agent C: Prompt Engineer Node
    
    Receives selected_item_ids + construction_plan and generates an optimized prompt for FLUX.
    Updates flux_prompt in state.
    """
    llm = get_llm()
    
    # Get details of selected items
    selected_items = [
        item for item in state["inventory_data"]
        if item.get("id") in state["selected_item_ids"]
    ]
    
    items_description = "\n".join([
        f"- {item.get('name')}: {item.get('description', 'No description')}"
        for item in selected_items
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a prompt engineer specializing in photorealistic image generation.
        Your task is to create a detailed, optimized prompt for the FLUX API that will generate
        a stunning hero shot of the construction project.
        
        The prompt should:
        - Be highly descriptive and visual
        - Include lighting, composition, and style details
        - Reference the specific materials and construction
        - Be optimized for photorealistic rendering
        - Be concise but detailed (aim for 100-200 words)"""),
        ("human", """Construction Plan:
{construction_plan}

Selected Materials:
{items_description}

Generate an optimized FLUX prompt for a photorealistic hero shot of this construction project.
The image should showcase the final result in an impressive, professional manner."""),
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "construction_plan": state["construction_plan"],
        "items_description": items_description,
    })
    
    flux_prompt = response.content
    
    return {
        "flux_prompt": flux_prompt,
    }


def node_flux_generator(state: AgentState) -> Dict[str, Any]:
    """
    Agent D: Flux Generator Node
    
    Calls the mocked flux_service to generate an image.
    Updates final_image_url in state.
    """
    from app.services.flux_service import generate_image
    
    image_url = generate_image(state["flux_prompt"])
    
    return {
        "final_image_url": image_url,
    }

