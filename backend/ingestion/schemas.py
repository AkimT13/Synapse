"""
Schema for raw chunks produced by the ingestion stage. A RawChunk is
the first structured representation of a source document or code file
before any normalization or embedding takes place.
"""
from __future__ import annotations

import uuid
from abc import ABC
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator, ConfigDict


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------

SYNAPSE_UUID_NAMESPACE = uuid.UUID("a3f2b8c1-7d4e-4f6a-9b2c-1e8d5f0a3c7b")


def deterministic_id(key: str) -> str:
    """Produce a deterministic UUID from a content key."""
    return str(uuid.uuid5(SYNAPSE_UUID_NAMESPACE, key))


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class RawChunk(BaseModel, ABC):
    """
    Abstract base for all raw chunk types.
    Not instantiated directly — use RawDocumentChunk or RawCodeChunk.
    """
    model_config = ConfigDict(use_enum_values=True)

    id: str = ""
    chunk_type: Literal["knowledge", "code"]
    source_file: str
    raw_text: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _set_deterministic_id(self) -> RawChunk:
        if not self.id:
            self.id = deterministic_id(
                f"{self.chunk_type}::{self.source_file}::{self.chunk_index}::{self.raw_text}"
            )
        return self

# ---------------------------------------------------------------------------
# Knowledge chunks
# ---------------------------------------------------------------------------

class RawKnowledgeChunk(RawChunk, ABC):
    """
    Abstract base for all knowledge chunk types.
    Leaves room for other knowledge sources beyond documents —
    e.g. RawExpertAnnotationChunk in the future.
    """
    chunk_type: Literal["knowledge"] = "knowledge"


class RawDocumentChunk(RawKnowledgeChunk):
    """
    Knowledge chunk produced by document parsing (PDF, DOCX, MD, etc.).
    embed_text is intentionally absent — it belongs to the normalization
    schema, not the raw ingestion stage.
    """
    content_type: Literal["text", "table", "figure"] = "text"
    section_heading: str | None = None
    page_number: int | None = None

    @classmethod
    def from_raw_text(
        cls,
        raw_text: str,
        source_file: str,
        chunk_index: int = 0,
        content_type: Literal["text", "table", "figure"] = "text",
        section_heading: str | None = None,
        page_number: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RawDocumentChunk:
        return cls(
            source_file=source_file,
            raw_text=raw_text,
            chunk_index=chunk_index,
            content_type=content_type,
            section_heading=section_heading,
            page_number=page_number,
            metadata=metadata or {},
        )


# ---------------------------------------------------------------------------
# Code chunks
# ---------------------------------------------------------------------------

class ParameterInfo(BaseModel):
    name: str
    type_annotation: str | None = None
    default_value: str | None = None


class LineRange(BaseModel):
    start: int
    end: int


class RawCodeChunk(RawChunk):
    """
    Code chunk produced by AST parsing of a source file.
    Each chunk represents a single meaningful unit: a function,
    method, or class body.
    calls, imports, and raises are populated by the enrichment
    step after initial AST parsing.
    """
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


# ---------------------------------------------------------------------------
# Discriminated union — use this for deserialization from Actian or JSON
# ---------------------------------------------------------------------------

AnnotatedRawChunk = Annotated[
    Union[
        Annotated[RawDocumentChunk, Tag("knowledge")],
        Annotated[RawCodeChunk, Tag("code")],
    ],
    Discriminator("chunk_type"),
]