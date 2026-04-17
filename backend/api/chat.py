"""
HTTP surface for Synapse chat.

This router exposes conversation and message endpoints for the chat
experience. Conversations and their messages are persisted in the
SQLite-backed ``ChatStore``; each user message triggers a retrieval
call against the shared ``VectorStore`` and an LLM-generated answer
via ``retrieval.pipelines.answer_question``. Responses include the
citation sources used to produce the answer so the UI can render
inline references.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from api.chat_store import ChatStore
from api.dependencies import get_chat_store, get_vector_store
from api.schemas import (
    ChatMessage,
    ConversationDetail,
    ConversationHeader,
    NewConversationRequest,
    PostMessageRequest,
    PostMessageResponse,
    SourceRef,
    make_source_ref,
    truncate_for_preview,
)
from retrieval.pipelines import answer_question
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore

router = APIRouter()


_DEFAULT_TITLE = "New conversation"
_TITLE_MAX_CHARS = 60


def _derive_title(result: RetrievalResult) -> str:
    raw = result.chunk.source_chunk.source_chunk
    if result.chunk_type == "code":
        return getattr(raw, "name", None) or Path(result.source_file).name
    return getattr(raw, "section_heading", None) or Path(result.source_file).name


def _derive_conversation_title(content: str) -> str:
    cleaned = content.strip().replace("\n", " ")
    if len(cleaned) <= _TITLE_MAX_CHARS:
        return cleaned or _DEFAULT_TITLE
    return cleaned[:_TITLE_MAX_CHARS].rstrip() + "..."


def _results_to_sources(results: list[RetrievalResult]) -> list[SourceRef]:
    return [
        make_source_ref(
            index=i,
            chunk_type=result.chunk_type,
            source_file=result.source_file,
            title=_derive_title(result),
            excerpt=truncate_for_preview(result.embed_text),
            score=result.score,
            kind=result.kind,
        )
        for i, result in enumerate(results, start=1)
    ]


@router.get("/conversations", response_model=list[ConversationHeader])
async def list_conversations(
    chat_store: ChatStore = Depends(get_chat_store),
) -> list[ConversationHeader]:
    rows = await chat_store.list_conversations()
    return [ConversationHeader.model_validate(row) for row in rows]


@router.post("/conversations", response_model=ConversationHeader)
async def create_conversation(
    payload: NewConversationRequest,
    chat_store: ChatStore = Depends(get_chat_store),
) -> ConversationHeader:
    title = (payload.title or "").strip() or _DEFAULT_TITLE
    row = await chat_store.create_conversation(title)
    return ConversationHeader.model_validate(row)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    chat_store: ChatStore = Depends(get_chat_store),
) -> ConversationDetail:
    conversation = await chat_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await chat_store.list_messages(conversation_id)
    return ConversationDetail(
        id=conversation["id"],
        title=conversation["title"],
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        messages=[ChatMessage.model_validate(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    chat_store: ChatStore = Depends(get_chat_store),
) -> dict:
    await chat_store.delete_conversation(conversation_id)
    return {"ok": True}


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=PostMessageResponse,
)
async def post_message(
    conversation_id: str,
    payload: PostMessageRequest,
    chat_store: ChatStore = Depends(get_chat_store),
    vector_store: VectorStore = Depends(get_vector_store),
) -> PostMessageResponse:
    conversation = await chat_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    prior_messages = await chat_store.list_messages(conversation_id)
    is_first_message = len(prior_messages) == 0

    user_row = await chat_store.add_message(conversation_id, "user", payload.content)

    if is_first_message:
        await chat_store.update_title(
            conversation_id,
            _derive_conversation_title(payload.content),
        )

    # TODO: honour payload.scope ("code" / "knowledge") with a scope-aware
    # retrieval path. For now we always call answer_question so we always
    # return an LLM-generated answer; the scope chip is decorative.
    result = answer_question(
        question=payload.content,
        store=vector_store,
        k=payload.k,
    )
    answer_text: str = result["answer"]
    source_refs = _results_to_sources(result["results"])

    assistant_row = await chat_store.add_message(
        conversation_id,
        "assistant",
        answer_text,
        sources=[ref.model_dump() for ref in source_refs],
    )

    return PostMessageResponse(
        user_message=ChatMessage.model_validate(user_row),
        assistant_message=ChatMessage.model_validate(assistant_row),
    )
