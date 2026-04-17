"""Tests for retrieval/filters.py."""
from __future__ import annotations

from retrieval.filters import code_filter, constraint_filter, knowledge_filter


# ---------------------------------------------------------------------------
# knowledge_filter
# ---------------------------------------------------------------------------

def test_knowledge_filter_base_has_chunk_type():
    f = knowledge_filter()
    assert f["chunk_type"] == "knowledge"


def test_knowledge_filter_adds_domain():
    f = knowledge_filter(domain="spectroscopy")
    assert f["domain"] == "spectroscopy"


def test_knowledge_filter_adds_knowledge_type():
    f = knowledge_filter(knowledge_type="constraint")
    assert f["knowledge_type"] == "constraint"


def test_knowledge_filter_constraints_only():
    f = knowledge_filter(constraints_only=True)
    assert f["contains_constraint"] is True


def test_knowledge_filter_min_confidence():
    f = knowledge_filter(min_confidence=0.8)
    assert f["confidence"] == {"$gte": 0.8}


def test_knowledge_filter_source_type():
    f = knowledge_filter(source_type="instrument_spec")
    assert f["source_type"] == "instrument_spec"


def test_knowledge_filter_no_optional_fields_by_default():
    f = knowledge_filter()
    assert "domain" not in f
    assert "knowledge_type" not in f
    assert "contains_constraint" not in f
    assert "confidence" not in f
    assert "source_type" not in f


def test_knowledge_filter_all_options():
    f = knowledge_filter(
        domain="genomics",
        knowledge_type="procedure",
        constraints_only=True,
        min_confidence=0.9,
        source_type="journal_paper",
    )
    assert f["chunk_type"] == "knowledge"
    assert f["domain"] == "genomics"
    assert f["knowledge_type"] == "procedure"
    assert f["contains_constraint"] is True
    assert f["confidence"] == {"$gte": 0.9}
    assert f["source_type"] == "journal_paper"


# ---------------------------------------------------------------------------
# code_filter
# ---------------------------------------------------------------------------

def test_code_filter_base_has_chunk_type():
    f = code_filter()
    assert f["chunk_type"] == "code"


def test_code_filter_adds_language():
    f = code_filter(language="python")
    assert f["language"] == "python"


def test_code_filter_adds_module_path():
    f = code_filter(module_path="signal.processing")
    assert f["module_path"] == "signal.processing"


def test_code_filter_no_optional_fields_by_default():
    f = code_filter()
    assert "language" not in f
    assert "module_path" not in f


# ---------------------------------------------------------------------------
# constraint_filter
# ---------------------------------------------------------------------------

def test_constraint_filter_sets_contains_constraint():
    f = constraint_filter()
    assert f["contains_constraint"] is True


def test_constraint_filter_sets_min_confidence():
    f = constraint_filter()
    assert f["confidence"] == {"$gte": 0.7}


def test_constraint_filter_sets_chunk_type():
    f = constraint_filter()
    assert f["chunk_type"] == "knowledge"


def test_constraint_filter_includes_domain_when_provided():
    f = constraint_filter(domain="aerospace")
    assert f["domain"] == "aerospace"


def test_constraint_filter_no_domain_by_default():
    f = constraint_filter()
    assert "domain" not in f