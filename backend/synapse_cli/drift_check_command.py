from __future__ import annotations

import json
from pathlib import Path

from ingestion.code.python_parser import PythonParser
from normalization.code.normalizer import CodeNormalizer
from retrieval.pipelines import check_code_against_constraints
from storage.vector_store import VectorStore
from workspace import init_models_from_workspace
from workspace.loader import LoadedWorkspaceConfig, load_workspace_config


def run_drift_check(
    *,
    start_path: str | Path = ".",
    text: str | None = None,
    file_path: str | Path | None = None,
    as_json: bool = False,
    k: int = 5,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    if bool(text) == bool(file_path):
        return 1, "Provide exactly one of text or file_path."

    init_models_from_workspace(workspace)

    try:
        checks = _build_checks(
            workspace=workspace,
            text=text,
            file_path=file_path,
        )
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)

    try:
        with VectorStore() as store:
            results = [
                _run_single_check(check=check, store=store, k=k)
                for check in checks
            ]
    except Exception as exc:  # noqa: BLE001
        return 3, str(exc)

    payload = {
        "workspace": workspace.config.workspace.name,
        "target": str(file_path) if file_path is not None else "<inline>",
        "status": _aggregate_status(result["status"] for result in results),
        "checks": results,
    }

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_drift(payload)


def _build_checks(
    *,
    workspace: LoadedWorkspaceConfig,
    text: str | None,
    file_path: str | Path | None,
) -> list[dict]:
    if file_path is not None:
        return _build_file_checks(workspace, file_path)
    assert text is not None
    return _build_inline_checks(text)


def _build_file_checks(
    workspace: LoadedWorkspaceConfig,
    file_path: str | Path,
) -> list[dict]:
    candidate = Path(file_path)
    resolved = candidate if candidate.is_absolute() else (workspace.workspace_root / candidate)
    resolved = resolved.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Code file not found: {resolved}")
    source = resolved.read_text(encoding="utf-8")
    raw_chunks = PythonParser().parse_file(
        source,
        file_path=str(resolved),
        module_path=resolved.stem,
    )
    if not raw_chunks:
        raise ValueError(f"No Python functions found in {resolved}")

    normalized = CodeNormalizer(should_use_llm=True).normalize_batch(raw_chunks)
    return [
        {
            "label": chunk.subject or chunk.source_chunk.name or "<unknown>",
            "query_text": chunk.embed_text,
            "source_file": str(resolved),
            "line_range": {
                "start": chunk.source_chunk.line_range.start,
                "end": chunk.source_chunk.line_range.end,
            },
        }
        for chunk in normalized
    ]


def _build_inline_checks(text: str) -> list[dict]:
    parser = PythonParser()
    raw_chunks = parser.parse_file(
        text,
        file_path="<inline>",
        module_path="<inline>",
    )
    if not raw_chunks:
        return [
            {
                "label": "<inline>",
                "query_text": text,
                "source_file": "<inline>",
                "line_range": None,
            }
        ]

    normalized = CodeNormalizer(should_use_llm=True).normalize_batch(raw_chunks)
    return [
        {
            "label": chunk.subject or chunk.source_chunk.name or "<unknown>",
            "query_text": chunk.embed_text,
            "source_file": "<inline>",
            "line_range": {
                "start": chunk.source_chunk.line_range.start,
                "end": chunk.source_chunk.line_range.end,
            },
        }
        for chunk in normalized
    ]


def _run_single_check(*, check: dict, store: VectorStore, k: int) -> dict:
    result = check_code_against_constraints(
        code_embed_text=check["query_text"],
        store=store,
        k=k,
    )
    supporting_sources = [
        {
            "source_file": item.source_file,
            "chunk_type": item.chunk_type,
            "kind": item.kind,
            "score": item.score,
            "embed_text": item.embed_text,
        }
        for item in result["constraints"]
    ]
    status = _determine_status(
        has_conflict=result["has_conflict"],
        used_fallback=result.get("used_fallback", False),
        source_count=len(supporting_sources),
        top_score=max((item["score"] for item in supporting_sources), default=None),
    )
    confidence = _confidence_label(max((item["score"] for item in supporting_sources), default=None))

    return {
        "label": check["label"],
        "source_file": check["source_file"],
        "line_range": check["line_range"],
        "status": status,
        "summary": result["explanation"],
        "violations": [result["explanation"]] if status == "conflict" else [],
        "confidence": confidence,
        "used_fallback": result.get("used_fallback", False),
        "supporting_sources": supporting_sources,
    }


def _determine_status(
    *,
    has_conflict: bool,
    used_fallback: bool,
    source_count: int,
    top_score: float | None,
) -> str:
    if source_count == 0:
        return "unknown"
    if has_conflict:
        return "conflict"
    if used_fallback or top_score is None or top_score < 0.7:
        return "warning"
    return "aligned"


def _confidence_label(score: float | None) -> str:
    if score is None:
        return "low"
    if score >= 0.8:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def _aggregate_status(statuses) -> str:
    rank = {"conflict": 3, "warning": 2, "unknown": 1, "aligned": 0}
    return max(statuses, key=lambda status: rank[status], default="unknown")


def _render_text_drift(payload: dict) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Target: {payload['target']}",
        f"Status: {payload['status']}",
        "",
        f"Checks ({len(payload['checks'])}):",
    ]

    for check in payload["checks"]:
        line_range = check["line_range"]
        location = ""
        if line_range:
            location = f" lines={line_range['start']}-{line_range['end']}"
        lines.append(
            f"  - {check['label']}: status={check['status']}, "
            f"confidence={check['confidence']}{location}"
        )
        lines.append(f"    summary: {check['summary']}")
        lines.append(
            f"    supporting_sources={len(check['supporting_sources'])}, "
            f"used_fallback={check['used_fallback']}"
        )
        for source in check["supporting_sources"][:3]:
            lines.append(
                f"    source: {source['chunk_type']} {source['kind']} "
                f"{source['source_file']} score={source['score']:.3f}"
            )

    return "\n".join(lines)
