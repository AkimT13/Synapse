from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from storage.vector_store import VectorStore, actian_available
from workspace.loader import LoadedWorkspaceConfig, load_workspace_config


@dataclass(frozen=True)
class DbStatus:
    actian_installed: bool
    reachable: bool
    error: str | None = None


def run_status(
    *,
    start_path: str | Path = ".",
    as_json: bool = False,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    db_status = _get_db_status(workspace.collection_name)
    payload = _build_status_payload(workspace, db_status)

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)

    return 0, _render_text_status(payload)


def _get_db_status(collection_name: str) -> DbStatus:
    if not actian_available():
        return DbStatus(
            actian_installed=False,
            reachable=False,
            error="Actian VectorAI client is not installed",
        )

    try:
        with VectorStore(collection=workspace.collection_name) as store:
            store.client.collections.exists(store.collection)
        return DbStatus(actian_installed=True, reachable=True)
    except Exception as exc:  # noqa: BLE001 - status should surface failures
        return DbStatus(
            actian_installed=True,
            reachable=False,
            error=str(exc),
        )


def _build_status_payload(
    workspace: LoadedWorkspaceConfig,
    db_status: DbStatus,
) -> dict:
    return {
        "workspace": {
            "name": workspace.config.workspace.name,
            "repo_root": str(workspace.repo_root),
            "config_path": str(workspace.config_path),
        },
        "sources": {
            "code_roots": [
                {
                    "path": str(root.path),
                    "language_hints": root.metadata["language_hints"],
                }
                for root in workspace.code_roots
            ],
            "knowledge_roots": [
                {
                    "path": str(root.path),
                    "kinds": root.metadata["kinds"],
                }
                for root in workspace.knowledge_roots
            ],
        },
        "models": {
            "chat": {
                "provider": workspace.chat_model.provider,
                "model": workspace.chat_model.model,
                "api_key_configured": bool(workspace.chat_model.api_key),
                "base_url": workspace.chat_model.base_url,
            },
            "embeddings": {
                "provider": workspace.embedding_model.provider,
                "model": workspace.embedding_model.model,
                "api_key_configured": bool(workspace.embedding_model.api_key),
                "base_url": workspace.embedding_model.base_url,
            },
        },
        "runtime": {
            "watch_enabled": workspace.config.watch.enabled,
            "default_top_k": workspace.config.retrieval.default_top_k,
            "db": asdict(db_status),
        },
    }


def _render_text_status(payload: dict) -> str:
    workspace = payload["workspace"]
    code_roots = payload["sources"]["code_roots"]
    knowledge_roots = payload["sources"]["knowledge_roots"]
    chat = payload["models"]["chat"]
    embeddings = payload["models"]["embeddings"]
    db = payload["runtime"]["db"]

    lines = [
        f"Workspace: {workspace['name']}",
        f"Repo root: {workspace['repo_root']}",
        f"Config: {workspace['config_path']}",
        "",
        f"Code roots ({len(code_roots)}):",
    ]
    lines.extend(
        f"  - {root['path']} [{', '.join(root['language_hints']) or 'unspecified'}]"
        for root in code_roots
    )
    lines.append(f"Knowledge roots ({len(knowledge_roots)}):")
    lines.extend(
        f"  - {root['path']} [{', '.join(root['kinds']) or 'unspecified'}]"
        for root in knowledge_roots
    )
    lines.extend(
        [
            "",
            "Models:",
            (
                f"  - chat: {chat['provider']} / {chat['model']}"
                f" (api_key_configured={chat['api_key_configured']})"
            ),
            (
                f"  - embeddings: {embeddings['provider']} / {embeddings['model']}"
                f" (api_key_configured={embeddings['api_key_configured']})"
            ),
            "",
            "Runtime:",
            f"  - watch_enabled: {payload['runtime']['watch_enabled']}",
            f"  - default_top_k: {payload['runtime']['default_top_k']}",
            (
                f"  - actian_installed: {db['actian_installed']}, "
                f"db_reachable: {db['reachable']}"
            ),
        ]
    )
    if db["error"]:
        lines.append(f"  - db_error: {db['error']}")

    return "\n".join(lines)
