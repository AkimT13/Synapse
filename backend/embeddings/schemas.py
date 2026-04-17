"""
Schema for the output of the embedding stage. An EmbeddedChunk is the
unit of storage in the vector DB — it carries the vector and the full
lineage back to the original source. Text and chunk_type are derived
from the source NormalizedChunk, not duplicated.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ingestion.schemas import deterministic_id
from normalization.schemas import NormalizedChunk


class EmbeddedChunk(BaseModel):
    id: str = ""
    source_chunk: NormalizedChunk
    vector: list[float]
    vector_model: str
    vector_dimension: int

    @model_validator(mode="after")
    def _set_deterministic_id(self) -> EmbeddedChunk:
        if not self.id:
            self.id = deterministic_id(f"emb::{self.source_chunk.id}")
        return self

    @property
    def embed_text(self) -> str:
        return self.source_chunk.embed_text

    @property
    def chunk_type(self) -> str:
        return self.source_chunk.chunk_type

    @property
    def metadata(self) -> dict:
        return self.source_chunk.source_chunk.metadata

    def to_storage_record(self) -> dict:
        source = self.source_chunk.source_chunk
        norm = self.source_chunk

        record = {
            "id": self.id,
            "chunk_type": self.chunk_type,
            "source_file": source.source_file,
            "chunk_index": source.chunk_index,
            "vector": self.vector,
            "vector_model": self.vector_model,
            "vector_dimension": self.vector_dimension,
            "embed_text": self.embed_text,
            "raw_text": source.raw_text,
            "kind": norm.kind,
            "subject": norm.subject,
            "keywords": norm.keywords,
            "metadata": source.metadata,
            "_raw": self.model_dump(mode="json")
        }

        if self.chunk_type == "knowledge":
            record.update({
                "domain": source.metadata.get("domain", ""),
                "knowledge_type": source.metadata.get("knowledge_type", "unknown"),
                "contains_constraint": source.metadata.get("contains_constraint", False),
                "constraint_name": source.metadata.get("constraint_name"),
                "source_type": source.metadata.get("source_type", "unknown"),
                "confidence": source.metadata.get("confidence", 0.0),
                "section_heading": getattr(source, "section_heading", None),
                "page_number": getattr(source, "page_number", None),
            })

        if self.chunk_type == "code":
            record.update({
                "language": getattr(source, "language", "unknown"),
                "function_name": getattr(source, "name", None),
                "class_name": getattr(source, "parent_class", None),
                "module_path": getattr(source, "module_path", ""),
            })

        return record