"""Tests for retrieval/schemas.py."""
from __future__ import annotations

from retrieval.schemas import RetrievalQuery, RetrievalResult


# ---------------------------------------------------------------------------
# RetrievalQuery
# ---------------------------------------------------------------------------

def test_retrieval_query_defaults():
    q = RetrievalQuery(text="test query", direction="free_text")
    assert q.k == 10
    assert q.filters is None
    assert q.score_threshold is None


def test_retrieval_query_all_fields():
    q = RetrievalQuery(
        text="wavelength",
        direction="code_to_knowledge",
        filters={"domain": "spectroscopy"},
        k=5,
        score_threshold=0.7,
    )
    assert q.text == "wavelength"
    assert q.direction == "code_to_knowledge"
    assert q.filters == {"domain": "spectroscopy"}
    assert q.k == 5
    assert q.score_threshold == 0.7


# ---------------------------------------------------------------------------
# RetrievalResult properties
# ---------------------------------------------------------------------------

def test_retrieval_result_source_file(knowledge_result):
    assert knowledge_result.source_file == "spec.pdf"


def test_retrieval_result_chunk_type(knowledge_result):
    assert knowledge_result.chunk_type == "knowledge"


def test_retrieval_result_kind(knowledge_result):
    assert knowledge_result.kind == "constraint"


def test_retrieval_result_embed_text(knowledge_result):
    assert "wavelength" in knowledge_result.embed_text


def test_retrieval_result_code_chunk_type(code_result):
    assert code_result.chunk_type == "code"


def test_retrieval_result_code_source_file(code_result):
    assert code_result.source_file == "signal/processing.py"