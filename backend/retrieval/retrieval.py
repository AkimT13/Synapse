"""
Core retrieval functions. Thin wrappers around VectorStore.search()
that handle embedding the query text, applying typed filters, and
returning RetrievalResult objects.
"""
from __future__ import annotations

import models
from retrieval.filters import code_filter, knowledge_filter
from retrieval.schemas import RetrievalQuery, RetrievalResult
from storage.vector_store import VectorStore


def retrieve(
    query: RetrievalQuery,
    store: VectorStore,
) -> list[RetrievalResult]:
    """Execute a retrieval query against the vector store.

    Embeds query.text, applies direction-appropriate filters,
    and returns ranked RetrievalResult objects.
    """
    query_vector = models.embed_single(query.text)

    if query.direction == "free_text":
        return _free_text_retrieve(query, query_vector, store)

    filters = _build_directional_filter(query)
    results = store.search(
        vector=query_vector,
        k=query.k,
        filters=filters,
    )

    return [
        RetrievalResult(
            chunk=r.chunk,
            score=r.score,
            query_text=query.text,
            direction=query.direction,
        )
        for r in results
        if query.score_threshold is None or r.score >= query.score_threshold
    ]


def code_to_knowledge(
    code_embed_text: str,
    store: VectorStore,
    domain: str | None = None,
    constraints_only: bool = False,
    k: int = 10,
) -> list[RetrievalResult]:
    """Find domain knowledge chunks relevant to a code chunk."""
    query = RetrievalQuery(
        text=code_embed_text,
        direction="code_to_knowledge",
        filters=knowledge_filter(
            domain=domain,
            constraints_only=constraints_only,
        ),
        k=k,
    )
    return retrieve(query, store)


def knowledge_to_code(
    knowledge_embed_text: str,
    store: VectorStore,
    language: str | None = None,
    k: int = 10,
) -> list[RetrievalResult]:
    """Find code chunks relevant to a domain knowledge chunk."""
    query = RetrievalQuery(
        text=knowledge_embed_text,
        direction="knowledge_to_code",
        filters=code_filter(language=language),
        k=k,
    )
    return retrieve(query, store)


def free_text(
    question: str,
    store: VectorStore,
    k: int = 10,
) -> list[RetrievalResult]:
    """Retrieve from both knowledge and code chunks for a plain language question."""
    query = RetrievalQuery(
        text=question,
        direction="free_text",
        k=k,
    )
    return retrieve(query, store)


def _build_directional_filter(query: RetrievalQuery) -> dict:
    if query.direction == "code_to_knowledge":
        base = knowledge_filter()
    else:
        base = code_filter()

    if query.filters:
        base.update(query.filters)

    return base


def _free_text_retrieve(
    query: RetrievalQuery,
    query_vector: list[float],
    store: VectorStore,
) -> list[RetrievalResult]:
    """Retrieve from both chunk types and merge by score."""
    knowledge_results = store.search(
        vector=query_vector,
        k=query.k,
        filters={"chunk_type": "knowledge"},
    )
    code_results = store.search(
        vector=query_vector,
        k=query.k,
        filters={"chunk_type": "code"},
    )

    all_results = [
        RetrievalResult(
            chunk=r.chunk,
            score=r.score,
            query_text=query.text,
            direction="free_text",
        )
        for r in knowledge_results + code_results
        if query.score_threshold is None or r.score >= query.score_threshold
    ]

    return sorted(all_results, key=lambda r: r.score, reverse=True)[: query.k]