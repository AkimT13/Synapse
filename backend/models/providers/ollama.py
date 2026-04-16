"""Ollama provider for chat completions and embeddings."""
from __future__ import annotations

import httpx


_BASE_URL = "http://localhost:11434"


def complete(model: str, system_prompt: str, user_prompt: str) -> str:
    """Send a chat completion request to the local Ollama server."""
    response = httpx.post(
        f"{_BASE_URL}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def embed(model: str, texts: list[str]) -> list[list[float]]:
    """Send an embedding request to the local Ollama server."""
    vectors = []
    for text in texts:
        response = httpx.post(
            f"{_BASE_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        vectors.append(response.json()["embedding"])
    return vectors