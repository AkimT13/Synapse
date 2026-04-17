"""
In-process registry for long-running background jobs (ingestion).

A job is a producer/consumer pair backed by an asyncio.Queue. The
producer (the ingestion worker) pushes progress events; the consumer
(the SSE endpoint) drains them and streams each one to the client.

State is in-memory only. The registry does not persist across server
restarts, which is fine: an ingestion job that dies with the server is
over anyway. Reset the workspace and start over.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobEvent:
    event: str
    data: dict[str, Any]


@dataclass
class Job:
    id: str
    events: asyncio.Queue[JobEvent] = field(default_factory=asyncio.Queue)
    completed: asyncio.Event = field(default_factory=asyncio.Event)

    async def push(self, event: str, data: dict[str, Any]) -> None:
        await self.events.put(JobEvent(event=event, data=data))

    def mark_complete(self) -> None:
        self.completed.set()


class JobRegistry:
    """Thread-unsafe by design — backed by a single-worker uvicorn."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def drop(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)


registry = JobRegistry()
