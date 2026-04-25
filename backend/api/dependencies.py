"""
FastAPI dependency helpers. Hand route handlers the shared VectorStore
and ChatStore instances created during app startup.
"""
from __future__ import annotations

from fastapi import Request

from api.chat_store import ChatStore
from storage.vector_store import VectorStore
from workspace.loader import LoadedWorkspaceConfig


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_chat_store(request: Request) -> ChatStore:
    return request.app.state.chat_store


def get_workspace_config(request: Request) -> LoadedWorkspaceConfig | None:
    return getattr(request.app.state, "workspace_config", None)
