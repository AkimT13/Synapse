"""
Run the full knowledge ingestion pipeline: parse (docling) → chunk →
normalize (with LLM) → embed → store in Actian VectorAI DB.

Requires:
- .env with OPENAI_API_KEY
- Actian VectorAI DB running on localhost:50051 (docker-compose up -d)

Usage::

    python -m app.knowledge_ingestion /path/to/docs
    py -m app.knowledge_ingestion ../sample/knowledge
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

import models
from jobs.ingest_knowledge import KnowledgeIngestionJob
from storage.vector_store import VectorStore


def run(directory_path: str) -> None:
    load_dotenv()
    models.init()

    with VectorStore() as store:
        job = KnowledgeIngestionJob(vector_store=store, on_progress=print, should_use_llm=True)
        result = job.run(directory_path)

    print(f"\nFiles processed:    {result.files_processed}")
    print(f"Chunks parsed:      {result.chunks_parsed}")
    print(f"Chunks normalized:  {result.chunks_normalized}")
    print(f"Chunks embedded:    {result.chunks_embedded}")
    print(f"Chunks stored:      {result.chunks_stored}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    run(path)
