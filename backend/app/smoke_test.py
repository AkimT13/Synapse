"""
End-to-end smoke test. Runs the full pipeline against the sample data:

  1. Ingest sample code      (../sample/code → code chunks)
  2. Ingest sample knowledge (../sample/knowledge → knowledge chunks)
  3. Run a free-text query
  4. Run a code-to-knowledge query
  5. Run a knowledge-to-code query

Prints enough output at each step that a human can eyeball whether
retrieval is finding the right things.

Requires:
- .env with OPENAI_API_KEY
- Actian VectorAI DB running on localhost:50051 (docker-compose up -d)

Usage::

    python -m app.smoke_test
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

import models
from jobs.ingest_code import CodeIngestionJob
from jobs.ingest_knowledge import KnowledgeIngestionJob
from retrieval.pipelines import (
    answer_question,
    check_code_against_constraints,
    explain_constraint_coverage,
)
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore


HERE = Path(__file__).resolve().parent
SAMPLE_ROOT = HERE.parent.parent / "sample"
SAMPLE_CODE = SAMPLE_ROOT / "code"
SAMPLE_KNOWLEDGE = SAMPLE_ROOT / "knowledge"

CODE_QUERY_FILE = SAMPLE_CODE / "spike_detection.py"
KNOWLEDGE_QUERY_FILE = SAMPLE_KNOWLEDGE / "spike_detection_protocol.md"
FREE_QUERY = "how is the spike detection threshold set?"

TOP_K = 5
PREVIEW_CHARS = 200


def _section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def _print_results(label: str, results: list[RetrievalResult]) -> None:
    print(f"\n--- {label} ({len(results)} results) ---")
    if not results:
        print("  (no results)")
        return
    for index, result in enumerate(results, 1):
        print(
            f"[{index}] score={result.score:.3f}  "
            f"{result.chunk_type}  {result.source_file}"
        )
        preview = result.embed_text.strip().replace("\n", " ")
        if len(preview) > PREVIEW_CHARS:
            preview = preview[:PREVIEW_CHARS] + "..."
        print(f"    {preview}")


def _ingest_code(store: VectorStore) -> None:
    _section(f"Ingesting code from {SAMPLE_CODE}")
    job = CodeIngestionJob(vector_store=store, on_progress=print, should_use_llm=True)
    result = job.run(str(SAMPLE_CODE))
    print(f"\nStored {result.chunks_stored}/{result.chunks_parsed} chunks")


def _ingest_knowledge(store: VectorStore) -> None:
    _section(f"Ingesting knowledge from {SAMPLE_KNOWLEDGE}")
    job = KnowledgeIngestionJob(vector_store=store, on_progress=print, should_use_llm=True)
    result = job.run(str(SAMPLE_KNOWLEDGE))
    print(f"\nStored {result.chunks_stored}/{result.chunks_parsed} chunks")


def _run_free(store: VectorStore) -> None:
    _section(f"Free-text query: {FREE_QUERY!r}")
    response = answer_question(FREE_QUERY, store=store, k=TOP_K)
    _print_results("retrieved chunks", response["results"])
    print("\n--- LLM answer ---")
    print(response["answer"])


def _run_code_to_knowledge(store: VectorStore) -> None:
    _section(f"Code → Knowledge: query = contents of {CODE_QUERY_FILE.name}")
    query = CODE_QUERY_FILE.read_text(encoding="utf-8")
    response = check_code_against_constraints(query, store=store, k=TOP_K)
    _print_results("relevant knowledge", response["constraints"])
    print(f"\n--- LLM analysis (has_conflict={response['has_conflict']}) ---")
    print(response["explanation"])


def _run_knowledge_to_code(store: VectorStore) -> None:
    _section(f"Knowledge → Code: query = contents of {KNOWLEDGE_QUERY_FILE.name}")
    query = KNOWLEDGE_QUERY_FILE.read_text(encoding="utf-8")
    response = explain_constraint_coverage(query, store=store, k=TOP_K)
    _print_results("relevant code", response["code_chunks"])
    print(f"\n--- LLM coverage (is_implemented={response['is_implemented']}) ---")
    print(response["explanation"])


def run() -> None:
    load_dotenv()
    models.init()

    with VectorStore() as store:
        _ingest_code(store)
        _ingest_knowledge(store)
        _run_free(store)
        _run_code_to_knowledge(store)
        _run_knowledge_to_code(store)

    _section("Smoke test complete")


if __name__ == "__main__":
    run()
