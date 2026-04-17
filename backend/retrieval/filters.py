from __future__ import annotations


def knowledge_filter(
    domain: str | None = None,
    knowledge_type: str | None = None,
    constraints_only: bool = False,
    min_confidence: float | None = None,
    source_type: str | None = None,
) -> dict:
    """Build a filter dict for knowledge chunk retrieval."""
    f: dict = {"chunk_type": "knowledge"}

    if domain:
        f["domain"] = domain
    if knowledge_type:
        f["knowledge_type"] = knowledge_type
    if constraints_only:
        f["contains_constraint"] = True
    if min_confidence is not None:
        f["confidence"] = {"$gte": min_confidence}
    if source_type:
        f["source_type"] = source_type

    return f


def code_filter(
    language: str | None = None,
    module_path: str | None = None,
) -> dict:
    """Build a filter dict for code chunk retrieval."""
    f: dict = {"chunk_type": "code"}

    if language:
        f["language"] = language
    if module_path:
        f["module_path"] = module_path

    return f


def constraint_filter(domain: str | None = None) -> dict:
    """Shorthand filter for constraint-only knowledge chunks."""
    return knowledge_filter(
        domain=domain,
        constraints_only=True,
        min_confidence=0.7,
    )