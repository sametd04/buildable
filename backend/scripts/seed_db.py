"""Standalone script to populate MongoDB with inventory data from inventory.json."""
import json
import sys
from pathlib import Path

# Add the backend directory to Python path so we can import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from pymongo import MongoClient
from bson import ObjectId
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings


def seed_database():
    """
    Load inventory.json and populate MongoDB inventory collection with embeddings.
    
    Clears the current inventory collection and inserts items from JSON with vector embeddings.
    """
    # Get the project root
    project_root = Path(__file__).parent.parent
    inventory_path = project_root / settings.inventory_path
    
    if not inventory_path.exists():
        print(f"Error: Inventory file not found at {inventory_path}")
        sys.exit(1)
    
    # Load JSON data
    print(f"Loading inventory from {inventory_path}...")
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory_data = json.load(f)
    
    if not isinstance(inventory_data, list):
        print("Error: Inventory data must be a list of items.")
        sys.exit(1)
    
    # Initialize OpenAI embeddings
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set. Required for generating embeddings.")
        sys.exit(1)
    
    print("Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key,model=settings.embedding_model)
    
    # Connect to MongoDB
    print(f"Connecting to MongoDB at {settings.mongo_uri}...")
    try:
        client = MongoClient(settings.mongo_uri)
        db = client[settings.mongo_db_name]
        collection = db.inventory
        
        # Test connection
        client.admin.command('ping')
        print(f"Connected to database: {settings.mongo_db_name}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        sys.exit(1)
    
    # Clear existing inventory
    print("Clearing existing inventory collection...")
    result = collection.delete_many({})
    print(f"Deleted {result.deleted_count} existing items.")
    
    # Prepare items for insertion with embeddings
    print(f"Generating embeddings for {len(inventory_data)} items...")
    items_to_insert = []
    
    for i, item in enumerate(inventory_data):
        # Create a copy to avoid mutating original
        item_copy = dict(item)
        
        # Create text representation for embedding
        text_to_embed = f"{item.get('name', '')} - {item.get('description', '')} - {item.get('category', '')}"
        
        # Store the text field (required by MongoDBAtlasVectorSearch)
        item_copy["text"] = text_to_embed
        
        # Generate embedding
        try:
            embedding = embeddings.embed_query(text_to_embed)
            item_copy["embedding"] = embedding
            items_to_insert.append(item_copy)
            
            if (i + 1) % 5 == 0:
                print(f"  Processed {i + 1}/{len(inventory_data)} items...")
        except Exception as e:
            print(f"  Warning: Failed to generate embedding for item {item.get('id', 'unknown')}: {str(e)}")
            # Insert without embedding (not ideal, but allows seeding to continue)
            items_to_insert.append(item_copy)
    
    print(f"Generated embeddings for {len(items_to_insert)} items.")
    
    # Insert items
    print(f"Inserting {len(items_to_insert)} items into MongoDB...")
    try:
        result = collection.insert_many(items_to_insert)
        print(f"Successfully inserted {len(result.inserted_ids)} items.")
        
        # Verify insertion
        count = collection.count_documents({})
        print(f"Total items in database: {count}")
        
        # Show sample items
        sample = list(collection.find().limit(3))
        print("\nSample items:")
        for item in sample:
            has_embedding = "embedding" in item and len(item.get("embedding", [])) > 0
            print(f"  - {item.get('name', 'Unknown')} (id: {item.get('id', 'N/A')}, embedding: {has_embedding})")
        
        print("\nâ ï¸  IMPORTANT: Make sure to create a vector search index in MongoDB Atlas!")
        print("   See the comment in app/core/database.py for the index schema.")
        
    except Exception as e:
        print(f"Error inserting items: {str(e)}")
        sys.exit(1)
    
    print("\nDatabase seeding completed successfully!")
    client.close()


if __name__ == "__main__":
    seed_database()

