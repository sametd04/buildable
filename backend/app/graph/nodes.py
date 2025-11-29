"""Node logic for Agent A (Planner), B (Inventory Clerk), C (Prompt Engineer), and D (Flux Generator)."""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph.state import AgentState
from app.services.tools import get_inventory_retriever_tool, get_inventory_retriever


# Initialize LLM based on configuration
def get_llm():
    """Get the configured LLM instance."""
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not set. Set OPENAI_API_KEY in .env")
    
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )
    
    return llm


@observe(name="style_optimizer")
def node_style_optimizer(state: AgentState) -> Dict[str, Any]:
    """
    Node 0: Style Optimizer
    
    Takes the raw user_query and expands it into a detailed visual/aesthetic description.
    Focuses on mood, texture, lighting, and overall vibe without listing specific parts.
    Updates style_description in state.
    """
    llm = get_llm()
    

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
    User's request: {user_query}
    """)
    ])

    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", ""You are an expert Design Consultant. Your job is to take a short user request 
        and expand it into a detailed, paragraph-long visual description focusing on mood, texture, 
        and lighting. Do not list specific parts, just the vibe.
        
        Create a rich, evocative description that captures:
        - The overall aesthetic and mood
        - Visual textures and finishes
        - Color palette and lighting atmosphere
        - The feeling and character of the design
        - Any thematic elements or style references
        
        Keep it focused on the visual and emotional aspects, not on construction details or materials.""),
        ("human", ""User's request: {user_query}

Expand this into a detailed visual description focusing on the aesthetic, mood, texture, and lighting. 
Write a paragraph that captures the vibe and feeling of this design.""),
    ])"""
    
    chain = prompt | llm
    response = chain.invoke({
        "user_query": state["user_query"],
    })
    
    style_description = response.content
    
    return {
        "style_description": style_description,
    }


@observe(name="planner")
def node_planner(state: AgentState) -> Dict[str, Any]:
    """
    Agent A: Planner Node
    
    Receives style_description and generates a detailed construction plan.
    Uses style_description as primary context for the design.
    If clerk_feedback exists, adapts the plan to use alternative materials.
    Updates construction_plan in state.
    """
    llm = get_llm()
    
    # Get style description (should always be present after style_optimizer)
    style_description = state.get("style_description", "")
    
    # Check if there's feedback from the clerk
    clerk_feedback = state.get("clerk_feedback")
    
    if clerk_feedback:
        # Previous attempt failed - need to revise with alternative materials
        system_prompt = """You are an expert construction planner. Your previous construction plan failed 
        because the required materials were not available in the inventory.
        
        The Inventory Clerk reported: {clerk_feedback}
        
        Your task is to REWRITE the construction plan using ALTERNATIVE materials that are commonly 
        available in a standard hardware store. Focus on:
        - Standard materials like wood, metal, concrete, plastic, fabric, lighting
        - Common hardware items like pipes, planks, blocks, cables, bolts
        - Avoid exotic or specialized materials
        
        IMPORTANT: Maintain the design aesthetic described in the style description.
        Use alternative materials but preserve the visual character and mood.
        
        Be specific about:
        - What alternative materials and parts will be used
        - How they will be assembled
        - The final structure's appearance and function
        
        Make the plan practical and achievable with standard hardware store inventory."""
        
        human_prompt = """Style Description (maintain this aesthetic):
{style_description}

User's original idea: {user_query}

Previous attempt failed. Please rewrite the construction plan using ALTERNATIVE materials 
that are available in a standard hardware store. Avoid the materials that were missing, 
but maintain the visual style and aesthetic described above."""
    else:
        # Standard planning behavior - use style_description as primary context
        system_prompt = """You are an expert construction planner. Your task is to create a detailed, 
        step-by-step construction plan based on a style description and user request.
        
        The style description provides the aesthetic vision - your job is to translate that vision 
        into a practical construction plan using standard hardware store materials.
        
        Be specific about:
        - What materials and parts will be used (describe them clearly)
        - How they will be assembled
        - How the final structure will achieve the desired aesthetic
        - The final structure's appearance and function
        
        Make the plan practical and achievable. Describe materials and parts in detail so they can be 
        found in a hardware inventory catalog. Use descriptive terms like "steel pipe", "wood plank", 
        "LED lighting", etc. Focus on standard hardware store materials."""
        
        human_prompt = """Style Description (this is your primary design context):
{style_description}

User's original idea: {user_query}

Generate a detailed construction plan that realizes the aesthetic vision described above.
The plan should be specific, actionable, and clearly describe the materials and parts needed 
to achieve this design style."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt),
    ])
    
    chain = prompt | llm
    
    if clerk_feedback:
        response = chain.invoke({
            "style_description": style_description,
            "user_query": state["user_query"],
            "clerk_feedback": clerk_feedback,
        })
    else:
        response = chain.invoke({
            "style_description": style_description,
            "user_query": state["user_query"],
        })
    
    construction_plan = response.content
    
    return {
        "construction_plan": construction_plan,
    }


class ClerkOutput(BaseModel):
    """Pydantic model for structured output from Inventory Clerk."""
    selected_ids: List[str] = Field(
        default_factory=list,
        description="List of item IDs from the inventory that match the construction plan requirements."
    )
    missing_parts_description: Optional[str] = Field(
        default=None,
        description="Description of missing parts if no suitable matches were found."
        "Example: 'No titanium pipes found' or 'No specialized LED strips available'."
    )
    is_successful: bool = Field(
        description="Whether suitable inventory items were found for the construction plan. "
        "Set to True if matches are good, False if matches are poor or missing."
    )


@observe(name="inventory_clerk")
def node_inventory_clerk(state: AgentState) -> Dict[str, Any]:
    """
    Agent B: Inventory Clerk Node
    
    Receives construction_plan and uses the search_hardware_catalog tool to find matching items.
    Validates if matches are suitable and returns ClerkOutput with success status and feedback.
    Updates selected_item_ids, is_clerk_successful, and clerk_feedback in state.
    """
    llm = get_llm()
    
    # Get the retriever directly (not the tool) to access full Document objects with metadata
    retriever = get_inventory_retriever()
    
    # Extract key terms from the construction plan for searching
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
    
    # Parse search terms
    search_terms = [term.strip() for term in search_terms_text.split(",") if term.strip()]
    
    # Search for items using the retriever directly to get Document objects with metadata
    selected_ids = set()
    all_found_items = []
    
    # Import helper function for converting ObjectId to id
    from app.core.database import _convert_objectid_to_id
    
    for search_term in search_terms:  # Limit to 10 searches
        # Use the retriever directly - returns Document objects with .metadata containing full MongoDB doc
        documents = retriever.invoke(search_term)
        
        # Extract full MongoDB documents from Document metadata
        for doc in documents:
            # Document objects have .metadata containing the full MongoDB document
            if hasattr(doc, 'metadata') and doc.metadata:
                item_doc = dict(doc.metadata)  # Make a copy
                # Convert _id to id if needed
                item_doc = _convert_objectid_to_id(item_doc)
                item_id = doc.id
                item_doc["id"] = str(item_id)
                
                if item_id and str(item_id) not in selected_ids:
                    selected_ids.add(str(item_id))
                    all_found_items.append(item_doc)
    
    # Format found items for validation
    found_items_text = "\n".join([
        f"- ID: {item.get('id')}, Name: {item.get('name', 'Unknown')}, Description: {item.get('description', '')}"
        for item in all_found_items
    ]) if all_found_items else "No items found."
    
    # Use structured output with ClerkOutput to validate matches
    structured_llm = llm.with_structured_output(ClerkOutput)
    validation_prompt = ChatPromptTemplate.from_messages([
        ("system", """Act as an inventory checker. Compare the construction plan against the found inventory items. We only care about raw materials right now (ignore tools and finishes).

If you find what we need, mark is_successful=True and output the IDs. If the inventory falls short, set is_successful=False, list what you found, and tell the planner exactly what's missing. Use your best judgment to ensure the materials are actually suitable."""),
        ("human", """Construction Plan:
{construction_plan}

Found Inventory Items:
{found_items}

Evaluate if these items are suitable for the construction plan. """),
    ])
    
    validation_chain = validation_prompt | structured_llm
    result = validation_chain.invoke({
        "construction_plan": construction_plan,
        "found_items": found_items_text,
    })
    
    # Validate IDs are from our found items
    valid_ids = [
        item_id for item_id in result.selected_ids
        if item_id in selected_ids
    ]
    
    # Prepare return state
    return_state = {
        "selected_item_ids": valid_ids,
        "is_clerk_successful": result.is_successful,
    }
    
    if not result.is_successful:
        # Provide feedback for the planner
        return_state["clerk_feedback"] = result.missing_parts_description or (
            "No suitable inventory items found for the required materials in the construction plan. Here are the items I found: " + found_items_text
        )
    else:
        # Clear any previous feedback on success
        return_state["clerk_feedback"] = None
    
    return return_state


@observe(name="prompt_engineer")
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


@observe(name="flux_generator")
def node_flux_generator(state: AgentState) -> Dict[str, Any]:
    """
    Agent D: Flux Generator Node
    
    Calls the mocked flux_service to generate an image.
    Updates final_image_url and sets status to success in state.
    """
    from app.services.flux_service import generate_image
    
    image_url = generate_image(state["flux_prompt"], "https://www.thecontractchair.co.uk/media/re_branding/ck_uploads/from_tiny_editor/ash-wood-table-top%20(3).webp", )
    
    return {
        "final_image_url": image_url,
        "status": "success",
    }

