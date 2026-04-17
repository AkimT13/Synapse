"""
API-specific configuration. Knobs for the HTTP layer — upload paths,
CORS origins, chat DB location. Kept separate from the domain-level
config/settings so route handlers never reach into model / vector
DB concerns.
"""
from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_ROOT = BACKEND_ROOT / "uploads"
CODE_UPLOADS_DIR = UPLOADS_ROOT / "code"
KNOWLEDGE_UPLOADS_DIR = UPLOADS_ROOT / "knowledge"

DATA_ROOT = BACKEND_ROOT / "data"
CHAT_DB_PATH = DATA_ROOT / "chat.db"

# Frontend is served separately (Next.js dev server); allow its origin.
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def ensure_directories() -> None:
    """Create upload and data directories if they do not yet exist."""
    for directory in (CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR, DATA_ROOT):
        directory.mkdir(parents=True, exist_ok=True)
