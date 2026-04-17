"""
FastAPI dependency helpers. Hand route handlers the shared VectorStore
and ChatStore instances created during app startup.
"""
from __future__ import annotations

from fastapi import Request

from api.chat_store import ChatStore
from storage.vector_store import VectorStore


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_chat_store(request: Request) -> ChatStore:
    return request.app.state.chat_store
