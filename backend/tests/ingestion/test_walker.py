"""
Tests for the shared filesystem walker used by both code and knowledge
ingestion. These exercise ``iter_files`` directly — the domain-specific
tests (tests/ingestion/walker.py for code, tests/ingestion/test_pipeline.py
for knowledge) cover the full dispatch path.
"""
from __future__ import annotations

from pathlib import Path

from ingestion.walker import (
    DEFAULT_EXCLUDE_PATTERNS,
    iter_files,
    should_exclude,
)


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_iter_files_is_recursive(tmp_path: Path) -> None:
    _touch(tmp_path / "a.md")
    _touch(tmp_path / "sub" / "b.md")
    _touch(tmp_path / "sub" / "deep" / "c.md")

    names = sorted(p.name for p in iter_files(tmp_path, extensions={".md"}))
    assert names == ["a.md", "b.md", "c.md"]


def test_iter_files_filters_by_extension(tmp_path: Path) -> None:
    _touch(tmp_path / "doc.pdf")
    _touch(tmp_path / "doc.md")
    _touch(tmp_path / "image.png")
    _touch(tmp_path / "script.py")

    names = sorted(
        p.name
        for p in iter_files(tmp_path, extensions={".pdf", ".md"})
    )
    assert names == ["doc.md", "doc.pdf"]


def test_iter_files_yields_everything_when_no_extensions_given(tmp_path: Path) -> None:
    _touch(tmp_path / "a.md")
    _touch(tmp_path / "b.random")
    _touch(tmp_path / "c")  # no extension

    names = sorted(p.name for p in iter_files(tmp_path))
    assert names == ["a.md", "b.random", "c"]


def test_iter_files_skips_default_noise(tmp_path: Path) -> None:
    _touch(tmp_path / "keep.md")
    _touch(tmp_path / ".git" / "config")
    _touch(tmp_path / "node_modules" / "pkg" / "index.md")
    _touch(tmp_path / "__pycache__" / "x.md")

    paths = list(iter_files(tmp_path, extensions={".md"}))
    names = [str(p) for p in paths]
    assert any(n.endswith("keep.md") for n in names)
    assert not any(".git" in n for n in names)
    assert not any("node_modules" in n for n in names)
    assert not any("__pycache__" in n for n in names)


def test_iter_files_merges_custom_excludes_with_defaults(tmp_path: Path) -> None:
    _touch(tmp_path / "keep.md")
    _touch(tmp_path / "generated" / "skip.md")
    _touch(tmp_path / ".git" / "HEAD")  # should still be excluded by default

    paths = list(
        iter_files(
            tmp_path,
            extensions={".md"},
            exclude_patterns=["generated"],
        )
    )
    names = [str(p) for p in paths]
    assert any(n.endswith("keep.md") for n in names)
    assert not any("generated" in n for n in names)
    assert not any(".git" in n for n in names)


def test_iter_files_treats_missing_root_as_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    # Degrades silently rather than raising — callers want "no files".
    assert list(iter_files(missing, extensions={".md"})) == []


def test_iter_files_is_case_insensitive_on_extensions(tmp_path: Path) -> None:
    _touch(tmp_path / "doc.PDF")
    _touch(tmp_path / "note.Md")

    names = sorted(
        p.name
        for p in iter_files(tmp_path, extensions={".pdf", ".md"})
    )
    assert names == ["doc.PDF", "note.Md"]


def test_should_exclude_matches_per_segment() -> None:
    patterns = DEFAULT_EXCLUDE_PATTERNS
    assert should_exclude("/tmp/project/.git/HEAD", patterns) is True
    assert should_exclude("/tmp/project/foo/dist/out.js", patterns) is True
    assert should_exclude("/tmp/project/src/main.py", patterns) is False


def test_should_exclude_supports_glob_patterns(tmp_path: Path) -> None:
    patterns = ["*.egg-info"]
    assert should_exclude("/tmp/project/pkg.egg-info/PKG-INFO", patterns) is True
    assert should_exclude("/tmp/project/pkg/main.py", patterns) is False
