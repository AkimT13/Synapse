"""
Language parser registry for the code ingestion pipeline.

Each language (Python, TypeScript, etc.) provides a concrete parser that
knows how to turn source text into a list of RawCodeChunk objects.  Parsers
self-register at import time so the rest of the pipeline stays language-
agnostic: callers look up parsers by file extension rather than hard-coding
language-specific logic.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ingestion.schemas import RawCodeChunk


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LanguageParser(Protocol):
    """Contract every language-specific parser must satisfy."""

    @property
    def language(self) -> str:  # pragma: no cover
        ...

    @property
    def file_extensions(self) -> list[str]:  # pragma: no cover
        ...

    def parse_file(
        self,
        source: str,
        file_path: str,
        module_path: str,
    ) -> list[RawCodeChunk]:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Registry internals
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, LanguageParser] = {}


def register_parser(parser: LanguageParser) -> None:
    """Add *parser* to the global registry, keyed by each of its extensions."""
    for extension in parser.file_extensions:
        _REGISTRY[extension] = parser


def get_parser_for_extension(extension: str) -> LanguageParser | None:
    """Return the parser registered for *extension*, or ``None``."""
    return _REGISTRY.get(extension)


def supported_extensions() -> set[str]:
    """Return every file extension that has a registered parser."""
    return set(_REGISTRY.keys())
