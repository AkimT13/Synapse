from __future__ import annotations

from agents.constraint_agent import check_code
from agents.schemas import ConflictReport


def test_check_code_wraps_pipeline_result(mocker, mock_store, knowledge_result):
    pipeline_result = {
        "constraints": [knowledge_result],
        "explanation": (
            "The code violates the documented wavelength threshold because it "
            "permits values below 0.5nm."
        ),
        "has_conflict": True,
    }

    mocked = mocker.patch(
        "agents.constraint_agent.check_code_against_constraints",
        return_value=pipeline_result,
    )

    response = check_code(
        code_embed_text="Behavior: accepts wavelength values down to 0.1nm",
        store=mock_store,
        domain="spectroscopy",
        k=3,
    )

    mocked.assert_called_once_with(
        code_embed_text="Behavior: accepts wavelength values down to 0.1nm",
        store=mock_store,
        domain="spectroscopy",
        k=3,
    )

    assert isinstance(response, ConflictReport)
    assert response.code_embed_text == "Behavior: accepts wavelength values down to 0.1nm"
    assert response.constraints == [knowledge_result]
    assert response.explanation == pipeline_result["explanation"]
    assert response.has_conflict is True
    assert response.memory_hits == []


def test_check_code_handles_no_constraints(mocker, mock_store):
    mocked = mocker.patch(
        "agents.constraint_agent.check_code_against_constraints",
        return_value={
            "constraints": [],
            "explanation": "No relevant domain constraints found.",
            "has_conflict": False,
        },
    )

    response = check_code(
        code_embed_text="Behavior: computes baseline offset",
        store=mock_store,
    )

    mocked.assert_called_once()
    assert isinstance(response, ConflictReport)
    assert response.constraints == []
    assert response.explanation == "No relevant domain constraints found."
    assert response.has_conflict is False
    assert response.memory_hits == []