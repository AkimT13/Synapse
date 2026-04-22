from __future__ import annotations

from pathlib import Path

import pytest

from workspace.loader import load_workspace_config
from workspace.model_init import infer_embedding_dimension, init_models_from_workspace


def test_init_models_from_workspace_sets_shared_model_config_and_ollama_base_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SYNAPSE_OLLAMA_BASE_URL", raising=False)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    synapse_dir = repo_root / ".synapse"
    synapse_dir.mkdir()
    (synapse_dir / "config.yaml").write_text(_sample_config(), encoding="utf-8")

    loaded = load_workspace_config(repo_root)
    captured: dict[str, object] = {}

    monkeypatch.setattr("workspace.model_init.models.init", lambda config: captured.setdefault("config", config))
    monkeypatch.setattr(
        "workspace.model_init.models.get_config",
        lambda: type("Config", (), {"embedding_dimension": 3072})(),
    )

    init_models_from_workspace(loaded)

    assert captured["config"].chat_provider == "ollama"
    assert captured["config"].chat_model == "gemma4:e2b"
    assert captured["config"].embedding_provider == "ollama"
    assert captured["config"].embedding_model == "nomic-embed-text"
    assert captured["config"].embedding_dimension == 768
    assert (repo_root / ".synapse" / "config.yaml").is_file()
    assert __import__("os").environ["OLLAMA_BASE_URL"] == "http://127.0.0.1:11435"


def test_init_models_from_workspace_rejects_conflicting_ollama_base_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    synapse_dir = repo_root / ".synapse"
    synapse_dir.mkdir()
    (synapse_dir / "config.yaml").write_text(_conflicting_ollama_config(), encoding="utf-8")

    loaded = load_workspace_config(repo_root)
    monkeypatch.setattr("workspace.model_init.models.get_config", lambda: type("Config", (), {"embedding_dimension": 3072})())

    with pytest.raises(ValueError, match="different Ollama base URLs"):
        init_models_from_workspace(loaded)


def test_infer_embedding_dimension_uses_known_model_defaults() -> None:
    assert infer_embedding_dimension("text-embedding-3-large", default_dimension=1) == 3072
    assert infer_embedding_dimension("text-embedding-3-small", default_dimension=1) == 1536
    assert infer_embedding_dimension("nomic-embed-text", default_dimension=1) == 768
    assert infer_embedding_dimension("custom-embedder", default_dimension=123) == 123


def _sample_config() -> str:
    return """
version: 1

workspace:
  name: test-workspace
  root: .

sources:
  code_roots:
    - path: sample/code
      language_hints: [python]
      include:
        - "**/*.py"
  knowledge_roots:
    - path: sample/knowledge
      kinds: [scientific]
      include:
        - "**/*.md"

models:
  chat:
    provider: ollama
    model: gemma4:e2b
  embeddings:
    provider: ollama
    model: nomic-embed-text

runtime:
  ollama:
    base_url: http://127.0.0.1:11435
"""


def _conflicting_ollama_config() -> str:
    return """
version: 1

workspace:
  name: test-workspace
  root: .

sources:
  code_roots:
    - path: sample/code
      language_hints: [python]
      include:
        - "**/*.py"
  knowledge_roots:
    - path: sample/knowledge
      kinds: [scientific]
      include:
        - "**/*.md"

models:
  chat:
    provider: ollama
    model: gemma4:e2b
    base_url: http://127.0.0.1:11435
  embeddings:
    provider: ollama
    model: nomic-embed-text
    base_url: http://127.0.0.1:11436
"""
