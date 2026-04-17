"""Tests for the knowledge ingestion pipeline."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

docling = pytest.importorskip("docling", reason="docling is required for pipeline tests")

from ingestion.knowledge.pipeline import ingest_directory, ingest_file
from ingestion.schemas import RawDocumentChunk


def test_ingest_file_returns_document_chunks(sample_pdf: Path) -> None:
    chunks = ingest_file(sample_pdf)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, RawDocumentChunk) for c in chunks)


def test_ingest_directory_returns_chunks_from_all_documents(
    sample_pdf: Path,
    tmp_path: Path,
) -> None:
    # Copy the fixture twice to simulate a directory with multiple docs
    shutil.copy(sample_pdf, tmp_path / "a.pdf")
    shutil.copy(sample_pdf, tmp_path / "b.pdf")

    chunks = ingest_directory(tmp_path)
    assert isinstance(chunks, list)
    assert len(chunks) > 0

    # Chunks should reference both source files
    sources = {c.source_file for c in chunks}
    assert len(sources) == 2


def test_ingest_directory_walks_subdirectories(
    sample_pdf: Path,
    tmp_path: Path,
) -> None:
    # A user-uploaded folder can be nested — the pipeline must recurse.
    shutil.copy(sample_pdf, tmp_path / "top.pdf")
    (tmp_path / "specs" / "regulatory").mkdir(parents=True)
    shutil.copy(sample_pdf, tmp_path / "specs" / "regulatory" / "nested.pdf")
    # Default-excluded directory: must not be walked.
    (tmp_path / ".git").mkdir()
    shutil.copy(sample_pdf, tmp_path / ".git" / "ignored.pdf")

    chunks = ingest_directory(tmp_path)
    sources = {c.source_file for c in chunks}
    assert any(s.endswith("top.pdf") for s in sources)
    assert any(s.endswith("nested.pdf") for s in sources)
    assert not any(".git" in s for s in sources)
