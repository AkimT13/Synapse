from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from workspace.schemas import (
    CodeRoot,
    DomainConfig,
    DriftChecksSection,
    FiltersSection,
    IngestionSection,
    KnowledgeRoot,
    ModelSelection,
    ModelsSection,
    OllamaRuntimeConfig,
    RetrievalSection,
    RuntimeSection,
    SourcesSection,
    WatchSection,
    WorkspaceConfig,
    WorkspaceSection,
)


DEFAULT_EXCLUDES = [
    "**/.git/**",
    "**/.venv/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/.next/**",
    "**/*.egg-info/**",
]

DEFAULT_CODE_INCLUDE = [
    "**/*.py",
    "**/*.ts",
    "**/*.tsx",
    "**/*.js",
    "**/*.jsx",
]

DEFAULT_KNOWLEDGE_INCLUDE = [
    "**/*.md",
    "**/*.pdf",
    "**/*.docx",
    "**/*.txt",
    "**/*.html",
]


@dataclass(frozen=True)
class InitOptions:
    repo_root: Path
    workspace_name: str
    code_paths: list[str]
    knowledge_paths: list[str]
    domains: list[str]
    force: bool = False
    chat_provider: str = "openai"
    chat_model: str = "gpt-4o-mini"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-large"


def run_init(options: InitOptions) -> Path:
    repo_root = options.repo_root.resolve()
    synapse_dir = repo_root / ".synapse"
    config_path = synapse_dir / "config.yaml"
    env_example_path = synapse_dir / ".env.example"
    gitignore_path = synapse_dir / ".gitignore"

    if config_path.exists() and not options.force:
        raise FileExistsError(
            f"{config_path} already exists. Re-run with --force to overwrite it."
        )

    synapse_dir.mkdir(parents=True, exist_ok=True)

    config = WorkspaceConfig(
        workspace=WorkspaceSection(name=options.workspace_name, root="."),
        sources=SourcesSection(
            code_roots=[
                CodeRoot(
                    path=path,
                    include=list(DEFAULT_CODE_INCLUDE),
                )
                for path in options.code_paths
            ],
            knowledge_roots=[
                KnowledgeRoot(
                    path=path,
                    kinds=["reference"],
                    include=list(DEFAULT_KNOWLEDGE_INCLUDE),
                )
                for path in options.knowledge_paths
            ],
        ),
        filters=FiltersSection(global_exclude=list(DEFAULT_EXCLUDES)),
        domains=[DomainConfig(name=domain) for domain in options.domains],
        models=ModelsSection(
            chat=_build_model_selection(
                provider=options.chat_provider,
                model=options.chat_model,
            ),
            embeddings=_build_model_selection(
                provider=options.embedding_provider,
                model=options.embedding_model,
            ),
        ),
        runtime=RuntimeSection(
            ollama=OllamaRuntimeConfig(
                base_url="http://localhost:11434",
                base_url_env="SYNAPSE_OLLAMA_BASE_URL",
            )
        ),
        ingestion=IngestionSection(),
        watch=WatchSection(),
        retrieval=RetrievalSection(),
        drift_checks=DriftChecksSection(),
    )

    config_path.write_text(
        yaml.safe_dump(
            config.model_dump(mode="python", exclude_none=True),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    env_example_path.write_text(_build_env_example(config), encoding="utf-8")
    gitignore_path.write_text(".env\n", encoding="utf-8")

    return config_path


def prompt_for_init_options(
    *,
    repo_root: Path,
    workspace_name: str | None,
    chat_provider: str,
    chat_model: str,
    embedding_provider: str,
    embedding_model: str,
    force: bool,
) -> InitOptions:
    resolved_repo_root = repo_root.resolve()

    name = workspace_name or _prompt(
        f"Workspace name [{resolved_repo_root.name}]: ",
        default=resolved_repo_root.name,
    )
    code_paths = _prompt_list(
        "Code directories (comma-separated) [backend,frontend]: ",
        default=["backend", "frontend"],
    )
    knowledge_paths = _prompt_list(
        "Knowledge directories (comma-separated) [sample/knowledge]: ",
        default=["sample/knowledge"],
    )
    domains = _prompt_list(
        "Domain labels (comma-separated) [domain-aware-development]: ",
        default=["domain-aware-development"],
    )

    return InitOptions(
        repo_root=resolved_repo_root,
        workspace_name=name,
        code_paths=code_paths,
        knowledge_paths=knowledge_paths,
        domains=domains,
        force=force,
        chat_provider=chat_provider,
        chat_model=chat_model,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )


def _build_model_selection(*, provider: str, model: str) -> ModelSelection:
    kwargs = {
        "provider": provider,
        "model": model,
    }
    if provider == "openai":
        kwargs["api_key_env"] = "OPENAI_API_KEY"
    return ModelSelection(**kwargs)


def _build_env_example(config: WorkspaceConfig) -> str:
    lines = ["# Workspace-local secrets and runtime overrides for Synapse."]

    needs_openai = (
        config.models.chat.provider == "openai"
        or config.models.embeddings.provider == "openai"
    )
    if needs_openai:
        lines.append("OPENAI_API_KEY=")

    lines.append(
        f"{config.runtime.ollama.base_url_env}={config.runtime.ollama.base_url}"
    )
    return "\n".join(lines) + "\n"


def _prompt(message: str, *, default: str) -> str:
    value = input(message).strip()
    return value or default


def _prompt_list(message: str, *, default: list[str]) -> list[str]:
    value = input(message).strip()
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]
