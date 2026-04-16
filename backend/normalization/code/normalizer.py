"""
Code normalization pipeline. Takes RawCodeChunks and produces
NormalizedChunks with natural-language embed_text suitable for
embedding alongside domain knowledge.

Each chunk flows through: template generation -> optional LLM rewrite
-> kind inference -> keyword extraction. The LLM step is skipped for
boilerplate functions (dunders, tests, primitive-only signatures) to
save cost without losing retrieval quality.
"""
from __future__ import annotations

import re

import models
from ingestion.schemas import RawCodeChunk
from normalization.code.prompts import SYSTEM_PROMPT, build_user_prompt
from normalization.code.template import build_template, has_domain_signals
from normalization.schemas import NormalizedChunk

# ---------------------------------------------------------------------------
# Kind-inference patterns
# ---------------------------------------------------------------------------

_KIND_PATTERNS: list[tuple[str, list[str]]] = [
    ("constraint", ["validate", "check", "assert", "ensure"]),
    ("behavior", ["process", "compute", "calculate", "transform", "filter"]),
    ("procedure", ["run", "execute", "pipeline", "orchestrate", "main"]),
    ("mapping", ["convert", "map", "translate", "to_", "from_"]),
]

_CONSTRAINT_DECORATORS: set[str] = {"validator", "field_validator", "root_validator"}


# ---------------------------------------------------------------------------
# CodeNormalizer
# ---------------------------------------------------------------------------


class CodeNormalizer:
    """Normalizes RawCodeChunks into NormalizedChunks.

    Parameters
    ----------
    should_use_llm:
        When True (default), functions with domain signals are rewritten
        by the configured LLM for richer natural-language descriptions.
        When False, every chunk gets the deterministic template only.
    """

    def __init__(self, should_use_llm: bool = True) -> None:
        self._should_use_llm = should_use_llm

    def normalize(self, chunk: RawCodeChunk) -> NormalizedChunk:
        template = build_template(chunk)
        embed_text = self._maybe_rewrite(template, chunk)
        kind = _infer_kind(chunk)
        keywords = _extract_keywords(chunk)

        return NormalizedChunk(
            source_chunk=chunk,
            kind=kind,
            subject=chunk.name,
            embed_text=embed_text,
            keywords=keywords,
        )

    def normalize_batch(self, chunks: list[RawCodeChunk]) -> list[NormalizedChunk]:
        """Individual errors fall back to template-only — never fails the full batch."""
        results: list[NormalizedChunk] = []
        for chunk in chunks:
            try:
                results.append(self.normalize(chunk))
            except Exception:
                # Fall back to template-only normalization
                template = build_template(chunk)
                results.append(NormalizedChunk(
                    source_chunk=chunk,
                    kind="unknown",
                    subject=chunk.name,
                    embed_text=template,
                    keywords=_extract_keywords(chunk),
                ))
        return results

    def _maybe_rewrite(self, template: str, chunk: RawCodeChunk) -> str:
        """Call LLM for domain-rich functions, otherwise return template."""
        if not self._should_use_llm or not has_domain_signals(chunk):
            return template

        try:
            user_prompt = build_user_prompt(template, chunk)
            return models.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception:
            return template


# ---------------------------------------------------------------------------
# Kind inference
# ---------------------------------------------------------------------------


def _infer_kind(chunk: RawCodeChunk) -> str:
    name = chunk.name.lower()

    for decorator in chunk.decorators:
        if decorator in _CONSTRAINT_DECORATORS:
            return "constraint"

    if name == "__init__":
        return "definition"

    for kind, patterns in _KIND_PATTERNS:
        for pattern in patterns:
            if pattern in name:
                return kind

    return "unknown"


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------


def _extract_keywords(chunk: RawCodeChunk) -> list[str]:
    """Sources: function name tokens, parameter type names, and import roots.

    These carry the richest domain signals without requiring LLM calls.
    """
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(word: str) -> None:
        lower = word.lower().strip()
        if lower and lower not in seen and len(lower) > 1:
            seen.add(lower)
            keywords.append(lower)

    for part in chunk.name.split("_"):
        _add(part)

    for parameter in chunk.parameters:
        if parameter.type_annotation:
            type_name = re.sub(r"[\[\]|,]", " ", parameter.type_annotation)
            for token in type_name.split():
                _add(token)

    for import_path in chunk.imports:
        parts = import_path.split(".")
        _add(parts[0])

    return keywords
