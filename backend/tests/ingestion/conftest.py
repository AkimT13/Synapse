"""Shared fixtures for ingestion tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample.pdf"


@pytest.fixture()
def sample_pdf() -> Path:
    """Path to the minimal test PDF in tests/fixtures/."""
    assert SAMPLE_PDF.exists(), f"Fixture missing: {SAMPLE_PDF}"
    return SAMPLE_PDF


@pytest.fixture()
def fixtures_dir() -> Path:
    """Path to the tests/fixtures/ directory."""
    assert FIXTURES_DIR.is_dir(), f"Fixtures directory missing: {FIXTURES_DIR}"
    return FIXTURES_DIR
