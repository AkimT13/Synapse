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
        """Build the Actian payload.

        Only fields used as filter predicates by the retrieval layer are
        promoted to the top level. Everything else lives inside ``_raw``,
        which round-trips the full EmbeddedChunk on read. The vector
        itself is excluded from ``_raw`` because Actian already indexes
        it separately — duplicating it here would push every chunk over
        the DB's per-point size limit.
        """
        source = self.source_chunk.source_chunk
        record: dict = {
            "chunk_type": self.chunk_type,
            "_raw": self.model_dump(mode="json", exclude={"vector"}),
        }

        if self.chunk_type == "knowledge":
            record.update({
                "domain": source.metadata.get("domain", ""),
                "knowledge_type": source.metadata.get("knowledge_type", "unknown"),
                "contains_constraint": source.metadata.get("contains_constraint", False),
                "confidence": source.metadata.get("confidence", 0.0),
                "source_type": source.metadata.get("source_type", "unknown"),
            })
        elif self.chunk_type == "code":
            record.update({
                "language": getattr(source, "language", "unknown"),
                "module_path": getattr(source, "module_path", ""),
            })

        return record