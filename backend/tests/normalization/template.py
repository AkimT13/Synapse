"""
Tests for the deterministic template builder and domain-signal heuristic.

All tests construct RawCodeChunk objects directly -- no parsing or
filesystem access required.
"""
from __future__ import annotations

from ingestion.schemas import ParameterInfo, RawCodeChunk
from normalization.code.template import build_template, has_domain_signals


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


# ---------------------------------------------------------------------------
# build_template tests
# ---------------------------------------------------------------------------


def test_template_includes_function_name_and_module() -> None:
    chunk = _make_chunk(name="process_order", module_path="shop.orders")
    result = build_template(chunk)

    assert "`process_order`" in result
    assert "`shop.orders`" in result


def test_template_formats_typed_parameters() -> None:
    chunk = _make_chunk(
        name="create_user",
        parameters=[
            ParameterInfo(name="self"),
            ParameterInfo(name="name", type_annotation="str"),
            ParameterInfo(name="age", type_annotation="int", default_value="0"),
        ],
    )
    result = build_template(chunk)

    # self should be excluded, name and age included
    assert "name: str" in result
    assert "age: int = 0" in result
    assert "self" not in result


def test_template_includes_docstring_when_present() -> None:
    chunk = _make_chunk(
        name="validate_input",
        docstring="Ensures the input conforms to the schema.",
    )
    result = build_template(chunk)

    assert "Ensures the input conforms to the schema." in result


def test_template_omits_sections_with_no_data() -> None:
    chunk = _make_chunk(
        name="simple",
        parameters=[],
        return_type=None,
        docstring=None,
        calls=[],
    )
    result = build_template(chunk)

    assert "Takes parameters" not in result
    assert "Returns" not in result
    assert "Docstring" not in result
    assert "Calls" not in result


def test_template_includes_calls() -> None:
    chunk = _make_chunk(
        name="orchestrate",
        calls=["fetch_data", "transform", "store"],
    )
    result = build_template(chunk)

    assert "fetch_data" in result
    assert "transform" in result
    assert "store" in result


# ---------------------------------------------------------------------------
# has_domain_signals tests
# ---------------------------------------------------------------------------


def test_has_domain_signals_false_for_dunder_methods() -> None:
    chunk = _make_chunk(name="__repr__")
    assert has_domain_signals(chunk) is False

    chunk = _make_chunk(name="__eq__")
    assert has_domain_signals(chunk) is False

    chunk = _make_chunk(name="__str__")
    assert has_domain_signals(chunk) is False


def test_has_domain_signals_false_for_test_functions() -> None:
    chunk = _make_chunk(name="test_user_creation")
    assert has_domain_signals(chunk) is False

    chunk = _make_chunk(name="test_basic")
    assert has_domain_signals(chunk) is False


def test_has_domain_signals_true_for_domain_typed_function() -> None:
    chunk = _make_chunk(
        name="calculate_risk_score",
        parameters=[
            ParameterInfo(name="patient", type_annotation="PatientRecord"),
            ParameterInfo(name="history", type_annotation="ClinicalHistory"),
        ],
        return_type="RiskAssessment",
        docstring="Computes the aggregate risk score for a clinical trial participant.",
    )
    assert has_domain_signals(chunk) is True
