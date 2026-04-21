from __future__ import annotations

import os

import models
from models.config import ModelConfig

from .loader import LoadedWorkspaceConfig


def init_models_from_workspace(workspace: LoadedWorkspaceConfig) -> None:
    _apply_ollama_base_url(workspace)

    embedding_model = workspace.embedding_model.model
    models.init(
        ModelConfig(
            chat_provider=workspace.chat_model.provider,
            chat_model=workspace.chat_model.model,
            embedding_provider=workspace.embedding_model.provider,
            embedding_model=embedding_model,
            embedding_dimension=infer_embedding_dimension(
                embedding_model,
                default_dimension=models.get_config().embedding_dimension,
            ),
        )
    )


def infer_embedding_dimension(model: str, *, default_dimension: int) -> int:
    normalized = model.strip().lower()
    if normalized == "text-embedding-3-large":
        return 3072
    if normalized == "text-embedding-3-small":
        return 1536
    if "nomic-embed-text" in normalized:
        return 768
    return default_dimension


def _apply_ollama_base_url(workspace: LoadedWorkspaceConfig) -> None:
    base_urls = {
        config.base_url
        for config in (workspace.chat_model, workspace.embedding_model)
        if config.provider == "ollama" and config.base_url
    }
    if not base_urls:
        return
    if len(base_urls) > 1:
        raise ValueError(
            "Workspace config specifies different Ollama base URLs for chat and "
            "embedding models, but the current provider layer supports only one "
            "OLLAMA_BASE_URL per process."
        )
    os.environ["OLLAMA_BASE_URL"] = next(iter(base_urls))
