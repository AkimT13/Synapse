"""
Schema for raw chunks produced by the ingestion stage. A RawChunk is
the first structured representation of a source document or code file
before any normalization or embedding takes place.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator

"""Namespace for deterministic UUID5 generation across all chunk types."""
SYNAPSE_UUID_NAMESPACE = uuid.UUID("a3f2b8c1-7d4e-4f6a-9b2c-1e8d5f0a3c7b")


def deterministic_id(key: str) -> str:
    """Produce a deterministic UUID from a content key."""
    return str(uuid.uuid5(SYNAPSE_UUID_NAMESPACE, key))


class RawChunk(BaseModel):
    id: str = ""
    chunk_type: Literal["knowledge", "code"]
    source_file: str
    raw_text: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _set_deterministic_id(self) -> RawChunk:
        if not self.id:
            self.id = deterministic_id(f"{self.chunk_type}::{self.source_file}::{self.raw_text}")
        return self


class RawKnowledgeChunk(RawChunk):
    chunk_type: Literal["knowledge"] = "knowledge"


# -- Code-specific sub-models --


class ParameterInfo(BaseModel):
    name: str
    type_annotation: str | None = None
    default_value: str | None = None


class LineRange(BaseModel):
    start: int
    end: int


class RawCodeChunk(RawChunk):
    chunk_type: Literal["code"] = "code"

    name: str = ""
    signature: str = ""
    language: str = "python"
    kind: Literal[
        "function",
        "method",
        "classmethod",
        "staticmethod",
        "async_function",
        "async_method",
        "property",
    ] = "function"

    parameters: list[ParameterInfo] = Field(default_factory=list)
    return_type: str | None = None
    docstring: str | None = None
    decorators: list[str] = Field(default_factory=list)
    line_range: LineRange | None = None

    parent_class: str | None = None
    module_path: str = ""

    calls: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    raises: list[str] = Field(default_factory=list)


AnnotatedRawChunk = Annotated[
    Union[
        Annotated[RawKnowledgeChunk, Tag("knowledge")],
        Annotated[RawCodeChunk, Tag("code")],
    ],
    Discriminator("chunk_type"),
]
