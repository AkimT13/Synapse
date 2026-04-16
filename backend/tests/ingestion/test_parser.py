"""Tests for the knowledge document parser."""
from __future__ import annotations

from pathlib import Path

import pytest

docling = pytest.importorskip("docling", reason="docling is required for parser tests")

from docling.document_converter import ConversionResult

from ingestion.knowledge.parser import parse_document


def test_parse_document_returns_conversion_result(sample_pdf: Path) -> None:
    result = parse_document(sample_pdf)
    assert isinstance(result, ConversionResult)


def test_unsupported_format_raises_value_error(tmp_path: Path) -> None:
    bad_file = tmp_path / "data.xlsx"
    bad_file.write_text("")
    with pytest.raises(ValueError, match="Unsupported format"):
        parse_document(bad_file)


def test_missing_file_raises_file_not_found_error() -> None:
    with pytest.raises(FileNotFoundError):
        parse_document("/nonexistent/path/doc.pdf")
