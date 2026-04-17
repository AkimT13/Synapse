from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ingestion.schemas import deterministic_id
from retrieval.schemas import RetrievalResult


class AgentDecision(BaseModel):
    """
    A persisted agent-side decision or review outcome.

    This is intentionally separate from retrieval/storage schemas.
    The memory agent can translate this into the existing
    RawChunk -> NormalizedChunk -> EmbeddedChunk pipeline for storage.
    """

    id: str = ""

    decision_type: Literal[
        "dismissed_warning",
        "accepted_warning",
        "query_feedback",
        "drift_baseline",
    ]

    summary: str
    rationale: str | None = None

    code_ref: str | None = None
    constraint_ref: str | None = None
    domain: str | None = None

    created_by: str = "agent"
    metadata: dict = Field(default_factory=dict)

    embed_text: str

    @model_validator(mode="after")
    def _set_deterministic_id(self) -> AgentDecision:
        if not self.id:
            self.id = deterministic_id(
                "::".join(
                    [
                        "agent-decision",
                        self.decision_type,
                        self.summary,
                        self.rationale or "",
                        self.code_ref or "",
                        self.constraint_ref or "",
                        self.domain or "",
                        self.created_by,
                        self.embed_text,
                    ]
                )
            )
        return self


class ConflictReport(BaseModel):
    """
    Typed wrapper around retrieval.pipelines.check_code_against_constraints().
    """

    code_embed_text: str
    constraints: list[RetrievalResult] = Field(default_factory=list)
    explanation: str
    has_conflict: bool
    memory_hits: list[RetrievalResult] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """
    Typed wrapper around retrieval.pipelines.answer_question().
    """

    question: str
    answer: str
    results: list[RetrievalResult] = Field(default_factory=list)