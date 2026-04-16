"""
Deterministic template builder for knowledge chunks. Converts a
RawDocumentChunk into a structured natural-language description without
any LLM calls. Used as both the fallback embed_text and the input to
LLM rewriting.
"""
from __future__ import annotations

from ingestion.schemas import RawDocumentChunk


def build_template(chunk: RawDocumentChunk) -> str:
    """Build a natural-language paragraph from document chunk metadata.

    Only includes sections that have actual data — never writes
    empty placeholders.
    """
    parts: list[str] = []

    # opening — section heading if available
    if chunk.section_heading:
        parts.append(f"Section: {chunk.section_heading}.")

    # page reference
    if chunk.page_number is not None:
        parts.append(f"Page {chunk.page_number}.")

    # content type context
    if chunk.content_type == "table":
        # use table description from metadata if available
        # set by chunker.py as a hint for normalization
        description = chunk.metadata.get("table_description")
        if description:
            parts.append(description)
        else:
            parts.append(chunk.raw_text)

    elif chunk.content_type == "figure":
        if chunk.raw_text:
            parts.append(f"Figure caption: {chunk.raw_text}")

    else:
        parts.append(chunk.raw_text)

    return " ".join(parts)


def has_domain_signals(chunk: RawDocumentChunk) -> bool:
    """Heuristic check for whether an LLM rewrite is worth the cost.

    Returns False for:
    - Very short chunks — likely headers, page numbers, or artifacts
    - Figure chunks with no caption
    - Table chunks with no description and very short raw text
    """
    # too short to contain meaningful domain knowledge
    if len(chunk.raw_text.strip()) < 50:
        return False

    # figure with no caption
    if chunk.content_type == "figure" and not chunk.raw_text.strip():
        return False

    # table with no description and no meaningful text
    if chunk.content_type == "table":
        description = chunk.metadata.get("table_description", "")
        if not description and len(chunk.raw_text.strip()) < 50:
            return False

    return True