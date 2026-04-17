from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents.schemas import AgentDecision
from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import RawDocumentChunk, RawCodeChunk
from normalization.schemas import NormalizedChunk
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore


def _make_embedded_chunk(
    source_file: str,
    embed_text: str,
    chunk_type: str = "knowledge",
    kind: str = "constraint",
    domain: str = "spectroscopy",
) -> EmbeddedChunk:
    if chunk_type == "code":
        raw = RawCodeChunk(
            source_file=source_file,
            raw_text=f"def test_func(): return '{source_file}'",
            name="test_func",
            chunk_type="code",
        )
    else:
        raw = RawDocumentChunk.from_raw_text(
            raw_text=f"raw text for {source_file}",
            source_file=source_file,
            metadata={"domain": domain},
        )

    normalized = NormalizedChunk(
        source_chunk=raw,
        kind=kind,
        subject="test subject",
        embed_text=embed_text,
    )

    return EmbeddedChunk(
        source_chunk=normalized,
        vector=[0.1] * 8,
        vector_model="test-model",
        vector_dimension=8,
    )


@pytest.fixture()
def mock_store() -> MagicMock:
    return MagicMock(spec=VectorStore)


@pytest.fixture()
def sample_agent_decision() -> AgentDecision:
    return AgentDecision(
        decision_type="dismissed_warning",
        summary="Developer dismissed a wavelength warning",
        rationale="The instrument is calibrated to a different baseline in this deployment.",
        code_ref="signal/processing.py::normalize_wavelength",
        constraint_ref="spec.pdf::minimum_wavelength",
        domain="spectroscopy",
        created_by="tester",
        metadata={"ticket": "SYN-123"},
        embed_text=(
            "Dismissed warning for normalize_wavelength because this deployment "
            "uses a different calibrated wavelength baseline."
        ),
    )


@pytest.fixture()
def knowledge_result() -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="spec.pdf",
        embed_text="Constraint: wavelength must exceed 0.5nm",
        chunk_type="knowledge",
        kind="constraint",
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.95,
        query_text="wavelength normalization",
        direction="code_to_knowledge",
    )


@pytest.fixture()
def code_result() -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="signal/processing.py",
        embed_text="Behavior: normalizes wavelength relative to reference",
        chunk_type="code",
        kind="behavior",
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.88,
        query_text="wavelength normalization",
        direction="knowledge_to_code",
    )