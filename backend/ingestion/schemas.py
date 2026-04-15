from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class RawChunk(BaseModel, ABC):
    """A source-agnostic abstract representation of a parsed chunk"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_file: str
    raw_text: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict) # TODO maybe define schema for this

    @property
    @abstractmethod
    def chunk_type(self) -> str:
        pass

class RawKnowledgeChunk(RawChunk):
    # TODO fields

    @property
    def chunk_type(self) -> str:
        return "knowledge"
    
class RawCodeChunk(RawChunk):
    # TODO fields

    @property
    def chunk_type(self) -> str:
        return "code"