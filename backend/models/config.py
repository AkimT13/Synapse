"""
Model configuration for the Synapse backend.
Defines which providers and model names are used for chat completions
and embeddings. Provider-specific credentials (e.g. OPENAI_API_KEY) are
NOT stored here — each provider module reads its own key from the
environment at call time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    """Immutable configuration describing the active providers and models."""
    chat_provider: str = "openai"
    chat_model: str = "gpt-4o-mini"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 3072


def load_config() -> ModelConfig:
    """Create a ModelConfig from environment variables with fallback defaults."""
    return ModelConfig(
        chat_provider=os.getenv("LLM_PROVIDER", "openai"),
        chat_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "3072")),
    )