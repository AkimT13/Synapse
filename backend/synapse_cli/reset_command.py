from __future__ import annotations

import json
from pathlib import Path

from storage.vector_store import VectorStore, actian_available
from workspace.loader import load_workspace_config


def run_reset(
    *,
    start_path: str | Path = ".",
    as_json: bool = False,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    if not actian_available():
        return 3, "Actian VectorAI client is not installed."

    try:
        with VectorStore() as store:
            deleted = store.reset()
    except Exception as exc:  # noqa: BLE001
        return 3, str(exc)

    payload = {
        "workspace": workspace.config.workspace.name,
        "collection": "chunks",
        "deleted": deleted,
    }

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)

    if deleted:
        return 0, f"Reset collection 'chunks' for workspace {workspace.config.workspace.name}."
    return 0, f"Collection 'chunks' did not exist for workspace {workspace.config.workspace.name}."
