"""Node logic for Agent A (Planner), B (Inventory Clerk), C (Prompt Engineer), and D (Flux Generator)."""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph.state import AgentState
from app.services.tools import get_inventory_retriever_tool


# Initialize LLM based on configuration
def get_llm():
    """Get the configured LLM instance."""
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
    
    Receives user_query and generates a detailed construction plan.
    The plan should reference materials and parts that can be found in the hardware inventory.
    Updates construction_plan in state.
    """
    llm = get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert construction planner. Your task is to create a detailed, 
        step-by-step construction plan based on a user's vague idea.
        
        Be specific about:
        - What materials and parts will be used (describe them clearly)
        - How they will be assembled
        - The final structure's appearance and function
        
        Make the plan practical and achievable. Describe materials and parts in detail so they can be 
        found in a hardware inventory catalog. Use descriptive terms like "steel pipe", "wood plank", 
        "LED lighting", etc."""),
        ("human", """User's idea: {user_query}

Generate a detailed construction plan that realizes the user's idea.
The plan should be specific, actionable, and clearly describe the materials and parts needed."""),
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "user_query": state["user_query"],
    })
    
    construction_plan = response.content
    
    return {
        "construction_plan": construction_plan,
    }


class ItemSelection(BaseModel):
    """Pydantic model for structured output from Inventory Clerk."""
    selected_item_ids: List[str] = Field(
        description="List of item IDs from the inventory that are needed for the construction plan. "
        "Only include IDs that were returned by the search_hardware_catalog tool."
    )


def node_inventory_clerk(state: AgentState) -> Dict[str, Any]:
    """
    Agent B: Inventory Clerk Node
    
    Receives construction_plan and uses the search_hardware_catalog tool to find matching items.
    Iterates through parts mentioned in the plan and searches for matching inventory items.
    Uses structured output to return a list of item IDs.
    Updates selected_item_ids in state.
    """
    llm = get_llm()
    
    # Get the search tool/retriever
    search_tool = get_inventory_retriever_tool()
    
    # Extract key terms from the construction plan for searching
    # We'll search for materials and parts mentioned in the plan
    construction_plan = state["construction_plan"] or ""
    
    # Use the LLM to extract search terms from the plan
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract material and part names from a construction plan. 
        Return a comma-separated list of key terms that would be used to search a hardware catalog.
        Focus on materials, components, and parts (e.g., "steel pipe", "wood plank", "LED light")."""),
        ("human", "Construction Plan:\n{construction_plan}\n\nExtract search terms:"),
    ])
    
    extraction_chain = extraction_prompt | llm
    extraction_response = extraction_chain.invoke({"construction_plan": construction_plan})
    search_terms_text = extraction_response.content
    
    # Parse search terms (simple split, could be improved)
    search_terms = [term.strip() for term in search_terms_text.split(",") if term.strip()]
    
    # Search for items using the tool
    selected_ids = set()
    all_found_items = []
    
    for search_term in search_terms[:10]:  # Limit to 10 searches to avoid too many API calls
        try:
            # Use the tool to search
            search_results = search_tool.invoke({"query": search_term})
            
            # Extract IDs from results
            # The retriever tool returns Document objects from LangChain
            if isinstance(search_results, list):
                for doc in search_results:
                    item_data = None
                    
                    # Handle Document objects from LangChain
                    if hasattr(doc, "metadata") and doc.metadata:
                        # The metadata should contain the full MongoDB document
                        # MongoDBAtlasVectorSearch stores the full document in metadata
                        item_data = doc.metadata
                        # Also check if there's a nested document structure
                        if not item_data.get("id") and not item_data.get("_id"):
                            # Try to get from the document itself
                            if hasattr(doc, "dict") or isinstance(doc.metadata, dict):
                                item_data = doc.metadata
                    elif isinstance(doc, dict):
                        item_data = doc
                    
                    if item_data:
                        # Extract ID (could be 'id' or '_id')
                        item_id = item_data.get("id") or (str(item_data.get("_id")) if item_data.get("_id") else None)
                        if item_id:
                            selected_ids.add(item_id)
                            all_found_items.append({
                                "id": item_id,
                                "name": item_data.get("name", ""),
                                "description": item_data.get("description", ""),
                                "category": item_data.get("category", ""),
                            })
        except Exception as e:
            # Continue if a search fails
            print(f"Warning: Search failed for '{search_term}': {str(e)}")
            continue
    
    # Format found items for the LLM to make final selection
    found_items_text = "\n".join([
        f"- ID: {item.get('id')}, Name: {item.get('name', 'Unknown')}"
        for item in all_found_items
    ])
    
    # Use structured output to get final list of IDs
    structured_llm = llm.with_structured_output(ItemSelection)
    selection_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an inventory clerk. Analyze the construction plan and the found inventory items.
        Return ONLY the item IDs that are actually needed for the construction plan.
        Be precise - only include items that match materials or parts mentioned in the plan."""),
        ("human", """Construction Plan:
{construction_plan}

Found Inventory Items:
{found_items}

Return the item IDs needed for this project. Only include IDs from the found items list above."""),
    ])
    
    selection_chain = selection_prompt | structured_llm
    result = selection_chain.invoke({
        "construction_plan": construction_plan,
        "found_items": found_items_text or "No items found.",
    })
    
    # Validate IDs are from our found items
    valid_ids = [
        item_id for item_id in result.selected_item_ids
        if item_id in selected_ids
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
    
    # Get details of selected items from database
    from app.core.database import get_inventory_item_by_id
    
    selected_items = []
    for item_id in state["selected_item_ids"]:
        item = get_inventory_item_by_id(item_id)
        if item:
            selected_items.append(item)
    
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

