"""
Filesystem discovery shared by code and knowledge ingestion.

This module intentionally does not know about parsing, chunking, or
any domain-specific data model — it only walks a directory tree and
yields regular files that match an extension allowlist and are not
matched by an exclude pattern.

Both code ingestion (which then dispatches to a ``LanguageParser``) and
knowledge ingestion (which then hands files to docling) build on top of
``iter_files``. Keeping the shared surface this thin means the two
pipelines stay independent — only the filesystem concern is shared.
"""
from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable, Iterator
from pathlib import Path

# Directory / filename patterns that should never be traversed,
# regardless of the caller. These are the same entries used by the
# code walker historically; they apply equally well to documentation
# trees (people drop ``.git`` into wiki exports too).
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


def should_exclude(path: str | os.PathLike[str], patterns: Iterable[str]) -> bool:
    """Return ``True`` if any segment of *path* matches one of *patterns*.

    Matching is done per-segment with ``fnmatch`` so callers can pass
    either literal names (``".git"``) or globs (``"*.egg-info"``).
    """
    parts = Path(path).parts
    for pattern in patterns:
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def iter_files(
    root: str | os.PathLike[str],
    *,
    extensions: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> Iterator[Path]:
    """Recursively yield regular files under *root*.

    Parameters
    ----------
    root:
        Directory to walk. Non-existent or non-directory roots yield
        nothing rather than raising — callers typically want the empty
        case to degrade silently into "no files to ingest".
    extensions:
        Optional iterable of lowercase file extensions (each starting
        with ``"."``). When provided, only files whose suffix is in the
        set are yielded. When ``None``, every file is yielded.
    exclude_patterns:
        Extra patterns to merge with :data:`DEFAULT_EXCLUDE_PATTERNS`.
        The merge is a simple concatenation — callers cannot drop the
        defaults, which is intentional: noise directories are always
        excluded.

    Notes
    -----
    * Directory pruning is done in-place on ``dirnames`` so ``os.walk``
      never descends into excluded subtrees.
    * Yielded paths use :class:`pathlib.Path` so callers can use
      ``.suffix``, ``.read_text``, etc. without re-constructing.
    * Order is filesystem-dependent; tests that care should sort
      explicitly.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return

    allowed = (
        {ext.lower() for ext in extensions} if extensions is not None else None
    )

    merged_excludes = list(DEFAULT_EXCLUDE_PATTERNS)
    if exclude_patterns is not None:
        merged_excludes.extend(exclude_patterns)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune excluded directories in-place so os.walk does not descend.
        dirnames[:] = [
            d
            for d in dirnames
            if not should_exclude(os.path.join(dirpath, d), merged_excludes)
        ]

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if should_exclude(file_path, merged_excludes):
                continue
            if allowed is not None and Path(filename).suffix.lower() not in allowed:
                continue
            yield Path(file_path)
