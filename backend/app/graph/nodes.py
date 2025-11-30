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
- **CRITICAL: You CANNOT call the RequiredData tool on the first message. You MUST ask at least one question first, even if the user's request seems complete.**
- Only call the RequiredData tool AFTER you have asked about all 6 fields and received responses
- For optional fields (4-6), if the user says "none" or "no preference", you can leave them empty in the tool call
- Required fields (1-3) must have actual answers from the user

User's initial request: {user_query}

**You MUST start by asking questions. Do NOT call the RequiredData tool yet - ask about the first 1-2 fields to begin gathering information.**"""
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
    
    # VALIDATION: Reject tool calls if this is the first message (no conversation history)
    # The agent MUST ask at least one question before calling the tool
    is_first_message = len(conversation_history) == 0
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                # Reject tool call if this is the first message - agent must ask questions first
                if is_first_message:
                    # Remove the tool call from the response and force the agent to ask questions
                    # The response content should already be asking questions, so we just don't accept the tool call
                    has_tool_call = False
                    break
                
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


class AssemblyManualOutput(BaseModel):
    """Pydantic model for structured output from Assembly Manual Prompt Engineer."""
    steps: List[str] = Field(
        description="List of prompts for each assembly step, in sequential order"
    )


@observe(name="assembly_manual_prompt_engineer")
def node_assembly_manual_prompt_engineer(state: AgentState) -> Dict[str, Any]:
    """
    Assembly Manual Prompt Engineer Node
    
    Receives construction_plan and generates step-by-step prompts for FLUX 2
    to create an assembly manual. Each prompt describes one step of the assembly process.
    Updates assembly_manual_prompts in state.
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
        final_image_context = f"""
CRITICAL: The final product image is available at: {final_image_url}
The assembly manual steps MUST match the visual style, materials, colors, lighting, and overall appearance of this confirmed final product image.
Analyze the final product image to understand:
- The exact visual style and aesthetic
- Material textures and finishes
- Color scheme and tones
- Lighting conditions and mood
- Camera angle and perspective
- Overall composition and design details

The assembly steps should progressively build toward this exact final product appearance."""
        
    construction_plan
    # Load prompt template from markdown file
    prompt_variables = {
        "construction_plan": construction_plan,
        "items_description": items_description,
        "final_image_context": final_image_context,
    }
    
    rendered_prompt = load_prompt("promt_engineer", prompt_variables)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", rendered_prompt),
    ])
    
    # Use structured output for reliable parsing
    try:
        structured_llm = llm.with_structured_output(AssemblyManualOutput)
        chain = prompt | structured_llm
        result = chain.invoke({
            "construction_plan": construction_plan,
            "items_description": items_description,
            "final_image_context": final_image_context,
        })
        assembly_prompts = result.steps
        
        # Post-process prompts to ensure explicit step references and action focus
        processed_prompts = []
        action_verbs = ["attaching", "connecting", "positioning", "securing", "inserting", "aligning", 
                       "fastening", "placing", "mounting", "joining", "assembling", "installing"]
        
        for i, prompt in enumerate(assembly_prompts):
            prompt_lower = prompt.lower()
            
            if i == 0:
                # First step: ensure it describes an action, not just setup
                if not any(verb in prompt_lower for verb in action_verbs):
                    # Add action verb if missing
                    if any(word in prompt_lower for word in ["position", "place", "set"]):
                        processed_prompts.append(f"Positioning and placing {prompt}")
                    else:
                        processed_prompts.append(f"Positioning {prompt}")
                else:
                    processed_prompts.append(prompt)
            else:
                # Subsequent steps: ensure they reference previous step and show action
                enhanced = prompt
                
                # Add continuity reference if missing
                if not any(phrase in prompt_lower for phrase in ["continuing", "previous", "previous step", "from step", "building on"]):
                    enhanced = f"Continuing from the previous step, {enhanced}"
                
                # Ensure action verb is present
                if not any(verb in enhanced.lower() for verb in action_verbs):
                    # Try to infer action from context or add generic action
                    if "add" in enhanced.lower() or "new" in enhanced.lower():
                        enhanced = enhanced.replace("add", "attaching").replace("adding", "attaching")
                    else:
                        enhanced = f"Attaching {enhanced}"
                
                processed_prompts.append(enhanced)
        
        assembly_prompts = processed_prompts
    except Exception as e:
        # Fallback to non-structured output if structured output fails
        print(f"⚠️  Structured output failed, falling back to text parsing: {e}")
        chain = prompt | llm
        response = chain.invoke({
            "construction_plan": construction_plan,
            "items_description": items_description,
            "final_image_context": final_image_context,
        })
        
        # Parse the response - it should be a JSON array of strings or numbered list
        import json
        import re
        content = response.content.strip()
        
        # Try to extract JSON array
        try:
            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            if "```json" in content:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            assembly_prompts = json.loads(content)
            if not isinstance(assembly_prompts, list):
                assembly_prompts = [str(assembly_prompts)]
        except json.JSONDecodeError:
            # Fallback: try to extract numbered list items
            lines = content.split("\n")
            assembly_prompts = []
            for line in lines:
                line = line.strip()
                # Match numbered items (1., 2., Step 1, etc.)
                if re.match(r'^\d+[\.\)]', line) or re.match(r'^Step \d+', line, re.IGNORECASE):
                    # Remove the number prefix
                    prompt_text = re.sub(r'^\d+[\.\)]\s*', '', line)
                    prompt_text = re.sub(r'^Step \d+[:\-]?\s*', '', prompt_text, flags=re.IGNORECASE)
                    if prompt_text:
                        assembly_prompts.append(prompt_text)
            
            if not assembly_prompts:
                # Last resort: split by double newlines or use whole response
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                assembly_prompts = paragraphs if paragraphs else [content]
    
    return {
        "assembly_manual_prompts": assembly_prompts,
    }


@observe(name="assembly_manual_generator")
def node_assembly_manual_generator(state: AgentState) -> Dict[str, Any]:
    """
    Assembly Manual Generator Node
    
    Receives assembly_manual_prompts and generates step-by-step images using FLUX 2.
    Each prompt generates one image showing that step of the assembly process.
    Uses consistent seed and enhanced prompts for better continuity.
    Updates assembly_manual_images in state.
    """
    from app.services.flux_service import generate_image
    import hashlib
    
    assembly_prompts = state.get("assembly_manual_prompts", [])
    if not assembly_prompts:
        return {
            "assembly_manual_images": [],
        }
    
    # Material image URL (same as used for product image)
    material_image_url = "https://www.thecontractchair.co.uk/media/re_branding/ck_uploads/from_tiny_editor/ash-wood-table-top%20(3).webp"
    
    # Generate a consistent seed based on the construction plan for visual consistency
    construction_plan = state.get("construction_plan", "")
    seed_hash = int(hashlib.md5(construction_plan.encode()).hexdigest()[:8], 16) % (2**31)
    base_seed = seed_hash  # Use same base seed for all steps
    
    # Get the final product image URL for visual consistency
    final_image_url = state.get("final_image_url")
    
    assembly_images = []
    previous_image_url = None
    previous_step_description = None
    
    # Generate images for each step
    for i, step_prompt in enumerate(assembly_prompts):
        print(f"📸 Generating assembly step {i+1}/{len(assembly_prompts)}...")
        
        # Enhance the prompt with explicit continuity instructions and action focus
        enhanced_prompt = step_prompt
        
        # Ensure action/movement is emphasized
        action_keywords = ["attaching", "connecting", "positioning", "securing", "inserting", "aligning", 
                          "fastening", "placing", "mounting", "joining", "hands", "tools", "movement"]
        
        # Check if prompt already emphasizes action
        has_action_focus = any(keyword in step_prompt.lower() for keyword in action_keywords)
        
        if not has_action_focus:
            # Add action emphasis
            if "position" in step_prompt.lower() or "place" in step_prompt.lower():
                enhanced_prompt = step_prompt.replace("position", "positioning").replace("place", "placing")
            elif "connect" in step_prompt.lower() or "attach" in step_prompt.lower():
                enhanced_prompt = step_prompt.replace("connect", "connecting").replace("attach", "attaching")
            else:
                # Add generic action context
                enhanced_prompt = f"Performing assembly action: {step_prompt}"
        
        # Add reference to final product image for visual consistency
        final_image_note = ""
        if final_image_url:
            if i == 0:
                final_image_note = f" Match the visual style, materials, colors, lighting, and aesthetic of the final product image (reference available). The assembly should progressively build toward that exact final appearance."
            else:
                final_image_note = f" Continue building toward the final product appearance. Match the visual style, materials, colors, and lighting of the final product image (reference available)."
        
        # For steps after the first, add explicit continuity instructions
        if i > 0 and previous_step_description:
            # Ensure the prompt explicitly references maintaining the previous state
            if "continuing from" not in enhanced_prompt.lower() and "previous step" not in enhanced_prompt.lower():
                enhanced_prompt = f"Continuing from the previous assembly step, {enhanced_prompt.lower()}"
            # Add consistency and action instructions
            enhanced_prompt += " Maintain the exact same lighting, camera angle, and visual style as the previous step. Keep all previously assembled components in their exact positions. Show the assembly action in progress with hands or tools visible."
        
        # Add consistency and action instructions for all steps
        if i == 0:
            # First step: establish the visual style with action focus
            enhanced_prompt += " Professional technical illustration showing assembly action in progress. Consistent lighting from the front-left, neutral background, clear focus on assembly components. Show hands positioning components or tools being used." + final_image_note
        else:
            # Subsequent steps: maintain consistency with action focus
            enhanced_prompt += " Maintain identical lighting, perspective, and visual style as previous steps. Show the assembly action being performed with hands or tools visible. Only add new components without changing existing ones." + final_image_note
        
        # Use a consistent seed with slight variation per step for reproducibility
        # Same base seed ensures similar style, slight variation prevents exact duplicates
        step_seed = (base_seed + i) % (2**31)
        
        # For the first step, generate from materials
        # For subsequent steps, use iterative editing with previous image
        image_url = generate_image(
            prompt=enhanced_prompt,
            material_image_url=material_image_url,
            previous_image_url=previous_image_url,
            width=1024,
            height=1024,
            seed=step_seed,
        )
        
        if image_url:
            assembly_images.append(image_url)
            previous_image_url = image_url  # Use this as the base for the next step
            # Store a brief description of this step for next iteration
            previous_step_description = step_prompt[:100]  # Store first 100 chars as reference
        else:
            print(f"⚠️  Failed to generate image for step {i+1}")
            # Continue with other steps even if one fails
    
    return {
        "assembly_manual_images": assembly_images,
    }

