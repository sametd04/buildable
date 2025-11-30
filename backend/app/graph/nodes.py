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


@observe(name="style_optimizer")
def node_style_optimizer(state: AgentState) -> Dict[str, Any]:
    """
    Node 0: Style Optimizer
    
    Takes the raw user_query and expands it into a detailed visual/aesthetic description.
    Focuses on mood, texture, lighting, and overall vibe without listing specific parts.
    Updates style_description in state.
    """
    llm = get_llm()
    
    # Check if we have previous style description (for iterative edits)
    previous_style = state.get("style_description", "")
    
    # Get user query
    user_query = state.get("user_query")
    
    if previous_style:
        # Iterative edit - modify existing description
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Design Consultant. You are modifying an existing design based on new user feedback.
            
Previous design description:
{previous_style}

User's new request: {user_query}

Update the design description to incorporate the user's changes while maintaining the overall vision.
Focus on what changed (mood, texture, color, lighting, etc.)."""),
            ("human", "Update the design description based on my request."),
        ])
        
        response = llm.invoke(prompt.format_messages(
            previous_style=previous_style,
            user_query=state["user_query"]
        ))
    else:
        # Get user query
        user_query = state.get("user_query")
        
        prompt_variables = {
            "user_query": user_query,
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
    
    #loaded_prompt = load_prompt("inventory_clerk", prompt_variables)
    
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
    
    loaded_prompt = load_prompt("promt_engineer", prompt_variables)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a prompt engineer specializing in photorealistic image generation for FLUX API. Follow the instructions in the prompt carefully."),
        ("human", loaded_prompt if loaded_prompt else f"""Construction Plan:
{state.get("construction_plan", "")}

Selected Materials:
{items_description}

Generate an optimized FLUX prompt for a photorealistic hero shot of this construction project.
The image should showcase the final result in an impressive, professional manner."""),
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "construction_plan": state.get("construction_plan", ""),
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
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a technical writer specializing in creating step-by-step assembly instructions.
        Your task is to analyze a construction plan and break it down into clear, sequential assembly steps.
        For each step, generate a detailed visual prompt that describes the ASSEMBLY ACTION being performed.
        
        CRITICAL: Each step must show the ACTION/MOVEMENT, not just the static result!
        
        ASSEMBLY ACTION REQUIREMENTS:
        - Each prompt must describe the SPECIFIC ACTION being performed (attaching, connecting, positioning, securing, inserting, etc.)
        - Show the MOVEMENT or PROCESS, not just the final state
        - Include visual cues: hands positioning components, tools being used, components being moved into place
        - Describe the action in progress: "attaching X to Y", "positioning Z", "connecting A to B"
        - Show components in the process of being assembled, not just fully assembled
        
        CRITICAL CONSISTENCY REQUIREMENTS:
        - Each prompt must explicitly reference what was built in previous steps
        - Maintain consistent lighting, camera angle, and visual style across all steps
        - Use consistent terminology for materials and parts throughout
        - Each step should build logically on the previous one
        
        PROMPT STRUCTURE:
        - Step 1: Describe the initial ACTION (e.g., "Positioning [components] on [surface]...")
        - Step 2+: Start with "Continuing from the previous step, now [ACTION] [components] to [location]..."
        - Always use ACTION VERBS: attaching, connecting, positioning, securing, inserting, aligning, fastening, etc.
        - Include visual elements: hands, tools, movement indicators, components in motion
        - Show the assembly process, not just the completed state
        - Maintain the same visual perspective and lighting conditions
        
        The prompts should:
        - Focus on the ACTION being performed (use action verbs)
        - Show components being moved/positioned/attached (not just final positions)
        - Include visual cues for the assembly process (hands, tools, movement)
        - Explicitly reference the previous step's state for continuity
        - Be optimized for photorealistic technical illustration
        - Use consistent material names and descriptions
        - Be concise but detailed (aim for 70-130 words per step)
        - Describe the ASSEMBLY PROCESS, not just the result
        
        Break down the construction plan into 4-8 clear sequential steps.
        Each step should show a specific assembly action being performed."""),
        ("human", """Construction Plan:
{construction_plan}

Selected Materials:
{items_description}

Generate step-by-step assembly prompts that show ASSEMBLY ACTIONS and MOVEMENTS. Break down the construction plan into clear sequential steps.
Each prompt must:
1. Describe the SPECIFIC ACTION being performed (attaching, connecting, positioning, securing, etc.)
2. Show the MOVEMENT/PROCESS, not just the static result
3. Include visual cues: hands positioning components, tools, components being moved
4. For step 2+: Explicitly reference what was built in the previous step, then describe the action to perform
5. Use consistent material names and terminology throughout
6. Maintain the same visual style, lighting, and perspective
7. Focus on the ASSEMBLY ACTION, not just what the structure looks like

Example format:
Step 1: "Positioning [base components] on [surface], aligning them [details], hands visible placing components..."
Step 2: "Continuing from step 1, now attaching [new components] to [location] by [method], hands connecting [details], showing the fastening process..."
Step 3: "Building on step 2, securing [components] to [location] using [method], showing the connection being made, tools visible..."
Step 4: "Aligning and positioning [components] onto the structure from step 3, hands adjusting placement, showing the alignment process...""
"""),
    ])
    
    # Use structured output for reliable parsing
    try:
        structured_llm = llm.with_structured_output(AssemblyManualOutput)
        chain = prompt | structured_llm
        result = chain.invoke({
            "construction_plan": construction_plan,
            "items_description": items_description,
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
            enhanced_prompt += " Professional technical illustration showing assembly action in progress. Consistent lighting from the front-left, neutral background, clear focus on assembly components. Show hands positioning components or tools being used."
        else:
            # Subsequent steps: maintain consistency with action focus
            enhanced_prompt += " Maintain identical lighting, perspective, and visual style as previous steps. Show the assembly action being performed with hands or tools visible. Only add new components without changing existing ones."
        
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

