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
    
    # FLUX API Configuration (for future use)
    flux_api_key: Optional[str] = None
    flux_api_url: str = "https://api.flux.dev/v1"
    
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

