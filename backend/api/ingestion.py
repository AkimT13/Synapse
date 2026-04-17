"""
HTTP surface for code and knowledge ingestion.

Two POST endpoints accept a multipart directory upload (the frontend
sends each ``UploadFile`` with ``filename`` set to its
``webkitRelativePath`` so the on-disk tree can be reconstructed),
persist the files under the corresponding uploads directory, and spawn
a background ingestion job. A GET endpoint streams that job's progress
as Server-Sent Events so the UI can render a live log.

Each upload replaces the prior corpus for its side (code vs knowledge)
— the single-workspace model. The job itself runs in a worker thread
via ``run_in_executor`` because the ingestion pipeline is CPU- and
network-bound (parsing, LLM calls, embeddings) and would otherwise
block the event loop.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_vector_store
from api.jobs import Job, registry
from api.schemas import IngestionAck
from api.settings import CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR
from jobs.ingest_code import CodeIngestionJob
from jobs.ingest_knowledge import KnowledgeIngestionJob
from storage.vector_store import VectorStore


router = APIRouter()


# -- helpers ----------------------------------------------------------------


_CHUNK_SIZE = 1024 * 1024  # 1 MiB streaming reads for uploaded files


def _reset_uploads_dir(uploads_dir: Path) -> None:
    """Wipe and re-create the target directory so each upload is a
    clean replacement of the prior corpus."""
    shutil.rmtree(uploads_dir, ignore_errors=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)


def _resolve_safe_target(uploads_dir: Path, relpath: str) -> Path:
    """Resolve ``uploads_dir / relpath`` and guarantee the result stays
    inside ``uploads_dir``. Raises ``HTTPException(400)`` on any
    traversal attempt (``..`` segments, absolute paths, symlink tricks)."""
    base = uploads_dir.resolve()
    candidate = (uploads_dir / relpath).resolve()
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


async def _save_uploads(
    files: list[UploadFile],
    uploads_dir: Path,
) -> int:
    """Stream every upload to disk under ``uploads_dir`` preserving the
    relative path carried in ``UploadFile.filename``. Returns the count
    of files actually written."""
    saved = 0
    for upload in files:
        relpath = upload.filename
        if not relpath:
            continue
        target = _resolve_safe_target(uploads_dir, relpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as sink:
            while True:
                chunk = await upload.read(_CHUNK_SIZE)
                if not chunk:
                    break
                sink.write(chunk)
        await upload.close()
        saved += 1
    return saved


def _make_progress_callback(
    job: Job,
    loop: asyncio.AbstractEventLoop,
):
    """Build a synchronous callback that schedules a progress push onto
    the main event loop — ingestion runs inside a worker thread so we
    cannot ``await`` directly from it."""

    def on_progress(message: str) -> None:
        asyncio.run_coroutine_threadsafe(
            job.push("progress", {"message": message}),
            loop,
        )

    return on_progress


async def _run_code_ingestion(
    job: Job,
    path: Path,
    store: VectorStore,
) -> None:
    loop = asyncio.get_running_loop()
    on_progress = _make_progress_callback(job, loop)
    try:
        result = await loop.run_in_executor(
            None,
            lambda: CodeIngestionJob(
                vector_store=store,
                should_use_llm=True,
                on_progress=on_progress,
            ).run(str(path)),
        )
        await job.push("done", result.model_dump())
    except Exception as exc:  # noqa: BLE001 — surface to the SSE client
        await job.push("error", {"message": str(exc)})
    finally:
        job.mark_complete()


async def _run_knowledge_ingestion(
    job: Job,
    path: Path,
    store: VectorStore,
) -> None:
    loop = asyncio.get_running_loop()
    on_progress = _make_progress_callback(job, loop)
    try:
        result = await loop.run_in_executor(
            None,
            lambda: KnowledgeIngestionJob(
                vector_store=store,
                should_use_llm=True,
                on_progress=on_progress,
            ).run(str(path)),
        )
        await job.push("done", result.model_dump())
    except Exception as exc:  # noqa: BLE001 — surface to the SSE client
        await job.push("error", {"message": str(exc)})
    finally:
        job.mark_complete()


# -- endpoints --------------------------------------------------------------


@router.post("/code", response_model=IngestionAck)
async def ingest_code(
    files: list[UploadFile] = File(...),
    store: VectorStore = Depends(get_vector_store),
) -> IngestionAck:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    job = registry.create()
    _reset_uploads_dir(CODE_UPLOADS_DIR)
    files_saved = await _save_uploads(files, CODE_UPLOADS_DIR)
    if files_saved == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    asyncio.create_task(_run_code_ingestion(job, CODE_UPLOADS_DIR, store))
    return IngestionAck(job_id=job.id, files_saved=files_saved)


@router.post("/knowledge", response_model=IngestionAck)
async def ingest_knowledge(
    files: list[UploadFile] = File(...),
    store: VectorStore = Depends(get_vector_store),
) -> IngestionAck:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    job = registry.create()
    _reset_uploads_dir(KNOWLEDGE_UPLOADS_DIR)
    files_saved = await _save_uploads(files, KNOWLEDGE_UPLOADS_DIR)
    if files_saved == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    asyncio.create_task(
        _run_knowledge_ingestion(job, KNOWLEDGE_UPLOADS_DIR, store)
    )
    return IngestionAck(job_id=job.id, files_saved=files_saved)


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE stream of a job's progress. Emits ``progress`` events while
    the worker runs, a terminal ``done`` or ``error`` event, and
    periodic ``ping`` keepalives so intermediaries do not close the
    connection on idle."""
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(job.events.get(), timeout=1.0)
                yield {"event": event.event, "data": json.dumps(event.data)}
                if event.event in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                if job.completed.is_set() and job.events.empty():
                    break
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(event_generator())
