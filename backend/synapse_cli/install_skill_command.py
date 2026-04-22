from __future__ import annotations

import json
from pathlib import Path

from workspace.loader import load_workspace_config


SKILL_NAME = "synapse-review"
SUPPORTED_AGENTS = ("codex", "claude")


def run_install_skill(
    *,
    start_path: str | Path = ".",
    agent: str = "both",
    force: bool = False,
    as_json: bool = False,
) -> tuple[int, str]:
    try:
        workspace = load_workspace_config(start_path)
    except FileNotFoundError as exc:
        return 2, str(exc)

    targets = _resolve_targets(workspace.repo_root, agent)
    existing = [target for target in targets if target["skill_path"].exists()]
    if existing and not force:
        existing_paths = ", ".join(str(target["skill_path"]) for target in existing)
        return 4, f"Skill already exists. Pass --force to overwrite: {existing_paths}"

    overwritten_paths = {target["skill_path"] for target in existing}
    installed: list[dict[str, object]] = []
    for target in targets:
        skill_dir = target["skill_dir"]
        skill_path = target["skill_path"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(_render_skill_markdown(), encoding="utf-8")
        installed.append(
            {
                "agent": target["agent"],
                "skill_name": SKILL_NAME,
                "path": str(skill_path),
                "overwritten": skill_path in overwritten_paths,
            }
        )

    payload = {
        "workspace": workspace.config.workspace.name,
        "skill_name": SKILL_NAME,
        "installed": installed,
    }

    if as_json:
        return 0, json.dumps(payload, indent=2, sort_keys=True)
    return 0, _render_text_install_skill(payload)


def _resolve_targets(repo_root: Path, agent: str) -> list[dict[str, object]]:
    if agent == "both":
        selected_agents = list(SUPPORTED_AGENTS)
    elif agent in SUPPORTED_AGENTS:
        selected_agents = [agent]
    else:
        raise ValueError(f"Unsupported agent: {agent}")

    targets: list[dict[str, object]] = []
    for selected_agent in selected_agents:
        base_dir = (
            repo_root / ".agents" / "skills"
            if selected_agent == "codex"
            else repo_root / ".claude" / "skills"
        )
        skill_dir = base_dir / SKILL_NAME
        targets.append(
            {
                "agent": selected_agent,
                "skill_dir": skill_dir,
                "skill_path": skill_dir / "SKILL.md",
            }
        )
    return targets


def _render_skill_markdown() -> str:
    return """---
name: synapse-review
description: Use when editing domain-relevant code in this repository, especially under sample/code. Before editing, run Synapse review on the target file. After editing, run Synapse review again and use the findings to verify alignment with sample/knowledge.
---

# Synapse Review

Use this skill for domain-sensitive code changes in this repository.

Current workspace defaults:
- edit target files under `sample/code`
- treat `sample/knowledge` as the domain reference corpus
- avoid modifying `backend/`, `frontend/`, or `.synapse/` unless the task explicitly requires it

## Required workflow

1. Start from the repository root.
2. Before editing a target Python file, run:

```bash
cd backend && python -m synapse_cli.main review --file ../sample/code/TARGET_FILE.py --json
```

3. Read the drift status, findings, and supporting sources before making changes.
4. Make the requested code changes.
5. After editing the same file, run the same review command again.
6. If the post-edit drift status is `warning` or `conflict`, explain why and try to fix it.

## Fallback commands

If review is inconclusive, use one of these:

```bash
cd backend && python -m synapse_cli.main drift-check --file ../sample/code/TARGET_FILE.py --json
```

```bash
cd backend && python -m synapse_cli.main query code "Behavior: ..." --json
```

## Final response requirements

Include:
- what changed
- key Synapse findings before the edit
- key Synapse findings after the edit
- final drift status for the file

Keep changes scoped to `sample/code` unless the user explicitly asks for broader repository changes.
"""


def _render_text_install_skill(payload: dict[str, object]) -> str:
    lines = [
        f"Workspace: {payload['workspace']}",
        f"Skill: {payload['skill_name']}",
        "",
        "Installed:",
    ]
    for item in payload["installed"]:
        overwrite_note = " (overwritten)" if item["overwritten"] else ""
        lines.append(f"  - {item['agent']}: {item['path']}{overwrite_note}")
    return "\n".join(lines)
