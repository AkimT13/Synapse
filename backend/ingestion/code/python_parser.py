"""
Tree-sitter based Python parser for the code ingestion pipeline.

Walks the concrete syntax tree produced by tree-sitter-python and emits one
RawCodeChunk per function or method definition.  Only top-level functions and
direct class methods are extracted — nested / closure functions are
intentionally skipped so each chunk maps to a single addressable symbol.

The parser self-registers with the language registry at import time so it is
automatically available when any module imports ``ingestion.code``.
"""
from __future__ import annotations

from typing import Literal

import tree_sitter_python as ts_python
from tree_sitter import Language, Node, Parser

from ingestion.code.languages import register_parser
from ingestion.schemas import LineRange, ParameterInfo, RawCodeChunk

PYTHON_LANGUAGE = Language(ts_python.language())

# ---------------------------------------------------------------------------
# Kind inference helpers
# ---------------------------------------------------------------------------

_DECORATOR_KIND_MAP: dict[str, Literal[
    "property", "classmethod", "staticmethod",
]] = {
    "property": "property",
    "classmethod": "classmethod",
    "staticmethod": "staticmethod",
}


def _infer_kind(
    decorators: list[str],
    parent_class: str | None,
    is_async: bool,
) -> Literal[
    "function",
    "method",
    "classmethod",
    "staticmethod",
    "async_function",
    "async_method",
    "property",
]:
    """Derive the semantic *kind* of a function from its context."""
    for decorator in decorators:
        mapped = _DECORATOR_KIND_MAP.get(decorator)
        if mapped is not None:
            return mapped

    if parent_class is not None:
        return "async_method" if is_async else "method"
    return "async_function" if is_async else "function"


# ---------------------------------------------------------------------------
# Extraction helpers — each operates on a single tree-sitter Node
# ---------------------------------------------------------------------------

def _node_text(node: Node) -> str:
    return node.text.decode("utf-8")


def _extract_parameters(params_node: Node) -> list[ParameterInfo]:
    """Return structured parameter info from a ``parameters`` node."""
    result: list[ParameterInfo] = []

    for child in params_node.named_children:
        if child.type == "identifier":
            # Plain, un-typed parameter (e.g. ``self``, ``x``)
            result.append(ParameterInfo(name=_node_text(child)))

        elif child.type == "typed_parameter":
            name_node = child.child_by_field_name("name") or child.named_children[0]
            type_node = child.child_by_field_name("type")
            result.append(ParameterInfo(
                name=_node_text(name_node),
                type_annotation=_node_text(type_node) if type_node else None,
            ))

        elif child.type == "default_parameter":
            name_node = child.child_by_field_name("name") or child.named_children[0]
            value_node = child.child_by_field_name("value") or child.named_children[-1]
            result.append(ParameterInfo(
                name=_node_text(name_node),
                default_value=_node_text(value_node),
            ))

        elif child.type == "typed_default_parameter":
            name_node = child.child_by_field_name("name") or child.named_children[0]
            type_node = child.child_by_field_name("type")
            value_node = child.child_by_field_name("value") or child.named_children[-1]
            result.append(ParameterInfo(
                name=_node_text(name_node),
                type_annotation=_node_text(type_node) if type_node else None,
                default_value=_node_text(value_node),
            ))

        elif child.type == "list_splat_pattern":
            # *args
            identifier = child.named_children[0] if child.named_children else None
            name = "*" + _node_text(identifier) if identifier else "*"
            result.append(ParameterInfo(name=name))

        elif child.type == "dictionary_splat_pattern":
            # **kwargs
            identifier = child.named_children[0] if child.named_children else None
            name = "**" + _node_text(identifier) if identifier else "**"
            result.append(ParameterInfo(name=name))

    return result


def _extract_decorators(function_node: Node) -> list[str]:
    """Return decorator names from a ``decorated_definition`` parent, if any."""
    parent = function_node.parent
    if parent is None or parent.type != "decorated_definition":
        return []

    decorators: list[str] = []
    for child in parent.children:
        if child.type != "decorator":
            continue
        # The decorator node's children are ``@`` followed by an expression.
        # That expression is either an identifier (``@foo``) or a call whose
        # first child is the identifier / attribute (``@foo.bar(...)``).
        expression = child.named_children[0] if child.named_children else None
        if expression is None:
            continue
        if expression.type == "identifier":
            decorators.append(_node_text(expression))
        elif expression.type == "call":
            function_node = expression.named_children[0] if expression.named_children else None
            if function_node is not None:
                decorators.append(_node_text(function_node))
        elif expression.type == "attribute":
            decorators.append(_node_text(expression))
    return decorators


def _extract_docstring(body_node: Node) -> str | None:
    """Extract the docstring from the first statement in a function body."""
    if not body_node.named_children:
        return None

    first_stmt = body_node.named_children[0]
    if first_stmt.type != "expression_statement":
        return None

    string_node = first_stmt.named_children[0] if first_stmt.named_children else None
    if string_node is None or string_node.type != "string":
        return None

    raw = _node_text(string_node)
    # Strip surrounding triple-quotes or single quotes
    for quote in ('"""', "'''", '"', "'"):
        if raw.startswith(quote) and raw.endswith(quote):
            return raw[len(quote):-len(quote)]
    return raw


def _extract_calls(body_node: Node) -> list[str]:
    """Recursively collect unique function-call names from *body_node*."""
    calls: list[str] = []
    seen: set[str] = set()

    def _walk(node: Node) -> None:
        if node.type == "call":
            callee = node.named_children[0] if node.named_children else None
            if callee is not None:
                name = _node_text(callee)
                if name not in seen:
                    seen.add(name)
                    calls.append(name)
        for child in node.children:
            _walk(child)

    _walk(body_node)
    return calls


def _exception_name_from_raise(raise_node: Node) -> str | None:
    """Extract the exception class name from a raise_statement node."""
    expression = raise_node.named_children[0] if raise_node.named_children else None
    if expression is None:
        return None
    if expression.type == "call":
        name_node = expression.named_children[0] if expression.named_children else None
        return _node_text(name_node) if name_node else None
    if expression.type == "identifier":
        return _node_text(expression)
    return None


def _extract_raises(body_node: Node) -> list[str]:
    """Collect unique exception names from ``raise`` statements."""
    raises: list[str] = []
    seen: set[str] = set()

    def _walk(node: Node) -> None:
        if node.type == "raise_statement":
            name = _exception_name_from_raise(node)
            if name and name not in seen:
                seen.add(name)
                raises.append(name)
        for child in node.children:
            _walk(child)

    _walk(body_node)
    return raises


def _extract_return_type(function_node: Node) -> str | None:
    """Return the text of the return-type annotation, if present."""
    return_type_node = function_node.child_by_field_name("return_type")
    if return_type_node is None:
        return None
    return _node_text(return_type_node)


def _build_signature(source: str, function_node: Node) -> str:
    """Return the ``def …:`` line (first line) of the function."""
    start_line = function_node.start_point[0]
    lines = source.splitlines()
    if start_line < len(lines):
        return lines[start_line].strip()
    return ""


# ---------------------------------------------------------------------------
# PythonParser
# ---------------------------------------------------------------------------

class PythonParser:
    """Concrete tree-sitter parser for Python source files."""

    @property
    def language(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py"]

    def parse_file(
        self,
        source: str,
        file_path: str,
        module_path: str,
    ) -> list[RawCodeChunk]:
        """Parse *source* and return one RawCodeChunk per function/method."""
        parser = Parser(PYTHON_LANGUAGE)
        tree = parser.parse(source.encode("utf-8"))
        root = tree.root_node

        if root.has_error:
            return []

        chunks: list[RawCodeChunk] = []
        self._walk_module(root, source, file_path, module_path, chunks)
        return chunks

    # -- Private traversal --------------------------------------------------

    def _walk_module(
        self,
        root: Node,
        source: str,
        file_path: str,
        module_path: str,
        chunks: list[RawCodeChunk],
    ) -> None:
        """Walk top-level statements looking for functions and classes."""
        for child in root.children:
            if child.type == "function_definition":
                self._process_function(child, source, file_path, module_path, None, chunks)
            elif child.type == "decorated_definition":
                inner = self._unwrap_decorated(child)
                if inner is not None and inner.type == "function_definition":
                    self._process_function(inner, source, file_path, module_path, None, chunks)
                elif inner is not None and inner.type == "class_definition":
                    self._walk_class(inner, source, file_path, module_path, chunks)
            elif child.type == "class_definition":
                self._walk_class(child, source, file_path, module_path, chunks)

    def _walk_class(
        self,
        class_node: Node,
        source: str,
        file_path: str,
        module_path: str,
        chunks: list[RawCodeChunk],
    ) -> None:
        """Walk class body for direct method definitions."""
        name_node = class_node.child_by_field_name("name")
        class_name = _node_text(name_node) if name_node else ""
        body = class_node.child_by_field_name("body")
        if body is None:
            return

        for child in body.children:
            if child.type == "function_definition":
                self._process_function(child, source, file_path, module_path, class_name, chunks)
            elif child.type == "decorated_definition":
                inner = self._unwrap_decorated(child)
                if inner is not None and inner.type == "function_definition":
                    self._process_function(inner, source, file_path, module_path, class_name, chunks)

    @staticmethod
    def _unwrap_decorated(node: Node) -> Node | None:
        """Return the function/class inside a ``decorated_definition``."""
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return child
        return None

    def _process_function(
        self,
        function_node: Node,
        source: str,
        file_path: str,
        module_path: str,
        parent_class: str | None,
        chunks: list[RawCodeChunk],
    ) -> None:
        """Build a RawCodeChunk from a single ``function_definition`` node."""
        if function_node.has_error:
            return

        name_node = function_node.child_by_field_name("name")
        name = _node_text(name_node) if name_node else ""

        params_node = function_node.child_by_field_name("parameters")
        parameters = _extract_parameters(params_node) if params_node else []

        decorators = _extract_decorators(function_node)

        is_async = any(
            child.type == "async" for child in function_node.children
        )
        kind = _infer_kind(decorators, parent_class, is_async)

        body_node = function_node.child_by_field_name("body")
        docstring = _extract_docstring(body_node) if body_node else None
        calls = _extract_calls(body_node) if body_node else []
        raises = _extract_raises(body_node) if body_node else []

        return_type = _extract_return_type(function_node)
        signature = _build_signature(source, function_node)

        # Include decorators in raw_text so normalization can see the full context
        outer_node = function_node.parent if function_node.parent and function_node.parent.type == "decorated_definition" else function_node
        raw_text = _node_text(outer_node)

        line_range = LineRange(
            start=outer_node.start_point[0] + 1,
            end=outer_node.end_point[0] + 1,
        )

        chunks.append(RawCodeChunk(
            source_file=file_path,
            chunk_index=len(chunks),
            raw_text=raw_text,
            name=name,
            signature=signature,
            language="python",
            kind=kind,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            decorators=decorators,
            line_range=line_range,
            parent_class=parent_class,
            module_path=module_path,
            calls=calls,
            raises=raises,
        ))


# ---------------------------------------------------------------------------
# Auto-registration
# ---------------------------------------------------------------------------

register_parser(PythonParser())
