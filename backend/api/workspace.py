"""
Workspace-level endpoints. Provides coarse stats about the corpora on
disk and a destructive reset that wipes uploads, drops the vector
collection, and clears chat history. Intended for development and
for the "start over" action in the UI.
"""
from __future__ import annotations

import shutil
from fnmatch import fnmatch
from pathlib import Path

from fastapi import APIRouter, Depends

import models
from api.chat_store import ChatStore
from api.dependencies import get_chat_store, get_vector_store
from api.schemas import WorkspaceStats
from api.settings import CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR
from storage.vector_store import VectorStore


router = APIRouter()


_NOISE_DIR_NAMES = {"__pycache__", ".git", ".venv", "node_modules"}
_NOISE_GLOB_PATTERNS = ("*.egg-info",)


def _is_noise(name: str) -> bool:
    if name.startswith("."):
        return True
    if name in _NOISE_DIR_NAMES:
        return True
    for pattern in _NOISE_GLOB_PATTERNS:
        if fnmatch(name, pattern):
            return True
    return False


def _count_files(root: Path) -> int:
    """Count regular files under ``root``, skipping hidden and noise entries."""
    if not root.exists() or not root.is_dir():
        return 0

    total = 0
    for entry in root.iterdir():
        if _is_noise(entry.name):
            continue
        if entry.is_dir():
            total += _count_files(entry)
        elif entry.is_file():
            total += 1
    return total


@router.get("/stats", response_model=WorkspaceStats)
def get_stats(
    store: VectorStore = Depends(get_vector_store),
) -> WorkspaceStats:
    # Counts come straight from the vector DB so they persist across
    # sessions; a freshly started backend with on-disk uploads still
    # reports the correct totals without re-ingesting. If the collection
    # is missing or the DB hiccups we quietly fall back to None so the
    # UI can render em-dashes instead of a misleading zero.
    total_code: int | None
    total_knowledge: int | None
    try:
        total_code = store.count({"chunk_type": "code"})
        total_knowledge = store.count({"chunk_type": "knowledge"})
    except Exception:
        total_code = None
        total_knowledge = None

    return WorkspaceStats(
        code_files=_count_files(CODE_UPLOADS_DIR),
        knowledge_files=_count_files(KNOWLEDGE_UPLOADS_DIR),
        total_code_chunks=total_code,
        total_knowledge_chunks=total_knowledge,
    )


@router.post("/reset")
async def reset_workspace(
    store: VectorStore = Depends(get_vector_store),
    chat_store: ChatStore = Depends(get_chat_store),
) -> dict:
    for directory in (CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True, exist_ok=True)

    if store.client.collections.exists("chunks"):
        store.client.collections.delete("chunks")
    store.ensure_collection(models.get_config().embedding_dimension)

    await chat_store.clear_all()

    return {"cleared": True}
