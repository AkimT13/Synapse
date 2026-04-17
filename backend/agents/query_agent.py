from __future__ import annotations

from agents.schemas import QueryResponse
from retrieval.pipelines import answer_question
from storage.vector_store import VectorStore


def answer(
    question: str,
    store: VectorStore,
    k: int = 10,
) -> QueryResponse:
    """
    Answer a natural-language question using the existing retrieval pipeline.

    This is a thin typed wrapper around retrieval.pipelines.answer_question()
    so the agent layer owns response shaping without re-implementing retrieval
    or LLM logic.
    """
    result = answer_question(question=question, store=store, k=k)

    return QueryResponse(
        question=question,
        answer=result["answer"],
        results=result["results"],
    )