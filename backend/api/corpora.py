"""
Corpora browsing endpoints. Exposes read-only access to the raw files
stored under the code and knowledge upload roots so the frontend can
render a file tree and preview individual files.

Both corpora share the same surface — tree walk plus single-file fetch
— so the handlers are generated from a small pair of helpers that
bind the corpus-specific upload root.
"""
from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.schemas import TreeNode
from api.settings import CODE_UPLOADS_DIR, KNOWLEDGE_UPLOADS_DIR


router = APIRouter()


_NOISE_DIR_NAMES = {"__pycache__", ".git", ".venv", "node_modules"}
_NOISE_GLOB_PATTERNS = ("*.egg-info",)


def _is_noise(name: str) -> bool:
    if name.startswith("."):
        return True
    if name in _NOISE_DIR_NAMES:
        return True
    for pattern in _NOISE_GLOB_PATTERNS:
        if fnmatch(name, pattern):
            return True
    return False


def _build_tree(root: Path) -> TreeNode:
    """Walk ``root`` recursively and build a TreeNode structure.

    Directories are listed before files, both alphabetically. Hidden
    entries and well-known noise folders are skipped. When ``root``
    does not exist yet a placeholder empty-tree node is returned —
    an empty workspace is a valid state, not a 404.
    """
    if not root.exists() or not root.is_dir():
        return TreeNode(name="root", path="", type="dir", children=[])

    def walk(directory: Path, relative: str) -> list[TreeNode]:
        dirs: list[TreeNode] = []
        files: list[TreeNode] = []
        for entry in directory.iterdir():
            if _is_noise(entry.name):
                continue
            child_relative = f"{relative}/{entry.name}" if relative else entry.name
            if entry.is_dir():
                dirs.append(
                    TreeNode(
                        name=entry.name,
                        path=child_relative,
                        type="dir",
                        children=walk(entry, child_relative),
                    )
                )
            elif entry.is_file():
                files.append(
                    TreeNode(
                        name=entry.name,
                        path=child_relative,
                        type="file",
                        children=[],
                    )
                )
        dirs.sort(key=lambda node: node.name.lower())
        files.sort(key=lambda node: node.name.lower())
        return dirs + files

    return TreeNode(
        name="root",
        path="",
        type="dir",
        children=walk(root, ""),
    )


def _resolve_within_root(root: Path, relative_path: str) -> Path:
    """Resolve ``relative_path`` under ``root`` and guard against traversal.

    Raises 400 if the resolved path escapes the root, 404 if the file
    does not exist or is not a regular file.
    """
    if not root.exists():
        raise HTTPException(status_code=404, detail="File not found")

    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()

    if not candidate.is_relative_to(root_resolved):
        raise HTTPException(status_code=400, detail="Path escapes corpus root")

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return candidate


# -- code corpus -----------------------------------------------------------


@router.get("/code/tree", response_model=TreeNode)
def get_code_tree() -> TreeNode:
    return _build_tree(CODE_UPLOADS_DIR)


@router.get("/code/files/{path:path}")
def get_code_file(path: str) -> FileResponse:
    resolved = _resolve_within_root(CODE_UPLOADS_DIR, path)
    return FileResponse(resolved)


# -- knowledge corpus -----------------------------------------------------


@router.get("/knowledge/tree", response_model=TreeNode)
def get_knowledge_tree() -> TreeNode:
    return _build_tree(KNOWLEDGE_UPLOADS_DIR)


@router.get("/knowledge/files/{path:path}")
def get_knowledge_file(path: str) -> FileResponse:
    resolved = _resolve_within_root(KNOWLEDGE_UPLOADS_DIR, path)
    return FileResponse(resolved)
