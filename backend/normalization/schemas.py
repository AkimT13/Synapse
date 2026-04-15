"""
Schema for normalized chunks. A NormalizedChunk extracts semantic
structure (constraints, behaviors, procedures) from a RawChunk so
downstream embedding captures intent rather than raw text.
Carries the full source RawChunk for provenance.
"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from ingestion.schemas import AnnotatedRawChunk


class NormalizedChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_chunk: AnnotatedRawChunk

    kind: Literal[
        "constraint",
        "behavior",
        "procedure",
        "definition",
        "mapping",
        "unknown",
    ] = "unknown"

    subject: str | None = None
    condition: str | None = None
    constraint: str | None = None
    failure_mode: str | None = None

    keywords: list[str] = Field(default_factory=list)

    embed_text: str

    @property
    def chunk_type(self) -> str:
        return self.source_chunk.chunk_type
