"""Configuration management using environment variables."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_title: str = "Buildable API"
    api_version: str = "0.1.0"
    debug: bool = False
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4o-mini"  # Default model

    # Embedding Model
    embedding_model: str = "text-embedding-3-small"  # OpenAI embedding model
    
    # FLUX API Configuration (Black Forest Labs)
    bfl_api_key: Optional[str] = None
    flux_model: str = "flux-2-pro"  # Options: flux-pro-1.1, flux-pro, flux-dev, flux-schnell
    
    # Image Hosting Configuration (for composed parent images)
    imgbb_api_key: Optional[str] = None  # Get free API key from https://api.imgbb.com/

    # Langfuse Configuration
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_base_url: str = "https://cloud.langfuse.com"  # Default to cloud, can be self-hosted
    langfuse_project: Optional[str] = None  # Optional: defaults to default project
    
    # MongoDB Configuration
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "buildable_db"
    
    # Data Configuration (for seeding)
    inventory_path: str = "data/inventory.json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

