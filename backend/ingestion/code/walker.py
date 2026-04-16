"""
Walks a repository directory, discovers source files by extension,
dispatches each to the appropriate language parser, and returns
RawCodeChunks.

This is the entry point for code ingestion: given a local checkout path
the walker enumerates every supported source file, reads it, delegates
to the matching LanguageParser, and collects all resulting chunks into a
flat list ready for normalization.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from ingestion.code.languages import get_parser_for_extension, supported_extensions
from ingestion.schemas import RawCodeChunk

DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    ".venv",
    "__pycache__",
    ".git",
    "node_modules",
    "*.egg-info",
    "dist",
    "build",
    ".tox",
]


def _should_exclude(path: str, patterns: list[str]) -> bool:
    """Return True if any segment of *path* matches one of *patterns*."""
    parts = Path(path).parts
    for pattern in patterns:
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


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
        defaults.
    """
    effective_excludes = list(DEFAULT_EXCLUDE_PATTERNS)
    if exclude_patterns is not None:
        effective_excludes.extend(exclude_patterns)

    allowed_extensions = supported_extensions()
    chunks: list[RawCodeChunk] = []

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Prune excluded directories in-place so os.walk skips them
        dirnames[:] = [
            d for d in dirnames
            if not _should_exclude(os.path.join(dirpath, d), effective_excludes)
        ]

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            if _should_exclude(file_path, effective_excludes):
                continue

            extension = Path(filename).suffix
            if extension not in allowed_extensions:
                continue

            parser = get_parser_for_extension(extension)
            if parser is None:
                continue

            if languages is not None and parser.language not in languages:
                continue

            try:
                source = Path(file_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            module_path = _compute_module_path(file_path, repo_path)

            try:
                file_chunks = parser.parse_file(source, file_path, module_path)
                chunks.extend(file_chunks)
            except Exception:
                continue

    return chunks
