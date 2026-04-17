"""
End-to-end retrieval smoke test. Exercises one retrieval direction per
invocation, matching how the real system works:

  free  — plain-language question against both knowledge and code
  c2k   — query is a verbatim code chunk; find relevant knowledge
  k2c   — query is a verbatim knowledge chunk; find relevant code

Each mode runs retrieval AND the matching LLM-backed pipeline so the
full stack is exercised.

Requires:
- .env with OPENAI_API_KEY
- Actian VectorAI DB running on localhost:50051 with ingested content

Usage::

    py -m app.retrieval free "how is the spike threshold set?"
    py -m app.retrieval c2k "def detect_spikes(signal, sampling_rate, threshold_sigma=4.0): ..."
    py -m app.retrieval k2c "Spike detection threshold must be 3 to 5 standard deviations below baseline"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

import models
from retrieval.pipelines import (
    answer_question,
    check_code_against_constraints,
    explain_constraint_coverage,
)
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore


TOP_K = 5
PREVIEW_CHARS = 200


def _read_query(text: str | None, file: str | None) -> str:
    if file:
        return Path(file).read_text(encoding="utf-8")
    if text:
        return text
    sys.exit("No query provided. Pass a positional string or use -f PATH.")


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


def _print_query(query: str) -> None:
    preview = query.strip()
    if len(preview) > 400:
        preview = preview[:400] + "..."
    print(f"Query:\n{preview}\n")


def _run_free(query: str, store: VectorStore) -> None:
    _print_query(query)
    response = answer_question(query, store=store, k=TOP_K)
    _print_results("retrieved chunks", response["results"])
    print("\n--- LLM answer ---")
    print(response["answer"])


def _run_code_to_knowledge(query: str, store: VectorStore) -> None:
    _print_query(query)
    response = check_code_against_constraints(query, store=store, k=TOP_K)
    _print_results("relevant knowledge", response["constraints"])
    print("\n--- LLM constraint analysis ---")
    print(f"has_conflict: {response['has_conflict']}")
    print(response["explanation"])


def _run_knowledge_to_code(query: str, store: VectorStore) -> None:
    _print_query(query)
    response = explain_constraint_coverage(query, store=store, k=TOP_K)
    _print_results("relevant code", response["code_chunks"])
    print("\n--- LLM coverage explanation ---")
    print(f"is_implemented: {response['is_implemented']}")
    print(response["explanation"])


def run(mode: str, query: str) -> None:
    load_dotenv()
    models.init()

    with VectorStore() as store:
        match mode:
            case "free":
                _run_free(query, store)
            case "c2k":
                _run_code_to_knowledge(query, store)
            case "k2c":
                _run_knowledge_to_code(query, store)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test one retrieval direction end-to-end.",
    )
    parser.add_argument(
        "mode",
        choices=["free", "c2k", "k2c"],
        help="free = plain question; c2k = code → knowledge; k2c = knowledge → code",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Inline query text (use -f to read from a file instead)",
    )
    parser.add_argument(
        "-f",
        "--file",
        default=None,
        help="Path to a file containing the query (useful for long chunks)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(args.mode, _read_query(args.query, args.file))
