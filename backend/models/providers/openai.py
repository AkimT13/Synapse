"""
OpenAI provider for chat completions and embeddings.

Private to the models package — external code should use the public
functions in models/__init__.py instead of importing this module
directly. The OpenAI client is lazily initialised on first use and
reads OPENAI_API_KEY from the environment (callers are expected to
have loaded .env beforehand via python-dotenv or similar).
"""

from __future__ import annotations

import os

import openai

_client: openai.OpenAI | None = None


def _get_client() -> openai.OpenAI:
    """Return the module-level OpenAI client, creating it on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Please export it or add it to your .env file."
            )
        _client = openai.OpenAI(api_key=api_key)
    return _client


"""Low temperature for deterministic normalization rewrites."""
DEFAULT_TEMPERATURE = 0.3


def complete(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
) -> str:
    """Single-turn chat completion via OpenAI.

    Parameters
    ----------
    model:
        The OpenAI model identifier (e.g. ``"gpt-4o-mini"``).
    system_prompt:
        The system message that sets the assistant's behaviour.
    user_prompt:
        The user message to respond to.
    temperature:
        Sampling temperature (0.0–2.0). Lower values are more
        deterministic.

    Returns
    -------
    str
        The assistant's reply text.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def embed(
    model: str,
    texts: list[str],
    dimension: int,
) -> list[list[float]]:
    """Embed a batch of texts via OpenAI.

    Parameters
    ----------
    model:
        The OpenAI embedding model identifier
        (e.g. ``"text-embedding-3-large"``).
    texts:
        One or more strings to embed in a single API call.
    dimension:
        The desired dimensionality of each embedding vector.

    Returns
    -------
    list[list[float]]
        A list of embedding vectors, one per input text, each of
        length *dimension*.
    """
    client = _get_client()
    response = client.embeddings.create(
        model=model,
        input=texts,
        dimensions=dimension,
    )
    return [item.embedding for item in response.data]
