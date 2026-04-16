"""
Document parser using docling. Converts raw files into docling
ConversionResult objects for downstream chunking.
"""
from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import ConversionResult, DocumentConverter

# File extension → docling InputFormat
_EXT_TO_FORMAT: dict[str, InputFormat] = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".md": InputFormat.MD,
    ".txt": InputFormat.MD,  # plain text treated as markdown
    ".html": InputFormat.HTML,
    ".htm": InputFormat.HTML,
}

_CONVERTER = DocumentConverter(
    allowed_formats=list(set(_EXT_TO_FORMAT.values())),
)


def parse_document(file_path: str | Path) -> ConversionResult:
    """Parse a single document file into a docling ConversionResult.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        ValueError: If the file extension is not supported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    ext = path.suffix.lower()
    if ext not in _EXT_TO_FORMAT:
        raise ValueError(
            f"Unsupported format: {ext!r}. "
            f"Supported: {', '.join(sorted(_EXT_TO_FORMAT))}"
        )
    return _CONVERTER.convert(str(path))


def parse_directory(dir_path: str | Path) -> list[ConversionResult]:
    """Parse all supported documents in a directory (non-recursive).

    Raises:
        FileNotFoundError: If *dir_path* does not exist or is not a directory.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")
    results: list[ConversionResult] = []
    for child in sorted(path.iterdir()):
        if child.is_file() and child.suffix.lower() in _EXT_TO_FORMAT:
            results.append(parse_document(child))
    return results
