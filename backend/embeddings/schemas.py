"""
Schema for the output of the embedding stage. An EmbeddedChunk is the
unit of storage in the vector DB — it carries the vector and the full
lineage back to the original source. Text and chunk_type are derived
from the source NormalizedChunk, not duplicated.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from normalization.schemas import NormalizedChunk


class EmbeddedChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_chunk: NormalizedChunk
    vector: list[float]
    vector_model: str
    vector_dimension: int

    @property
    def embed_text(self) -> str:
        return self.source_chunk.embed_text

    @property
    def chunk_type(self) -> str:
        return self.source_chunk.chunk_type

