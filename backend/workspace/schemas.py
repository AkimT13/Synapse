"""
Versioned schema for repo-local Synapse workspace configuration.

The config is intended to live at ``.synapse/config.yaml`` in a project
root and be safe to commit. Secrets are referenced by environment-variable
name and resolved at load time; they are never stored directly here.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkspaceSection(BaseModel):
    name: str
    root: str = "."

    @field_validator("name", "root")
    @classmethod
    def _require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class SourceRoot(BaseModel):
    path: str
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)

    @field_validator("path")
    @classmethod
    def _require_path(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("path must not be empty")
        return value


class CodeRoot(SourceRoot):
    language_hints: list[str] = Field(default_factory=list)


class KnowledgeRoot(SourceRoot):
    kinds: list[str] = Field(default_factory=list)


class SourcesSection(BaseModel):
    code_roots: list[CodeRoot] = Field(default_factory=list)
    knowledge_roots: list[KnowledgeRoot] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_at_least_one_root(self) -> SourcesSection:
        if not self.code_roots and not self.knowledge_roots:
            raise ValueError(
                "at least one code_root or knowledge_root must be configured"
            )
        return self


class FiltersSection(BaseModel):
    global_exclude: list[str] = Field(default_factory=list)


class DomainConfig(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("domain name must not be empty")
        return value


class ModelSelection(BaseModel):
    provider: Literal["openai", "ollama"]
    model: str
    api_key_env: str | None = None
    base_url: str | None = None
    base_url_env: str | None = None

    @field_validator("model")
    @classmethod
    def _require_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model must not be empty")
        return value

    @field_validator("api_key_env", "base_url", "base_url_env")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ModelsSection(BaseModel):
    chat: ModelSelection
    embeddings: ModelSelection


class OllamaRuntimeConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    base_url_env: str | None = "SYNAPSE_OLLAMA_BASE_URL"

    @field_validator("base_url", "base_url_env")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class RuntimeSection(BaseModel):
    ollama: OllamaRuntimeConfig = Field(default_factory=OllamaRuntimeConfig)


class IngestionSection(BaseModel):
    auto_ingest_on_init: bool = False
    follow_symlinks: bool = False
    max_file_size_mb: int = 25


class WatchSection(BaseModel):
    enabled: bool = True
    debounce_ms: int = 1500


class RetrievalSection(BaseModel):
    default_top_k: int = 8


class DriftChecksSection(BaseModel):
    enabled: bool = True
    severity_threshold: Literal["low", "medium", "high"] = "medium"


class WorkspaceConfig(BaseModel):
    version: Literal[1] = 1
    workspace: WorkspaceSection
    sources: SourcesSection
    filters: FiltersSection = Field(default_factory=FiltersSection)
    domains: list[DomainConfig] = Field(default_factory=list)
    models: ModelsSection
    runtime: RuntimeSection = Field(default_factory=RuntimeSection)
    ingestion: IngestionSection = Field(default_factory=IngestionSection)
    watch: WatchSection = Field(default_factory=WatchSection)
    retrieval: RetrievalSection = Field(default_factory=RetrievalSection)
    drift_checks: DriftChecksSection = Field(default_factory=DriftChecksSection)
