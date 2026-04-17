"""
SQLite-backed persistence for chat conversations and messages.
Thin wrapper around aiosqlite; no ORM. The schema is flat — two
tables, no foreign-key cascades — because the data model really is
that simple and we stay away from migrations.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    sources_json    TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class ChatStore:
    """Minimal async wrapper around the chat SQLite file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("ChatStore not initialised")
        return self._db

    # -- conversations -----------------------------------------------------

    async def list_conversations(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def create_conversation(self, title: str) -> dict[str, Any]:
        now = _now()
        conversation_id = _new_id()
        await self.db.execute(
            "INSERT INTO conversations(id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, title, now, now),
        )
        await self.db.commit()
        return {"id": conversation_id, "title": title, "created_at": now, "updated_at": now}

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_conversation(self, conversation_id: str) -> None:
        await self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        await self.db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        await self.db.commit()

    async def touch_conversation(self, conversation_id: str) -> None:
        await self.db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )
        await self.db.commit()

    async def update_title(self, conversation_id: str, title: str) -> None:
        await self.db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), conversation_id),
        )
        await self.db.commit()

    async def clear_all(self) -> None:
        await self.db.execute("DELETE FROM messages")
        await self.db.execute("DELETE FROM conversations")
        await self.db.commit()

    # -- messages ----------------------------------------------------------

    async def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT id, conversation_id, role, content, sources_json, created_at "
            "FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [self._row_to_message(row) for row in rows]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        message_id = _new_id()
        sources_json = json.dumps(sources) if sources else None
        await self.db.execute(
            "INSERT INTO messages(id, conversation_id, role, content, sources_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, conversation_id, role, content, sources_json, now),
        )
        await self.touch_conversation(conversation_id)
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": now,
        }

    @staticmethod
    def _row_to_message(row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
            "created_at": row["created_at"],
        }
