# Retrieval Layer Specification

**Version:** 0.1  
**Status:** Draft

---

## Overview

The retrieval layer sits between the vector store and the agent layer. It owns the logic for translating a query — a code chunk, a domain knowledge chunk, or a plain language question — into a ranked list of semantically relevant results from Actian. It does not own embedding, storage, or agent reasoning. It owns query construction, filter building, result ranking, and the two core retrieval directions the system is built around.

---

## Retrieval Directions

The system has three query patterns. All three hit the same Actian collection but differ in what is used as the query vector and what filters are applied.

**Code → Knowledge**  
Given a code chunk, find the domain knowledge chunks most semantically relevant to it. Used by the constraint monitoring agent to surface physical or scientific constraints relevant to a piece of code.

**Knowledge → Code**  
Given a domain knowledge chunk, find the code chunks most likely to be implementing or violating it. Used by the scientist-facing interface to answer "where in the codebase is this constraint relevant?"

**Free text → Both**  
Given a plain language question from a developer or scientist, embed the question and retrieve from both chunk types ranked together. Used by the query interface on both the CLI and the GUI.

---

## File Structure

```
retrieval/
├── __init__.py
├── retrieval.py        # core retrieval functions
├── pipelines.py        # higher-level query pipelines combining retrieval + LLM
├── filters.py          # typed filter builders for common query patterns
└── schemas.py          # RetrievalResult, RetrievalQuery
```

---

## Schemas — `retrieval/schemas.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from embeddings.schemas import EmbeddedChunk


@dataclass
class RetrievalQuery:
    """
    Represents a retrieval request before it is executed.
    Constructed by callers and passed to retrieval functions.
    """
    text: str                               # text to embed and search with
    direction: Literal[
        "code_to_knowledge",
        "knowledge_to_code",
        "free_text",
    ]
    filters: dict | None = None             # additional metadata filters
    k: int = 10                             # number of results to return
    score_threshold: float | None = None    # minimum similarity score


@dataclass
class RetrievalResult:
    """
    A single result returned by the retrieval layer.
    Wraps the matched EmbeddedChunk with retrieval metadata.
    """
    chunk: EmbeddedChunk
    score: float
    query_text: str                         # the text that produced this result
    direction: str                          # which retrieval direction was used

    @property
    def source_file(self) -> str:
        return self.chunk.source_chunk.source_chunk.source_file

    @property
    def chunk_type(self) -> str:
        return self.chunk.chunk_type

    @property
    def kind(self) -> str:
        return self.chunk.source_chunk.kind

    @property
    def embed_text(self) -> str:
        return self.chunk.embed_text
```

---

## Filters — `retrieval/filters.py`

Typed filter builders for the most common retrieval patterns. Callers use these rather than constructing raw dicts.

```python
from __future__ import annotations


def knowledge_filter(
    domain: str | None = None,
    knowledge_type: str | None = None,
    constraints_only: bool = False,
    min_confidence: float | None = None,
    source_type: str | None = None,
) -> dict:
    """Build a filter dict for knowledge chunk retrieval."""
    f: dict = {"chunk_type": "knowledge"}

    if domain:
        f["domain"] = domain
    if knowledge_type:
        f["knowledge_type"] = knowledge_type
    if constraints_only:
        f["contains_constraint"] = True
    if min_confidence is not None:
        f["confidence"] = {"$gte": min_confidence}
    if source_type:
        f["source_type"] = source_type

    return f


def code_filter(
    language: str | None = None,
    module_path: str | None = None,
) -> dict:
    """Build a filter dict for code chunk retrieval."""
    f: dict = {"chunk_type": "code"}

    if language:
        f["language"] = language
    if module_path:
        f["module_path"] = module_path

    return f


def constraint_filter(domain: str | None = None) -> dict:
    """Shorthand filter for constraint-only knowledge chunks."""
    return knowledge_filter(
        domain=domain,
        constraints_only=True,
        min_confidence=0.7,
    )
```

---

## Core Retrieval — `retrieval/retrieval.py`

```python
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
```

---

## Pipelines — `retrieval/pipelines.py`

Higher-level pipelines that combine retrieval with LLM explanation generation. These are what the agent layer calls rather than the raw retrieval functions.

```python
"""
Higher-level retrieval pipelines. Combine vector retrieval with LLM
explanation generation to produce human-readable output suitable for
both the developer CLI and the scientist GUI.
"""
from __future__ import annotations

import models
from retrieval.retrieval import code_to_knowledge, knowledge_to_code, free_text
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore


_CONFLICT_SYSTEM_PROMPT = """\
You are an assistant that explains relationships between source code and \
domain knowledge constraints. Given a code description and a set of \
relevant domain knowledge chunks, identify any conflicts, gaps, or \
relevant constraints the developer should be aware of.

Rules:
- Be specific — reference actual values, units, and thresholds from the
  domain knowledge.
- If there is a conflict, explain exactly what the code does wrong and
  what it should do instead.
- If there is no conflict, say so clearly and explain why the code is
  consistent with the constraints.
- Write in plain English suitable for a software developer.
- Do NOT use bullet points. Write in prose.
- Keep the response to 3-5 sentences.
"""

_SCIENTIST_SYSTEM_PROMPT = """\
You are an assistant that explains software behavior to domain experts \
who are not software developers. Given a domain constraint and a set of \
relevant code chunks, explain in plain language whether the software \
correctly implements the constraint.

Rules:
- Avoid programming terminology.
- Describe what the software does in terms of the domain — physical
  quantities, units, biological processes, chemical properties.
- If the software appears to violate the constraint, explain the
  practical consequence.
- Keep the response to 3-5 sentences.
"""


def check_code_against_constraints(
    code_embed_text: str,
    store: VectorStore,
    domain: str | None = None,
    k: int = 5,
) -> dict:
    """Retrieve domain constraints relevant to a code chunk and explain conflicts.

    Returns a dict with retrieved constraints and an LLM-generated explanation.
    Used by the constraint monitoring agent and the developer CLI.
    """
    results = code_to_knowledge(
        code_embed_text=code_embed_text,
        store=store,
        domain=domain,
        constraints_only=True,
        k=k,
    )

    if not results:
        return {
            "constraints": [],
            "explanation": "No relevant domain constraints found.",
            "has_conflict": False,
        }

    context = _format_knowledge_context(results)
    explanation = models.complete(
        system_prompt=_CONFLICT_SYSTEM_PROMPT,
        user_prompt=(
            f"Code description:\n{code_embed_text}\n\n"
            f"Relevant domain constraints:\n{context}"
        ),
    )

    return {
        "constraints": results,
        "explanation": explanation,
        "has_conflict": _detect_conflict_signal(explanation),
    }


def explain_constraint_coverage(
    knowledge_embed_text: str,
    store: VectorStore,
    language: str | None = None,
    k: int = 5,
) -> dict:
    """Find code relevant to a domain constraint and explain coverage.

    Returns a dict with relevant code chunks and an LLM explanation
    written for a domain expert, not a developer.
    Used by the scientist-facing GUI.
    """
    results = knowledge_to_code(
        knowledge_embed_text=knowledge_embed_text,
        store=store,
        language=language,
        k=k,
    )

    if not results:
        return {
            "code_chunks": [],
            "explanation": "No relevant code found for this constraint.",
            "is_implemented": False,
        }

    context = _format_code_context(results)
    explanation = models.complete(
        system_prompt=_SCIENTIST_SYSTEM_PROMPT,
        user_prompt=(
            f"Domain constraint:\n{knowledge_embed_text}\n\n"
            f"Relevant code:\n{context}"
        ),
    )

    return {
        "code_chunks": results,
        "explanation": explanation,
        "is_implemented": _detect_implementation_signal(explanation),
    }


def answer_question(
    question: str,
    store: VectorStore,
    k: int = 10,
) -> dict:
    """Answer a plain language question using both knowledge and code chunks."""
    results = free_text(question=question, store=store, k=k)

    if not results:
        return {
            "results": [],
            "answer": "No relevant information found.",
        }

    context = _format_mixed_context(results)
    answer = models.complete(
        system_prompt=(
            "You are an assistant that answers questions about a software "
            "codebase and its domain knowledge. Use the provided context "
            "from both source code and domain documents to answer the "
            "question clearly and concisely."
        ),
        user_prompt=f"Question: {question}\n\nContext:\n{context}",
    )

    return {
        "results": results,
        "answer": answer,
    }


def _format_knowledge_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] {r.kind.upper()} from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _format_code_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] CODE from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _format_mixed_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        label = "DOMAIN KNOWLEDGE" if r.chunk_type == "knowledge" else "CODE"
        lines.append(
            f"[{i}] {label} from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _detect_conflict_signal(explanation: str) -> bool:
    conflict_signals = [
        "violates", "conflict", "incorrect", "wrong", "should not",
        "must not", "exceeds", "below the", "above the", "invalid",
    ]
    lower = explanation.lower()
    return any(signal in lower for signal in conflict_signals)


def _detect_implementation_signal(explanation: str) -> bool:
    implementation_signals = [
        "correctly", "implements", "consistent", "respects",
        "enforces", "handles", "validates",
    ]
    lower = explanation.lower()
    return any(signal in lower for signal in implementation_signals)
```

---

## `retrieval/__init__.py`

```python
from retrieval.retrieval import (
    retrieve,
    code_to_knowledge,
    knowledge_to_code,
    free_text,
)
from retrieval.pipelines import (
    check_code_against_constraints,
    explain_constraint_coverage,
    answer_question,
)
from retrieval.schemas import RetrievalQuery, RetrievalResult

__all__ = [
    "retrieve",
    "code_to_knowledge",
    "knowledge_to_code",
    "free_text",
    "check_code_against_constraints",
    "explain_constraint_coverage",
    "answer_question",
    "RetrievalQuery",
    "RetrievalResult",
]
```

---

## Out of Scope

The following are explicitly out of scope for this layer and are handled in subsequent stages:

- Reranking — post-retrieval cross-encoder reranking is a future optimization
- Caching — query result caching belongs in the agent layer
- Memory — storing retrieval decisions over time belongs in the agent layer
- Streaming — streaming LLM responses for the GUI belongs in the API layer

---

## Tests Needed

### Without LLM (fast, no Ollama required)

- `retrieve()` returns `RetrievalResult` objects
- `code_to_knowledge()` applies `chunk_type: knowledge` filter
- `knowledge_to_code()` applies `chunk_type: code` filter
- `free_text()` returns results from both chunk types merged by score
- `_free_text_retrieve()` merges and re-ranks correctly
- `_build_directional_filter()` returns correct base filter per direction
- `check_code_against_constraints()` returns dict with correct keys
- `explain_constraint_coverage()` returns dict with correct keys
- `_detect_conflict_signal()` correctly identifies conflict language
- `_detect_implementation_signal()` correctly identifies implementation language

### With LLM (`pytest.mark.llm`)

- `check_code_against_constraints()` returns non-empty explanation
- `answer_question()` returns a coherent answer

### With Actian (`pytest.mark.actian`)

- Full pipeline: ingest → normalize → embed → store → retrieve → explain

---

*Previous step: Storage*  
*Next step: Agent Layer*
