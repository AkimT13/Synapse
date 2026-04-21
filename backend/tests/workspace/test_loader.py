from __future__ import annotations

from pathlib import Path

import pytest

from workspace.loader import find_workspace_root, load_workspace_config


def test_find_workspace_root_walks_up_from_nested_directory(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    nested = repo_root / "backend" / "src"
    nested.mkdir(parents=True)
    synapse_dir = repo_root / ".synapse"
    synapse_dir.mkdir()
    (synapse_dir / "config.yaml").write_text(_sample_config(), encoding="utf-8")

    assert find_workspace_root(nested) == repo_root.resolve()


def test_load_workspace_config_resolves_relative_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "backend").mkdir(parents=True)
    (repo_root / "docs").mkdir()
    synapse_dir = repo_root / ".synapse"
    synapse_dir.mkdir()
    (synapse_dir / "config.yaml").write_text(_sample_config(), encoding="utf-8")

    loaded = load_workspace_config(repo_root / "backend")

    assert loaded.repo_root == repo_root.resolve()
    assert loaded.workspace_root == repo_root.resolve()
    assert loaded.code_roots[0].path == (repo_root / "backend").resolve()
    assert loaded.code_roots[0].metadata["language_hints"] == ["python"]
    assert loaded.knowledge_roots[0].path == (repo_root / "docs").resolve()
    assert loaded.knowledge_roots[0].metadata["kinds"] == ["spec", "reference"]
    assert "**/.git/**" in loaded.config.filters.global_exclude


def test_load_workspace_config_resolves_env_backed_model_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    synapse_dir = repo_root / ".synapse"
    synapse_dir.mkdir()
    (synapse_dir / "config.yaml").write_text(_sample_config(), encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYNAPSE_OLLAMA_BASE_URL", "http://127.0.0.1:11435")

    loaded = load_workspace_config(repo_root)

    assert loaded.chat_model.provider == "openai"
    assert loaded.chat_model.model == "gpt-4o-mini"
    assert loaded.chat_model.api_key_env == "OPENAI_API_KEY"
    assert loaded.chat_model.api_key == "test-key"

    assert loaded.embedding_model.provider == "ollama"
    assert loaded.embedding_model.model == "nomic-embed-text"
    assert loaded.embedding_model.base_url == "http://127.0.0.1:11435"


def test_load_workspace_config_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_workspace_config(tmp_path)


def _sample_config() -> str:
    return """
version: 1

workspace:
  name: test-workspace
  root: .

sources:
  code_roots:
    - path: backend
      language_hints: [python]
      include:
        - "**/*.py"
  knowledge_roots:
    - path: docs
      kinds: [spec, reference]
      include:
        - "**/*.md"
        - "**/*.pdf"

filters:
  global_exclude:
    - "**/.git/**"

models:
  chat:
    provider: openai
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
  embeddings:
    provider: ollama
    model: nomic-embed-text

runtime:
  ollama:
    base_url: http://localhost:11434
    base_url_env: SYNAPSE_OLLAMA_BASE_URL
"""
