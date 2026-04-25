from __future__ import annotations

import subprocess
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

LOCAL_RUNTIME_GITIGNORE = [
    ".env",
    "runtime/",
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


def run_init(options: InitOptions, *, interactive: bool = False) -> Path:
    repo_root = options.repo_root.resolve()
    synapse_dir = repo_root / ".synapse"
    config_path = synapse_dir / "config.yaml"
    env_example_path = synapse_dir / ".env.example"
    env_path = synapse_dir / ".env"
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
    gitignore_path.write_text(
        "".join(f"{entry}\n" for entry in LOCAL_RUNTIME_GITIGNORE),
        encoding="utf-8",
    )

    # In interactive mode, prompt for the API key and write .env directly.
    needs_openai = (
        options.chat_provider == "openai"
        or options.embedding_provider == "openai"
    )
    if interactive and needs_openai and not env_path.exists():
        print()
        print("  OpenAI requires an API key to run.")
        api_key = _prompt_secret("  OPENAI_API_KEY: ")
        if api_key:
            env_path.write_text(
                f"OPENAI_API_KEY={api_key}\n",
                encoding="utf-8",
            )
            print(f"  Saved to {env_path}")
        else:
            print(f"  Skipped. Add your key to {env_path} before ingesting.")

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
        "Code directories (comma-separated) [src]: ",
        default=["src"],
    )
    knowledge_paths = _prompt_list(
        "Knowledge directories (comma-separated) [docs]: ",
        default=["docs"],
    )

    # Validate that the directories exist.
    _warn_missing_paths(resolved_repo_root, code_paths + knowledge_paths)

    domains = _prompt_list(
        "Domain labels (comma-separated) [domain-aware-development]: ",
        default=["domain-aware-development"],
    )

    # Provider selection.
    provider = _prompt_choice(
        "Model provider",
        choices=["openai", "ollama"],
        default="openai",
    )

    if provider == "ollama":
        chat_provider = "ollama"
        embedding_provider = "ollama"
        local_models = _list_ollama_models()
        if local_models:
            print(f"\n  Found {len(local_models)} local Ollama model(s):\n")
            chat_model = _prompt_menu(
                "Chat model",
                options=local_models,
                default=_pick_default(local_models, ["llama3", "gemma", "mistral"]),
            )
            embed_candidates = [m for m in local_models if "embed" in m.lower()]
            if embed_candidates:
                embedding_model = _prompt_menu(
                    "Embedding model",
                    options=local_models,
                    default=_pick_default(local_models, ["nomic-embed", "embed"]),
                )
            else:
                print("  No embedding models found locally.")
                embedding_model = _prompt(
                    "  Embedding model name [nomic-embed-text]: ",
                    default="nomic-embed-text",
                )
                print(f"  Run: ollama pull {embedding_model}")
        else:
            print("  Could not list Ollama models (is Ollama running?).")
            chat_model = _prompt("  Chat model [llama3]: ", default="llama3")
            embedding_model = _prompt(
                "  Embedding model [nomic-embed-text]: ",
                default="nomic-embed-text",
            )
    else:
        chat_provider = "openai"
        embedding_provider = "openai"
        openai_chat = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"]
        openai_embed = ["text-embedding-3-large", "text-embedding-3-small"]
        print()
        chat_model = _prompt_menu("Chat model", options=openai_chat, default="gpt-4o-mini")
        embedding_model = _prompt_menu(
            "Embedding model", options=openai_embed, default="text-embedding-3-large",
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


def _prompt_secret(message: str) -> str:
    """Prompt for a value without echoing (API keys, passwords)."""
    import getpass
    return getpass.getpass(message).strip()


def _prompt_list(message: str, *, default: list[str]) -> list[str]:
    value = input(message).strip()
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _prompt_choice(label: str, *, choices: list[str], default: str) -> str:
    display = " / ".join(
        f"[{c}]" if c == default else c for c in choices
    )
    value = input(f"{label} ({display}): ").strip().lower()
    if not value:
        return default
    if value in choices:
        return value
    print(f"  Invalid choice '{value}', using default '{default}'")
    return default


def _warn_missing_paths(repo_root: Path, paths: list[str]) -> None:
    for p in paths:
        full = repo_root / p
        if not full.exists():
            print(f"  ⚠ Directory '{p}' does not exist yet — create it before ingesting.")


def _prompt_menu(label: str, *, options: list[str], default: str) -> str:
    """Show a numbered menu and return the selected option."""
    for i, opt in enumerate(options, 1):
        marker = " (default)" if opt == default else ""
        print(f"  {i}. {opt}{marker}")
    raw = input(f"  {label} [1-{len(options)}]: ").strip()
    if not raw:
        return default
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        # Allow typing the model name directly.
        if raw in options:
            return raw
        # Accept freeform input for custom models.
        return raw
    print(f"  Invalid selection, using default '{default}'")
    return default


def _list_ollama_models() -> list[str]:
    """Run ``ollama list`` and return model names, or empty list on failure."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        models: list[str] = []
        for line in result.stdout.strip().splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _pick_default(available: list[str], preferences: list[str]) -> str:
    """Return the first available model matching any preference prefix."""
    for pref in preferences:
        for model in available:
            if model.lower().startswith(pref.lower()):
                return model
    return available[0] if available else ""
