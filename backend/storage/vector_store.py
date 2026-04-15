"""
Persistence layer for EmbeddedChunks backed by Actian VectorAI DB.
Vectors are indexed for KNN retrieval; the full chunk is stored as
the point payload so a single search round-trips the complete object.
"""
from __future__ import annotations

from dataclasses import dataclass

from actian_vectorai import (
    Distance,
    PointStruct,
    VectorAIClient,
    VectorParams,
)

from embeddings.schemas import EmbeddedChunk


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

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        points = [
            PointStruct(
                id=chunk.id,
                vector=chunk.vector,
                payload=chunk.model_dump(),
            )
            for chunk in chunks
        ]
        self.client.points.upsert(self._collection, points)

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
