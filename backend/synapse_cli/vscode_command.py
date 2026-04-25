"""
``synapse vscode`` — build and install the Synapse VS Code extension.

Compiles the TypeScript source, packages it as a .vsix, and installs
it into VS Code via ``code --install-extension``.
"""
from __future__ import annotations

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

    print(f"{BOLD}Installing Synapse VS Code extension…{RESET}\n")

    # 1. npm install
    if not _run(["npm", "install", "--silent"], ext_dir, "Installing dependencies…"):
        return 1

    # 2. Build TypeScript
    if not _run(["npm", "run", "build"], ext_dir, "Compiling TypeScript…"):
        return 1

    # 3. Package as .vsix
    if not _run(
        ["npx", "@vscode/vsce", "package", "--no-dependencies", "-o", "synapse.vsix"],
        ext_dir,
        "Packaging extension…",
    ):
        return 1

    vsix_path = ext_dir / "synapse.vsix"
    if not vsix_path.is_file():
        print(f"  {RED}Expected {vsix_path} but it wasn't created.{RESET}")
        return 1

    # 4. Install into VS Code
    if not _run(
        ["code", "--install-extension", str(vsix_path), "--force"],
        ext_dir,
        "Installing into VS Code…",
    ):
        return 1

    # Clean up the .vsix
    vsix_path.unlink(missing_ok=True)

    print(f"\n{GREEN}✓ Synapse extension installed.{RESET}")
    print(f"  Reload VS Code to activate (Cmd+Shift+P → 'Developer: Reload Window').")
    return 0
