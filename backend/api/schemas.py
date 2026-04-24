"""
Pydantic request/response models for the HTTP surface. These are
intentionally distinct from domain schemas in embeddings/, ingestion/,
normalization/ — the API shape is a public contract; the domain shape
is internal. Keep them decoupled.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# -- retrieval --------------------------------------------------------------


class SourceRef(BaseModel):
    index: int
    chunk_type: Literal["code", "knowledge"]
    source_file: str
    title: str
    excerpt: str
    score: float
    kind: str | None = None


class RetrievalResponse(BaseModel):
    results: list[SourceRef]
    explanation: str | None = None
    answer: str | None = None
    has_conflict: bool | None = None
    is_implemented: bool | None = None
    used_fallback: bool | None = None


class CodeToKnowledgeRequest(BaseModel):
    text: str
    k: int = 5
    domain: str | None = None
    constraints_only: bool = True


class KnowledgeToCodeRequest(BaseModel):
    text: str
    k: int = 5
    language: str | None = None


class FreeTextRequest(BaseModel):
    question: str
    k: int = 10


# -- review -----------------------------------------------------------------


class ReviewRequest(BaseModel):
    path: str
    k: int = 5


class ReviewLineRange(BaseModel):
    start: int
    end: int


class ReviewFinding(BaseModel):
    issue_type: str
    expected: str
    observed: str
    comparison: str
    severity: str
    confidence: str
    summary: str


class ReviewSource(BaseModel):
    source_file: str
    chunk_type: Literal["code", "knowledge"]
    kind: str | None = None
    score: float
    embed_text: str


class ReviewCheck(BaseModel):
    label: str
    source_file: str
    line_range: ReviewLineRange | None = None
    status: Literal["aligned", "warning", "conflict", "unknown"]
    summary: str
    violations: list[str] = Field(default_factory=list)
    confidence: str
    used_fallback: bool = False
    query_text: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    supporting_sources: list[ReviewSource] = Field(default_factory=list)


class ReviewContextEntry(BaseModel):
    label: str
    query_text: str
    has_conflict: bool
    used_fallback: bool = False
    sources: list[ReviewSource] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    workspace: str
    target: str
    drift_status: Literal["aligned", "warning", "conflict", "unknown"]
    drift: list[ReviewCheck] = Field(default_factory=list)
    context: list[ReviewContextEntry] = Field(default_factory=list)


# -- workspace --------------------------------------------------------------


class WorkspaceStats(BaseModel):
    code_files: int
    knowledge_files: int
    total_code_chunks: int | None = None
    total_knowledge_chunks: int | None = None


# -- ingestion --------------------------------------------------------------


class IngestionAck(BaseModel):
    job_id: str
    files_saved: int


# -- corpora ----------------------------------------------------------------


class TreeNode(BaseModel):
    name: str
    path: str
    type: Literal["file", "dir"]
    children: list["TreeNode"] = Field(default_factory=list)


TreeNode.model_rebuild()


# -- chat -------------------------------------------------------------------


class ConversationHeader(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceRef] = Field(default_factory=list)
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage]


class NewConversationRequest(BaseModel):
    title: str | None = None


class PostMessageRequest(BaseModel):
    content: str
    scope: Literal["all", "code", "knowledge"] = "all"
    k: int = 10


class PostMessageResponse(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage


# -- result payload conversion ---------------------------------------------


def make_source_ref(
    index: int,
    *,
    chunk_type: str,
    source_file: str,
    title: str,
    excerpt: str,
    score: float,
    kind: str | None = None,
) -> SourceRef:
    """Small convenience shared by retrieval handlers."""
    return SourceRef(
        index=index,
        chunk_type=chunk_type,  # type: ignore[arg-type]
        source_file=source_file,
        title=title,
        excerpt=excerpt,
        score=score,
        kind=kind,
    )


def truncate_for_preview(text: str, max_chars: int = 200) -> str:
    cleaned = text.strip().replace("\n", " ")
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + "..."
