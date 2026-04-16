"""
Public API for LLM completions and embeddings.

Provider-agnostic — callers use complete() and embed() without knowing
the underlying provider. Configure via init() or let it auto-load from
defaults on first use.

Usage::

    import models

    answer = models.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarise this document.",
    )

    vectors = models.embed(["hello world", "foo bar"])
"""

from __future__ import annotations

from models.config import ModelConfig, load_config

_config: ModelConfig | None = None


def init(config: ModelConfig | None = None) -> None:
    """Initialize with an explicit config, or fall back to defaults.

    Calling this is optional — ``get_config()`` (and therefore
    ``complete()`` / ``embed()``) will auto-initialize with defaults
    if ``init()`` was never called.
    """
    global _config
    _config = config if config is not None else load_config()


def get_config() -> ModelConfig:
    """Return the current ModelConfig, auto-initializing if needed."""
    global _config
    if _config is None:
        init()
    assert _config is not None  # guaranteed by init()
    return _config


def complete(system_prompt: str, user_prompt: str) -> str:
    """Route a single-turn chat completion to the configured provider.

    Parameters
    ----------
    system_prompt:
        The system message that sets the assistant's behaviour.
    user_prompt:
        The user message to respond to.

    Returns
    -------
    str
        The assistant's reply text.
    """
    config = get_config()
    match config.chat_provider:
        case "openai":
            from models.providers import openai as openai_provider

            return openai_provider.complete(
                config.chat_model, system_prompt, user_prompt
            )
        case _:
            raise ValueError(f"Unknown chat provider: {config.chat_provider}")


def embed(texts: list[str]) -> list[list[float]]:
    """Route an embedding request to the configured provider.

    Parameters
    ----------
    texts:
        One or more strings to embed.

    Returns
    -------
    list[list[float]]
        A list of embedding vectors, one per input text.
    """
    config = get_config()
    match config.embedding_provider:
        case "openai":
            from models.providers import openai as openai_provider

            return openai_provider.embed(
                config.embedding_model, texts, config.embedding_dimension
            )
        case _:
            raise ValueError(
                f"Unknown embedding provider: {config.embedding_provider}"
            )


def embed_single(text: str) -> list[float]:
    """Convenience wrapper that embeds a single string and returns its vector."""
    return embed([text])[0]
