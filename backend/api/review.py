"""
HTTP surface for browser-based drift review workflows.

Both stored code files and one-off uploaded Python files reuse the same
review/drift helpers so the GUI and CLI stay aligned on status,
findings, and supporting evidence.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.corpora import _resolve_within_root
from api.dependencies import get_vector_store
from api.schemas import (
    ReviewCheck,
    ReviewContextEntry,
    ReviewFinding,
    ReviewLineRange,
    ReviewRequest,
    ReviewResponse,
    ReviewSource,
)
from api.settings import CODE_UPLOADS_DIR, UPLOADS_ROOT, ensure_directories
from storage.vector_store import VectorStore
from synapse_cli.drift_check_command import _build_file_checks, _run_single_check
from synapse_cli.review_command import _aggregate_status, _build_context_entry
from workspace.loader import load_workspace_config

router = APIRouter()

_CHUNK_SIZE = 1024 * 1024
_SUPPORTED_SUFFIXES = {".py"}


def _load_workspace():
    try:
        return load_workspace_config(Path(__file__))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Workspace not initialized. Run `synapse init` and ingest "
                "knowledge before using drift review."
            ),
        ) from exc


def _sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "uploaded.py"
    return Path(filename).name or "uploaded.py"


def _validate_python_target(name: str) -> None:
    if Path(name).suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Only Python .py files are supported for drift review today.",
        )


async def _save_upload(upload: UploadFile, target: Path) -> None:
    with target.open("wb") as sink:
        while True:
            chunk = await upload.read(_CHUNK_SIZE)
            if not chunk:
                break
            sink.write(chunk)
    await upload.close()


def _build_uploaded_file_checks(workspace, path: Path) -> list[dict]:
    return _build_file_checks(workspace, path)


def _serialize_check(check: dict, *, public_source_file: str | None = None) -> ReviewCheck:
    return ReviewCheck(
        label=check["label"],
        source_file=public_source_file or check["source_file"],
        line_range=(
            ReviewLineRange(**check["line_range"])
            if check.get("line_range") is not None
            else None
        ),
        status=check["status"],
        summary=check["summary"],
        violations=list(check.get("violations", [])),
        confidence=check["confidence"],
        used_fallback=bool(check.get("used_fallback", False)),
        query_text=check.get("query_text", ""),
        findings=[
            ReviewFinding(
                issue_type=finding["issue_type"],
                expected=finding["expected"],
                observed=finding["observed"],
                comparison=finding["comparison"],
                severity=finding["severity"],
                confidence=finding["confidence"],
                summary=finding["summary"],
            )
            for finding in check.get("findings", [])
        ],
        supporting_sources=[
            ReviewSource(
                source_file=source["source_file"],
                chunk_type=source["chunk_type"],
                kind=source.get("kind"),
                score=source["score"],
                embed_text=source["embed_text"],
            )
            for source in check.get("supporting_sources", [])
        ],
    )


def _serialize_context(entry: dict) -> ReviewContextEntry:
    return ReviewContextEntry(
        label=entry["label"],
        query_text=entry["query_text"],
        has_conflict=entry["has_conflict"],
        used_fallback=entry.get("used_fallback", False),
        sources=[
            ReviewSource(
                source_file=source["source_file"],
                chunk_type=source["chunk_type"],
                kind=source.get("kind"),
                score=source["score"],
                embed_text=source["embed_text"],
            )
            for source in entry.get("sources", [])
        ],
    )


def _review_path(
    *,
    resolved: Path,
    target: str,
    k: int,
    store: VectorStore,
) -> ReviewResponse:
    workspace = _load_workspace()
    try:
        checks = _build_uploaded_file_checks(workspace, resolved)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    drift = [
        _serialize_check(
            _run_single_check(check=check, store=store, k=k),
            public_source_file=target,
        )
        for check in checks
    ]
    context = [
        _serialize_context(_build_context_entry(check=check, store=store, k=k))
        for check in checks
    ]
    return ReviewResponse(
        workspace=workspace.config.workspace.name,
        target=target,
        drift_status=_aggregate_status(item.status for item in drift),
        drift=drift,
        context=context,
    )


def review_code_file(
    payload: ReviewRequest,
    store: VectorStore,
) -> ReviewResponse:
    _validate_python_target(payload.path)
    resolved = _resolve_within_root(CODE_UPLOADS_DIR, payload.path)
    return _review_path(
        resolved=resolved,
        target=payload.path,
        k=payload.k,
        store=store,
    )


@router.post("/file", response_model=ReviewResponse)
def review_file(
    payload: ReviewRequest,
    store: VectorStore = Depends(get_vector_store),
) -> ReviewResponse:
    return review_code_file(payload, store)


@router.post("/upload", response_model=ReviewResponse)
async def review_upload(
    file: UploadFile = File(...),
    k: int = Form(5, ge=1),
    store: VectorStore = Depends(get_vector_store),
) -> ReviewResponse:
    display_name = _sanitize_filename(file.filename)
    _validate_python_target(display_name)

    ensure_directories()
    with tempfile.TemporaryDirectory(dir=UPLOADS_ROOT, prefix="review-") as tempdir:
        temp_path = Path(tempdir) / display_name
        await _save_upload(file, temp_path)
        return _review_path(
            resolved=temp_path,
            target=display_name,
            k=k,
            store=store,
        )
