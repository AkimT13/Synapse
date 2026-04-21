"""
Persistence layer for EmbeddedChunks backed by Actian VectorAI DB.
Vectors are indexed for KNN retrieval; the full chunk is stored as
the point payload so a single search round-trips the complete object.
Uses Actian's SmartBatcher for bulk upserts.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

try:
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
    _ACTIAN_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:  # pragma: no cover - exercised in dev envs
    AsyncVectorAIClient = None  # type: ignore[assignment]
    BatcherConfig = None  # type: ignore[assignment]
    Distance = None  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    FilterBuilder = None  # type: ignore[assignment]
    PointStruct = None  # type: ignore[assignment]
    SmartBatcher = None  # type: ignore[assignment]
    VectorAIClient = None  # type: ignore[assignment]
    VectorParams = None  # type: ignore[assignment]
    _ACTIAN_IMPORT_ERROR = exc

if _ACTIAN_IMPORT_ERROR is None:
    import grpc.aio
    from actian_vectorai._executor import BackgroundLoop
    from actian_vectorai._collections import CollectionsNamespace
    from actian_vectorai._points import PointsNamespace
    from actian_vectorai._vde import VDENamespace
    from actian_vectorai.client import VectorAIClient as BaseVectorAIClient
    from actian_vectorai.async_client import AsyncVectorAIClient as BaseAsyncVectorAIClient
    from actian_vectorai.async_client import (
        col_grpc,
        ext_grpc,
        pts_grpc,
        vectorai_grpc,
    )
    from actian_vectorai.exceptions import ConnectionError as VaiConnectionError
    from actian_vectorai.exceptions import ErrorCode
    from actian_vectorai.transport import (
        AuthInterceptor,
        LoggingInterceptor,
        MetadataInterceptor,
        RetryInterceptor,
        TracingInterceptor,
        UserAgentInterceptor,
        create_credentials_from_files,
    )
else:  # pragma: no cover - import-free fallback for dev envs
    BaseVectorAIClient = None  # type: ignore[assignment]
    BaseAsyncVectorAIClient = None  # type: ignore[assignment]

from embeddings.schemas import EmbeddedChunk

"""Keep batches under the beta DB's ~64KB-per-point payload limit."""
BATCHER_SIZE_LIMIT = 5
BATCHER_BYTE_LIMIT = 512 * 1024
DEFAULT_GRPC_OPTIONS = [
    ("grpc.keepalive_time_ms", 120_000),
    ("grpc.keepalive_timeout_ms", 20_000),
    ("grpc.keepalive_permit_without_calls", 0),
    ("grpc.http2.max_pings_without_data", 1),
]


if _ACTIAN_IMPORT_ERROR is None:
    class ConservativeAsyncVectorAIClient(BaseAsyncVectorAIClient):
        """Actian client wrapper with safer gRPC keepalive settings."""

        async def connect(self) -> None:  # noqa: C901
            if self._connected:
                return

            cfg = self._config

            interceptors: list[grpc.aio.UnaryUnaryClientInterceptor] = []
            if cfg.api_key:
                interceptors.append(AuthInterceptor(api_key=cfg.api_key))
            if cfg.max_retries > 0:
                interceptors.append(RetryInterceptor(max_retries=cfg.max_retries))
            if cfg.enable_tracing:
                interceptors.append(TracingInterceptor())
            if cfg.enable_logging:
                interceptors.append(LoggingInterceptor())
            if cfg.metadata:
                interceptors.append(
                    MetadataInterceptor(metadata=list(cfg.metadata.items()))
                )
            interceptors.append(UserAgentInterceptor())

            options: list[tuple[str, object]] = [
                ("grpc.max_receive_message_length", cfg.max_message_size),
                ("grpc.max_send_message_length", cfg.max_message_size),
                *cfg.grpc_options,
            ]
            if cfg.tls:
                credentials = create_credentials_from_files(
                    ca_cert_path=cfg.tls_ca_cert,
                    client_key_path=cfg.tls_client_key,
                    client_cert_path=cfg.tls_client_cert,
                )
                self._channel = grpc.aio.secure_channel(
                    cfg.url,
                    credentials,
                    options=options,
                    interceptors=interceptors or None,
                )
            else:
                self._channel = grpc.aio.insecure_channel(
                    cfg.url,
                    options=options,
                    interceptors=interceptors or None,
                )
            channel = self._channel

            self._collections = CollectionsNamespace(
                col_grpc.CollectionsStub(channel),
                timeout=cfg.timeout,
            )
            self._points = PointsNamespace(
                pts_grpc.PointsStub(channel),
                timeout=cfg.timeout,
            )
            self._vde = VDENamespace(
                ext_grpc.CollectionsExtStub(channel),
                timeout=cfg.timeout,
            )
            self._vectorai_stub = vectorai_grpc.ActianVectorAIStub(channel)
            self._connected = True

            try:
                await self.health_check(timeout=min(cfg.timeout or 5.0, 5.0))
            except Exception as e:
                await self.close()
                raise VaiConnectionError(
                    f"Server at '{cfg.url}' is not reachable",
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                ) from e


    class ConservativeVectorAIClient(BaseVectorAIClient):
        def __init__(self, url: str = "localhost:50051", **kwargs) -> None:
            self._loop = BackgroundLoop()
            self._async_client = ConservativeAsyncVectorAIClient(url, **kwargs)
            self._collections = None
            self._points = None
            self._vde = None


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


def _require_actian() -> None:
    if _ACTIAN_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Actian VectorAI client is not installed. "
            "Run `pip install -r requirements-actian.txt` from backend/."
        ) from _ACTIAN_IMPORT_ERROR


def actian_available() -> bool:
    return _ACTIAN_IMPORT_ERROR is None


async def _try_upsert_one(
    async_client: AsyncVectorAIClient,
    collection_name: str,
    item,
) -> bool:
    """Upsert a single point, swallowing errors. Returns True on success."""
    _require_actian()
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
    _require_actian()
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
        distance=None,
        grpc_options: list[tuple[str, object]] | None = None,
    ):
        _require_actian()
        self._host = host
        self._collection = collection
        self._distance = distance if distance is not None else Distance.Cosine
        self._grpc_options = grpc_options or list(DEFAULT_GRPC_OPTIONS)
        self._client: VectorAIClient | None = None

    def connect(self) -> None:
        _require_actian()
        self._client = ConservativeVectorAIClient(
            self._host,
            grpc_options=self._grpc_options,
        )
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
        _require_actian()
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
        _require_actian()
        stored = 0

        async with ConservativeAsyncVectorAIClient(
            self._host,
            grpc_options=self._grpc_options,
        ) as async_client:

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
        _require_actian()
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

    def count(self, filters: dict | None = None) -> int:
        """Count points in the collection, optionally filtered.

        Returns 0 if the collection does not exist yet, so callers can
        invoke this on a fresh workspace without pre-checking existence.
        """
        _require_actian()
        if not self.client.collections.exists(self._collection):
            return 0
        actian_filter = _build_filter(filters) if filters else None
        return self.client.points.count(
            self._collection,
            filter=actian_filter,
        )
