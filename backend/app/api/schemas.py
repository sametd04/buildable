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
    previous_style_description: Optional[str] = Field(
        None,
        description="Previous style description for context (for iterative edits)",
    )
    previous_image_url: Optional[str] = Field(
        None,
        description="Previous generated image URL (for image-to-image editing)",
    )


class BuildResponse(BaseModel):
    """Response schema for the /build endpoint."""
    success: bool = Field(..., description="Whether the build was successful")
    user_query: str = Field(..., description="The original user query")
    style_description: Optional[str] = Field(None, description="The generated style description")
    construction_plan: Optional[str] = Field(None, description="The generated construction plan")
    selected_item_ids: List[str] = Field(default_factory=list, description="IDs of selected inventory items")
    selected_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full details of selected inventory items"
    )
    flux_prompt: Optional[str] = Field(None, description="The optimized FLUX prompt")
    final_image_url: Optional[str] = Field(None, description="URL of the generated image")
    assembly_manual_prompts: List[str] = Field(
        default_factory=list,
        description="List of prompts for each assembly step"
    )
    assembly_manual_images: List[str] = Field(
        default_factory=list,
        description="List of image URLs for each assembly step"
    )
    error: Optional[str] = Field(None, description="Error message if build failed")


class FluxTestRequest(BaseModel):
    """Request schema for the /test-flux endpoint."""
    prompt: str = Field(
        ...,
        description="The prompt for FLUX describing what to build",
        min_length=1,
        max_length=1000,
    )
    material_image_url: str = Field(
        ...,
        description="URL of the material composition image",
    )
    previous_image_url: Optional[str] = Field(
        None,
        description="Optional URL of a previous generation step for iterative editing",
    )
    width: int = Field(1024, description="Image width", ge=256, le=2048)
    height: int = Field(1024, description="Image height", ge=256, le=2048)
    seed: Optional[int] = Field(None, description="Optional seed for reproducible results")


class FluxTestResponse(BaseModel):
    """Response schema for the /test-flux endpoint."""
    success: bool = Field(..., description="Whether the image generation was successful")
    image_url: Optional[str] = Field(None, description="URL of the generated image")
    error: Optional[str] = Field(None, description="Error message if generation failed")

