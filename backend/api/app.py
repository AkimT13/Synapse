"""
FastAPI entry point for the Synapse backend. Exposes ingestion,
retrieval, corpora browsing, and chat over HTTP.

The VectorStore connection and model layer are initialised once at
startup and shared across requests via a dependency; the SQLite
chat store is opened here too.

Run with::

    python -m api.app
    # or:
    uvicorn api.app:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from api.chat_store import ChatStore
from api.settings import CHAT_DB_PATH, CORS_ORIGINS, ensure_directories
from storage.vector_store import VectorStore
from workspace import init_models_from_workspace, load_workspace_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    ensure_directories()
    try:
        workspace = load_workspace_config(Path(__file__))
    except FileNotFoundError:
        models.init()
        app.state.workspace_config = None
    else:
        init_models_from_workspace(workspace)
        app.state.workspace_config = workspace

    store = VectorStore()
    store.connect()
    app.state.vector_store = store

    chat_store = ChatStore(CHAT_DB_PATH)
    await chat_store.init()
    app.state.chat_store = chat_store

    try:
        yield
    finally:
        store.close()
        await chat_store.close()


app = FastAPI(title="Synapse API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Routers are attached in package-level imports so circular-import
# concerns stay contained.
from api import chat, corpora, ingestion, retrieval, review, workspace  # noqa: E402

app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
app.include_router(corpora.router, prefix="/api/corpora", tags=["corpora"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(retrieval.router, prefix="/api", tags=["retrieval"])
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)
