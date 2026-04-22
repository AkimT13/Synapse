from __future__ import annotations

import json
from pathlib import Path

from synapse_cli.services_command import COMPOSE_FILENAME, RUNTIME_DIRNAME
from storage.vector_store import VectorStore, actian_available
from workspace.loader import load_workspace_config


def run_doctor(
    *,
    start_path: str | Path = ".",
    as_json: bool = False,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    runtime_compose_path = (
        workspace.repo_root / ".synapse" / RUNTIME_DIRNAME / COMPOSE_FILENAME
    )
    checks = []
    checks.append(
        _check(
            "workspace_config",
            True,
            f"Loaded {workspace.config_path}",
        )
    )

    missing_code_roots = [str(root.path) for root in workspace.code_roots if not root.path.exists()]
    checks.append(
        _check(
            "code_roots",
            not missing_code_roots,
            "All configured code roots exist."
            if not missing_code_roots
            else "Missing code roots: " + ", ".join(missing_code_roots),
        )
    )

    missing_knowledge_roots = [
        str(root.path) for root in workspace.knowledge_roots if not root.path.exists()
    ]
    checks.append(
        _check(
            "knowledge_roots",
            not missing_knowledge_roots,
            "All configured knowledge roots exist."
            if not missing_knowledge_roots
            else "Missing knowledge roots: " + ", ".join(missing_knowledge_roots),
        )
    )

    checks.append(_check_model("chat_model", workspace.chat_model))
    checks.append(_check_model("embedding_model", workspace.embedding_model))

    actian_installed = actian_available()
    checks.append(
        _check(
            "actian_client",
            actian_installed,
            "Actian VectorAI client is installed."
            if actian_installed
            else "Actian VectorAI client is not installed. Install backend/requirements-actian.txt.",
            fix="pip install -r backend/requirements-actian.txt" if not actian_installed else None,
        )
    )

    db_reachable = False
    db_error = None
    if actian_installed:
        try:
            with VectorStore() as store:
                store.client.collections.exists("chunks")
            db_reachable = True
        except Exception as exc:  # noqa: BLE001
            db_error = str(exc)

    checks.append(
        _check(
            "actian_service",
            db_reachable,
            "Actian VectorAI is reachable on localhost:50051."
            if db_reachable
            else (
                "Actian VectorAI is not reachable on localhost:50051. "
                f"Try `synapse services up` using {runtime_compose_path}."
                + (f" {db_error}" if db_error else "")
            ),
            fix=f"synapse services up  # uses {runtime_compose_path}" if not db_reachable else None,
        )
    )

    ok = all(check["ok"] for check in checks)
    suggested_fixes = _collect_fixes(checks)
    payload = {
        "workspace": {
            "name": workspace.config.workspace.name,
            "repo_root": str(workspace.repo_root),
            "config_path": str(workspace.config_path),
            "runtime_compose_path": str(runtime_compose_path),
        },
        "ok": ok,
        "checks": checks,
        "suggested_fixes": suggested_fixes,
    }

    if as_json:
        return (0 if ok else 3), json.dumps(payload, indent=2, sort_keys=True)
    return (0 if ok else 3), _render_text_doctor(payload)


def _check(
    name: str,
    ok: bool,
    detail: str,
    *,
    fix: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"name": name, "ok": ok, "detail": detail}
    if fix:
        payload["fix"] = fix
    return payload


def _check_model(name: str, model) -> dict[str, object]:
    if model.provider == "openai":
        ok = bool(model.api_key)
        detail = (
            f"OpenAI model {model.model} configured with API key."
            if ok
            else (
                f"OpenAI model {model.model} selected but {model.api_key_env or 'api key env'} "
                "is not set."
            )
        )
        fix = (
            f"Set {model.api_key_env or 'OPENAI_API_KEY'} in the environment or .synapse/.env"
            if not ok
            else None
        )
        return _check(name, ok, detail, fix=fix)

    if model.provider == "ollama":
        ok = bool(model.base_url)
        detail = (
            f"Ollama model {model.model} configured at {model.base_url}."
            if ok
            else f"Ollama model {model.model} selected but no base URL is configured."
        )
        fix = "Set SYNAPSE_OLLAMA_BASE_URL or configure runtime.ollama.base_url" if not ok else None
        return _check(name, ok, detail, fix=fix)

    return _check(name, False, f"Unsupported model provider: {model.provider}")


def _collect_fixes(checks: list[dict[str, object]]) -> list[str]:
    fixes: list[str] = []
    seen: set[str] = set()
    for check in checks:
        if check["ok"]:
            continue
        fix = check.get("fix")
        if not fix or fix in seen:
            continue
        seen.add(str(fix))
        fixes.append(str(fix))
    return fixes


def _render_text_doctor(payload: dict[str, object]) -> str:
    lines = [
        f"Workspace: {payload['workspace']['name']}",
        f"Repo root: {payload['workspace']['repo_root']}",
        f"Config: {payload['workspace']['config_path']}",
        f"Runtime compose: {payload['workspace']['runtime_compose_path']}",
        f"Overall: {'ok' if payload['ok'] else 'issues found'}",
        "",
        "Checks:",
    ]
    for check in payload["checks"]:
        status = "ok" if check["ok"] else "fail"
        lines.append(f"  - {check['name']}: {status}")
        lines.append(f"    {check['detail']}")
        if check.get("fix"):
            lines.append(f"    fix: {check['fix']}")
    if payload["suggested_fixes"]:
        lines.extend(["", "Suggested fixes:"])
        for fix in payload["suggested_fixes"]:
            lines.append(f"  - {fix}")
    return "\n".join(lines)
