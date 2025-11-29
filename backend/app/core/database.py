"""Database helper to load inventory.json."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from app.core.config import settings


def load_inventory() -> List[Dict[str, Any]]:
    """
    Load inventory data from inventory.json file.
    
    Returns:
        List of inventory items as dictionaries.
        
    Raises:
        FileNotFoundError: If inventory.json doesn't exist.
        json.JSONDecodeError: If inventory.json is invalid JSON.
    """
    # Get the project root (assuming this file is in app/core/)
    project_root = Path(__file__).parent.parent.parent
    inventory_path = project_root / settings.inventory_path
    
    if not inventory_path.exists():
        raise FileNotFoundError(
            f"Inventory file not found at {inventory_path}. "
            "Please ensure data/inventory.json exists."
        )
    
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory_data = json.load(f)
    
    # Ensure it's a list
    if not isinstance(inventory_data, list):
        raise ValueError("Inventory data must be a list of items.")
    
    return inventory_data


def get_inventory_item_by_id(item_id: str) -> Dict[str, Any] | None:
    """
    Get a specific inventory item by its ID.
    
    Args:
        item_id: The ID of the item to retrieve.
        
    Returns:
        The item dictionary if found, None otherwise.
    """
    inventory = load_inventory()
    for item in inventory:
        if item.get("id") == item_id:
            return item
    return None

