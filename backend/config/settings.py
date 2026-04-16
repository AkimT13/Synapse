"""
Central configuration for the Synapse pipeline.
All values can be overridden via environment variables or a .env file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- embedding ---
    
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    tokenizer: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_dimension: int = 768

    # --- chunking ---
    max_chunk_tokens: int = 512

    # --- llm ---
    llm_provider: str = "ollama"        # "ollama" | "openai"
    llm_model: str = "gemma4:e4b"
    openai_api_key: str = ""

    # --- actian ---
    actian_connection_string: str = ""

    # --- ingestion ---
    ingested_by: str = "system"


settings = Settings()

# module-level aliases so existing imports keep working
# chunker.py imports TOKENIZER and MAX_TOKENS directly
TOKENIZER = settings.tokenizer
MAX_TOKENS = settings.max_chunk_tokens