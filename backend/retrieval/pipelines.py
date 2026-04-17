"""
Higher-level retrieval pipelines. Combine vector retrieval with LLM
explanation generation to produce human-readable output suitable for
both the developer CLI and the scientist GUI.
"""
from __future__ import annotations

import models
from retrieval.retrieval import code_to_knowledge, knowledge_to_code, free_text
from retrieval.schemas import RetrievalResult
from storage.vector_store import VectorStore


_CONFLICT_SYSTEM_PROMPT = """\
You are an assistant that explains relationships between source code and \
domain knowledge constraints. Given a code description and a set of \
relevant domain knowledge chunks, identify any conflicts, gaps, or \
relevant constraints the developer should be aware of.

Rules:
- Be specific — reference actual values, units, and thresholds from the
  domain knowledge.
- If there is a conflict, explain exactly what the code does wrong and
  what it should do instead.
- If there is no conflict, say so clearly and explain why the code is
  consistent with the constraints.
- Write in plain English suitable for a software developer.
- Do NOT use bullet points. Write in prose.
- Keep the response to 3-5 sentences.
"""

_SCIENTIST_SYSTEM_PROMPT = """\
You are an assistant that explains software behavior to domain experts \
who are not software developers. Given a domain constraint and a set of \
relevant code chunks, explain in plain language whether the software \
correctly implements the constraint.

Rules:
- Avoid programming terminology.
- Describe what the software does in terms of the domain — physical
  quantities, units, biological processes, chemical properties.
- If the software appears to violate the constraint, explain the
  practical consequence.
- Keep the response to 3-5 sentences.
"""


def check_code_against_constraints(
    code_embed_text: str,
    store: VectorStore,
    domain: str | None = None,
    k: int = 5,
) -> dict:
    """Retrieve domain constraints relevant to a code chunk and explain conflicts.

    Returns a dict with retrieved constraints and an LLM-generated explanation.
    Used by the constraint monitoring agent and the developer CLI.
    """
    results = code_to_knowledge(
        code_embed_text=code_embed_text,
        store=store,
        domain=domain,
        constraints_only=True,
        k=k,
    )

    # Cascade: if no chunks were labelled as constraints, fall back to the
    # full knowledge space so the developer still gets relevant context
    # (definitions, procedures, background) to reason against.
    used_fallback = False
    if not results:
        results = code_to_knowledge(
            code_embed_text=code_embed_text,
            store=store,
            domain=domain,
            constraints_only=False,
            k=k,
        )
        used_fallback = True

    if not results:
        return {
            "constraints": [],
            "explanation": "No relevant domain knowledge found.",
            "has_conflict": False,
            "used_fallback": used_fallback,
        }

    context = _format_knowledge_context(results)
    explanation = models.complete(
        system_prompt=_CONFLICT_SYSTEM_PROMPT,
        user_prompt=(
            f"Code description:\n{code_embed_text}\n\n"
            f"Relevant domain constraints:\n{context}"
        ),
    )

    return {
        "constraints": results,
        "explanation": explanation,
        "has_conflict": _detect_conflict_signal(explanation),
        "used_fallback": used_fallback,
    }


def explain_constraint_coverage(
    knowledge_embed_text: str,
    store: VectorStore,
    language: str | None = None,
    k: int = 5,
) -> dict:
    """Find code relevant to a domain constraint and explain coverage.

    Returns a dict with relevant code chunks and an LLM explanation
    written for a domain expert, not a developer.
    Used by the scientist-facing GUI.
    """
    results = knowledge_to_code(
        knowledge_embed_text=knowledge_embed_text,
        store=store,
        language=language,
        k=k,
    )

    if not results:
        return {
            "code_chunks": [],
            "explanation": "No relevant code found for this constraint.",
            "is_implemented": False,
        }

    context = _format_code_context(results)
    explanation = models.complete(
        system_prompt=_SCIENTIST_SYSTEM_PROMPT,
        user_prompt=(
            f"Domain constraint:\n{knowledge_embed_text}\n\n"
            f"Relevant code:\n{context}"
        ),
    )

    return {
        "code_chunks": results,
        "explanation": explanation,
        "is_implemented": _detect_implementation_signal(explanation),
    }


def answer_question(
    question: str,
    store: VectorStore,
    k: int = 10,
) -> dict:
    """Answer a plain language question using both knowledge and code chunks."""
    results = free_text(question=question, store=store, k=k)

    if not results:
        return {
            "results": [],
            "answer": "No relevant information found.",
        }

    context = _format_mixed_context(results)
    answer = models.complete(
        system_prompt=(
            "You are an assistant that answers questions about a software "
            "codebase and its domain knowledge. Use the provided context "
            "from both source code and domain documents to answer the "
            "question clearly and concisely."
        ),
        user_prompt=f"Question: {question}\n\nContext:\n{context}",
    )

    return {
        "results": results,
        "answer": answer,
    }


def _format_knowledge_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] {r.kind.upper()} from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _format_code_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] CODE from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _format_mixed_context(results: list[RetrievalResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        label = "DOMAIN KNOWLEDGE" if r.chunk_type == "knowledge" else "CODE"
        lines.append(
            f"[{i}] {label} from {r.source_file} "
            f"(score: {r.score:.3f}):\n{r.embed_text}"
        )
    return "\n\n".join(lines)


def _detect_conflict_signal(explanation: str) -> bool:
    conflict_signals = [
        "violates", "conflict", "incorrect", "wrong", "should not",
        "must not", "exceeds", "below the", "above the", "invalid",
    ]
    lower = explanation.lower()
    return any(signal in lower for signal in conflict_signals)


def _detect_implementation_signal(explanation: str) -> bool:
    implementation_signals = [
        "correctly", "implements", "consistent", "respects",
        "enforces", "handles", "validates",
    ]
    lower = explanation.lower()
    return any(signal in lower for signal in implementation_signals)