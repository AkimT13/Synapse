from __future__ import annotations

from agents.memory_agent import build_memory_chunk, store_decision, store_decisions
from embeddings.schemas import EmbeddedChunk


def test_build_memory_chunk_creates_embedded_chunk(mocker, sample_agent_decision):
    mocker.patch("agents.memory_agent.models.embed_single", return_value=[0.25] * 8)
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "test-embed-model"})(),
    )

    chunk = build_memory_chunk(sample_agent_decision)

    assert isinstance(chunk, EmbeddedChunk)
    assert chunk.embed_text == sample_agent_decision.embed_text
    assert chunk.vector == [0.25] * 8
    assert chunk.vector_model == "test-embed-model"
    assert chunk.vector_dimension == 8

    source = chunk.source_chunk.source_chunk
    norm = chunk.source_chunk

    assert source.source_file == "agent_memory/dismissed_warning.md"
    assert source.metadata["domain"] == "spectroscopy"
    assert source.metadata["knowledge_type"] == "agent_memory"
    assert source.metadata["source_type"] == "agent_decision"
    assert source.metadata["contains_constraint"] is False
    assert source.metadata["confidence"] == 1.0
    assert source.metadata["decision_type"] == "dismissed_warning"
    assert source.metadata["code_ref"] == "signal/processing.py::normalize_wavelength"
    assert source.metadata["constraint_ref"] == "spec.pdf::minimum_wavelength"
    assert source.metadata["created_by"] == "tester"
    assert source.metadata["ticket"] == "SYN-123"

    assert norm.kind == "mapping"
    assert norm.subject == sample_agent_decision.summary
    assert norm.constraint == sample_agent_decision.rationale
    assert norm.embed_text == sample_agent_decision.embed_text
    assert "dismissed_warning" in norm.keywords
    assert "spectroscopy" in norm.keywords
    assert "signal/processing.py::normalize_wavelength" in norm.keywords
    assert "spec.pdf::minimum_wavelength" in norm.keywords


def test_build_memory_chunk_calls_embed_single(mocker, sample_agent_decision):
    embed_mock = mocker.patch(
        "agents.memory_agent.models.embed_single",
        return_value=[0.5] * 4,
    )
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "unit-test-model"})(),
    )

    chunk = build_memory_chunk(sample_agent_decision)

    embed_mock.assert_called_once_with(sample_agent_decision.embed_text)
    assert chunk.vector == [0.5] * 4
    assert chunk.vector_dimension == 4
    assert chunk.vector_model == "unit-test-model"


def test_store_decision_upserts_single_chunk(mocker, sample_agent_decision, mock_store):
    mocker.patch("agents.memory_agent.models.embed_single", return_value=[0.1] * 8)
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "test-model"})(),
    )
    mock_store.upsert.return_value = 1

    chunk = store_decision(sample_agent_decision, mock_store)

    mock_store.upsert.assert_called_once()
    args, kwargs = mock_store.upsert.call_args
    assert kwargs == {}
    assert len(args) == 1
    assert len(args[0]) == 1
    assert args[0][0] == chunk


def test_store_decisions_batches_chunks(mocker, sample_agent_decision, mock_store):
    mocker.patch("agents.memory_agent.models.embed_single", return_value=[0.2] * 8)
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "test-model"})(),
    )
    mock_store.upsert.return_value = 2

    second = sample_agent_decision.model_copy(
        update={
            "summary": "Developer accepted the warning after review",
            "decision_type": "accepted_warning",
            "embed_text": "Accepted warning after confirming the threshold mismatch.",
        }
    )

    stored = store_decisions([sample_agent_decision, second], mock_store)

    assert stored == 2
    mock_store.upsert.assert_called_once()
    chunks = mock_store.upsert.call_args.args[0]
    assert len(chunks) == 2
    assert chunks[0].embed_text == sample_agent_decision.embed_text
    assert chunks[1].embed_text == second.embed_text


def test_store_decisions_returns_zero_for_empty_input(mock_store):
    stored = store_decisions([], mock_store)

    assert stored == 0
    mock_store.upsert.assert_not_called()


def test_identical_decisions_produce_identical_ids(mocker, sample_agent_decision):
    mocker.patch("agents.memory_agent.models.embed_single", return_value=[0.3] * 8)
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "test-model"})(),
    )

    chunk_one = build_memory_chunk(sample_agent_decision)
    chunk_two = build_memory_chunk(sample_agent_decision)

    assert chunk_one.source_chunk.id == chunk_two.source_chunk.id
    assert chunk_one.id == chunk_two.id


def test_different_decisions_produce_different_ids(mocker, sample_agent_decision):
    mocker.patch("agents.memory_agent.models.embed_single", return_value=[0.3] * 8)
    mocker.patch(
        "agents.memory_agent.models.get_config",
        return_value=type("Config", (), {"embedding_model": "test-model"})(),
    )

    modified = sample_agent_decision.model_copy(
        update={"summary": "Different summary", "embed_text": "Different embed text"}
    )

    chunk_one = build_memory_chunk(sample_agent_decision)
    chunk_two = build_memory_chunk(modified)

    assert chunk_one.source_chunk.id != chunk_two.source_chunk.id
    assert chunk_one.id != chunk_two.id