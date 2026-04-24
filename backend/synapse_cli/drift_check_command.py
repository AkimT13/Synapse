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
            "query_text": chunk.embed_text,
            "source_file": str(resolved),
            "line_range": {
                "start": chunk.source_chunk.line_range.start,
                "end": chunk.source_chunk.line_range.end,
            },
            "signals": _extract_code_signals(
                source=source,
                function_name=chunk.source_chunk.name,
                line_range=chunk.source_chunk.line_range,
                module_constants=module_constants,
            ),
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
            "query_text": chunk.embed_text,
            "source_file": "<inline>",
            "line_range": {
                "start": chunk.source_chunk.line_range.start,
                "end": chunk.source_chunk.line_range.end,
            },
            "signals": _extract_code_signals(
                source=text,
                function_name=chunk.source_chunk.name,
                line_range=chunk.source_chunk.line_range,
                module_constants=module_constants,
            ),
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
    findings = _extract_structured_findings(
        signals=check.get("signals") or {},
        supporting_sources=supporting_sources,
        confidence=_confidence_label(max((item["score"] for item in supporting_sources), default=None)),
    )
    status = _status_from_findings(findings)
    if status is None:
        status = _determine_status(
            has_conflict=result["has_conflict"],
            used_fallback=result.get("used_fallback", False),
            source_count=len(supporting_sources),
            top_score=max((item["score"] for item in supporting_sources), default=None),
        )
    summary = _render_summary_from_findings(findings) or result["explanation"]
    confidence = _confidence_label(max((item["score"] for item in supporting_sources), default=None))

    return {
        "label": check["label"],
        "source_file": check["source_file"],
        "line_range": check["line_range"],
        "status": status,
        "summary": summary,
        "violations": [finding["summary"] for finding in findings],
        "confidence": confidence,
        "used_fallback": result.get("used_fallback", False),
        "findings": findings,
        "supporting_sources": supporting_sources,
    }


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


def _extract_code_signals(
    *,
    source: str,
    function_name: str,
    line_range,
    module_constants: dict[str, object],
) -> dict:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"constants": {}, "comparisons": []}

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
        return {"constants": {}, "comparisons": []}

    comparisons: list[str] = []
    referenced_constants = {
        name: value
        for name, value in module_constants.items()
        if name in _referenced_constants(target)
    }

    for node in ast.walk(target):
        if isinstance(node, ast.Compare):
            comparisons.append(ast.unparse(node))

    return {
        "constants": referenced_constants,
        "comparisons": comparisons,
    }


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


def _extract_structured_findings(
    *,
    signals: dict,
    supporting_sources: list[dict],
    confidence: str,
) -> list[dict]:
    findings: list[dict] = []
    constants = signals.get("constants", {})
    comparisons = signals.get("comparisons", [])
    support_text = _normalize_support_text(
        " ".join(source["embed_text"] for source in supporting_sources)
    )

    threshold_sigma = _find_numeric_constant(constants, "THRESHOLD_SIGMA")
    if threshold_sigma is not None and "3 to 5 standard deviations" in support_text:
        if threshold_sigma < 3:
            findings.append(_make_finding(
                issue_type="threshold_range",
                expected="threshold sigma between 3 and 5 standard deviations below baseline",
                observed=f"threshold sigma set to {threshold_sigma}",
                comparison="observed < minimum",
                severity="high",
                confidence=confidence,
                summary=f"Configured threshold sigma {threshold_sigma} is below the required 3-5 range.",
            ))
        elif threshold_sigma > 5:
            findings.append(_make_finding(
                issue_type="threshold_range",
                expected="threshold sigma between 3 and 5 standard deviations below baseline",
                observed=f"threshold sigma set to {threshold_sigma}",
                comparison="observed > maximum",
                severity="high",
                confidence=confidence,
                summary=f"Configured threshold sigma {threshold_sigma} is above the required 3-5 range.",
            ))

    if "negative-going" in support_text or "negative threshold" in support_text:
        if any(">" in comparison and "threshold" in comparison for comparison in comparisons):
            findings.append(_make_finding(
                issue_type="threshold_polarity",
                expected="detect threshold crossings against a negative-going threshold",
                observed="comparison uses a positive threshold crossing condition",
                comparison="sign mismatch",
                severity="high",
                confidence=confidence,
                summary="The code compares samples above threshold even though the protocol requires negative-going detections.",
            ))

    refractory_ms = _find_numeric_constant(constants, "REFRACTORY_PERIOD_MS")
    if refractory_ms is not None and "at least 1 millisecond" in support_text:
        if refractory_ms < 1:
            findings.append(_make_finding(
                issue_type="timing_lower_bound",
                expected="refractory period of at least 1 millisecond",
                observed=f"refractory period set to {refractory_ms} milliseconds",
                comparison="observed < minimum",
                severity="high",
                confidence=confidence,
                summary=f"Refractory period {refractory_ms} ms is below the required 1 ms minimum.",
            ))

    blink_rejection_uv = _find_numeric_constant(constants, "BLINK_REJECTION_UV")
    if (
        blink_rejection_uv is not None
        and _contains_100_microvolt_bound(support_text)
        and any(
            token in support_text
            for token in (
                "blink",
                "epoch",
                "excluded",
                "corrected",
                "artifact",
                "peak-to-peak",
            )
        )
    ):
        if blink_rejection_uv > 100:
            findings.append(_make_finding(
                issue_type="artifact_threshold",
                expected="reject or regress epochs above 100 microvolts peak-to-peak",
                observed=f"blink rejection threshold set to {blink_rejection_uv} microvolts",
                comparison="observed > maximum allowed threshold",
                severity="high",
                confidence=confidence,
                summary=f"Blink rejection threshold {blink_rejection_uv} uV is more permissive than the required 100 uV limit.",
            ))

    return findings


def _find_numeric_constant(constants: dict[str, object], token: str) -> float | None:
    for name, value in constants.items():
        if token in name and isinstance(value, (int, float)):
            return float(value)
    return None


def _normalize_support_text(text: str) -> str:
    return (
        text.lower()
        .replace("μv", "microvolts")
        .replace("µv", "microvolts")
        .replace(" uv", " microvolts")
    )


def _contains_100_microvolt_bound(text: str) -> bool:
    return (
        "100 microvolts" in text
        or "100 microvolt" in text
        or "100uv" in text
    )


def _make_finding(
    *,
    issue_type: str,
    expected: str,
    observed: str,
    comparison: str,
    severity: str,
    confidence: str,
    summary: str,
) -> dict:
    return {
        "issue_type": issue_type,
        "expected": expected,
        "observed": observed,
        "comparison": comparison,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
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


def _status_from_findings(findings: list[dict]) -> str | None:
    if not findings:
        return None
    if any(finding["severity"] == "high" for finding in findings):
        return "conflict"
    if any(finding["severity"] == "medium" for finding in findings):
        return "warning"
    return "warning"


def _render_summary_from_findings(findings: list[dict]) -> str | None:
    if not findings:
        return None
    if len(findings) == 1:
        return findings[0]["summary"]
    summaries = "; ".join(finding["summary"] for finding in findings)
    return f"Detected {len(findings)} structured drift findings: {summaries}"


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
        if check["findings"]:
            lines.append(f"    findings={len(check['findings'])}")
            for finding in check["findings"]:
                lines.append(
                    f"    finding: {finding['issue_type']} severity={finding['severity']} "
                    f"comparison={finding['comparison']}"
                )
                lines.append(f"      expected: {finding['expected']}")
                lines.append(f"      observed: {finding['observed']}")
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
