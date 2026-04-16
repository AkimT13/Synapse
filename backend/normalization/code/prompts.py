"""LLM prompts for code-to-natural-language normalization.

The system prompt instructs the model to produce a concise domain-aware
description. The user prompt combines the deterministic template with
the raw source for full context.
"""
from __future__ import annotations

from ingestion.schemas import RawCodeChunk

SYSTEM_PROMPT = """\
You are a technical writer specializing in describing source code using \
domain-specific terminology. Your goal is to produce a concise, natural-language \
paragraph that captures what a function does, why it exists, and how it relates \
to the broader domain.

Rules:
- Write a single paragraph of 2-5 sentences.
- Use domain terminology from the docstring, type annotations, and naming conventions.
- Describe intent and behavior, not low-level implementation details.
- Mention important constraints, preconditions, or failure modes.
- Do NOT reproduce the source code or signature verbatim.
- Do NOT use bullet points or markdown formatting.
- Write in third person present tense ("validates", "computes", "transforms").
"""


def build_user_prompt(template: str, chunk: RawCodeChunk) -> str:
    """Assemble the user-facing prompt from the template and raw source.

    Parameters
    ----------
    template:
        The deterministic natural-language template produced by
        ``build_template()``.
    chunk:
        The original code chunk with full source text.

    Returns
    -------
    str
        A prompt combining structured metadata with the raw source.
    """
    parts: list[str] = [
        "Here is a structured summary of the function:",
        "",
        template,
        "",
        "Here is the full source code:",
        "",
        "```",
        chunk.raw_text,
        "```",
        "",
        "Rewrite the summary into a clear, domain-aware natural-language description.",
    ]
    return "\n".join(parts)
