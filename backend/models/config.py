"""
Model configuration for the Synapse backend.

Defines which providers and model names are used for chat completions
and embeddings. Provider-specific credentials (e.g. OPENAI_API_KEY) are
NOT stored here — each provider module reads its own key from the
environment at call time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Immutable configuration describing the active providers and models."""

    chat_provider: str = "openai"
    chat_model: str = "gpt-4o-mini"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 3072  # text-embedding-3-large native dimension


def load_config() -> ModelConfig:
    """Create a ModelConfig with default values.

    This factory exists so callers have a single entry-point for
    obtaining configuration. Future versions may read overrides from
    environment variables or a config file.
    """
    return ModelConfig()
