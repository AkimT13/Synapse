"""Tests for retrieval/retrieval.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from retrieval.filters import code_filter, knowledge_filter
from retrieval.retrieval import (
    _build_directional_filter,
    _free_text_retrieve,
    code_to_knowledge,
    free_text,
    knowledge_to_code,
    retrieve,
)
from retrieval.schemas import RetrievalQuery, RetrievalResult


# ---------------------------------------------------------------------------
# _build_directional_filter
# ---------------------------------------------------------------------------

def test_build_directional_filter_code_to_knowledge():
    query = RetrievalQuery(text="test", direction="code_to_knowledge")
    f = _build_directional_filter(query)
    assert f["chunk_type"] == "knowledge"


def test_build_directional_filter_knowledge_to_code():
    query = RetrievalQuery(text="test", direction="knowledge_to_code")
    f = _build_directional_filter(query)
    assert f["chunk_type"] == "code"


def test_build_directional_filter_merges_caller_filters():
    query = RetrievalQuery(
        text="test",
        direction="code_to_knowledge",
        filters={"domain": "spectroscopy"},
    )
    f = _build_directional_filter(query)
    assert f["chunk_type"] == "knowledge"
    assert f["domain"] == "spectroscopy"


def test_build_directional_filter_caller_filters_do_not_override_chunk_type():
    query = RetrievalQuery(
        text="test",
        direction="code_to_knowledge",
        filters={"domain": "spectroscopy"},
    )
    f = _build_directional_filter(query)
    assert f["chunk_type"] == "knowledge"


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------

def test_retrieve_returns_retrieval_results(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(text="wavelength", direction="code_to_knowledge")
        results = retrieve(query, mock_store)

    assert len(results) > 0
    assert all(isinstance(r, RetrievalResult) for r in results)


def test_retrieve_passes_correct_filters_to_store(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(
            text="wavelength",
            direction="code_to_knowledge",
            filters={"domain": "spectroscopy"},
        )
        retrieve(query, mock_store)

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["chunk_type"] == "knowledge"
    assert call_kwargs["filters"]["domain"] == "spectroscopy"


def test_retrieve_passes_k_to_store(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(text="test", direction="code_to_knowledge", k=3)
        retrieve(query, mock_store)

    assert mock_store.search.call_args.kwargs["k"] == 3


def test_retrieve_applies_score_threshold(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(
            text="test",
            direction="code_to_knowledge",
            score_threshold=0.99,   # higher than any mock result
        )
        results = retrieve(query, mock_store)

    assert len(results) == 0


def test_retrieve_no_score_threshold_returns_all(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(
            text="test",
            direction="code_to_knowledge",
            score_threshold=None,
        )
        results = retrieve(query, mock_store)

    assert len(results) == 2


def test_retrieve_result_carries_query_text(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(text="my query", direction="code_to_knowledge")
        results = retrieve(query, mock_store)

    assert all(r.query_text == "my query" for r in results)


def test_retrieve_result_carries_direction(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        query = RetrievalQuery(text="test", direction="code_to_knowledge")
        results = retrieve(query, mock_store)

    assert all(r.direction == "code_to_knowledge" for r in results)


# ---------------------------------------------------------------------------
# code_to_knowledge
# ---------------------------------------------------------------------------

def test_code_to_knowledge_filters_by_knowledge_chunk_type(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        code_to_knowledge("normalize wavelength", mock_store)

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["chunk_type"] == "knowledge"


def test_code_to_knowledge_adds_domain_filter(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        code_to_knowledge("normalize wavelength", mock_store, domain="spectroscopy")

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["domain"] == "spectroscopy"


def test_code_to_knowledge_constraints_only_adds_filter(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        code_to_knowledge("normalize wavelength", mock_store, constraints_only=True)

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["contains_constraint"] is True


def test_code_to_knowledge_returns_retrieval_results(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = code_to_knowledge("normalize wavelength", mock_store)

    assert all(isinstance(r, RetrievalResult) for r in results)


# ---------------------------------------------------------------------------
# knowledge_to_code
# ---------------------------------------------------------------------------

def test_knowledge_to_code_filters_by_code_chunk_type(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        knowledge_to_code("wavelength must exceed 0.5nm", mock_store)

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["chunk_type"] == "code"


def test_knowledge_to_code_adds_language_filter(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        knowledge_to_code(
            "wavelength must exceed 0.5nm", mock_store, language="python"
        )

    call_kwargs = mock_store.search.call_args.kwargs
    assert call_kwargs["filters"]["language"] == "python"


def test_knowledge_to_code_returns_retrieval_results(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = knowledge_to_code("wavelength must exceed 0.5nm", mock_store)

    assert all(isinstance(r, RetrievalResult) for r in results)


# ---------------------------------------------------------------------------
# free_text
# ---------------------------------------------------------------------------

def test_free_text_calls_store_twice(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        free_text("what is the wavelength limit", mock_store)

    assert mock_store.search.call_count == 2


def test_free_text_searches_both_chunk_types(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        free_text("what is the wavelength limit", mock_store)

    calls = mock_store.search.call_args_list
    filter_values = [c.kwargs["filters"]["chunk_type"] for c in calls]
    assert "knowledge" in filter_values
    assert "code" in filter_values


def test_free_text_results_sorted_by_score_descending():
    from tests.retrieval.conftest import _make_search_result

    store = MagicMock()
    store.search.side_effect = [
        [_make_search_result("a.pdf", "text a", score=0.7)],
        [_make_search_result("b.py", "text b", score=0.9, chunk_type="code")],
    ]

    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = free_text("test", store)

    assert results[0].score >= results[1].score


def test_free_text_returns_retrieval_results(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = free_text("test query", mock_store)

    assert all(isinstance(r, RetrievalResult) for r in results)


def test_free_text_direction_is_free_text(mock_store):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = free_text("test query", mock_store)

    assert all(r.direction == "free_text" for r in results)


def test_free_text_empty_store_returns_empty_list(mock_store_empty):
    with patch("retrieval.retrieval.models.embed_single", return_value=[0.1] * 8):
        results = free_text("test query", mock_store_empty)

    assert results == []