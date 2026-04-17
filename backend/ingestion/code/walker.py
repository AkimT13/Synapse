"""
Walks a repository directory, discovers source files by extension,
dispatches each to the appropriate language parser, and returns
RawCodeChunks.

File discovery itself (walk + exclude + extension match) lives in
:mod:`ingestion.walker`. This module owns the code-specific work:
filtering by registered language parsers, computing dotted module paths,
and invoking each parser.
"""
from __future__ import annotations

import os
from pathlib import Path

from ingestion.code.languages import get_parser_for_extension, supported_extensions
from ingestion.schemas import RawCodeChunk
from ingestion.walker import (
    DEFAULT_EXCLUDE_PATTERNS,
    iter_files,
    should_exclude as _should_exclude,  # re-exported for tests
)

__all__ = [
    "DEFAULT_EXCLUDE_PATTERNS",
    "walk_repository",
    "_should_exclude",
]


def _compute_module_path(file_path: str, repo_root: str) -> str:
    """Convert a relative file path to a dotted module path.

    Example: ``src/ingestion/code/parser.py`` -> ``src.ingestion.code.parser``
    """
    relative_path = os.path.relpath(file_path, repo_root)
    relative_path = relative_path.replace(os.sep, "/")
    if relative_path.endswith(".py"):
        relative_path = relative_path[:-3]
    elif "." in Path(relative_path).name:
        relative_path = str(Path(relative_path).with_suffix(""))
        relative_path = relative_path.replace(os.sep, "/")
    return relative_path.replace("/", ".")


def walk_repository(
    repo_path: str,
    languages: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[RawCodeChunk]:
    """Discover source files in *repo_path* and parse them into chunks.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository root.
    languages:
        Optional whitelist of language names (e.g. ``["python"]``).
        When ``None``, all registered languages are used.
    exclude_patterns:
        Directory / file patterns to skip.  Merged with the built-in
        defaults inside :func:`ingestion.walker.iter_files`.
    """
    chunks: list[RawCodeChunk] = []

    for file_path in iter_files(
        repo_path,
        extensions=supported_extensions(),
        exclude_patterns=exclude_patterns,
    ):
        parser = get_parser_for_extension(file_path.suffix)
        if parser is None:
            continue

        if languages is not None and parser.language not in languages:
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        module_path = _compute_module_path(str(file_path), repo_path)

        try:
            file_chunks = parser.parse_file(source, str(file_path), module_path)
            chunks.extend(file_chunks)
        except Exception:
            continue

    return chunks
