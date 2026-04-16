"""
Orchestrates the knowledge ingestion pipeline: parse → chunk.
"""
from __future__ import annotations

from pathlib import Path

from ingestion.knowledge.chunker import chunk_document
from ingestion.knowledge.parser import parse_document, parse_directory
from ingestion.schemas import RawDocumentChunk


def ingest_file(file_path: str | Path) -> list[RawDocumentChunk]:
    """Parse and chunk a single document file."""
    path = Path(file_path)
    result = parse_document(path)
    return chunk_document(result, source_file=str(path))


def ingest_directory(dir_path: str | Path) -> list[RawDocumentChunk]:
    """Parse and chunk every supported document in a directory (non-recursive).

    Returns a flat list of chunks from all documents.
    """
    path = Path(dir_path)
    results = parse_directory(path)
    chunks: list[RawDocumentChunk] = []
    for result in results:
        source = str(result.input.file) if result.input and result.input.file else str(path)
        chunks.extend(chunk_document(result, source_file=source))
    return chunks
