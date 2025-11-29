"""LangChain tools for agent use."""
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.tools import create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.database import get_database


def get_inventory_retriever_tool():
    """
    Create a LangChain retriever tool for semantic search of the hardware inventory.
    
    Returns:
        A LangChain tool that can be used by agents to search the inventory.
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set. Required for vector search.")
    
    # Initialize embeddings (must match the embeddings used during seeding)
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
    
    # Get database connection
    db = get_database()
    collection = db.inventory
    
    # Initialize MongoDB Atlas Vector Search
    vector_search = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name="vector_index",  # This should match the index name in MongoDB Atlas
    )
    
    # Create retriever with proper configuration
    # The retriever will return Document objects with metadata containing the full document
    retriever = vector_search.as_retriever(
        search_kwargs={"k": 5}  # Return top 5 matches
    )
    
    # Create the retriever tool
    tool = create_retriever_tool(
        retriever=retriever,
        name="search_hardware_catalog",
        description="Search for available hardware parts by name, category, or physical description. "
        "Use this tool to find inventory items that match a description or requirement. "
        "Returns a list of matching items with their IDs, names, descriptions, and categories. "
        "Input should be a search query describing the part or material you need.",
    )
    
    return tool

