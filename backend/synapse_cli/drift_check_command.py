from __future__ import annotations

import ast
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
    module_constants = _extract_module_constants(source)
    return [
        {
            "label": chunk.subject or chunk.source_chunk.name or "<unknown>",
            "query_text": _augment_query_text(
                base_text=chunk.embed_text,
                raw_text=chunk.source_chunk.raw_text,
                source=source,
                function_name=chunk.source_chunk.name,
                line_range=chunk.source_chunk.line_range,
                module_constants=module_constants,
            ),
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
    module_constants = _extract_module_constants(text)
    return [
        {
            "label": chunk.subject or chunk.source_chunk.name or "<unknown>",
            "query_text": _augment_query_text(
                base_text=chunk.embed_text,
                raw_text=chunk.source_chunk.raw_text,
                source=text,
                function_name=chunk.source_chunk.name,
                line_range=chunk.source_chunk.line_range,
                module_constants=module_constants,
            ),
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


def _augment_query_text(
    *,
    base_text: str,
    raw_text: str,
    source: str,
    function_name: str,
    line_range,
    module_constants: dict[str, object],
) -> str:
    facts = _extract_code_facts(
        source=source,
        function_name=function_name,
        line_range=line_range,
        module_constants=module_constants,
    )
    if not facts:
        return base_text
    return (
        f"{base_text}\n\n"
        f"Deterministic code facts:\n"
        f"- Raw source summary is derived directly from the code body.\n"
        + "\n".join(f"- {fact}" for fact in facts)
        + f"\n- Raw source excerpt:\n{raw_text}"
    )


def _extract_module_constants(source: str) -> dict[str, object]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    constants: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if not name.isupper():
            continue
        try:
            constants[name] = ast.literal_eval(node.value)
        except Exception:  # noqa: BLE001
            constants[name] = ast.unparse(node.value)
    return constants


def _extract_code_facts(
    *,
    source: str,
    function_name: str,
    line_range,
    module_constants: dict[str, object],
) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            if line_range is None or (
                getattr(node, "lineno", None) == line_range.start
                or _range_matches(node, line_range.start, line_range.end)
            ):
                target = node
                break
    if target is None:
        return []

    facts: list[str] = []
    seen: set[str] = set()

    def add(fact: str) -> None:
        cleaned = fact.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            facts.append(cleaned)

    for node in ast.walk(target):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not names:
                continue
            rendered = ast.unparse(node.value)
            for name in names:
                add(f"assigns {name} = {rendered}")
                for constant_name in _referenced_constants(node.value):
                    if constant_name in module_constants:
                        add(f"module constant {constant_name} = {module_constants[constant_name]!r}")

        if isinstance(node, ast.Compare):
            add(f"compares using condition `{ast.unparse(node)}`")

        if isinstance(node, ast.Call):
            func = ast.unparse(node.func)
            if func == "int" and node.args:
                add(f"rounds or truncates value derived from `{ast.unparse(node.args[0])}`")

        if isinstance(node, ast.Return):
            if node.value is not None:
                add(f"returns `{ast.unparse(node.value)}`")

    for constant_name in _referenced_constants(target):
        if constant_name in module_constants:
            add(f"module constant {constant_name} = {module_constants[constant_name]!r}")

    return facts


def _referenced_constants(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id.isupper():
            names.add(child.id)
    return names


def _range_matches(node: ast.AST, start: int, end: int) -> bool:
    node_start = getattr(node, "lineno", None)
    node_end = getattr(node, "end_lineno", None)
    return node_start == start and node_end == end


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
