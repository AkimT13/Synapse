"""Tests for normalization/knowledge/template.py."""
from __future__ import annotations

import pytest

from normalization.knowledge.template import build_template, has_domain_signals


# ---------------------------------------------------------------------------
# build_template
# ---------------------------------------------------------------------------


def test_build_template_returns_non_empty_string(text_chunk):
    result = build_template(text_chunk)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_build_template_includes_section_heading(text_chunk):
    result = build_template(text_chunk)
    assert "Resolution Limits" in result


def test_build_template_includes_page_number(text_chunk):
    result = build_template(text_chunk)
    assert "12" in result


def test_build_template_includes_raw_text_for_text_chunk(text_chunk):
    result = build_template(text_chunk)
    assert "0.5 nanometers" in result


def test_build_template_uses_table_description_for_table_chunk(table_chunk):
    result = build_template(table_chunk)
    assert "385 watts per meter kelvin" in result


def test_build_template_falls_back_to_raw_text_for_table_without_description(
    table_chunk,
):
    # remove table_description from metadata
    table_chunk.metadata.pop("table_description", None)
    result = build_template(table_chunk)
    assert "Copper" in result


def test_build_template_uses_caption_for_figure_chunk():
    from ingestion.schemas import RawDocumentChunk

    chunk = RawDocumentChunk.from_raw_text(
        raw_text="Diagram of the optical path through the lens assembly.",
        source_file="manual.pdf",
        chunk_index=0,
        content_type="figure",
    )
    result = build_template(chunk)
    assert "optical path" in result


def test_build_template_no_section_heading_still_works(text_chunk):
    text_chunk.section_heading = None
    result = build_template(text_chunk)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


# ---------------------------------------------------------------------------
# has_domain_signals
# ---------------------------------------------------------------------------


def test_has_domain_signals_true_for_normal_text_chunk(text_chunk):
    assert has_domain_signals(text_chunk) is True


def test_has_domain_signals_false_for_short_chunk(short_chunk):
    assert has_domain_signals(short_chunk) is False


def test_has_domain_signals_false_for_empty_figure_chunk(figure_chunk):
    assert has_domain_signals(figure_chunk) is False


def test_has_domain_signals_true_for_table_with_description(table_chunk):
    assert has_domain_signals(table_chunk) is True


def test_has_domain_signals_false_for_table_without_description_and_short_text():
    from ingestion.schemas import RawDocumentChunk

    chunk = RawDocumentChunk.from_raw_text(
        raw_text="Table 1.",
        source_file="manual.pdf",
        chunk_index=0,
        content_type="table",
        metadata={},
    )
    assert has_domain_signals(chunk) is False


def test_has_domain_signals_true_for_entity_chunk(entity_chunk):
    assert has_domain_signals(entity_chunk) is True


def test_has_domain_signals_true_for_definition_chunk(definition_chunk):
    assert has_domain_signals(definition_chunk) is True