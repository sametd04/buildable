"""Database helper for MongoDB connection and inventory operations."""
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId
from app.core.config import settings


# Singleton MongoDB client
_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_database() -> Database:
    """
    Get or create a MongoDB database connection (singleton pattern).
    
    Returns:
        MongoDB Database instance.
        
    Raises:
        ConnectionError: If unable to connect to MongoDB.
    """
    global _client, _database
    
    if _database is not None:
        return _database
    
    try:
        _client = MongoClient(settings.mongo_uri)
        _database = _client[settings.mongo_db_name]
        # Test the connection
        _client.admin.command('ping')
        return _database
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")


def close_database_connection():
    """Close the MongoDB connection."""
    global _client, _database
    if _client is not None:
        _client.close()
        _client = None
        _database = None


def _convert_objectid_to_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB's _id (ObjectId) to string 'id' for JSON serialization.
    
    Preserves existing 'id' field if present, otherwise uses _id.
    
    Args:
        doc: MongoDB document with _id field.
        
    Returns:
        Document with 'id' as string (preserves existing 'id' if present).
    """
    if doc is None:
        return None
    
    # Create a copy to avoid mutating the original
    result = dict(doc)
    
    # Remove _id (ObjectId is not JSON serializable)
    if "_id" in result:
        # Only set 'id' from _id if 'id' doesn't already exist
        if "id" not in result:
            result["id"] = str(result["_id"])
        del result["_id"]
    
    return result


def get_inventory() -> List[Dict[str, Any]]:
    """
    Fetch all inventory items from MongoDB.
    
    Converts MongoDB's _id (ObjectId) to string 'id' for JSON serialization
    and Pydantic compatibility.
    
    Returns:
        List of inventory items as dictionaries with 'id' as string.
        
    Raises:
        ConnectionError: If unable to connect to MongoDB.
    """
    db = get_database()
    collection = db.inventory
    
    # Fetch all items
    items = list(collection.find({}))
    
    # Convert _id to id for each item
    return [_convert_objectid_to_id(item) for item in items]


def get_inventory_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific inventory item by its ID.
    
    Supports both MongoDB ObjectId and string ID lookups.
    
    Args:
        item_id: The ID of the item to retrieve (string or ObjectId).
        
    Returns:
        The item dictionary if found, None otherwise.
    """
    db = get_database()
    collection = db.inventory
    
    # Try to find by 'id' field first (if items have been seeded with id)
    item = collection.find_one({"id": item_id})
    if item:
        return _convert_objectid_to_id(item)
    
    # Try to find by _id (ObjectId)
    try:
        item = collection.find_one({"_id": ObjectId(item_id)})
        if item:
            return _convert_objectid_to_id(item)
    except Exception:
        pass
    
    return None

