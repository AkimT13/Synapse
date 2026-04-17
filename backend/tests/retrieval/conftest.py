"""Shared fixtures for retrieval tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import RawDocumentChunk
from normalization.schemas import NormalizedChunk
from retrieval.schemas import RetrievalResult
from storage.vector_store import SearchResult, VectorStore


def _make_embedded_chunk(
    source_file: str,
    embed_text: str,
    chunk_type: str = "knowledge",
    kind: str = "constraint",
    domain: str = "spectroscopy",
) -> EmbeddedChunk:
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


def _make_search_result(
    source_file: str,
    embed_text: str,
    score: float = 0.9,
    chunk_type: str = "knowledge",
) -> SearchResult:
    chunk = _make_embedded_chunk(
        source_file=source_file,
        embed_text=embed_text,
        chunk_type=chunk_type,
    )
    return SearchResult(id=chunk.id, score=score, chunk=chunk)


@pytest.fixture()
def mock_store() -> MagicMock:
    """A mock VectorStore that returns controllable search results."""
    store = MagicMock(spec=VectorStore)
    store.search.return_value = [
        _make_search_result("spec.pdf", "Constraint: wavelength must exceed 0.5nm", score=0.95),
        _make_search_result("manual.pdf", "Definition: spectral resolution", score=0.80),
    ]
    return store


@pytest.fixture()
def mock_store_empty() -> MagicMock:
    """A mock VectorStore that returns no results."""
    store = MagicMock(spec=VectorStore)
    store.search.return_value = []
    return store


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
    from ingestion.schemas import RawCodeChunk
    from normalization.schemas import NormalizedChunk

    raw = RawCodeChunk(
        source_file="signal/processing.py",
        raw_text="def normalize_wavelength(val, ref=632.8): ...",
        name="normalize_wavelength",
        chunk_type="code",
    )
    normalized = NormalizedChunk(
        source_chunk=raw,
        kind="behavior",
        subject="normalize_wavelength",
        embed_text="Behavior: normalizes wavelength relative to reference",
    )
    chunk = EmbeddedChunk(
        source_chunk=normalized,
        vector=[0.1] * 8,
        vector_model="test-model",
        vector_dimension=8,
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.88,
        query_text="wavelength normalization",
        direction="knowledge_to_code",
    )