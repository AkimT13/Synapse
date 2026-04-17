"""Tests for normalization/knowledge/normalizer.py.

LLM-dependent tests are marked with pytest.mark.llm and are skipped
by default. Run them with: pytest -m llm
"""
from __future__ import annotations

import pytest

from ingestion.schemas import RawDocumentChunk
from normalization.knowledge.normalizer import (
    KnowledgeNormalizer,
    _extract_keywords,
    _infer_kind,
)
from normalization.schemas import NormalizedChunk


# ---------------------------------------------------------------------------
# _infer_kind
# ---------------------------------------------------------------------------


def test_infer_kind_constraint_from_must_not(text_chunk):
    assert _infer_kind(text_chunk) == "constraint"


def test_infer_kind_constraint_from_limit():
    chunk = RawDocumentChunk.from_raw_text(
        raw_text="The maximum operating temperature limit is 85 degrees celsius.",
        source_file="spec.pdf",
        chunk_index=0,
    )
    assert _infer_kind(chunk) == "constraint"


def test_infer_kind_definition(definition_chunk):
    assert _infer_kind(definition_chunk) == "definition"


def test_infer_kind_procedure(procedure_chunk):
    assert _infer_kind(procedure_chunk) == "procedure"


def test_infer_kind_unknown_for_generic_text():
    chunk = RawDocumentChunk.from_raw_text(
        raw_text="This section covers general background information.",
        source_file="manual.pdf",
        chunk_index=0,
    )
    assert _infer_kind(chunk) == "unknown"


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------


def test_extract_keywords_from_named_entities(entity_chunk):
    keywords = _extract_keywords(entity_chunk)
    assert "centrifuge" in keywords


def test_extract_keywords_from_units_mentioned(entity_chunk):
    keywords = _extract_keywords(entity_chunk)
    assert "rpm" in keywords


def test_extract_keywords_from_section_heading(entity_chunk):
    keywords = _extract_keywords(entity_chunk)
    assert "operating" in keywords
    assert "limits" in keywords


def test_extract_keywords_from_constraint_name():
    chunk = RawDocumentChunk.from_raw_text(
        raw_text="The resolution must not fall below 0.5nm.",
        source_file="spec.pdf",
        chunk_index=0,
        metadata={"constraint_name": "spectral_resolution_limit"},
    )
    keywords = _extract_keywords(chunk)
    assert "spectral" in keywords
    assert "resolution" in keywords
    assert "limit" in keywords


def test_extract_keywords_no_duplicates(entity_chunk):
    keywords = _extract_keywords(entity_chunk)
    assert len(keywords) == len(set(keywords))


def test_extract_keywords_empty_when_no_metadata(text_chunk):
    # text_chunk has no named_entities or units in metadata
    # should still return section heading tokens
    keywords = _extract_keywords(text_chunk)
    assert "resolution" in keywords
    assert "limits" in keywords


# ---------------------------------------------------------------------------
# KnowledgeNormalizer — no LLM
# ---------------------------------------------------------------------------


def test_normalize_returns_normalized_chunk(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(text_chunk)
    assert isinstance(result, NormalizedChunk)


def test_normalize_embed_text_is_template_when_llm_disabled(text_chunk):
    from normalization.knowledge.template import build_template

    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(text_chunk)
    assert result.embed_text == build_template(text_chunk)


def test_normalize_sets_subject_from_section_heading(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(text_chunk)
    assert result.subject == "Resolution Limits"


def test_normalize_sets_subject_from_first_sentence_when_no_heading():
    chunk = RawDocumentChunk.from_raw_text(
        raw_text=(
            "The centrifuge must not exceed 5000 RPM. "
            "Exceeding this limit causes mechanical failure."
        ),
        source_file="manual.pdf",
        chunk_index=0,
    )
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(chunk)
    assert result.subject is not None
    assert len(result.subject) > 0


def test_normalize_kind_is_constraint_for_constraint_chunk(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(text_chunk)
    assert result.kind == "constraint"


def test_normalize_source_chunk_is_preserved(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(text_chunk)
    assert result.source_chunk.id == text_chunk.id
    assert result.source_chunk.raw_text == text_chunk.raw_text


def test_normalize_id_is_deterministic(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result_a = normalizer.normalize(text_chunk)
    result_b = normalizer.normalize(text_chunk)
    assert result_a.id == result_b.id


def test_normalize_batch_returns_one_result_per_chunk(
    text_chunk, table_chunk, entity_chunk
):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    chunks = [text_chunk, table_chunk, entity_chunk]
    results = normalizer.normalize_batch(chunks)
    assert len(results) == len(chunks)


def test_normalize_batch_all_results_are_normalized_chunks(
    text_chunk, table_chunk, entity_chunk
):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    results = normalizer.normalize_batch([text_chunk, table_chunk, entity_chunk])
    assert all(isinstance(r, NormalizedChunk) for r in results)


def test_normalize_batch_does_not_raise_on_short_chunk(short_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    results = normalizer.normalize_batch([short_chunk])
    assert len(results) == 1
    assert isinstance(results[0], NormalizedChunk)


def test_normalize_keywords_are_populated(entity_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(entity_chunk)
    assert len(result.keywords) > 0


def test_normalize_table_chunk(table_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=False)
    result = normalizer.normalize(table_chunk)
    assert isinstance(result, NormalizedChunk)
    assert "385" in result.embed_text or "Copper" in result.embed_text


# ---------------------------------------------------------------------------
# KnowledgeNormalizer — with LLM
# ---------------------------------------------------------------------------


@pytest.mark.llm
def test_normalize_with_llm_returns_normalized_chunk(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=True)
    result = normalizer.normalize(text_chunk)
    assert isinstance(result, NormalizedChunk)


@pytest.mark.llm
def test_normalize_with_llm_embed_text_is_non_empty(text_chunk):
    normalizer = KnowledgeNormalizer(should_use_llm=True)
    result = normalizer.normalize(text_chunk)
    assert len(result.embed_text.strip()) > 0


@pytest.mark.llm
def test_normalize_with_llm_embed_text_differs_from_template(text_chunk):
    from normalization.knowledge.template import build_template

    normalizer = KnowledgeNormalizer(should_use_llm=True)
    result = normalizer.normalize(text_chunk)
    template = build_template(text_chunk)
    assert result.embed_text != template


@pytest.mark.llm
def test_normalize_with_llm_embed_text_starts_with_kind_prefix(text_chunk):
    valid_prefixes = (
        "Constraint:",
        "Definition:",
        "Procedure:",
        "Behavior:",
        "Mapping:",
    )
    normalizer = KnowledgeNormalizer(should_use_llm=True)
    result = normalizer.normalize(text_chunk)
    assert any(result.embed_text.startswith(p) for p in valid_prefixes)


@pytest.mark.llm
def test_normalize_batch_falls_back_to_template_if_llm_raises(
    text_chunk, monkeypatch
):
    from normalization.knowledge.template import build_template

    def _raise(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("models.complete", _raise)

    normalizer = KnowledgeNormalizer(should_use_llm=True)
    results = normalizer.normalize_batch([text_chunk])
    assert len(results) == 1
    assert results[0].embed_text == build_template(text_chunk)