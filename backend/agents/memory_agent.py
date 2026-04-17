from __future__ import annotations

from agents.schemas import AgentDecision
from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import RawDocumentChunk
from normalization.schemas import NormalizedChunk
import models
from storage.vector_store import VectorStore


def build_memory_chunk(decision: AgentDecision) -> EmbeddedChunk:
    """
    Convert an AgentDecision into an EmbeddedChunk using the existing
    RawChunk -> NormalizedChunk -> EmbeddedChunk pipeline.

    Agent memory is stored as a knowledge-style document chunk so it can
    reuse the same storage schema, embedding flow, and reconstruction path
    as all other persisted chunks.
    """
    raw = RawDocumentChunk.from_raw_text(
        raw_text=_build_raw_text(decision),
        source_file=_build_source_file(decision),
        metadata={
            "domain": decision.domain or "",
            "knowledge_type": "agent_memory",
            "contains_constraint": False,
            "constraint_name": decision.constraint_ref,
            "source_type": "agent_decision",
            "confidence": 1.0,
            "decision_type": decision.decision_type,
            "code_ref": decision.code_ref,
            "constraint_ref": decision.constraint_ref,
            "created_by": decision.created_by,
            **decision.metadata,
        },
    )

    normalized = NormalizedChunk(
        source_chunk=raw,
        kind="mapping",
        subject=decision.summary,
        condition=None,
        constraint=decision.rationale,
        failure_mode=None,
        keywords=_build_keywords(decision),
        embed_text=decision.embed_text,
    )

    vector = models.embed_single(decision.embed_text)

    return EmbeddedChunk(
        source_chunk=normalized,
        vector=vector,
        vector_model=models.get_config().embedding_model,
        vector_dimension=len(vector),
    )


def store_decision(
    decision: AgentDecision,
    store: VectorStore,
) -> EmbeddedChunk:
    """
    Embed and persist a single agent decision.

    Returns the EmbeddedChunk that was written so callers can inspect its
    deterministic IDs and storage-ready lineage.
    """
    chunk = build_memory_chunk(decision)
    store.upsert([chunk])
    return chunk


def store_decisions(
    decisions: list[AgentDecision],
    store: VectorStore,
) -> int:
    """
    Embed and persist multiple agent decisions in one batch.

    Returns the number of stored chunks reported by VectorStore.upsert().
    """
    chunks = [build_memory_chunk(decision) for decision in decisions]
    if not chunks:
        return 0
    return store.upsert(chunks)


def _build_raw_text(decision: AgentDecision) -> str:
    parts = [
        f"Decision type: {decision.decision_type}",
        f"Summary: {decision.summary}",
    ]

    if decision.rationale:
        parts.append(f"Rationale: {decision.rationale}")
    if decision.code_ref:
        parts.append(f"Code reference: {decision.code_ref}")
    if decision.constraint_ref:
        parts.append(f"Constraint reference: {decision.constraint_ref}")
    if decision.domain:
        parts.append(f"Domain: {decision.domain}")

    return "\n".join(parts)


def _build_source_file(decision: AgentDecision) -> str:
    return f"agent_memory/{decision.decision_type}.md"


def _build_keywords(decision: AgentDecision) -> list[str]:
    keywords = [decision.decision_type]

    if decision.domain:
        keywords.append(decision.domain)
    if decision.code_ref:
        keywords.append(decision.code_ref)
    if decision.constraint_ref:
        keywords.append(decision.constraint_ref)

    return keywords