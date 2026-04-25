"""
``synapse ui`` — start the backend API and frontend dev server together.

Spawns both as child processes, streams their output with colour-coded
prefixes, and tears everything down on Ctrl-C.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _find_synapse_root() -> Path:
    """Walk up from this file to find the repo root (parent of backend/)."""
    current = Path(__file__).resolve().parent  # synapse_cli/
    for ancestor in (current, *current.parents):
        if (ancestor / "backend" / "pyproject.toml").is_file():
            return ancestor
        # We might be inside backend/ already.
        if (ancestor / "pyproject.toml").is_file() and (ancestor.parent / "frontend").is_dir():
            return ancestor.parent
    raise RuntimeError(
        "Cannot locate Synapse repo root. "
        "Make sure you installed with `pip install -e .` from the backend/ directory."
    )


GREY = "\033[90m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _stream_output(proc: subprocess.Popen, prefix: str, colour: str) -> None:
    """Read lines from a process stdout and print with a coloured prefix."""
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        print(f"{colour}{prefix}{RESET} {line}", flush=True)


def run_ui(*, port: int = 8000, frontend_port: int = 3000, no_open: bool = False) -> int:
    root = _find_synapse_root()
    backend_dir = root / "backend"
    frontend_dir = root / "frontend"

    if not frontend_dir.is_dir():
        print(f"{RED}Frontend directory not found at {frontend_dir}{RESET}", file=sys.stderr)
        return 2

    # Resolve the venv python so uvicorn uses the right environment.
    venv_python = backend_dir / ".venv" / "bin" / "python"
    if not venv_python.is_file():
        # Fall back to current python (already in the venv via pip install -e).
        venv_python = Path(sys.executable)

    env = {**os.environ}
    env["NEXT_PUBLIC_API_BASE"] = f"http://127.0.0.1:{port}"

    print(f"{BOLD}Starting Synapse…{RESET}")
    print(f"  {CYAN}Backend{RESET}  → http://127.0.0.1:{port}")
    print(f"  {MAGENTA}Frontend{RESET} → http://localhost:{frontend_port}")
    print(f"  {GREY}Press Ctrl+C to stop{RESET}")
    print()

    backend_proc = subprocess.Popen(
        [
            str(venv_python), "-m", "uvicorn",
            "api.app:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--reload",
        ],
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    frontend_proc = subprocess.Popen(
        ["npx", "next", "dev", "--port", str(frontend_port)],
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    backend_thread = threading.Thread(
        target=_stream_output,
        args=(backend_proc, "api |", CYAN),
        daemon=True,
    )
    frontend_thread = threading.Thread(
        target=_stream_output,
        args=(frontend_proc, " ui |", MAGENTA),
        daemon=True,
    )

    backend_thread.start()
    frontend_thread.start()

    # Open browser after a short delay so the servers have time to boot.
    if not no_open:
        def _open_browser():
            time.sleep(3)
            webbrowser.open(f"http://localhost:{frontend_port}")
        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        # Wait for either process to exit.
        while backend_proc.poll() is None and frontend_proc.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in (backend_proc, frontend_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print(f"\n{BOLD}Synapse stopped.{RESET}")

    return 0
