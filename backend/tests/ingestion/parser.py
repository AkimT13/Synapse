"""
Tests for the tree-sitter Python parser.

Every test uses inline source strings so the suite has zero filesystem
dependencies.  Test names describe *why* the assertion matters rather than
repeating the mechanics of what is checked.
"""
from __future__ import annotations

from ingestion.code.python_parser import PythonParser
from ingestion.schemas import RawCodeChunk


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse(source: str) -> list[RawCodeChunk]:
    """Convenience wrapper: parse *source* as if it were ``test.py``."""
    parser = PythonParser()
    return parser.parse_file(source, file_path="test.py", module_path="test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_basic_function_produces_one_chunk_with_correct_name() -> None:
    chunks = _parse("def greet(): pass")
    assert len(chunks) == 1
    assert chunks[0].name == "greet"


def test_typed_params_capture_type_annotations() -> None:
    chunks = _parse("def add(x: int, y: float) -> int: pass")
    params = chunks[0].parameters
    assert len(params) == 2
    assert params[0].name == "x"
    assert params[0].type_annotation == "int"
    assert params[1].name == "y"
    assert params[1].type_annotation == "float"


def test_default_values_are_preserved() -> None:
    chunks = _parse("def connect(host: str = 'localhost', port: int = 5432): pass")
    params = chunks[0].parameters
    assert params[0].default_value == "'localhost'"
    assert params[1].default_value == "5432"


def test_method_inside_class_records_parent_class() -> None:
    source = (
        "class Engine:\n"
        "    def start(self):\n"
        "        pass\n"
    )
    chunks = _parse(source)
    assert len(chunks) == 1
    assert chunks[0].parent_class == "Engine"
    assert chunks[0].kind == "method"


def test_async_function_is_tagged_as_async_function() -> None:
    chunks = _parse("async def fetch(): pass")
    assert chunks[0].kind == "async_function"


def test_decorated_function_captures_all_decorators() -> None:
    source = (
        "@login_required\n"
        "@cache(timeout=60)\n"
        "def view(): pass\n"
    )
    chunks = _parse(source)
    assert chunks[0].decorators == ["login_required", "cache"]


def test_property_decorator_sets_kind_to_property() -> None:
    source = (
        "class Config:\n"
        "    @property\n"
        "    def name(self):\n"
        "        return self._name\n"
    )
    chunks = _parse(source)
    assert chunks[0].kind == "property"


def test_docstring_extracted_from_first_string_expression() -> None:
    source = (
        'def documented():\n'
        '    """This is the docstring."""\n'
        '    pass\n'
    )
    chunks = _parse(source)
    assert chunks[0].docstring == "This is the docstring."


def test_function_with_no_docstring_leaves_field_none() -> None:
    chunks = _parse("def bare(): pass")
    assert chunks[0].docstring is None


def test_empty_file_produces_zero_chunks() -> None:
    assert _parse("") == []
    assert _parse("   \n\n") == []


def test_calls_list_captures_outgoing_function_calls() -> None:
    source = (
        "def process():\n"
        "    data = load()\n"
        "    transformed = transform(data)\n"
        "    save(transformed)\n"
    )
    chunks = _parse(source)
    assert set(chunks[0].calls) == {"load", "transform", "save"}


def test_return_type_annotation_extracted() -> None:
    chunks = _parse("def identity(x: int) -> int: return x")
    assert chunks[0].return_type == "int"


def test_raises_list_captures_raised_exceptions() -> None:
    source = (
        "def validate(x):\n"
        "    if x < 0:\n"
        "        raise ValueError('negative')\n"
        "    if x is None:\n"
        "        raise TypeError('none')\n"
    )
    chunks = _parse(source)
    assert set(chunks[0].raises) == {"ValueError", "TypeError"}


def test_module_path_passed_through_to_chunk() -> None:
    chunks = _parse("def noop(): pass")
    assert chunks[0].module_path == "test"
