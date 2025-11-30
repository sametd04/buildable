"""
Slot-Filling Conversation System using LangGraph.

This module implements a stateful conversation system where an agent gathers
required information through conversation before proceeding to the workflow.
"""
from typing import TypedDict, List, Literal, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, MemorySaver
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from app.core.config import settings


# Define the required data schema
class RequiredData(BaseModel):
    """Schema for the information that must be gathered before proceeding to workflow."""
    
    use_case: str = Field(
        description="What the item will be used for (e.g., workspace, storage, decoration)"
    )
    dimensions: str = Field(
        description="Approximate size requirements or constraints (e.g., 'fits in a corner', 'desk height')"
    )
    style_preferences: str = Field(
        description="Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)"
    )
    material_preferences: str = Field(
        default="",
        description="Any specific material preferences or constraints (e.g., wood type, metal finish). Leave empty if no preference."
    )
    personalization: str = Field(
        default="",
        description="Any personal touches or specific requirements (e.g., 'needs to match my existing furniture'). Leave empty if none."
    )
    constraints: str = Field(
        default="",
        description="Any space, budget, or functional constraints. Leave empty if none."
    )


# Define the state
class ConversationState(TypedDict):
    """State for the conversation slot-filling system."""
    messages: Annotated[List[BaseMessage], "add_messages"]
    user_query: str  # Original user query
    conversation_data: dict  # Extracted data when ready
    ready_for_workflow: bool  # Whether we have all required data


def get_conversation_llm():
    """Get the LLM instance for conversation."""
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not set. Set OPENAI_API_KEY in .env")
    
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )
    
    # Bind the RequiredData as a tool
    required_data_tool = RequiredData
    llm_with_tool = llm.bind_tools([required_data_tool])
    
    return llm_with_tool


def interviewer_node(state: ConversationState) -> ConversationState:
    """
    The Interviewer Node.
    
    Uses ChatOpenAI with RequiredData bound as a tool.
    Asks follow-up questions until it can populate the tool.
    """
    llm = get_conversation_llm()
    
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    
    # If this is the first message, add system prompt
    if len(messages) == 0:
        system_prompt = SystemMessage(content=f"""You are a friendly and helpful design consultant helping users create custom DIY furniture and structures.

Your goal is to have a natural conversation to gather the following information:
1. **Use Case & Purpose**: What will this be used for? (e.g., workspace, storage, decoration)
2. **Dimensions & Size**: Approximate size requirements (e.g., "fits in a corner", "desk height", "shelf width")
3. **Style Preferences**: Aesthetic style, mood, colors, textures (e.g., industrial, minimalist, rustic, modern)
4. **Material Preferences**: Any specific material preferences or constraints (e.g., wood type, metal finish) - optional
5. **Personalization**: Any personal touches or specific requirements (e.g., "needs to match my existing furniture") - optional
6. **Constraints**: Any space, budget, or functional constraints - optional

Keep the conversation natural and friendly. Ask 1-2 questions at a time. Don't be overwhelming.

IMPORTANT: Once you have gathered enough information to fill in the required fields (use_case, dimensions, style_preferences), you should call the RequiredData tool with the information you've collected. The material_preferences, personalization, and constraints fields are optional and can be left empty if not mentioned.

User's initial request: {user_query}

Start the conversation by asking 1-2 clarifying questions to better understand their needs.""")
        messages = [system_prompt]
    
    # Add the latest user message if it's not already in messages
    if user_query and (not messages or not isinstance(messages[-1], HumanMessage)):
        messages.append(HumanMessage(content=user_query))
    
    # Get response from LLM
    response = llm.invoke(messages)
    
    # Add the AI response to messages
    messages.append(response)
    
    return {
        "messages": messages,
        "user_query": user_query,
    }


def router(state: ConversationState) -> Literal["workflow", "end"]:
    """
    Router function.
    
    Checks if the last AI message contains a tool call for RequiredData.
    If yes, route to workflow. If no, route to END (await new user input).
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    # Check if the last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check if any tool call is for RequiredData
        for tool_call in last_message.tool_calls:
            if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                return "workflow"
    
    return "end"


def workflow_node(state: ConversationState) -> ConversationState:
    """
    The Workflow Node.
    
    Executes only when the data is ready.
    Extracts the tool arguments from the last message and processes them.
    """
    messages = state.get("messages", [])
    
    if not messages:
        return {
            "ready_for_workflow": False,
            "conversation_data": {},
        }
    
    last_message = messages[-1]
    
    # Extract tool call arguments
    conversation_data = {}
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get("name") == "RequiredData" or "RequiredData" in str(tool_call):
                args = tool_call.get("args", {})
                conversation_data = args
                break
    
    # Convert to the format expected by the rest of the system
    # Map the fields to match our existing conversation_data structure
    formatted_data = {
        "use_case": conversation_data.get("use_case", ""),
        "dimensions": conversation_data.get("dimensions", ""),
        "style_preferences": conversation_data.get("style_preferences", ""),
        "material_preferences": conversation_data.get("material_preferences", ""),
        "personalization": conversation_data.get("personalization", ""),
        "constraints": conversation_data.get("constraints", ""),
    }
    
    # Add confirmation message
    confirmation = AIMessage(content="Great! I have enough information to create your design. Let me proceed with generating it...")
    messages.append(confirmation)
    
    return {
        "messages": messages,
        "conversation_data": formatted_data,
        "ready_for_workflow": True,
    }


def create_conversation_graph() -> StateGraph:
    """
    Create and compile the conversation slot-filling graph.
    """
    # Create the graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("workflow", workflow_node)
    
    # Set entry point
    workflow.set_entry_point("interviewer")
    
    # Add conditional edge from interviewer
    workflow.add_conditional_edges(
        "interviewer",
        router,
        {
            "workflow": "workflow",
            "end": END,
        }
    )
    
    # Workflow node goes to END
    workflow.add_edge("workflow", END)
    
    # Compile with MemorySaver for persistence
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


# For testing
if __name__ == "__main__":
    import uuid
    
    graph = create_conversation_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    print("=" * 60)
    print("Design Consultant - Slot Filling Conversation")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the conversation.\n")
    
    # Get initial user query
    initial_query = input("What would you like to build? ")
    if initial_query.lower() in ["quit", "exit"]:
        print("Goodbye!")
        exit(0)
    
    # Initial state
    initial_state = {
        "messages": [],
        "user_query": initial_query,
        "conversation_data": {},
        "ready_for_workflow": False,
    }
    
    # Run the graph
    result = graph.invoke(initial_state, config=config)
    
    # Print the first response
    if result.get("messages"):
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            print(f"\nAssistant: {last_message.content}\n")
    
    # Continue conversation loop
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break
        
        # Update state with new user message
        current_state = graph.get_state(config)
        current_messages = current_state.values.get("messages", [])
        current_messages.append(HumanMessage(content=user_input))
        
        new_state = {
            "messages": current_messages,
            "user_query": initial_query,  # Keep original query
            "conversation_data": current_state.values.get("conversation_data", {}),
            "ready_for_workflow": current_state.values.get("ready_for_workflow", False),
        }
        
        # Continue the graph
        result = graph.invoke(new_state, config=config)
        
        # Print response
        if result.get("messages"):
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(f"\nAssistant: {last_message.content}\n")
            
            # Check if we're ready for workflow
            if result.get("ready_for_workflow"):
                print("\n" + "=" * 60)
                print("READY FOR WORKFLOW!")
                print("=" * 60)
                print("Gathered Data:")
                for key, value in result.get("conversation_data", {}).items():
                    if value:
                        print(f"  {key}: {value}")
                print("=" * 60 + "\n")
                break


