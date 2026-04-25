from __future__ import annotations

import json
from pathlib import Path

from retrieval.pipelines import (
    answer_question,
    check_code_against_constraints,
    explain_constraint_coverage,
)
from storage.vector_store import VectorStore
from workspace import init_models_from_workspace
from workspace.loader import load_workspace_config


def run_query(
    *,
    start_path: str | Path = ".",
    mode: str,
    text: str,
    as_json: bool = False,
    k: int | None = None,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    init_models_from_workspace(workspace)

    try:
        with VectorStore(collection=workspace.collection_name) as store:
            if mode == "free":
                result = answer_question(
                    question=text,
                    store=store,
                    k=k or workspace.config.retrieval.default_top_k,
                )
                payload = {
                    "mode": mode,
                    "query": text,
                    "answer": result["answer"],
                    "results": _serialize_results(result["results"]),
                }
            elif mode == "code":
                result = check_code_against_constraints(
                    code_embed_text=text,
                    store=store,
                    k=k or 5,
                )
                payload = {
                    "mode": mode,
                    "query": text,
                    "explanation": result["explanation"],
                    "has_conflict": result["has_conflict"],
                    "used_fallback": result.get("used_fallback", False),
                    "results": _serialize_results(result["constraints"]),
                }
            elif mode == "knowledge":
                result = explain_constraint_coverage(
                    knowledge_embed_text=text,
                    store=store,
                    k=k or 5,
                )
                payload = {
                    "mode": mode,
                    "query": text,
                    "explanation": result["explanation"],
                    "is_implemented": result["is_implemented"],
                    "results": _serialize_results(result["code_chunks"]),
                }
            else:
                return 1, f"Unsupported query mode: {mode}"
    except Exception as exc:  # noqa: BLE001
        return 3, str(exc)

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_query(payload)


def _serialize_results(results: list) -> list[dict]:
    return [
        {
            "source_file": result.source_file,
            "chunk_type": result.chunk_type,
            "kind": result.kind,
            "score": result.score,
            "embed_text": result.embed_text,
        }
        for result in results
    ]


def _render_text_query(payload: dict) -> str:
    lines = [
        f"Mode: {payload['mode']}",
        f"Query: {payload['query']}",
        "",
    ]

    if "answer" in payload:
        lines.extend(["Answer:", payload["answer"], ""])
    if "explanation" in payload:
        lines.extend(["Explanation:", payload["explanation"], ""])
    if "has_conflict" in payload:
        lines.append(f"Has conflict: {payload['has_conflict']}")
    if "used_fallback" in payload:
        lines.append(f"Used fallback: {payload['used_fallback']}")
    if "is_implemented" in payload:
        lines.append(f"Is implemented: {payload['is_implemented']}")
    if any(key in payload for key in ("has_conflict", "used_fallback", "is_implemented")):
        lines.append("")

    lines.append(f"Results ({len(payload['results'])}):")
    for index, result in enumerate(payload["results"], start=1):
        lines.append(
            f"  [{index}] {result['chunk_type']} {result['kind']} "
            f"{result['source_file']} score={result['score']:.3f}"
        )
        lines.append(f"      {result['embed_text']}")

    return "\n".join(lines)
