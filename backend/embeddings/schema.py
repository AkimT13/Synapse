from typing import Any, Literal
from pydantic import BaseModel, Field

# TODO refine as we go
class EmbeddedChunk(BaseModel):
    source_chunk_id: str
    chunk_type: Literal["knowledge", "code"]

    embed_text: str
    vector: list[float]
    vector_model: str
    vector_dimension: int

    metadata: dict[str, Any] = Field(default_factory=dict)