from __future__ import annotations

import json
from pathlib import Path

from retrieval.pipelines import check_code_against_constraints
from storage.vector_store import VectorStore
from synapse_cli.drift_check_command import _build_file_checks, _run_single_check
from workspace import init_models_from_workspace
from workspace.loader import load_workspace_config


def run_review(
    *,
    start_path: str | Path = ".",
    file_path: str | Path,
    as_json: bool = False,
    k: int = 5,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    init_models_from_workspace(workspace)

    try:
        checks = _build_file_checks(workspace, file_path)
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)

    try:
        with VectorStore() as store:
            drift = [
                _serialize_drift_entry(_run_single_check(check=check, store=store, k=k))
                for check in checks
            ]
            context = [
                _build_context_entry(check=check, store=store, k=k)
                for check in checks
            ]
    except Exception as exc:  # noqa: BLE001
        return 3, str(exc)

    payload = {
        "workspace": workspace.config.workspace.name,
        "target": str(file_path),
        "drift_status": _aggregate_status(item["status"] for item in drift),
        "drift": drift,
        "context": context,
    }

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_review(payload)


def _build_context_entry(*, check: dict, store: VectorStore, k: int) -> dict:
    result = check_code_against_constraints(
        code_embed_text=check["query_text"],
        store=store,
        k=k,
    )
    return {
        "label": check["label"],
        "query_text": check["query_text"],
        "has_conflict": result["has_conflict"],
        "used_fallback": result.get("used_fallback", False),
        "sources": [
            {
                "source_file": item.source_file,
                "chunk_type": item.chunk_type,
                "kind": item.kind,
                "score": item.score,
                "embed_text": item.embed_text,
            }
            for item in result["constraints"]
        ],
    }


def _serialize_drift_entry(entry: dict) -> dict:
    serialized = dict(entry)
    serialized["supporting_sources"] = [
        source
        if isinstance(source, dict)
        else {
            "source_file": source.source_file,
            "chunk_type": source.chunk_type,
            "kind": source.kind,
            "score": source.score,
            "embed_text": source.embed_text,
        }
        for source in entry.get("supporting_sources", [])
    ]
    return serialized


def _aggregate_status(statuses) -> str:
    rank = {"conflict": 3, "warning": 2, "unknown": 1, "aligned": 0}
    return max(statuses, key=lambda status: rank[status], default="unknown")


def _render_text_review(payload: dict) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Target: {payload['target']}",
        f"Drift status: {payload['drift_status']}",
        "",
        f"Checks ({len(payload['drift'])}):",
    ]
    for drift, context in zip(payload["drift"], payload["context"], strict=True):
        lines.append(
            f"  - {drift['label']}: status={drift['status']}, "
            f"confidence={drift['confidence']}, sources={len(context['sources'])}"
        )
        lines.append(f"    summary: {drift['summary']}")
        for source in context["sources"][:3]:
            lines.append(
                f"    source: {source['chunk_type']} {source['kind']} "
                f"{source['source_file']} score={source['score']:.3f}"
            )
    return "\n".join(lines)
