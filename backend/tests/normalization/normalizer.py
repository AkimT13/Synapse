"""
Tests for the CodeNormalizer.

LLM calls are mocked so tests are fast, deterministic, and never
require API credentials.
"""
from __future__ import annotations

from unittest.mock import patch

from ingestion.schemas import ParameterInfo, RawCodeChunk
from normalization.code.normalizer import CodeNormalizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(**overrides) -> RawCodeChunk:
    """Build a minimal RawCodeChunk with sensible defaults."""
    defaults = {
        "source_file": "test.py",
        "raw_text": "def foo(): pass",
        "name": "foo",
        "module_path": "mypackage.module",
    }
    defaults.update(overrides)
    return RawCodeChunk(**defaults)


def _domain_chunk() -> RawCodeChunk:
    """A chunk that should trigger LLM rewriting."""
    return _make_chunk(
        name="calculate_risk_score",
        parameters=[
            ParameterInfo(name="patient", type_annotation="PatientRecord"),
        ],
        return_type="RiskAssessment",
        docstring="Computes the aggregate risk score.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_normalizer_uses_template_when_llm_disabled() -> None:
    chunk = _domain_chunk()
    normalizer = CodeNormalizer(should_use_llm=False)

    result = normalizer.normalize(chunk)

    assert "`calculate_risk_score`" in result.embed_text
    assert result.embed_text is not None


def test_normalizer_calls_llm_for_domain_rich_chunks() -> None:
    chunk = _domain_chunk()
    normalizer = CodeNormalizer(should_use_llm=True)

    with patch("normalization.code.normalizer.models.complete") as mock_complete:
        mock_complete.return_value = "LLM rewritten description of risk scoring."
        result = normalizer.normalize(chunk)

    mock_complete.assert_called_once()
    assert result.embed_text == "LLM rewritten description of risk scoring."


def test_normalizer_falls_back_to_template_on_llm_error() -> None:
    chunk = _domain_chunk()
    normalizer = CodeNormalizer(should_use_llm=True)

    with patch("normalization.code.normalizer.models.complete") as mock_complete:
        mock_complete.side_effect = RuntimeError("API down")
        result = normalizer.normalize(chunk)

    # Should fall back to template, not raise
    assert "`calculate_risk_score`" in result.embed_text


def test_normalizer_infers_constraint_kind_for_validation_functions() -> None:
    chunk = _make_chunk(name="validate_email_format")
    normalizer = CodeNormalizer(should_use_llm=False)

    result = normalizer.normalize(chunk)
    assert result.kind == "constraint"


def test_normalizer_extracts_keywords_from_name_and_types() -> None:
    chunk = _make_chunk(
        name="transform_patient_data",
        parameters=[
            ParameterInfo(name="record", type_annotation="PatientRecord"),
        ],
        imports=["pandas", "numpy.linalg"],
    )
    normalizer = CodeNormalizer(should_use_llm=False)

    result = normalizer.normalize(chunk)

    assert "transform" in result.keywords
    assert "patient" in result.keywords
    assert "data" in result.keywords
    assert "PatientRecord" in [k for k in result.keywords] or "patientrecord" in result.keywords
    assert "pandas" in result.keywords
