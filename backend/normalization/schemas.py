from typing import Literal
from pydantic import BaseModel, Field

# TODO - refine as we go
class NormalizedChunk(BaseModel):
    source_chunk_id: str
    chunk_type: Literal["knowledge", "code"]

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