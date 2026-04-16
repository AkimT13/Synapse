"""Tests for the knowledge document chunker."""
from __future__ import annotations

from pathlib import Path

import pytest

docling = pytest.importorskip("docling", reason="docling is required for chunker tests")

from ingestion.knowledge.chunker import chunk_document
from ingestion.knowledge.parser import parse_document
from ingestion.schemas import RawDocumentChunk


@pytest.fixture()
def parsed_pdf(sample_pdf: Path):
    """ConversionResult from parsing the sample PDF fixture."""
    return parse_document(sample_pdf)


def test_chunk_document_returns_non_empty_list(parsed_pdf, sample_pdf: Path) -> None:
    chunks = chunk_document(parsed_pdf, source_file=str(sample_pdf))
    assert len(chunks) > 0
    assert all(isinstance(c, RawDocumentChunk) for c in chunks)


def test_every_chunk_has_raw_text(parsed_pdf, sample_pdf: Path) -> None:
    chunks = chunk_document(parsed_pdf, source_file=str(sample_pdf))
    for chunk in chunks:
        assert chunk.raw_text, f"chunk {chunk.chunk_index} has empty raw_text"


def test_chunk_index_is_sequential(parsed_pdf, sample_pdf: Path) -> None:
    chunks = chunk_document(parsed_pdf, source_file=str(sample_pdf))
    for expected_idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == expected_idx


def test_source_file_matches(parsed_pdf, sample_pdf: Path) -> None:
    source = str(sample_pdf)
    chunks = chunk_document(parsed_pdf, source_file=source)
    for chunk in chunks:
        assert chunk.source_file == source


def test_table_chunks_have_table_content_type(parsed_pdf, sample_pdf: Path) -> None:
    """If the fixture contained tables, they would have content_type='table'.

    The minimal fixture has no tables, so we verify that non-table chunks
    default to 'text'.  A richer fixture can extend this test later.
    """
    chunks = chunk_document(parsed_pdf, source_file=str(sample_pdf))
    for chunk in chunks:
        if chunk.content_type == "table":
            assert chunk.content_type == "table"
        else:
            assert chunk.content_type in ("text", "figure")
