"""
Tests for the repository walker.

Uses the ``tmp_path`` pytest fixture to create disposable directory
trees so tests never touch the real filesystem.
"""
from __future__ import annotations

import os
from pathlib import Path

from ingestion.code.walker import (
    _compute_module_path,
    _should_exclude,
    walk_repository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_PYTHON = """\
def greet(name: str) -> str:
    return f"hello {name}"
"""


def _write(path: Path, content: str = SIMPLE_PYTHON) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_walker_discovers_python_files_in_nested_directories(tmp_path: Path) -> None:
    _write(tmp_path / "a.py")
    _write(tmp_path / "sub" / "b.py")
    _write(tmp_path / "sub" / "deep" / "c.py")

    chunks = walk_repository(str(tmp_path))

    source_files = {c.source_file for c in chunks}
    assert len(source_files) == 3
    assert any("a.py" in f for f in source_files)
    assert any("b.py" in f for f in source_files)
    assert any("c.py" in f for f in source_files)


def test_walker_skips_venv_and_pycache_by_default(tmp_path: Path) -> None:
    _write(tmp_path / "good.py")
    _write(tmp_path / ".venv" / "lib" / "bad.py")
    _write(tmp_path / "__pycache__" / "cached.py")

    chunks = walk_repository(str(tmp_path))

    source_files = {c.source_file for c in chunks}
    assert any("good.py" in f for f in source_files)
    assert not any(".venv" in f for f in source_files)
    assert not any("__pycache__" in f for f in source_files)


def test_walker_respects_custom_exclude_patterns(tmp_path: Path) -> None:
    _write(tmp_path / "keep.py")
    _write(tmp_path / "generated" / "skip.py")

    chunks = walk_repository(
        str(tmp_path),
        exclude_patterns=["generated"],
    )

    source_files = {c.source_file for c in chunks}
    assert any("keep.py" in f for f in source_files)
    assert not any("generated" in f for f in source_files)


def test_walker_computes_correct_module_path(tmp_path: Path) -> None:
    assert _compute_module_path(
        os.path.join("/repo", "src", "ingestion", "parser.py"),
        "/repo",
    ) == "src.ingestion.parser"

    assert _compute_module_path(
        os.path.join("/repo", "main.py"),
        "/repo",
    ) == "main"


def test_walker_skips_unreadable_files_without_crashing(tmp_path: Path) -> None:
    _write(tmp_path / "good.py")

    bad_file = tmp_path / "bad.py"
    bad_file.write_bytes(b"\x80\x81\x82\x83\xff\xfe")

    chunks = walk_repository(str(tmp_path))

    # Should get chunks from good.py, bad.py may or may not parse
    # The important thing is no exception was raised
    assert isinstance(chunks, list)
