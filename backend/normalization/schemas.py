"""
Schema for normalized chunks. A NormalizedChunk extracts semantic
structure (constraints, behaviors, procedures) from a RawChunk so
downstream embedding captures intent rather than raw text.
Carries the full source RawChunk for provenance.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ingestion.schemas import AnnotatedRawChunk, deterministic_id


class NormalizedChunk(BaseModel):
    id: str = ""
    source_chunk: AnnotatedRawChunk

    @model_validator(mode="after")
    def _set_deterministic_id(self) -> NormalizedChunk:
        if not self.id:
            self.id = deterministic_id(f"norm::{self.source_chunk.id}")
        return self

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
