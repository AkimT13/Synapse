"""
Deterministic template builder. Converts a RawCodeChunk into a
structured natural-language description without any LLM calls.
Used as both the fallback embed_text and the input to LLM rewriting.
"""
from __future__ import annotations

from ingestion.schemas import RawCodeChunk

_PRIMITIVE_TYPES: set[str] = {
    "str", "int", "float", "bool", "list", "dict", "None", "Any",
    "bytes", "tuple", "set", "frozenset", "type",
}

_DUNDER_PATTERN = "__"

_GENERIC_NAMES: set[str] = {
    "run", "main", "execute", "do", "process", "handle",
    "get", "set", "update", "delete", "create",
    "func", "fn", "f", "helper", "util", "wrapper",
}


def build_template(chunk: RawCodeChunk) -> str:
    """Build a multi-sentence natural-language paragraph from chunk metadata.

    Only includes sections that have actual data -- never writes
    "Docstring: None" or empty placeholders.
    """
    parts: list[str] = []

    kind_label = chunk.kind.replace("_", " ")
    opening = f"Python {kind_label} `{chunk.name}`"
    if chunk.module_path:
        opening += f" in module `{chunk.module_path}`"
    if chunk.parent_class:
        opening += f", method of class `{chunk.parent_class}`"
    parts.append(opening + ".")

    visible_params = [parameter for parameter in chunk.parameters if parameter.name not in ("self", "cls")]
    if visible_params:
        formatted: list[str] = []
        for parameter in visible_params:
            entry = parameter.name
            if parameter.type_annotation:
                entry += f": {parameter.type_annotation}"
            if parameter.default_value:
                entry += f" = {parameter.default_value}"
            formatted.append(entry)
        parts.append(f"Takes parameters: {', '.join(formatted)}.")

    if chunk.return_type:
        parts.append(f"Returns {chunk.return_type}.")

    if chunk.docstring:
        parts.append(f"Docstring: {chunk.docstring}")

    if chunk.decorators:
        parts.append(f"Decorators: {', '.join(chunk.decorators)}.")

    if chunk.calls:
        parts.append(f"Calls: {', '.join(chunk.calls)}.")

    if chunk.raises:
        parts.append(f"Raises: {', '.join(chunk.raises)}.")

    return " ".join(parts)


def has_domain_signals(chunk: RawCodeChunk) -> bool:
    """Heuristic check for whether an LLM rewrite is worth the cost.

    Returns False for:
    - Dunder methods (__repr__, __str__, __eq__, etc.)
    - Functions named test_*
    - Functions with only primitive type annotations
    - Functions with generic names and no docstring
    """
    name = chunk.name

    # Dunder methods
    if name.startswith(_DUNDER_PATTERN) and name.endswith(_DUNDER_PATTERN):
        return False

    # Test functions
    if name.startswith("test_"):
        return False

    # Only primitive type annotations
    type_annotations: list[str] = []
    for p in chunk.parameters:
        if p.type_annotation:
            type_annotations.append(p.type_annotation)
    if chunk.return_type:
        type_annotations.append(chunk.return_type)

    if type_annotations and all(_is_primitive(t) for t in type_annotations):
        return False

    # Generic name with no docstring
    if name in _GENERIC_NAMES and not chunk.docstring:
        return False

    return True


def _is_primitive(annotation: str) -> bool:
    cleaned = annotation.strip()
    for wrapper in ("Optional[", "list[", "dict[", "set[", "tuple[", "frozenset["):
        if cleaned.startswith(wrapper):
            cleaned = cleaned[len(wrapper):]
            if cleaned.endswith("]"):
                cleaned = cleaned[:-1]

    parts = [part.strip() for part in cleaned.replace("|", ",").split(",")]
    return all(p in _PRIMITIVE_TYPES for p in parts if p)
