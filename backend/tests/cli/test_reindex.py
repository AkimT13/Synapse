from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_reindex_runs_reset_then_ingest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    import json as _json
    monkeypatch.setattr(
        "synapse_cli.main.run_reindex",
        lambda **kwargs: (
            0,
            _json.dumps({
                "workspace": "reindex-demo",
                "target": "all",
                "reset": {"workspace": "reindex-demo", "collection": "chunks", "deleted": True},
                "ingest": {"workspace": "reindex-demo", "target": "all", "summaries": [], "progress": []},
            }),
        ),
    )

    exit_code = main(["reindex", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Workspace: reindex-demo" in out
    assert "Reset: deleted_collection=True" in out


def test_cli_reindex_json_outputs_machine_readable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.setattr(
        "synapse_cli.main.run_reindex",
        lambda **kwargs: (
            0,
            json.dumps(
                {
                    "workspace": "reindex-demo",
                    "target": "code",
                    "reset": {"workspace": "reindex-demo", "collection": "chunks", "deleted": True},
                    "ingest": {"workspace": "reindex-demo", "target": "code", "summaries": [], "progress": []},
                }
            ),
        ),
    )

    exit_code = main(["reindex", "code", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == "reindex-demo"
    assert payload["reset"]["deleted"] is True
    assert payload["target"] == "code"


def test_cli_reindex_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["reindex", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="reindex-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root
