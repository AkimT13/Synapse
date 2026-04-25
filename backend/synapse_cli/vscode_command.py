"""
``synapse vscode`` — build and launch VS Code with the Synapse extension.

Compiles the TypeScript source and opens a new VS Code window in
Extension Development Host mode, so the extension loads from source
with ``synapse`` available on PATH from the current shell.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


GREY = "\033[90m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _find_extension_dir() -> Path:
    """Locate the vscode-extension/ directory relative to this file."""
    current = Path(__file__).resolve().parent  # synapse_cli/
    for ancestor in (current, *current.parents):
        candidate = ancestor / "vscode-extension"
        if (candidate / "package.json").is_file():
            return candidate
        # Might be inside backend/
        if ancestor.name == "backend":
            candidate = ancestor.parent / "vscode-extension"
            if (candidate / "package.json").is_file():
                return candidate
    raise RuntimeError(
        "Cannot find vscode-extension/ directory. "
        "Make sure you're running from the Synapse repo."
    )


def _find_repo_root(ext_dir: Path) -> Path:
    """Return the repo root (parent of vscode-extension/)."""
    return ext_dir.parent


def _run(cmd: list[str], cwd: Path, label: str) -> bool:
    """Run a command, print output on failure, return success."""
    print(f"  {CYAN}{label}{RESET}")
    result = subprocess.run(
        cmd, cwd=str(cwd),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  {RED}Failed:{RESET} {' '.join(cmd)}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"    {line}")
        if result.stdout:
            for line in result.stdout.strip().splitlines()[:10]:
                print(f"    {line}")
        return False
    return True


def run_vscode_install() -> int:
    ext_dir = _find_extension_dir()
    repo_root = _find_repo_root(ext_dir)

    # Check prerequisites.
    if not shutil.which("code"):
        print(
            f"{RED}VS Code CLI not found.{RESET}\n"
            "  Open VS Code → Cmd+Shift+P → 'Shell Command: Install code command in PATH'",
            file=sys.stderr,
        )
        return 2

    if not shutil.which("npx"):
        print(f"{RED}npx not found. Install Node.js first.{RESET}", file=sys.stderr)
        return 2

    print(f"{BOLD}Launching Synapse VS Code extension…{RESET}\n")

    # 1. npm install
    if not _run(["npm", "install", "--silent"], ext_dir, "Installing dependencies…"):
        return 1

    # 2. Build TypeScript
    if not _run(["npm", "run", "build"], ext_dir, "Compiling TypeScript…"):
        return 1

    # 3. Launch VS Code in Extension Development Host mode.
    # This opens a new window with the extension loaded from source,
    # inheriting the current PATH so `synapse` is found from the venv.
    print(f"  {CYAN}Opening VS Code…{RESET}")
    subprocess.Popen(
        ["code", f"--extensionDevelopmentPath={ext_dir}", str(repo_root)],
        env=os.environ,
    )

    print(f"\n{GREEN}✓ VS Code opened with Synapse extension loaded.{RESET}")
    return 0
