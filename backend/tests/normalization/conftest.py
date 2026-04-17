import pytest
from ingestion.schemas import RawDocumentChunk


@pytest.fixture()
def text_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text=(
            "The minimum wavelength resolution is 0.5 nanometers. "
            "Software must not make distinctions below this threshold."
        ),
        source_file="spectrometer_spec.pdf",
        chunk_index=0,
        section_heading="Resolution Limits",
        page_number=12,
    )


@pytest.fixture()
def table_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text="| Material | Conductivity |\n|---|---|\n| Copper | 385 W/mK |",
        source_file="materials_spec.pdf",
        chunk_index=1,
        content_type="table",
        metadata={
            "table_markdown": "| Material | Conductivity |\n|---|---|\n| Copper | 385 W/mK |",
            "table_description": "Copper has thermal conductivity of 385 watts per meter kelvin.",
        },
    )


@pytest.fixture()
def short_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text="See page 14.",
        source_file="manual.pdf",
        chunk_index=2,
    )


@pytest.fixture()
def figure_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text="",
        source_file="manual.pdf",
        chunk_index=3,
        content_type="figure",
    )


@pytest.fixture()
def entity_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text=(
            "The centrifuge must not exceed 5000 RPM during the separation phase."
        ),
        source_file="lab_manual.pdf",
        chunk_index=4,
        section_heading="Operating Limits",
        metadata={
            "named_entities": ["centrifuge", "separation phase"],
            "units_mentioned": ["RPM"],
        },
    )

@pytest.fixture()
def definition_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text=(
            "Spectral resolution is defined as the minimum wavelength "
            "difference that can be discriminated by the instrument."
        ),
        source_file="spectrometer_spec.pdf",
        chunk_index=5,
        section_heading="Definitions",
    )


@pytest.fixture()
def procedure_chunk() -> RawDocumentChunk:
    return RawDocumentChunk.from_raw_text(
        raw_text=(
            "Follow this procedure to calibrate the instrument. "
            "First, power on the device. Then allow 30 minutes warm-up time."
        ),
        source_file="calibration_manual.pdf",
        chunk_index=6,
        section_heading="Calibration Procedure",
    )