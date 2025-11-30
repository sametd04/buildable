"""API routes for triggering graph execution."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.schemas import (
    BuildRequest, 
    BuildResponse, 
    FluxTestRequest, 
    FluxTestResponse,
    GenerateAssemblyManualRequest,
    GenerateAssemblyManualResponse,
)
from app.core.database import get_inventory, get_inventory_item_by_id
from app.core.config import settings
from app.graph.workflow import get_workflow
from app.graph.state import AgentState
from app.graph.nodes import (
    node_assembly_manual_prompt_engineer,
    node_assembly_manual_generator,
)
from app.services.flux_service import generate_image
from langfuse import observe
import traceback
import json
import asyncio
from typing import AsyncGenerator


router = APIRouter(prefix="/api/v1", tags=["build"])


@router.get("/inventory")
async def get_all_inventory():
    """
    GET /inventory endpoint.
    
    Returns all inventory items from MongoDB.
    """
    try:
        items = get_inventory()
        return {"success": True, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch inventory: {str(e)}")


@router.delete("/inventory/{item_id}")
async def delete_inventory_item(item_id: str):
    """
    DELETE /inventory/{item_id} endpoint.
    
    Deletes an inventory item from MongoDB.
    """
    try:
        from app.core.database import get_database
        db = get_database()
        collection = db.inventory
        
        # Try to delete by 'id' field first
        result = collection.delete_one({"id": item_id})
        
        # If not found, try by _id (ObjectId)
        if result.deleted_count == 0:
            from bson import ObjectId
            try:
                result = collection.delete_one({"_id": ObjectId(item_id)})
            except Exception:
                pass
        
        if result.deleted_count > 0:
            return {"success": True, "message": f"Item {item_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")


async def stream_conversation_response(
    request: BuildRequest
) -> AsyncGenerator[str, None]:
    """
    Stream conversation agent responses as they are generated.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field
    
    # Define the required data schema (same as in nodes.py)
    class RequiredData(BaseModel):
        """Schema for the information that must be gathered before proceeding to workflow."""
        use_case: str = Field(description="What the item will be used for (e.g., workspace, storage, decoration)")
        dimensions: str = Field(description="Approximate size requirements or constraints (e.g., 'fits in a corner', 'desk height')")
        style_preferences: str = Field(description="Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)")
        material_preferences: str = Field(default="", description="Any specific material preferences or constraints. Leave empty if no preference.")
        personalization: str = Field(default="", description="Any personal touches or specific requirements. Leave empty if none.")
        constraints: str = Field(default="", description="Any space, budget, or functional constraints. Leave empty if none.")
    
    if not settings.openai_api_key:
        yield f"data: {json.dumps({'type': 'error', 'error': 'OpenAI API key not set'})}\n\n"
        return
    
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        streaming=True,  # Enable streaming
    )
    
    # Get conversation history
    conversation_history = request.conversation_history or []
    user_query = request.user_query
    skip_conversation = request.skip_conversation
    
    if skip_conversation:
        yield f"data: {json.dumps({'type': 'skip', 'ready_for_workflow': True})}\n\n"
        return
    
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
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    # Bind the RequiredData as a tool
    llm_with_tool = llm.bind_tools([RequiredData])
    
    # Stream the response
    full_content = ""
    has_tool_call = False
    conversation_data = {}
    all_chunks = []
    
    try:
        async for chunk in llm_with_tool.astream(messages):
            all_chunks.append(chunk)
            # Handle content chunks - content might be string or empty
            chunk_content = ""
            if hasattr(chunk, "content"):
                if isinstance(chunk.content, str):
                    chunk_content = chunk.content
                elif chunk.content:
                    # Content might be a list or other type
                    chunk_content = str(chunk.content)
            
            if chunk_content:
                full_content += chunk_content
                # Send chunk to client
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_content})}\n\n"
        
        # After streaming is complete, reconstruct the full message to get content and check for tool calls
        # VALIDATION: Reject tool calls if this is the first message (no conversation history)
        # The agent MUST ask at least one question before calling the tool
        is_first_message = len(conversation_history) == 0
        
        # Reconstruct the full message from chunks to get complete content and tool calls
        from langchain_core.messages import AIMessage
        reconstructed_message = None
        
        if all_chunks:
            try:
                # Start with the first chunk
                reconstructed_message = all_chunks[0]
                # Merge subsequent chunks
                for chunk in all_chunks[1:]:
                    if hasattr(reconstructed_message, "merge"):
                        try:
                            reconstructed_message = reconstructed_message.merge(chunk)
                        except:
                            # If merge fails, manually combine content
                            if hasattr(chunk, "content") and chunk.content:
                                if hasattr(reconstructed_message, "content"):
                                    if isinstance(reconstructed_message.content, str):
                                        reconstructed_message.content += (chunk.content if isinstance(chunk.content, str) else str(chunk.content))
                                    elif isinstance(reconstructed_message.content, list):
                                        if isinstance(chunk.content, list):
                                            reconstructed_message.content.extend(chunk.content)
                                        else:
                                            reconstructed_message.content.append(chunk.content)
            except Exception as e:
                # If reconstruction fails, we'll use the accumulated full_content
                pass
        
        # Extract content from reconstructed message if we didn't get it from chunks
        # This is important because when tool calls are made, content might not stream properly
        if not full_content and reconstructed_message:
            if hasattr(reconstructed_message, "content"):
                if isinstance(reconstructed_message.content, str):
                    full_content = reconstructed_message.content
                elif isinstance(reconstructed_message.content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for item in reconstructed_message.content:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    full_content = "".join(text_parts)
        
        # Check for tool calls in reconstructed message or chunks
        # CRITICAL: If this is the first message, we MUST reject any tool calls
        found_tool_call_in_message = False
        if reconstructed_message and hasattr(reconstructed_message, "tool_calls") and reconstructed_message.tool_calls:
            found_tool_call_in_message = True
            for tool_call in reconstructed_message.tool_calls:
                if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                    # Reject tool call if this is the first message - agent must ask questions first
                    if is_first_message:
                        # Don't accept the tool call - force the agent to ask questions
                        has_tool_call = False
                        break
                    
                    # Only accept tool call if NOT first message
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
                    break
        
        # Also check chunks as fallback (only if we didn't find one in reconstructed message)
        if not found_tool_call_in_message or (found_tool_call_in_message and is_first_message):
            for chunk in reversed(all_chunks):
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                            # Reject tool call if this is the first message - agent must ask questions first
                            if is_first_message:
                                # Don't accept the tool call - force the agent to ask questions
                                has_tool_call = False
                                break
                            
                            # Only accept tool call if NOT first message
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
                            break
                    if has_tool_call or (is_first_message and hasattr(chunk, "tool_calls")):
                        break
        
        # IMPORTANT: If we rejected a tool call on first message, we still need to return the content
        # The content should have been streamed, but if not, try to get it from reconstructed message
        # Also, if content is still empty, make a non-streaming call to get the full response
        if not full_content and reconstructed_message:
            # Try one more time to extract content
            if hasattr(reconstructed_message, "content"):
                if isinstance(reconstructed_message.content, str) and reconstructed_message.content:
                    full_content = reconstructed_message.content
                elif isinstance(reconstructed_message.content, list):
                    text_parts = []
                    for item in reconstructed_message.content:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    full_content = "".join(text_parts)
        
        # If we still don't have content and this is the first message, make a non-streaming call
        # This is a fallback to ensure we get the content even if streaming didn't capture it
        if not full_content and is_first_message:
            try:
                # Make a non-streaming call to get the full response
                response = llm_with_tool.invoke(messages)
                if hasattr(response, "content") and response.content:
                    if isinstance(response.content, str):
                        full_content = response.content
                    elif isinstance(response.content, list):
                        text_parts = []
                        for item in response.content:
                            if isinstance(item, dict) and "text" in item:
                                text_parts.append(item["text"])
                            elif isinstance(item, str):
                                text_parts.append(item)
                        full_content = "".join(text_parts)
                    
                    # If we got content from the fallback, send it as a chunk
                    if full_content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': full_content})}\n\n"
            except Exception as e:
                # If fallback fails, continue with empty content
                pass
        
        # Send final message
        # CRITICAL: On first message, ALWAYS return ready_for_workflow: False (agent must ask questions first)
        if is_first_message:
            # First message - always stay in conversation, even if tool call was attempted
            yield f"data: {json.dumps({'type': 'complete', 'content': full_content, 'ready_for_workflow': False})}\n\n"
        elif has_tool_call:
            # Not first message and we have a valid tool call - proceed to workflow
            yield f"data: {json.dumps({'type': 'complete', 'content': full_content, 'ready_for_workflow': True, 'conversation_data': conversation_data})}\n\n"
        else:
            # No tool call - stay in conversation
            yield f"data: {json.dumps({'type': 'complete', 'content': full_content, 'ready_for_workflow': False})}\n\n"
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'trace': error_trace})}\n\n"


@router.post("/build/stream")
async def build_stream(request: BuildRequest):
    """
    POST /build/stream endpoint.
    
    Streams conversation agent responses as they are generated.
    Uses Server-Sent Events (SSE) for real-time updates.
    """
    return StreamingResponse(
        stream_conversation_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/build", response_model=BuildResponse)
@observe(name="build_endpoint")
async def build(request: BuildRequest) -> BuildResponse:
    """
    POST /build endpoint.
    
    Initializes the Graph with user_query (inventory is accessed via vector search),
    and returns the final state (Plan, Selected Items, and Image URL).
    """
    try:
        # Initialize state (no need to load inventory into memory)
        # If skip_conversation is True and user_query is empty, use a default
        user_query = request.user_query.strip() if request.user_query else ""
        if request.skip_conversation and not user_query:
            user_query = "Generate a design based on available materials"
        
        initial_state: AgentState = {
            "user_query": user_query,
            "conversation_history": request.conversation_history or [],
            "conversation_data": request.conversation_data or {},
            "skip_conversation": request.skip_conversation,
            "ready_for_workflow": request.skip_conversation,  # If skipping, we're ready
            "style_description": request.previous_style_description or "",  # Use previous or empty
            "construction_plan": None,
            "selected_item_ids": [],
            "flux_prompt": None,
            "final_image_url": None,
            "assembly_manual_prompts": [],
            "assembly_manual_images": [],
            "retry_count": 0,
            "clerk_feedback": None,
            "status": "conversation" if not request.skip_conversation else "processing",
            "is_clerk_successful": False,
        }
        
        # Get workflow and execute with Langfuse callback if configured
        workflow = get_workflow()
        
        # Add Langfuse callback handler for LangGraph tracing
        config = {}
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            from langfuse.langchain import CallbackHandler
            # Explicitly pass credentials to CallbackHandler
            # Try base_url first, fallback to host if that doesn't work
            import os
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url
            """
            try:
                langfuse_handler = CallbackHandler(
                    public_key=settings.langfuse_public_key,
                    # secret_key=settings.langfuse_secret_key,
                    # base_url=settings.langfuse_base_url,
                )
            except TypeError:
                # If base_url doesn't work, try host parameter
                langfuse_handler = CallbackHandler(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    base_url=settings.langfuse_base_url,
                )"""
            langfuse_handler = CallbackHandler()
            config["callbacks"] = [langfuse_handler]
        
        final_state = workflow.invoke(initial_state, config=config if config else None)
        
        # Check status
        status = final_state.get("status", "processing")
        
        # If still in conversation, return conversation state
        if status == "conversation":
            return BuildResponse(
                success=True,
                user_query=final_state["user_query"],
                status="conversation",
                conversation_history=final_state.get("conversation_history", []),
                conversation_data=final_state.get("conversation_data", {}),
                ready_for_workflow=final_state.get("ready_for_workflow", False),
                style_description=None,
                construction_plan=None,
                selected_item_ids=[],
                selected_items=[],
                flux_prompt=None,
                final_image_url=None,
                assembly_manual_prompts=[],
                assembly_manual_images=[],
            )
        
        # Check if the workflow failed due to missing parts
        if status == "failed_no_parts" or (not final_state.get("is_clerk_successful", False) and final_state.get("retry_count", 0) >= 3):
            return BuildResponse(
                success=False,
                user_query=final_state["user_query"],
                status="failed_no_parts",
                conversation_history=final_state.get("conversation_history", []),
                conversation_data=final_state.get("conversation_data", {}),
                ready_for_workflow=False,
                construction_plan=final_state.get("construction_plan"),
                selected_item_ids=[],
                selected_items=[],
                flux_prompt=None,
                final_image_url=None,
                assembly_manual_prompts=[],
                assembly_manual_images=[],
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
            status="success",
            conversation_history=final_state.get("conversation_history", []),
            conversation_data=final_state.get("conversation_data", {}),
            ready_for_workflow=True,
            style_description=final_state.get("style_description"),
            construction_plan=final_state.get("construction_plan"),
            selected_item_ids=final_state.get("selected_item_ids", []),
            selected_items=selected_items,
            flux_prompt=final_state.get("flux_prompt"),
            final_image_url=final_state.get("final_image_url"),
            assembly_manual_prompts=[],  # Assembly manual not generated in workflow
            assembly_manual_images=[],  # Assembly manual not generated in workflow
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



@router.post("/test-flux", response_model=FluxTestResponse)
async def test_flux(request: FluxTestRequest) -> FluxTestResponse:
    """
    POST /test-flux endpoint.
    
    Test the FLUX image generation service directly with custom parameters.
    Useful for debugging and testing the FLUX API integration.
    
    Supports two modes:
    1. Initial generation: Only provide prompt and material_image_url
    2. Iterative editing: Also provide previous_image_url to edit an existing image
    """
    try:
        image_url = generate_image(
            prompt=request.prompt,
            material_image_url=request.material_image_url,
            previous_image_url=request.previous_image_url,
            width=request.width,
            height=request.height,
            seed=request.seed,
        )
        
        if image_url:
            return FluxTestResponse(
                success=True,
                image_url=image_url,
            )
        else:
            return FluxTestResponse(
                success=False,
                error="Image generation failed. Check server logs for details.",
            )
            
    except Exception as e:
        error_trace = traceback.format_exc()
        return FluxTestResponse(
            success=False,
            error=f"FLUX test failed: {str(e)}\n\nTraceback:\n{error_trace}",
        )


@router.post("/generate-assembly-manual", response_model=GenerateAssemblyManualResponse)
@observe(name="generate_assembly_manual_endpoint")
async def generate_assembly_manual(request: GenerateAssemblyManualRequest) -> GenerateAssemblyManualResponse:
    """
    POST /generate-assembly-manual endpoint.
    
    Generates an assembly manual for a confirmed product design.
    This endpoint is called after the user confirms they're happy with the final product image.
    
    Takes the construction plan and selected item IDs, then generates step-by-step
    assembly instructions with images.
    """
    try:
        # Create a minimal state with only the data needed for assembly manual generation
        state: AgentState = {
            "user_query": "",  # Not needed for assembly manual
            "style_description": "",  # Not needed for assembly manual
            "construction_plan": request.construction_plan,
            "selected_item_ids": request.selected_item_ids,
            "flux_prompt": None,  # Not needed for assembly manual
            "final_image_url": request.final_image_url,  # Use confirmed product image for consistency
            "assembly_manual_prompts": [],
            "assembly_manual_images": [],
            "retry_count": 0,
            "clerk_feedback": None,
            "status": "processing",
            "is_clerk_successful": True,  # Assume success since items were already selected
        }
        
        # Generate assembly manual prompts
        prompt_state = node_assembly_manual_prompt_engineer(state)
        state.update(prompt_state)
        
        # Generate assembly manual images
        image_state = node_assembly_manual_generator(state)
        state.update(image_state)
        
        return GenerateAssemblyManualResponse(
            success=True,
            assembly_manual_prompts=state.get("assembly_manual_prompts", []),
            assembly_manual_images=state.get("assembly_manual_images", []),
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        return GenerateAssemblyManualResponse(
            success=False,
            assembly_manual_prompts=[],
            assembly_manual_images=[],
            error=f"Assembly manual generation failed: {str(e)}\n\nTraceback:\n{error_trace}",
        )
