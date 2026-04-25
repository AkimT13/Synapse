from __future__ import annotations

import json
from pathlib import Path

import models
from jobs.ingest_code import CodeIngestionJob
from jobs.ingest_knowledge import KnowledgeIngestionJob
from storage.vector_store import VectorStore
from workspace import init_models_from_workspace
from workspace.loader import load_workspace_config


def run_ingest(
    *,
    start_path: str | Path = ".",
    target: str = "all",
    as_json: bool = False,
    progress_sink=None,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    init_models_from_workspace(workspace)

    summaries: list[dict] = []
    progress_lines: list[str] = []
    progress_sink = progress_sink or (lambda message: None)

    def on_progress(message: str) -> None:
        progress_lines.append(message)
        progress_sink(message)

    try:
        with VectorStore(collection=workspace.collection_name) as store:
            if target in ("all", "code"):
                for root in workspace.code_roots:
                    on_progress(f"[code] starting {root.path}")
                    result = CodeIngestionJob(
                        vector_store=store,
                        should_use_llm=True,
                        on_progress=on_progress,
                    ).run(
                        str(root.path),
                        languages=root.metadata["language_hints"] or None,
                    )
                    summaries.append(
                        {
                            "kind": "code",
                            "path": str(root.path),
                            "result": result.model_dump(),
                        }
                    )

            if target in ("all", "knowledge"):
                for root in workspace.knowledge_roots:
                    on_progress(f"[knowledge] starting {root.path}")
                    result = KnowledgeIngestionJob(
                        vector_store=store,
                        should_use_llm=True,
                        on_progress=on_progress,
                    ).run(str(root.path))
                    summaries.append(
                        {
                            "kind": "knowledge",
                            "path": str(root.path),
                            "result": result.model_dump(),
                        }
                    )
    except Exception as exc:  # noqa: BLE001 - CLI should surface direct cause
        return 3, str(exc)

    payload = {
        "workspace": workspace.config.workspace.name,
        "target": target,
        "summaries": summaries,
        "progress": progress_lines,
    }
    exit_code = 0 if all(not item["result"]["errors"] for item in summaries) else 3

    if as_json:
        return exit_code, json.dumps(payload, indent=2, sort_keys=True)
    return exit_code, _render_text_ingest(payload)
def _render_text_ingest(payload: dict) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Target: {payload['target']}",
    ]

    lines.extend(["", "Results:"])
    for item in payload["summaries"]:
        result = item["result"]
        lines.append(
            "  - "
            f"{item['kind']} {item['path']}: "
            f"files={result['files_processed']}, "
            f"parsed={result['chunks_parsed']}, "
            f"stored={result['chunks_stored']}, "
            f"errors={len(result['errors'])}"
        )
        for error in result["errors"]:
            lines.append(f"    error: {error}")

    return "\n".join(lines)
