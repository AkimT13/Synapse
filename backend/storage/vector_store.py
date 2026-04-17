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
    Field,
    FilterBuilder,
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


def _reconstruct_chunk(raw: dict) -> EmbeddedChunk:
    """Rebuild an EmbeddedChunk from its stored ``_raw`` payload.

    The vector is not stored inside ``_raw`` (Actian indexes it
    separately), so we inject an empty list. Downstream consumers read
    the chunk's text and metadata — they never read the vector back.
    """
    return EmbeddedChunk(**raw, vector=[])


async def _try_upsert_one(
    async_client: AsyncVectorAIClient,
    collection_name: str,
    item,
) -> bool:
    """Upsert a single point, swallowing errors. Returns True on success."""
    try:
        await async_client.points.upsert(
            collection_name,
            [PointStruct(id=item.id, vector=item.vector, payload=item.payload)],
        )
        return True
    except Exception:
        return False


def _build_filter(filters: dict) -> object:
    """Convert a flat dict of field: value pairs into an Actian Filter.

    All conditions are combined with must (AND logic).
    String and bool values use equality match.
    Dict values are treated as range conditions:
        {"confidence": {"$gte": 0.8}}  →  Field("confidence").gte(0.8)
    """
    builder = FilterBuilder()

    for field_name, value in filters.items():
        if isinstance(value, dict):
            for op, operand in value.items():
                match op:
                    case "$gte":
                        builder.must(Field(field_name).gte(operand))
                    case "$lte":
                        builder.must(Field(field_name).lte(operand))
                    case "$gt":
                        builder.must(Field(field_name).gt(operand))
                    case "$lt":
                        builder.must(Field(field_name).lt(operand))
                    case _:
                        raise ValueError(f"Unsupported filter operator: {op}")
        else:
            builder.must(Field(field_name).eq(value))

    return builder.build()


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
            raise RuntimeError(
                "Not connected — call .connect() or use as context manager"
            )
        return self._client

    def ensure_collection(self, dimension: int) -> None:
        if not self.client.collections.exists(self._collection):
            self.client.collections.create(
                self._collection,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=self._distance,
                ),
            )

    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        return asyncio.run(self._upsert_with_batcher(chunks))

    async def _upsert_with_batcher(self, chunks: list[EmbeddedChunk]) -> int:
        """Upsert via SmartBatcher, retrying failed batches item-by-item.

        When a batch flush fails — typically because one chunk's payload
        exceeds the DB's per-point limit — we retry each item in that
        batch individually so the good chunks aren't lost along with the
        bad. Chunks that still fail on their own are dropped silently;
        the caller sees the drop through the returned count.
        """
        stored = 0

        async with AsyncVectorAIClient(self._host) as async_client:

            async def flush(collection_name: str, items: list) -> None:
                nonlocal stored
                points = [
                    PointStruct(id=item.id, vector=item.vector, payload=item.payload)
                    for item in items
                ]
                try:
                    await async_client.points.upsert(collection_name, points)
                    stored += len(items)
                except Exception:
                    for item in items:
                        if await _try_upsert_one(async_client, collection_name, item):
                            stored += 1

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
                    chunk.to_storage_record(),
                )
                futures.append(future)

            await asyncio.gather(*futures, return_exceptions=True)
            await batcher.stop(flush_remaining=True)

        return stored

    def search(
        self,
        vector: list[float],
        k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Search for the k nearest neighbours to the given vector.

        Parameters
        ----------
        vector:
            The query vector to search against.
        k:
            Number of results to return.
        filters:
            Optional dict of field: value pairs to filter candidates
            before KNN search. All conditions are AND-ed together.
            Filterable fields are promoted to top level in the storage
            record by to_storage_record().

            Examples:
                {"chunk_type": "knowledge", "domain": "spectroscopy"}
                {"chunk_type": "code", "language": "python"}
                {"knowledge_type": "constraint", "confidence": {"$gte": 0.8}}
        """
        actian_filter = _build_filter(filters) if filters else None

        results = self.client.points.search(
            self._collection,
            vector=vector,
            limit=k,
            filter=actian_filter,
        )
        return [
            SearchResult(
                id=r.id,
                score=r.score,
                chunk=_reconstruct_chunk(r.payload["_raw"]),
            )
            for r in results
        ]