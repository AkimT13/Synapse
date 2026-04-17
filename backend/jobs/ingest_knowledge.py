"""
End-to-end knowledge ingestion job. Orchestrates: document parsing ->
chunking -> normalization -> embedding -> vector storage.

Minimal glue -- the real work happens in each pipeline stage.

Usage::

    from storage.vector_store import VectorStore
    from jobs.ingest_knowledge import KnowledgeIngestionJob

    with VectorStore() as store:
        result = KnowledgeIngestionJob(store).run("/path/to/docs")
        print(result)
"""
from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field

from embeddings.service import EmbeddingService
from ingestion.knowledge.pipeline import ingest_directory
from normalization.knowledge.normalizer import KnowledgeNormalizer
from storage.vector_store import VectorStore


class JobResult(BaseModel):
    """Summary statistics for a completed ingestion run."""

    files_processed: int = 0
    chunks_parsed: int = 0
    chunks_normalized: int = 0
    chunks_embedded: int = 0
    chunks_stored: int = 0
    errors: list[str] = Field(default_factory=list)


class KnowledgeIngestionJob:
    """Orchestrates the full knowledge-to-vector pipeline.

    Parameters
    ----------
    vector_store:
        Connected VectorStore instance for persisting embedded chunks.
    should_use_llm:
        Forwarded to KnowledgeNormalizer -- set False to skip LLM rewrites.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        should_use_llm: bool = True,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        self._store = vector_store
        self._normalizer = KnowledgeNormalizer(should_use_llm=should_use_llm)
        self._embedder = EmbeddingService()
        self._on_progress = on_progress or (lambda message: None)

    def run(
        self,
        directory_path: str,
    ) -> JobResult:
        """Execute the full ingestion pipeline.

        Parameters
        ----------
        directory_path:
            Path to a directory containing documents (PDF, etc.)

        Returns
        -------
        JobResult
            Statistics about the completed run.
        """
        result = JobResult()

        self._on_progress("Parsing and chunking documents...")
        try:
            raw_chunks = ingest_directory(directory_path)
            result.chunks_parsed = len(raw_chunks)
            source_files = {chunk.source_file for chunk in raw_chunks}
            result.files_processed = len(source_files)
            self._on_progress(
                f"Parsed {len(raw_chunks)} chunks from {len(source_files)} documents"
            )
        except Exception as exc:
            self._on_progress(f"Document ingestion failed: {exc}")
            result.errors.append(f"Ingestion failed: {exc}")
            return result

        if not raw_chunks:
            return result

        self._on_progress(f"Normalizing {len(raw_chunks)} chunks...")
        try:
            normalized = self._normalizer.normalize_batch(raw_chunks)
            result.chunks_normalized = len(normalized)
            self._on_progress(f"Normalized {len(normalized)} chunks")
        except Exception as exc:
            self._on_progress(f"Normalization failed: {exc}")
            result.errors.append(f"Normalization failed: {exc}")
            return result

        self._on_progress(f"Embedding {len(normalized)} chunks...")
        try:
            embedded = self._embedder.embed_batch(normalized)
            result.chunks_embedded = len(embedded)
            self._on_progress(f"Embedded {len(embedded)} chunks")
        except Exception as exc:
            self._on_progress(f"Embedding failed: {exc}")
            result.errors.append(f"Embedding failed: {exc}")
            return result

        self._on_progress("Storing in vector DB...")
        if embedded:
            config_dim = embedded[0].vector_dimension
            self._store.ensure_collection(config_dim)
            result.chunks_stored = self._store.upsert(embedded)
            self._on_progress(
                f"Stored {result.chunks_stored}/{len(embedded)} chunks"
            )

        return result