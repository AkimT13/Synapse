"""
LLM prompts for knowledge-to-natural-language normalization.
The system prompt instructs the model to produce a concise domain-aware
description with explicit software implications. The user prompt combines
the deterministic template with the raw source text for full context.
"""
from __future__ import annotations

from ingestion.schemas import RawDocumentChunk

SYSTEM_PROMPT = """\
You are a technical writer specializing in connecting scientific domain \
knowledge to software implementation. Your goal is to produce a concise \
natural-language description that captures what a domain knowledge chunk \
means and what it implies for software that operates in this domain.

Rules:
- Write a single paragraph of 2-5 sentences.
- Expand all abbreviations and symbols into plain English.
- Spell out all units in full (nm -> nanometers, RPM -> revolutions per minute).
- Explicitly state any constraints, limits, or thresholds in concrete terms.
- Frame the content in terms of software implications — what a software \
system working with this domain should or should not do.
- Use language like: "software processing X should...", \
"a function handling Y must not...", "any calculation involving Z should assume..."
- Start with the kind in title case followed by a colon \
(e.g. "Constraint:", "Definition:", "Procedure:").
- Do NOT use bullet points or markdown formatting.
- Write in declarative present tense.
- Do NOT reproduce the source text verbatim.
"""


def build_user_prompt(template: str, chunk: RawDocumentChunk) -> str:
    """Assemble the user-facing prompt from the template and raw source text.

    Parameters
    ----------
    template:
        The deterministic natural-language template produced by
        ``build_template()``.
    chunk:
        The original document chunk with full raw text.

    Returns
    -------
    str
        A prompt combining structured metadata with the raw source text.
    """
    parts: list[str] = [
        "Here is a structured summary of the document chunk:",
        "",
        template,
        "",
        "Here is the original source text:",
        "",
        chunk.raw_text,
        "",
        "Rewrite the summary into a clear, domain-aware description "
        "that explicitly states what this means for software operating "
        "in this domain.",
    ]
    return "\n".join(parts)