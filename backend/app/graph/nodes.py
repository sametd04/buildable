"""Node logic for Agent A (Planner), B (Inventory Clerk), C (Prompt Engineer), and D (Flux Generator)."""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph.state import AgentState
from app.services.tools import get_inventory_retriever_tool, get_inventory_retriever
from app.utils.parse_prompt import load_prompt

# Imports for Image Composition
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import base64
import math


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


@observe(name="conversation_agent")
def node_conversation_agent(state: AgentState) -> Dict[str, Any]:
    """
    Conversation Agent Node using Slot-Filling pattern.
    
    Uses ChatOpenAI with RequiredData bound as a tool.
    Asks follow-up questions until it can populate the tool.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from pydantic import BaseModel, Field
    
    # Define the required data schema
    class RequiredData(BaseModel):
        """Schema for the information that must be gathered before proceeding to workflow."""
        use_case: str = Field(description="What the item will be used for (e.g., workspace, storage, decoration)")
        dimensions: str = Field(description="Approximate size requirements or constraints (e.g., 'fits in a corner', 'desk height')")
        style_preferences: str = Field(description="Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)")
        material_preferences: str = Field(default="", description="Any specific material preferences or constraints. Leave empty if no preference.")
        personalization: str = Field(default="", description="Any personal touches or specific requirements. Leave empty if none.")
        constraints: str = Field(default="", description="Any space, budget, or functional constraints. Leave empty if none.")
    
    llm = get_llm()
    
    # Get conversation history and state
    conversation_history = state.get("conversation_history", [])
    user_query = state.get("user_query", "")
    skip_conversation = state.get("skip_conversation", False)
    
    # If user wants to skip, proceed immediately
    if skip_conversation:
        return {
            "ready_for_workflow": True,
            "status": "processing",
        }
    
    # Convert conversation_history to LangChain messages
    messages = []
    if len(conversation_history) == 0:
        # First message - add system prompt
        system_prompt = f"""You are a friendly and helpful design consultant helping users create custom DIY furniture and structures.

CRITICAL: You MUST always ask about ALL of the following fields before calling the RequiredData tool. Ask about them systematically, one or two at a time:

1. **Use Case & Purpose**: What will this be used for? (e.g., workspace, storage, decoration)
2. **Dimensions & Size**: Approximate size requirements (e.g., "fits in a corner", "desk height", "shelf width")
3. **Style Preferences**: Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)
4. **Material Preferences**: Any specific material preferences or constraints (e.g., wood type, metal finish) - optional but still ask
5. **Personalization**: Any personal touches or specific requirements (e.g., "needs to match my existing furniture") - optional but still ask
6. **Constraints**: Any space, budget, or functional constraints - optional but still ask

IMPORTANT RULES:
- You MUST ask about all 6 fields, even if some are optional
- Ask 1-2 questions at a time in a natural, friendly way
- Don't be overwhelming - keep it conversational
- Only call the RequiredData tool AFTER you have asked about all 6 fields and received responses
- For optional fields (4-6), if the user says "none" or "no preference", you can leave them empty in the tool call
- Required fields (1-3) must have actual answers from the user

User's initial request: {user_query}

Start by asking about the first 1-2 fields to begin gathering information."""
        messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_query))
    else:
        # Convert existing conversation history to LangChain messages
        # Add system prompt to remind agent of the fields to ask about
        system_prompt = """You are a friendly and helpful design consultant helping users create custom DIY furniture and structures.

CRITICAL: You MUST always ask about ALL of the following fields before calling the RequiredData tool. Ask about them systematically, one or two at a time:

1. **Use Case & Purpose**: What will this be used for? (e.g., workspace, storage, decoration)
2. **Dimensions & Size**: Approximate size requirements (e.g., "fits in a corner", "desk height", "shelf width")
3. **Style Preferences**: Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)
4. **Material Preferences**: Any specific material preferences or constraints (e.g., wood type, metal finish) - optional but still ask
5. **Personalization**: Any personal touches or specific requirements (e.g., "needs to match my existing furniture") - optional but still ask
6. **Constraints**: Any space, budget, or functional constraints - optional but still ask

IMPORTANT RULES:
- You MUST ask about all 6 fields, even if some are optional
- Ask 1-2 questions at a time in a natural, friendly way
- Don't be overwhelming - keep it conversational
- Only call the RequiredData tool AFTER you have asked about all 6 fields and received responses
- For optional fields (4-6), if the user says "none" or "no preference", you can leave them empty in the tool call
- Required fields (1-3) must have actual answers from the user

Continue the conversation by asking about the remaining fields you haven't covered yet."""
        messages.append(SystemMessage(content=system_prompt))
        
        # Convert existing conversation history to LangChain messages
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    # Bind the RequiredData as a tool and get response
    llm_with_tool = llm.bind_tools([RequiredData])
    
    # Check if we should stream (this will be set by the caller)
    stream = state.get("_stream", False)
    
    if stream:
        # For streaming, we'll collect chunks and return them
        # The actual streaming happens in the API endpoint
        response = llm_with_tool.invoke(messages)
    else:
        response = llm_with_tool.invoke(messages)
    
    # Convert response back to conversation_history format
    if hasattr(response, "content"):
        conversation_history.append({
            "role": "assistant",
            "content": response.content,
        })
    
    # Check if the response contains a tool call for RequiredData
    has_tool_call = False
    conversation_data = {}
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                has_tool_call = True
                args = tool_call.get("args", {})
                conversation_data = {
                    "use_case": args.get("use_case", ""),
                    "dimensions": args.get("dimensions", ""),
                    "style_preferences": args.get("style_preferences", ""),
                    "material_preferences": args.get("material_preferences", ""),
                    "personalization": args.get("personalization", ""),
                    "constraints": args.get("constraints", ""),
                }
                # Add confirmation message
                conversation_history.append({
                    "role": "assistant",
                    "content": "Great! I have enough information to create your design. Let me proceed with generating it...",
                })
                break
    
    if has_tool_call:
        return {
            "conversation_history": conversation_history,
            "conversation_data": conversation_data,
            "ready_for_workflow": True,
            "status": "processing",
        }
    else:
        return {
            "conversation_history": conversation_history,
            "conversation_data": state.get("conversation_data", {}),
            "ready_for_workflow": False,
            "status": "conversation",
        }


@observe(name="style_optimizer")
def node_style_optimizer(state: AgentState) -> Dict[str, Any]:
    """
    Node 0: Style Optimizer
    
    Takes the raw user_query and conversation data to expand into a detailed visual/aesthetic description.
    Focuses on mood, texture, lighting, and overall vibe without listing specific parts.
    Updates style_description in state.
    """
    llm = get_llm()
    
    # Check if we have previous style description (for iterative edits)
    previous_style = state.get("style_description", "")
    
    # Get user query and conversation data
    user_query = state.get("user_query")
    conversation_data = state.get("conversation_data", {})
    
    # Build enhanced query with conversation data
    enhanced_query = user_query
    if conversation_data:
        context_parts = []
        if conversation_data.get("use_case"):
            context_parts.append(f"Use case: {conversation_data['use_case']}")
        if conversation_data.get("dimensions"):
            context_parts.append(f"Dimensions: {conversation_data['dimensions']}")
        if conversation_data.get("style_preferences"):
            context_parts.append(f"Style preferences: {conversation_data['style_preferences']}")
        if conversation_data.get("material_preferences"):
            context_parts.append(f"Material preferences: {conversation_data['material_preferences']}")
        if conversation_data.get("personalization"):
            context_parts.append(f"Personalization: {conversation_data['personalization']}")
        if conversation_data.get("constraints"):
            context_parts.append(f"Constraints: {conversation_data['constraints']}")
        
        if context_parts:
            enhanced_query = f"{user_query}\n\nAdditional context from conversation:\n" + "\n".join(context_parts)
    
    if previous_style:
        prompt_variables = {
            "user_query": user_query,
            "previous_style": previous_style,
        }
        # Load your markdown template
        rendered_prompt = load_prompt(
            prompt_name="optimize_user_query_iter", 
            variables=prompt_variables
        )
        # Iterative edit - modify existing description
        prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
        ])

        chain = prompt | llm
        response = chain.invoke({})
    else:
        prompt_variables = {
            "user_query": enhanced_query,
        }

        # Load your markdown template
        rendered_prompt = load_prompt(
            prompt_name="optimize_user_query", 
            variables=prompt_variables
        )

        if not rendered_prompt:
            raise ValueError("Failed to load 'optimize_user_query.md' or template is empty")
        
        prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
        ])

        chain = prompt | llm
        response = chain.invoke({})
    
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

    # Get the previous construction plan
    construction_plan = state.get("construction_plan")

    # Get user query
    user_query = state.get("user_query")

    prompt_variables = {
        "style_description": style_description,
        "user_query": user_query,
    }

    rendered_prompt = ""
    if clerk_feedback:
        # Previous attempt failed - need to revise with alternative materials
        prompt_variables["clerk_feedback"] = clerk_feedback
        prompt_variables["previous_plan"] = construction_plan or ""
        rendered_prompt = load_prompt(
            prompt_name="planner_with_clerk_feedback", 
            variables=prompt_variables
        )
    else:
        # Standard planning behavior - use style_description as primary context
        rendered_prompt = load_prompt(
            prompt_name="planner_without_clerk_feedback", 
            variables=prompt_variables
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
    ])
    
    chain = prompt | llm
    
    # Invoke the LLM (no extra variables needed)
    response = chain.invoke({})
    
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
    #TODO: Put this prompt in a markdown file
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
    # Get the construction plan from state
    construction_plan = state.get("construction_plan", "")

    # Load prompt template from markdown file
    prompt_variables = {
        "construction_plan": construction_plan,
        "found_items": found_items_text

    }
    
    # Load your markdown template
    rendered_prompt = load_prompt(
        prompt_name="inventory_clerk", 
        variables=prompt_variables
    )

    # Iterative edit - modify existing description
    validation_prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
    ])

    # Use structured output with ClerkOutput to validate matches
    structured_llm = llm.with_structured_output(ClerkOutput)

    validation_chain = validation_prompt | structured_llm
    result = validation_chain.invoke({})

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
        if state.get("retry_count") == 1:
            # On final retry, just return
            return_state["is_clerk_successful"] = True  # Force success for now
            return_state["clerk_feedback"] = "The following required materials are missing or unsuitable: " + result.missing_parts_description
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
    
    # Load prompt template from markdown file
    prompt_variables = {
        "construction_plan": state.get("construction_plan", ""),
        "items_description": items_description
    }
    
    rendered_prompt = load_prompt("promt_engineer", prompt_variables)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
    ])
    
    chain = prompt | llm
    response = chain.invoke({})
    
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
    
    # Use previous image if available (for image-to-image editing)
    previous_image = state.get("final_image_url")
    
    image_url = generate_image(
        prompt=state["flux_prompt"],
        material_image_url="https://www.thecontractchair.co.uk/media/re_branding/ck_uploads/from_tiny_editor/ash-wood-table-top%20(3).webp",
        previous_image_url=previous_image,
    )
    
    return {
        "final_image_url": image_url,
        "status": "success",
    }


class AssemblyLayer(BaseModel):
    """One layer/item in an assembly step image."""
    item_name: str = Field(description="Name of the item (e.g. 'Leg', 'Bolt')")
    quantity: int = Field(description="Number of items in this group")
    layer_prompt: str = Field(description="Prompt to generate ONE representative image of this item on a white background")


class AssemblyStep(BaseModel):
    """One step in the assembly process."""
    instruction: str = Field(description="Text instruction for this step")
    layers: List[AssemblyLayer] = Field(description="List of item groups needed for this step")


class AssemblyManualOutput(BaseModel):
    """Pydantic model for structured output from Assembly Manual Prompt Engineer."""
    steps: List[AssemblyStep] = Field(
        description="List of assembly steps"
    )


@observe(name="assembly_manual_prompt_engineer")
def node_assembly_manual_prompt_engineer(state: AgentState) -> Dict[str, Any]:
    """
    Assembly Manual Prompt Engineer Node
    
    Receives construction_plan and generates step-by-step prompts using Layered Label + Sample strategy.
    Updates assembly_manual_prompts in state (now a list of step objects/dicts).
    """
    llm = get_llm()
    
    construction_plan = state.get("construction_plan", "")
    if not construction_plan:
        return {
            "assembly_manual_prompts": [],
        }
    
    # Get details of selected items for context
    from app.core.database import get_inventory_item_by_id
    
    selected_items = []
    for item_id in state.get("selected_item_ids", []):
        item = get_inventory_item_by_id(item_id)
        if item:
            selected_items.append(item)
    
    items_description = "\n".join([
        f"- {item.get('name')}: {item.get('description', 'No description')}"
        for item in selected_items
    ])
    
    # Get the final product image URL for visual consistency
    final_image_url = state.get("final_image_url")
    final_image_context = ""
    if final_image_url:
        final_image_context = f"CRITICAL: The final product image is available at: {final_image_url}"
    
    prompt_variables = {
        "construction_plan": construction_plan,
        "items_description": items_description,
        "final_image_context": final_image_context,
    }
    
    # Load new prompt template
    rendered_prompt = load_prompt("assembly_manual", prompt_variables)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
    ])
    
    # Use structured output
    structured_llm = llm.with_structured_output(AssemblyManualOutput)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({})
        # Convert pydantic objects to dicts for state storage
        assembly_steps = [step.model_dump() for step in result.steps]
    except Exception as e:
        print(f"⚠️ Structured output failed: {e}")
        assembly_steps = []
    
    return {
        "assembly_manual_prompts": assembly_steps,
    }


def composite_layers(step_data: Dict[str, Any], layer_images: Dict[str, Image.Image]) -> str:
    """
    Stitches transparent/white-bg item images onto a white 16:9 canvas.
    Returns base64 encoded image string.
    """
    # Canvas settings
    CANVAS_WIDTH = 1024
    CANVAS_HEIGHT = 576  # 16:9
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # Load font
    try:
        # Try to load a standard font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        
    # Instruction text at top
    instruction = step_data.get("instruction", "")
    draw.text((20, 20), instruction, fill="black", font=font)
    
    layers = step_data.get("layers", [])
    if not layers:
        return ""

    # Layout strategy: Horizontal row of groups
    # Each group has: [Representative Image] + Text "Nx Name"
    
    num_groups = len(layers)
    available_width = CANVAS_WIDTH
    group_width = available_width // num_groups
    
    for i, layer in enumerate(layers):
        item_name = layer.get("item_name", "Item")
        quantity = layer.get("quantity", 1)
        prompt = layer.get("layer_prompt", "")
        
        # Get the pre-generated image for this layer
        layer_key = f"{item_name}_{prompt}"
        img = layer_images.get(layer_key)
        
        if img:
            # Resize image to fit in group slot (maintain aspect ratio)
            # Max size: group_width - padding, height - padding
            target_size = min(group_width - 40, 300)
            img_ratio = img.width / img.height
            
            new_width = target_size
            new_height = int(new_width / img_ratio)
            
            # Make white transparent (simple thresholding)
            # Convert to RGBA
            img = img.convert("RGBA")
            datas = img.getdata()
            new_data = []
            for item in datas:
                # If pixel is very light/white, make it transparent
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Calculate position
            x_center = (i * group_width) + (group_width // 2)
            y_center = CANVAS_HEIGHT // 2
            
            paste_x = x_center - (new_width // 2)
            paste_y = y_center - (new_height // 2)
            
            # Paste with mask (for transparency)
            canvas.paste(img_resized, (paste_x, paste_y), img_resized)
            
            # Draw label below
            label = f"{quantity}x {item_name}"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x_center - (text_width // 2), paste_y + new_height + 10), label, fill="black", font=font)
            
        else:
            print(f"⚠️ Missing image for layer: {item_name}")
            
    # Convert to base64
    buffered = BytesIO()
    canvas.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


@observe(name="assembly_manual_generator")
def node_assembly_manual_generator(state: AgentState) -> Dict[str, Any]:
    """
    Assembly Manual Generator Node
    
    Receives assembly_manual_prompts (list of step dicts) and generates composite images.
    1. Identifies all unique layers needed across steps.
    2. Generates one sample image for each unique layer.
    3. Composites them for each step using the Label + Sample strategy.
    """
    from app.services.flux_service import generate_image
    import hashlib
    
    assembly_steps = state.get("assembly_manual_prompts", [])
    if not assembly_steps:
        return {
            "assembly_manual_images": [],
        }
    
    # Material image URL
    material_image_url = "https://www.thecontractchair.co.uk/media/re_branding/ck_uploads/from_tiny_editor/ash-wood-table-top%20(3).webp"
    
    # 1. Identify unique layers to generate
    # Key: "ItemName_Prompt", Value: Image.Image
    unique_layer_prompts = {} 
    
    for step in assembly_steps:
        layers = step.get("layers", [])
        for layer in layers:
            item_name = layer.get("item_name", "")
            prompt = layer.get("layer_prompt", "")
            key = f"{item_name}_{prompt}"
            unique_layer_prompts[key] = prompt
            
    # 2. Generate images for unique layers
    layer_images = {} # Key: "ItemName_Prompt", Value: PIL Image
    
    print(f"📸 Generating {len(unique_layer_prompts)} unique components...")
    
    for key, prompt in unique_layer_prompts.items():
        # Generate image
        # Use simple hash for seed
        seed = int(hashlib.md5(key.encode()).hexdigest()[:8], 16) % (2**31)
        
        image_url = generate_image(
            prompt=prompt,
            material_image_url=material_image_url,
            width=1024,
            height=1024,
            seed=seed,
        )
        
        if image_url:
            try:
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                layer_images[key] = img
                print(f"✅ Downloaded layer image for: {key}")
            except Exception as e:
                print(f"❌ Failed to download/open image {image_url}: {e}")
        else:
             print(f"⚠️ Failed to generate image for layer: {key}")

    # 3. Composite steps
    assembly_images = []
    
    for i, step in enumerate(assembly_steps):
        print(f"🎨 Compositing step {i+1}/{len(assembly_steps)}...")
        try:
            composite_b64 = composite_layers(step, layer_images)
            assembly_images.append(composite_b64)
        except Exception as e:
            print(f"❌ Composition failed for step {i+1}: {e}")
            import traceback
            traceback.print_exc()
            # Add placeholder or error
            assembly_images.append("")

    return {
        "assembly_manual_images": assembly_images,
    }
