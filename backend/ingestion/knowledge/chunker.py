"""
Document chunker using docling HybridChunker. Splits a parsed
document into RawDocumentChunk objects ready for normalization.
"""
from __future__ import annotations

from docling.chunking import HybridChunker
from docling.document_converter import ConversionResult
from docling_core.types.doc import DocItemLabel

from config.settings import MAX_TOKENS, TOKENIZER
from ingestion.schemas import RawDocumentChunk


def describe_table(raw_markdown: str) -> str:
    """
    Placeholder for LLM-based table description.
    Returns the markdown as-is — will be replaced by an LLM call
    in the normalization step.
    """
    return raw_markdown


def chunk_document(
    result: ConversionResult,
    source_file: str,
) -> list[RawDocumentChunk]:
    """
    Split a parsed document into RawDocumentChunk objects.

    Uses HybridChunker with the tokenizer and max_tokens defined in
    config/settings.py. Tables are exported as markdown and a
    placeholder description is stored in metadata for the normalization
    step. Figures use their caption as raw_text when available.
    """
    chunker = HybridChunker(
        tokenizer=TOKENIZER,
        max_tokens=MAX_TOKENS,
        merge_peers=True,
    )

    chunks: list[RawDocumentChunk] = []

    for idx, chunk in enumerate(chunker.chunk(result.document)):

        # --- section heading ---
        heading: str | None = None
        if chunk.meta.headings:
            heading = chunk.meta.headings[-1]  # most specific heading

        # --- page number ---
        page: int | None = None
        if chunk.meta.doc_items:
            first = chunk.meta.doc_items[0]
            if hasattr(first, "prov") and first.prov:
                page = first.prov[0].page_no

        # --- content type, raw_text, metadata ---
        content_type: str = "text"
        raw_text: str = chunk.text
        metadata: dict = {}

        if chunk.meta.doc_items:
            labels = {
                item.label
                for item in chunk.meta.doc_items
                if hasattr(item, "label")
            }

            if DocItemLabel.TABLE in labels:
                content_type = "table"

                # export table as markdown for raw_text
                for item in chunk.meta.doc_items:
                    if (
                        hasattr(item, "label")
                        and item.label == DocItemLabel.TABLE
                        and hasattr(item, "export_to_markdown")
                    ):
                        raw_text = item.export_to_markdown()
                        break

                # store description in metadata as a hint for
                # the normalization step — normalization will
                # replace this with a proper LLM-generated description
                # and use it as the starting point for embed_text
                metadata["table_markdown"] = raw_text
                metadata["table_description"] = describe_table(raw_text)

            elif DocItemLabel.PICTURE in labels:
                content_type = "figure"

                # use caption as raw_text when available
                for item in chunk.meta.doc_items:
                    if hasattr(item, "caption") and item.caption:
                        raw_text = item.caption
                        break

        chunks.append(
            RawDocumentChunk.from_raw_text(
                raw_text=raw_text,
                source_file=source_file,
                chunk_index=idx,
                content_type=content_type,
                section_heading=heading,
                page_number=page,
                metadata=metadata,
            )
        )

    return chunks