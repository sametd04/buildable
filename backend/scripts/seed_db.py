"""Standalone script to populate MongoDB with inventory data from inventory.json."""
import json
import sys
from pathlib import Path
from pymongo import MongoClient
from bson import ObjectId
from app.core.config import settings


def seed_database():
    """
    Load inventory.json and populate MongoDB inventory collection.
    
    Clears the current inventory collection and inserts items from JSON.
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
    
    # Prepare items for insertion
    # Ensure each item has an 'id' field (will be stored as-is)
    # MongoDB will also create _id automatically
    items_to_insert = []
    for item in inventory_data:
        # Create a copy to avoid mutating original
        item_copy = dict(item)
        # Keep the 'id' field if it exists, MongoDB will also add _id
        items_to_insert.append(item_copy)
    
    # Insert items
    print(f"Inserting {len(items_to_insert)} items...")
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
            print(f"  - {item.get('name', 'Unknown')} (id: {item.get('id', 'N/A')}, _id: {item.get('_id')})")
        
    except Exception as e:
        print(f"Error inserting items: {str(e)}")
        sys.exit(1)
    
    print("\nDatabase seeding completed successfully!")
    client.close()


if __name__ == "__main__":
    seed_database()

