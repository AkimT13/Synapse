"""
Round-trip integration tests for VectorStore.
Requires a running Actian VectorAI DB on localhost:50051.
"""
import pytest

from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import RawDocumentChunk
from normalization.schemas import NormalizedChunk
from storage.vector_store import SearchResult, VectorStore

DIMENSION = 8
COLLECTION = "test_chunks"

pytestmark = pytest.mark.actian

@pytest.fixture()
def store():
    with VectorStore(collection=COLLECTION) as s:
        s.ensure_collection(dimension=DIMENSION)
        yield s
        s.client.collections.delete(COLLECTION)


def _make_chunk(source_file: str, vector: list[float]) -> EmbeddedChunk:
    raw = RawDocumentChunk.from_raw_text(
    raw_text=f"raw text for {source_file}",
    source_file=source_file,
)
    normalized = NormalizedChunk(
        source_chunk=raw,
        embed_text=f"text for {source_file}",
    )
    return EmbeddedChunk(
        source_chunk=normalized,
        vector=vector,
        vector_model="test-model",
        vector_dimension=DIMENSION,
    )


def test_stored_chunks_survive_a_round_trip_through_the_vector_db(store: VectorStore):
    a = _make_chunk("a.md", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = _make_chunk("b.md", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    c = _make_chunk("c.md", [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    store.upsert([a, b, c])
    results = store.search(a.vector, k=2)

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    # embed_text and raw_text survive the round trip through Actian
    assert results[0].chunk.embed_text == "text for a.md"
    assert results[0].chunk.source_chunk.source_chunk.raw_text == "raw text for a.md"
    # id is preserved
    assert results[0].chunk.id == a.id
    # vector model metadata is preserved
    assert results[0].chunk.vector_model == "test-model"
    assert results[0].chunk.vector_dimension == DIMENSION

def test_nearest_neighbour_is_ranked_by_similarity(store: VectorStore):
    a = _make_chunk("a.md", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = _make_chunk("b.md", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    store.upsert([a, b])

    results = store.search(a.vector, k=2)

    assert results[0].id == a.id
    assert results[0].score > results[1].score

def test_filter_by_chunk_type_returns_only_matching_chunks(store: VectorStore):
    a = _make_chunk("a.md", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = _make_chunk("b.md", [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    store.upsert([a, b])

    results = store.search(
        a.vector,
        k=5,
        filters={"chunk_type": "knowledge"},
    )

    assert len(results) > 0
    assert all(r.chunk.chunk_type == "knowledge" for r in results)