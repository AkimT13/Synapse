from __future__ import annotations

from agents.query_agent import answer
from agents.schemas import QueryResponse


def test_answer_wraps_pipeline_result(mocker, mock_store, knowledge_result, code_result):
    pipeline_result = {
        "results": [knowledge_result, code_result],
        "answer": "The code appears consistent with the documented wavelength handling.",
    }

    mocked = mocker.patch(
        "agents.query_agent.answer_question",
        return_value=pipeline_result,
    )

    response = answer(
        question="How does the system handle wavelength normalization?",
        store=mock_store,
        k=7,
    )

    mocked.assert_called_once_with(
        question="How does the system handle wavelength normalization?",
        store=mock_store,
        k=7,
    )

    assert isinstance(response, QueryResponse)
    assert response.question == "How does the system handle wavelength normalization?"
    assert response.answer == pipeline_result["answer"]
    assert response.results == pipeline_result["results"]


def test_answer_handles_empty_results(mocker, mock_store):
    mocked = mocker.patch(
        "agents.query_agent.answer_question",
        return_value={
            "results": [],
            "answer": "No relevant information found.",
        },
    )

    response = answer(
        question="Is there any code for isotope correction?",
        store=mock_store,
    )

    mocked.assert_called_once()
    assert isinstance(response, QueryResponse)
    assert response.question == "Is there any code for isotope correction?"
    assert response.answer == "No relevant information found."
    assert response.results == []