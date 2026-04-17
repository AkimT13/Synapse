from __future__ import annotations

from agents.schemas import ConflictReport
from retrieval.pipelines import check_code_against_constraints
from storage.vector_store import VectorStore


def check_code(
    code_embed_text: str,
    store: VectorStore,
    domain: str | None = None,
    k: int = 5,
) -> ConflictReport:
    """
    Check a code description against relevant domain constraints.

    This is a thin typed wrapper around
    retrieval.pipelines.check_code_against_constraints() so the agent layer
    owns response shaping without re-implementing retrieval or explanation
    logic.
    """
    result = check_code_against_constraints(
        code_embed_text=code_embed_text,
        store=store,
        domain=domain,
        k=k,
    )

    return ConflictReport(
        code_embed_text=code_embed_text,
        constraints=result["constraints"],
        explanation=result["explanation"],
        has_conflict=result["has_conflict"],
        memory_hits=[],
    )