"""
Knowledge normalization pipeline. Takes RawDocumentChunks and produces
NormalizedChunks with natural-language embed_text suitable for embedding
alongside code chunks in a shared vector space.

Each chunk flows through: template generation -> optional LLM rewrite
-> kind inference -> keyword extraction. The LLM step is skipped for
short or content-poor chunks to save cost without losing retrieval quality.
"""
from __future__ import annotations

import re

import models
from ingestion.schemas import RawDocumentChunk
from normalization.knowledge.prompts import SYSTEM_PROMPT, build_user_prompt
from normalization.knowledge.template import build_template, has_domain_signals
from normalization.schemas import NormalizedChunk


# ---------------------------------------------------------------------------
# Kind-inference patterns
# ---------------------------------------------------------------------------

_KIND_PATTERNS: list[tuple[str, list[str]]] = [
    ("definition", [
        "defined as", "refers to", "is a", "means", "known as",
    ]),
    ("constraint", [
        "must", "shall", "required", "limit", "maximum", "minimum",
        "threshold", "tolerance", "not exceed", "must not",
    ]),
    ("behavior", [
        "process", "compute", "calculate", "transform", "filter",
        "operates", "functions", "performs", "produces", "outputs",
    ]),
    ("procedure", [
        "step", "procedure", "process", "follow", "sequence",
        "first", "then", "finally", "instruction",
    ]),
    ("mapping", [
        "corresponds to", "maps to", "equivalent", "converted",
        "translates",
    ]),
]


# ---------------------------------------------------------------------------
# KnowledgeNormalizer
# ---------------------------------------------------------------------------


class KnowledgeNormalizer:
    """Normalizes RawDocumentChunks into NormalizedChunks.

    Parameters
    ----------
    should_use_llm:
        When True (default), chunks with domain signals are rewritten
        by the configured LLM for richer natural-language descriptions.
        When False, every chunk gets the deterministic template only.
    """

    def __init__(self, should_use_llm: bool = True) -> None:
        self._should_use_llm = should_use_llm

    def normalize(self, chunk: RawDocumentChunk) -> NormalizedChunk:
        template = build_template(chunk)
        embed_text = self._maybe_rewrite(template, chunk)
        kind = _infer_kind(chunk)
        keywords = _extract_keywords(chunk)

        return NormalizedChunk(
            source_chunk=chunk,
            kind=kind,
            subject=_extract_subject(chunk),
            embed_text=embed_text,
            keywords=keywords,
        )

    def normalize_batch(
        self, chunks: list[RawDocumentChunk]
    ) -> list[NormalizedChunk]:
        """Individual errors fall back to template-only — never fails the full batch."""
        results: list[NormalizedChunk] = []
        for chunk in chunks:
            try:
                results.append(self.normalize(chunk))
            except Exception:
                template = build_template(chunk)
                results.append(NormalizedChunk(
                    source_chunk=chunk,
                    kind="unknown",
                    subject=_extract_subject(chunk),
                    embed_text=template,
                    keywords=_extract_keywords(chunk),
                ))
        return results

    def _maybe_rewrite(self, template: str, chunk: RawDocumentChunk) -> str:
        
        if not self._should_use_llm or not has_domain_signals(chunk):
            return template
        try:
            user_prompt = build_user_prompt(template, chunk)
            result = models.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            
            return result
        except Exception as e:
            
            return template    

# ---------------------------------------------------------------------------
# Kind inference
# ---------------------------------------------------------------------------


def _infer_kind(chunk: RawDocumentChunk) -> str:
    """Infer the semantic kind from the raw text content."""
    text = chunk.raw_text.lower()

    for kind, patterns in _KIND_PATTERNS:
        for pattern in patterns:
            if pattern in text:
                return kind

    return "unknown"


# ---------------------------------------------------------------------------
# Subject extraction
# ---------------------------------------------------------------------------


def _extract_subject(chunk: RawDocumentChunk) -> str | None:
    """Extract a subject from section heading or first sentence."""
    if chunk.section_heading:
        return chunk.section_heading

    # fall back to first sentence of raw text
    sentences = chunk.raw_text.strip().split(".")
    if sentences and sentences[0].strip():
        subject = sentences[0].strip()
        # keep it concise — truncate if too long
        if len(subject) > 100:
            subject = subject[:100] + "..."
        return subject

    return None


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------


def _extract_keywords(chunk: RawDocumentChunk) -> list[str]:
    """Extract keywords from named entities, units, and section heading.

    These carry the richest domain signals without requiring LLM calls.
    """
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(word: str) -> None:
        lower = word.lower().strip()
        if lower and lower not in seen and len(lower) > 1:
            seen.add(lower)
            keywords.append(lower)

    # named entities from metadata — set by GLiNER in metadata extraction
    for entity in chunk.metadata.get("named_entities", []):
        _add(entity)

    # units mentioned
    for unit in chunk.metadata.get("units_mentioned", []):
        _add(unit)

    # section heading tokens
    if chunk.section_heading:
        for token in re.split(r"[\s\-_/]+", chunk.section_heading):
            _add(token)

    # constraint name if present
    constraint_name = chunk.metadata.get("constraint_name")
    if constraint_name:
        for token in constraint_name.split("_"):
            _add(token)

    return keywords