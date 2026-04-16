"""
Persistence layer for EmbeddedChunks backed by Actian VectorAI DB.
Vectors are indexed for KNN retrieval; the full chunk is stored as
the point payload so a single search round-trips the complete object.
Uses Actian's SmartBatcher for bulk upserts.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from actian_vectorai import (
    AsyncVectorAIClient,
    BatcherConfig,
    Distance,
    PointStruct,
    SmartBatcher,
    VectorAIClient,
    VectorParams,
)

from embeddings.schemas import EmbeddedChunk

"""Keep batches under the beta DB's ~64KB-per-point payload limit."""
BATCHER_SIZE_LIMIT = 5
BATCHER_BYTE_LIMIT = 512 * 1024


@dataclass(frozen=True)
class SearchResult:
    id: str
    score: float
    chunk: EmbeddedChunk


class VectorStore:

    def __init__(
        self,
        host: str = "localhost:50051",
        collection: str = "chunks",
        distance: Distance = Distance.Cosine,
    ):
        self._host = host
        self._collection = collection
        self._distance = distance
        self._client: VectorAIClient | None = None

    def connect(self) -> None:
        self._client = VectorAIClient(self._host)
        self._client.connect()

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> VectorStore:
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def client(self) -> VectorAIClient:
        if self._client is None:
            raise RuntimeError("Not connected — call .connect() or use as context manager")
        return self._client

    def ensure_collection(self, dimension: int) -> None:
        if not self.client.collections.exists(self._collection):
            self.client.collections.create(
                self._collection,
                vectors_config=VectorParams(size=dimension, distance=self._distance),
            )

    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        return asyncio.run(self._upsert_with_batcher(chunks))

    async def _upsert_with_batcher(self, chunks: list[EmbeddedChunk]) -> int:
        stored = 0

        async with AsyncVectorAIClient(self._host) as async_client:
            async def flush(collection_name: str, items: list) -> None:
                nonlocal stored
                points = [
                    PointStruct(id=item.id, vector=item.vector, payload=item.payload)
                    for item in items
                ]
                await async_client.points.upsert(collection_name, points)
                stored += len(items)

            config = BatcherConfig(
                size_limit=BATCHER_SIZE_LIMIT,
                byte_limit=BATCHER_BYTE_LIMIT,
            )
            batcher = SmartBatcher(flush, config)
            await batcher.start()

            futures = []
            for chunk in chunks:
                future = await batcher.add(
                    self._collection,
                    chunk.id,
                    chunk.vector,
                    chunk.model_dump(),
                )
                futures.append(future)

            await asyncio.gather(*futures)
            await batcher.stop(flush_remaining=True)

        return stored

    def search(self, vector: list[float], k: int = 5) -> list[SearchResult]:
        results = self.client.points.search(
            self._collection,
            vector=vector,
            limit=k,
        )
        return [
            SearchResult(
                id=r.id,
                score=r.score,
                chunk=EmbeddedChunk(**r.payload),
            )
            for r in results
        ]
