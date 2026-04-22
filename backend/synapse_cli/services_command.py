from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from workspace.loader import load_workspace_config

RUNTIME_DIRNAME = "runtime"
COMPOSE_FILENAME = "docker-compose.yml"
DATA_DIRNAME = "data"


def run_services(
    *,
    start_path: str | Path = ".",
    action: str = "status",
    as_json: bool = False,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    compose_file = _ensure_runtime_compose(workspace.repo_root)

    try:
        compose_prefix = _resolve_compose_prefix()
    except RuntimeError as exc:
        return 3, str(exc)

    try:
        completed = _run_compose_action(compose_prefix, action, compose_file.parent)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        return 3, detail

    payload = {
        "workspace": workspace.config.workspace.name,
        "action": action,
        "compose_file": str(compose_file),
        "compose_command": compose_prefix,
        "ok": True,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }

    if action == "status":
        payload["running"] = _infer_running_from_ps(completed.stdout)

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_services(payload)


def _resolve_compose_prefix() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("Docker Compose is not installed or not on PATH.")


def _ensure_runtime_compose(repo_root: Path) -> Path:
    runtime_dir = repo_root / ".synapse" / RUNTIME_DIRNAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    compose_file = runtime_dir / COMPOSE_FILENAME
    if not compose_file.exists():
        compose_file.write_text(_render_runtime_compose(), encoding="utf-8")
    return compose_file


def _run_compose_action(
    compose_prefix: list[str],
    action: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    if action == "up":
        command = [*compose_prefix, "up", "-d"]
    elif action == "down":
        command = [*compose_prefix, "down"]
    elif action == "status":
        command = [*compose_prefix, "ps"]
    elif action == "logs":
        command = [*compose_prefix, "logs", "--tail", "200"]
    else:
        raise ValueError(f"Unsupported services action: {action}")

    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _infer_running_from_ps(output: str) -> bool:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return any("Up" in line or "running" in line.lower() for line in lines)


def _render_runtime_compose() -> str:
    return """version: "3.8"
services:
  vectoraidb:
    image: williamimoh/actian-vectorai-db:latest
    container_name: vectoraidb
    ports:
      - "50051:50051"
    volumes:
      - ./data:/data
    restart: unless-stopped
    stop_grace_period: 2m
"""


def _render_text_services(payload: dict[str, object]) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Action: {payload['action']}",
        f"Compose file: {payload['compose_file']}",
        f"Compose command: {' '.join(payload['compose_command'])}",
    ]

    if payload["action"] == "status":
        lines.append(f"Running: {payload['running']}")

    stdout = payload["stdout"]
    stderr = payload["stderr"]
    if stdout:
        lines.extend(["", "Output:", stdout])
    if stderr:
        lines.extend(["", "Error output:", stderr])
    return "\n".join(lines)
