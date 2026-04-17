"""
Embedding service. Takes NormalizedChunks, calls the embedding model
via the models package, and produces EmbeddedChunks ready for storage.
This is a thin orchestration layer: the actual vector computation is
delegated to the provider configured in ``models``. Batching is
handled here to respect provider rate / size limits.
"""
from __future__ import annotations

import numpy as np

import models
from embeddings.schemas import EmbeddedChunk
from normalization.schemas import NormalizedChunk

"""OpenAI allows up to 2048 texts per call; 100 balances throughput with memory."""
MAX_EMBEDDING_BATCH_SIZE = 100


def _normalize(vector: list[float]) -> list[float]:
    """L2-normalize a vector. Returns the original if norm is zero."""
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vector
    return (arr / norm).tolist()


class EmbeddingService:
    """Converts NormalizedChunks into EmbeddedChunks via the models API."""

    def embed(self, chunk: NormalizedChunk) -> EmbeddedChunk:
        config = models.get_config()
        vectors = models.embed([chunk.embed_text])
        return EmbeddedChunk(
            source_chunk=chunk,
            vector=_normalize(vectors[0]),
            vector_model=config.embedding_model,
            vector_dimension=config.embedding_dimension,
        )

    def embed_batch(
        self,
        chunks: list[NormalizedChunk],
        batch_size: int = MAX_EMBEDDING_BATCH_SIZE,
    ) -> list[EmbeddedChunk]:
        """Embed a list of NormalizedChunks in batches.

        Parameters
        ----------
        chunks:
            The normalized chunks to embed.
        batch_size:
            Maximum number of texts to send per embedding API call.
        """
        config = models.get_config()
        results: list[EmbeddedChunk] = []

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [chunk.embed_text for chunk in batch]
            vectors = models.embed(texts)

            for chunk, vector in zip(batch, vectors):
                results.append(EmbeddedChunk(
                    source_chunk=chunk,
                    vector=_normalize(vector),
                    vector_model=config.embedding_model,
                    vector_dimension=config.embedding_dimension,
                ))

        return results