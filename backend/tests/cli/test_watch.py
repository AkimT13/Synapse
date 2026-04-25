from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main
from synapse_cli.watch_command import _count_changes, _scan_target, run_watch


def test_count_changes_detects_modified_and_added_files() -> None:
    previous = {
        "a.py": __import__("synapse_cli.watch_command", fromlist=["FileFingerprint"]).FileFingerprint(1, 10)
    }
    current = {
        "a.py": __import__("synapse_cli.watch_command", fromlist=["FileFingerprint"]).FileFingerprint(2, 10),
        "b.py": __import__("synapse_cli.watch_command", fromlist=["FileFingerprint"]).FileFingerprint(1, 5),
    }
    assert _count_changes(previous, current) == 2


def test_scan_target_respects_include_and_exclude(tmp_path: Path) -> None:
    root = tmp_path / "code"
    root.mkdir()
    (root / "keep.py").write_text("print('x')", encoding="utf-8")
    ignored_dir = root / "__pycache__"
    ignored_dir.mkdir()
    (ignored_dir / "skip.py").write_text("print('x')", encoding="utf-8")

    target = __import__("synapse_cli.watch_command", fromlist=["WatchTarget"]).WatchTarget(
        kind="code",
        path=root,
        include=["**/*.py", "*.py"],
        exclude=["**/__pycache__/**"],
        metadata={"language_hints": ["python"]},
    )

    snapshot = _scan_target(target)
    assert str(root / "keep.py") in snapshot
    assert str(ignored_dir / "skip.py") not in snapshot


def test_run_watch_reindexes_changed_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="watch-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    (repo_root / "code").mkdir()
    (repo_root / "docs").mkdir()

    code_snapshots = iter([
        {str(repo_root / "code" / "a.py"): _fp(1, 1)},
        {str(repo_root / "code" / "a.py"): _fp(2, 1)},
        {str(repo_root / "code" / "a.py"): _fp(2, 1)},
    ])
    knowledge_snapshots = iter([{}, {}, {}])

    monkeypatch.setattr("synapse_cli.watch_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr("synapse_cli.watch_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.watch_command.time.sleep", lambda _: None)
    monkeypatch.setattr("synapse_cli.watch_command.time.monotonic", _Monotonic([0.0, 0.2]))
    monkeypatch.setattr(
        "synapse_cli.watch_command._scan_target",
        lambda target: next(code_snapshots) if target.kind == "code" else next(knowledge_snapshots),
    )
    monkeypatch.setattr("synapse_cli.watch_command.CodeIngestionJob", _DummyCodeJob)
    monkeypatch.setattr("synapse_cli.watch_command.KnowledgeIngestionJob", _DummyKnowledgeJob)

    exit_code, output = run_watch(
        start_path=repo_root,
        poll_interval=0.01,
        debounce_ms=100,
        max_cycles=2,
    )

    assert exit_code == 0
    assert "Events: 1" in output
    assert "code" in output


def test_cli_watch_json_outputs_machine_readable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="watch-json-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    (repo_root / "code").mkdir()
    (repo_root / "docs").mkdir()

    monkeypatch.setattr(
        "synapse_cli.main.run_watch",
        lambda **kwargs: (0, json.dumps({"workspace": "watch-json-demo", "watching": [], "events": []})),
    )

    exit_code = main(["watch", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == "watch-json-demo"


class _DummyVectorStore:
    def __init__(self, **kwargs):
        pass

    def __enter__(self) -> _DummyVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None


class _DummyCodeJob:
    def __init__(self, vector_store, should_use_llm, on_progress):
        self._on_progress = on_progress

    def run(self, path: str, languages=None):
        self._on_progress("parsed changed code")
        return _DummyResult(
            files_processed=1,
            chunks_parsed=2,
            chunks_normalized=2,
            chunks_embedded=2,
            chunks_stored=2,
            errors=[],
        )


class _DummyKnowledgeJob:
    def __init__(self, vector_store, should_use_llm, on_progress):
        self._on_progress = on_progress

    def run(self, path: str):
        self._on_progress("parsed changed docs")
        return _DummyResult(
            files_processed=1,
            chunks_parsed=2,
            chunks_normalized=2,
            chunks_embedded=2,
            chunks_stored=2,
            errors=[],
        )


class _DummyResult:
    def __init__(self, **data):
        self._data = data

    def model_dump(self):
        return dict(self._data)

    @property
    def files_processed(self):
        return self._data["files_processed"]

    @property
    def chunks_stored(self):
        return self._data["chunks_stored"]

    @property
    def errors(self):
        return self._data["errors"]


class _Monotonic:
    def __init__(self, values: list[float]) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def _fp(mtime_ns: int, size: int):
    return __import__("synapse_cli.watch_command", fromlist=["FileFingerprint"]).FileFingerprint(mtime_ns, size)
