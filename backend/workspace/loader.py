"""
Helpers for discovering and loading ``.synapse/config.yaml`` workspaces.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .schemas import (
    CodeRoot,
    KnowledgeRoot,
    ModelSelection,
    WorkspaceConfig,
)


WORKSPACE_DIR_NAME = ".synapse"
CONFIG_FILENAME = "config.yaml"


@dataclass(frozen=True)
class ResolvedSourceRoot:
    path: Path
    include: list[str]
    exclude: list[str]
    metadata: dict[str, list[str]]


@dataclass(frozen=True)
class ResolvedModelConfig:
    provider: str
    model: str
    api_key_env: str | None
    api_key: str | None
    base_url: str | None


@dataclass(frozen=True)
class LoadedWorkspaceConfig:
    config: WorkspaceConfig
    config_path: Path
    repo_root: Path
    workspace_root: Path

    @property
    def code_roots(self) -> list[ResolvedSourceRoot]:
        return [
            _resolve_code_root(root, self.workspace_root)
            for root in self.config.sources.code_roots
        ]

    @property
    def knowledge_roots(self) -> list[ResolvedSourceRoot]:
        return [
            _resolve_knowledge_root(root, self.workspace_root)
            for root in self.config.sources.knowledge_roots
        ]

    @property
    def chat_model(self) -> ResolvedModelConfig:
        return _resolve_model_config(
            self.config.models.chat,
            self.config.runtime.ollama.base_url,
            self.config.runtime.ollama.base_url_env,
        )

    @property
    def embedding_model(self) -> ResolvedModelConfig:
        return _resolve_model_config(
            self.config.models.embeddings,
            self.config.runtime.ollama.base_url,
            self.config.runtime.ollama.base_url_env,
        )


def find_workspace_root(start_path: str | Path = ".") -> Path:
    start = Path(start_path).resolve()
    current = start if start.is_dir() else start.parent

    for candidate in (current, *current.parents):
        config_path = candidate / WORKSPACE_DIR_NAME / CONFIG_FILENAME
        if config_path.is_file():
            return candidate

    raise FileNotFoundError(
        f"No {WORKSPACE_DIR_NAME}/{CONFIG_FILENAME} found from {start}"
    )


def load_workspace_config(start_path: str | Path = ".") -> LoadedWorkspaceConfig:
    repo_root = find_workspace_root(start_path)
    config_path = repo_root / WORKSPACE_DIR_NAME / CONFIG_FILENAME
    raw = _read_yaml_file(config_path)
    config = WorkspaceConfig.model_validate(raw)
    workspace_root = _resolve_relative_path(repo_root, config.workspace.root)

    return LoadedWorkspaceConfig(
        config=config,
        config_path=config_path,
        repo_root=repo_root,
        workspace_root=workspace_root,
    )


def _resolve_code_root(root: CodeRoot, workspace_root: Path) -> ResolvedSourceRoot:
    return ResolvedSourceRoot(
        path=_resolve_relative_path(workspace_root, root.path),
        include=list(root.include),
        exclude=list(root.exclude),
        metadata={"language_hints": list(root.language_hints)},
    )


def _resolve_knowledge_root(
    root: KnowledgeRoot,
    workspace_root: Path,
) -> ResolvedSourceRoot:
    return ResolvedSourceRoot(
        path=_resolve_relative_path(workspace_root, root.path),
        include=list(root.include),
        exclude=list(root.exclude),
        metadata={"kinds": list(root.kinds)},
    )


def _resolve_model_config(
    config: ModelSelection,
    default_ollama_base_url: str | None,
    default_ollama_base_url_env: str | None,
) -> ResolvedModelConfig:
    api_key = _read_env(config.api_key_env)
    base_url = _resolve_base_url(
        explicit_base_url=config.base_url,
        explicit_base_url_env=config.base_url_env,
        default_base_url=default_ollama_base_url if config.provider == "ollama" else None,
        default_base_url_env=(
            default_ollama_base_url_env if config.provider == "ollama" else None
        ),
    )
    return ResolvedModelConfig(
        provider=config.provider,
        model=config.model,
        api_key_env=config.api_key_env,
        api_key=api_key,
        base_url=base_url,
    )


def _resolve_base_url(
    *,
    explicit_base_url: str | None,
    explicit_base_url_env: str | None,
    default_base_url: str | None,
    default_base_url_env: str | None,
) -> str | None:
    if explicit_base_url_env:
        value = os.getenv(explicit_base_url_env)
        if value:
            return value
    if explicit_base_url:
        return explicit_base_url
    if default_base_url_env:
        value = os.getenv(default_base_url_env)
        if value:
            return value
    return default_base_url


def _read_env(name: str | None) -> str | None:
    if not name:
        return None
    value = os.getenv(name)
    return value if value else None


def _resolve_relative_path(base: Path, configured_path: str) -> Path:
    candidate = Path(configured_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (base / candidate).resolve()


def _read_yaml_file(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load .synapse/config.yaml. "
            "Install backend dependencies with `pip install -e .`."
        ) from exc

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
