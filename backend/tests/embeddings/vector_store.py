"""
Round-trip integration tests for VectorStore.
Requires a running Actian VectorAI DB on localhost:50051.
"""
import pytest

from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import RawKnowledgeChunk
from normalization.schemas import NormalizedChunk
from storage.vector_store import SearchResult, VectorStore

DIMENSION = 8
COLLECTION = "test_chunks"


@pytest.fixture()
def store():
    with VectorStore(collection=COLLECTION) as s:
        s.ensure_collection(dimension=DIMENSION)
        yield s
        s.client.collections.delete(COLLECTION)


def _make_chunk(id_: str, vector: list[float]) -> EmbeddedChunk:
    raw = RawKnowledgeChunk(
        id=f"{id_}_raw",
        source_file="test.md",
        raw_text=f"raw text for {id_}",
    )
    normalized = NormalizedChunk(
        id=f"{id_}_norm",
        source_chunk=raw,
        embed_text=f"text for {id_}",
    )
    return EmbeddedChunk(
        id=id_,
        source_chunk=normalized,
        vector=vector,
        vector_model="test-model",
        vector_dimension=DIMENSION,
    )


def test_stored_chunks_survive_a_round_trip_through_the_vector_db(store: VectorStore):
    a = _make_chunk("a", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = _make_chunk("b", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    c = _make_chunk("c", [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    store.upsert([a, b, c])

    results = store.search(a.vector, k=2)

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].chunk.embed_text == "text for a"
    assert results[0].chunk.source_chunk.source_chunk.raw_text == "raw text for a"


def test_nearest_neighbour_is_ranked_by_similarity(store: VectorStore):
    a = _make_chunk("a", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = _make_chunk("b", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    store.upsert([a, b])

    results = store.search(a.vector, k=2)

    assert results[0].id == "a"
    assert results[0].score > results[1].score
