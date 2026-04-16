"""
Serialization round-trip tests for the enriched RawCodeChunk.
Verifies that code-specific fields survive the full payload chain
(RawCodeChunk → NormalizedChunk → EmbeddedChunk → model_dump → reconstruct).
"""
from embeddings.schemas import EmbeddedChunk
from ingestion.schemas import (
    LineRange,
    ParameterInfo,
    RawCodeChunk,
    RawKnowledgeChunk,
)
from normalization.schemas import NormalizedChunk


def _make_code_chunk() -> RawCodeChunk:
    return RawCodeChunk(
        source_file="pharma/calculator.py",
        raw_text="def calculate_dosage(weight: float) -> float: ...",
        name="calculate_dosage",
        signature="def calculate_dosage(weight: float, compound: Compound) -> float",
        language="python",
        kind="method",
        parameters=[
            ParameterInfo(name="weight", type_annotation="float"),
            ParameterInfo(name="compound", type_annotation="Compound"),
            ParameterInfo(name="factor", type_annotation="float", default_value="1.0"),
        ],
        return_type="float",
        docstring="Calculate recommended dosage based on patient weight.",
        decorators=["@validate_input"],
        line_range=LineRange(start=10, end=15),
        parent_class="DosageEngine",
        module_path="pharma.calculator",
        calls=["compound.get_base_dosage", "validate_weight"],
        imports=["pharma.compounds", "pharma.validation"],
        raises=["ValueError"],
    )


def test_raw_code_chunk_round_trips_through_model_dump():
    chunk = _make_code_chunk()
    data = chunk.model_dump()
    restored = RawCodeChunk(**data)

    assert restored.name == "calculate_dosage"
    assert restored.kind == "method"
    assert len(restored.parameters) == 3
    assert restored.parameters[2].default_value == "1.0"
    assert restored.line_range.start == 10
    assert restored.parent_class == "DosageEngine"
    assert restored.calls == ["compound.get_base_dosage", "validate_weight"]


def test_full_chain_round_trips_with_code_chunk():
    raw = _make_code_chunk()
    normalized = NormalizedChunk(
        source_chunk=raw,
        embed_text="Calculates dosage based on patient weight and compound properties.",
    )
    embedded = EmbeddedChunk(
        source_chunk=normalized,
        vector=[0.1] * 8,
        vector_model="test-model",
        vector_dimension=8,
    )

    data = embedded.model_dump()
    restored = EmbeddedChunk(**data)

    assert restored.chunk_type == "code"
    assert restored.embed_text == "Calculates dosage based on patient weight and compound properties."

    restored_raw = restored.source_chunk.source_chunk
    assert isinstance(restored_raw, RawCodeChunk)
    assert restored_raw.name == "calculate_dosage"
    assert restored_raw.parameters[0].type_annotation == "float"
    assert restored_raw.calls == ["compound.get_base_dosage", "validate_weight"]


def test_knowledge_chunk_unaffected_by_code_fields():
    knowledge = RawKnowledgeChunk(
        source_file="guide.md",
        raw_text="When dosage exceeds threshold, file a safety report.",
    )
    data = knowledge.model_dump()
    restored = RawKnowledgeChunk(**data)

    assert restored.chunk_type == "knowledge"
    assert restored.raw_text == "When dosage exceeds threshold, file a safety report."
