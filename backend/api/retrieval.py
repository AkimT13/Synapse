"""
HTTP surface for Synapse retrieval flows.

This router exposes the three user-facing retrieval directions:

* ``/retrieve/code-to-knowledge`` — given code, surface relevant domain
  constraints plus an LLM explanation of whether they hold.
* ``/retrieve/knowledge-to-code`` — given a constraint, surface the code
  chunks that implement (or fail to implement) it.
* ``/retrieve/free`` — free-text Q&A over the unified corpus.

Each endpoint wraps a pipeline from ``retrieval.pipelines`` and shapes the
result into the ``RetrievalResponse`` contract consumed by the frontend.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from api.dependencies import get_vector_store
from api.schemas import (
    CodeToKnowledgeRequest,
    FreeTextRequest,
    KnowledgeToCodeRequest,
    RetrievalResponse,
    make_source_ref,
    truncate_for_preview,
)
from api.settings import CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR
from ingestion.code.python_parser import PythonParser
from normalization.code.normalizer import CodeNormalizer
from retrieval.pipelines import (
    answer_question,
    check_code_against_constraints,
    explain_constraint_coverage,
)
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore

router = APIRouter()


def _prepare_code_query(text: str) -> str:
    raw_chunks = PythonParser().parse_file(
        text,
        file_path="<query>",
        module_path="<query>",
    )
    if not raw_chunks:
        return text
    normalizer = CodeNormalizer(should_use_llm=True)
    normalized = normalizer.normalize_batch(raw_chunks)
    if not normalized:
        return text
    # Use the first chunk's embed_text as the representative query.
    # Callers who want per-chunk retrieval can split their query themselves.
    return normalized[0].embed_text


def _derive_title(result: RetrievalResult) -> str:
    raw = result.chunk.source_chunk.source_chunk
    if result.chunk_type == "code":
        return getattr(raw, "name", None) or Path(result.source_file).name
    return getattr(raw, "section_heading", None) or Path(result.source_file).name


def _to_relative_source_file(result: RetrievalResult) -> str:
    """Return the chunk's source_file as a POSIX path relative to its
    uploads root so frontend links match the corpora API's tree paths."""
    absolute = Path(result.source_file)
    root = CODE_UPLOADS_DIR if result.chunk_type == "code" else KNOWLEDGE_UPLOADS_DIR
    try:
        relative = absolute.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return absolute.name
    return relative.as_posix()


def _build_response(
    results: list[RetrievalResult],
    *,
    explanation: str | None = None,
    answer: str | None = None,
    has_conflict: bool | None = None,
    is_implemented: bool | None = None,
    used_fallback: bool | None = None,
) -> RetrievalResponse:
    sources = [
        make_source_ref(
            index=i,
            chunk_type=result.chunk_type,
            source_file=_to_relative_source_file(result),
            title=_derive_title(result),
            excerpt=truncate_for_preview(result.embed_text),
            score=result.score,
            kind=result.kind,
        )
        for i, result in enumerate(results, start=1)
    ]
    return RetrievalResponse(
        results=sources,
        explanation=explanation,
        answer=answer,
        has_conflict=has_conflict,
        is_implemented=is_implemented,
        used_fallback=used_fallback,
    )


@router.post("/retrieve/code-to-knowledge", response_model=RetrievalResponse)
def code_to_knowledge(
    payload: CodeToKnowledgeRequest,
    store: VectorStore = Depends(get_vector_store),
) -> RetrievalResponse:
    query = _prepare_code_query(payload.text)
    result = check_code_against_constraints(
        code_embed_text=query,
        store=store,
        domain=payload.domain,
        k=payload.k,
    )
    return _build_response(
        results=result["constraints"],
        explanation=result["explanation"],
        has_conflict=result["has_conflict"],
        used_fallback=result.get("used_fallback"),
    )


@router.post("/retrieve/knowledge-to-code", response_model=RetrievalResponse)
def knowledge_to_code(
    payload: KnowledgeToCodeRequest,
    store: VectorStore = Depends(get_vector_store),
) -> RetrievalResponse:
    result = explain_constraint_coverage(
        knowledge_embed_text=payload.text,
        store=store,
        language=payload.language,
        k=payload.k,
    )
    return _build_response(
        results=result["code_chunks"],
        explanation=result["explanation"],
        is_implemented=result["is_implemented"],
    )


@router.post("/retrieve/free", response_model=RetrievalResponse)
def free(
    payload: FreeTextRequest,
    store: VectorStore = Depends(get_vector_store),
) -> RetrievalResponse:
    result = answer_question(
        question=payload.question,
        store=store,
        k=payload.k,
    )
    return _build_response(
        results=result["results"],
        answer=result["answer"],
    )
