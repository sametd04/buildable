"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class BuildRequest(BaseModel):
    """Request schema for the /build endpoint."""
    user_query: str = Field(
        ...,
        description="The user's vague idea or request (e.g., 'Cyberpunk Throne')",
        min_length=1,
        max_length=500,
    )


class BuildResponse(BaseModel):
    """Response schema for the /build endpoint."""
    success: bool = Field(..., description="Whether the build was successful")
    user_query: str = Field(..., description="The original user query")
    construction_plan: Optional[str] = Field(None, description="The generated construction plan")
    selected_item_ids: List[str] = Field(default_factory=list, description="IDs of selected inventory items")
    selected_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full details of selected inventory items"
    )
    flux_prompt: Optional[str] = Field(None, description="The optimized FLUX prompt")
    final_image_url: Optional[str] = Field(None, description="URL of the generated image")
    error: Optional[str] = Field(None, description="Error message if build failed")

