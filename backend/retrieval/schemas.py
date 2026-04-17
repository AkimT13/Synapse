from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from embeddings.schemas import EmbeddedChunk


@dataclass
class RetrievalQuery:
    """
    Represents a retrieval request before it is executed.
    Constructed by callers and passed to retrieval functions.
    """
    text: str                               # text to embed and search with
    direction: Literal[
        "code_to_knowledge",
        "knowledge_to_code",
        "free_text",
    ]
    filters: dict | None = None             # additional metadata filters
    k: int = 10                             # number of results to return
    score_threshold: float | None = None    # minimum similarity score


@dataclass
class RetrievalResult:
    """
    A single result returned by the retrieval layer.
    Wraps the matched EmbeddedChunk with retrieval metadata.
    """
    chunk: EmbeddedChunk
    score: float
    query_text: str                         # the text that produced this result
    direction: str                          # which retrieval direction was used

    @property
    def source_file(self) -> str:
        return self.chunk.source_chunk.source_chunk.source_file

    @property
    def chunk_type(self) -> str:
        return self.chunk.chunk_type

    @property
    def kind(self) -> str:
        return self.chunk.source_chunk.kind

    @property
    def embed_text(self) -> str:
        return self.chunk.embed_text