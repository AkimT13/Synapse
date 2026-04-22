from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_services_up_runs_compose_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    seen: dict[str, object] = {}

    def fake_run(command, cwd, check, capture_output, text):
        seen["command"] = command
        seen["cwd"] = cwd
        return subprocess.CompletedProcess(command, 0, stdout="started", stderr="")

    monkeypatch.setattr("synapse_cli.services_command.shutil.which", lambda name: "/usr/bin/" + name if name == "docker-compose" else None)
    monkeypatch.setattr("synapse_cli.services_command.subprocess.run", fake_run)

    exit_code = main(["services", "up", "--repo-root", str(repo_root)])

    assert exit_code == 0
    assert seen["command"] == ["docker-compose", "up", "-d"]
    assert seen["cwd"] == repo_root / ".synapse" / "runtime"
    assert (repo_root / ".synapse" / "runtime" / "docker-compose.yml").is_file()
    assert "Action: up" in capsys.readouterr().out


def test_cli_services_status_json_reports_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.setattr("synapse_cli.services_command.shutil.which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    monkeypatch.setattr(
        "synapse_cli.services_command.subprocess.run",
        lambda command, cwd, check, capture_output, text: subprocess.CompletedProcess(
            command,
            0,
            stdout="NAME         IMAGE                               COMMAND     SERVICE      STATUS\nvectoraidb   williamimoh/actian-vectorai-db:latest   \"server\"   vectoraidb   Up 10 seconds",
            stderr="",
        ),
    )

    exit_code = main(["services", "status", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "status"
    assert payload["running"] is True
    assert payload["compose_command"] == ["docker", "compose"]


def test_cli_services_logs_runs_compose_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    seen: dict[str, object] = {}

    def fake_run(command, cwd, check, capture_output, text):
        seen["command"] = command
        seen["cwd"] = cwd
        return subprocess.CompletedProcess(command, 0, stdout="vectoraidb | ready", stderr="")

    monkeypatch.setattr(
        "synapse_cli.services_command.shutil.which",
        lambda name: "/usr/bin/" + name if name == "docker-compose" else None,
    )
    monkeypatch.setattr("synapse_cli.services_command.subprocess.run", fake_run)

    exit_code = main(["services", "logs", "--repo-root", str(repo_root)])

    assert exit_code == 0
    assert seen["command"] == ["docker-compose", "logs", "--tail", "200"]
    assert seen["cwd"] == repo_root / ".synapse" / "runtime"
    out = capsys.readouterr().out
    assert "Action: logs" in out
    assert "vectoraidb | ready" in out


def test_cli_services_returns_error_when_compose_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.setattr("synapse_cli.services_command.shutil.which", lambda _name: None)

    exit_code = main(["services", "status", "--repo-root", str(repo_root)])

    assert exit_code == 3
    assert "Docker Compose is not installed" in capsys.readouterr().err


def test_cli_services_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["services", "status", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="services-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root
