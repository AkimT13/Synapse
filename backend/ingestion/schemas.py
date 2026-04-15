"""
Schema for raw chunks produced by the ingestion stage. A RawChunk is
the first structured representation of a source document or code file
before any normalization or embedding takes place.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field, Tag


class RawChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chunk_type: Literal["knowledge", "code"]
    source_file: str
    raw_text: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawKnowledgeChunk(RawChunk):
    chunk_type: Literal["knowledge"] = "knowledge"


class RawCodeChunk(RawChunk):
    chunk_type: Literal["code"] = "code"


AnnotatedRawChunk = Annotated[
    Union[
        Annotated[RawKnowledgeChunk, Tag("knowledge")],
        Annotated[RawCodeChunk, Tag("code")],
    ],
    Discriminator("chunk_type"),
]
