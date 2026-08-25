"""Regression tests for narrow multi-sentence source grounding."""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.pipeline import CriteriaPipeline


class CachedRawLoader:
    def __init__(self, raw_outputs: list[str]) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._raw_outputs = iter(raw_outputs)

    def raw_output_generator(self, _messages: list[dict[str, str]]) -> str:
        return next(self._raw_outputs)


def section_output(*criteria: dict[str, str]) -> str:
    return json.dumps({"criteria": list(criteria)})


def run_case(responsibilities: list[str], responsibility_output: str) -> dict:
    job = {
        "jobTitle": "IT Support Engineer",
        "department": "Information Technology",
        "responsibilities": responsibilities,
        "requirements": [],
    }
    return CriteriaPipeline(
        CachedRawLoader([responsibility_output])
    ).generate(job)


def test_related_sentences_are_retained_as_multi_source_grounding() -> None:
    first = "Provide technical support to users."
    second = "Troubleshoot hardware, software and network issues."
    result = run_case(
        [first, second],
        section_output(
            {
                "type": "relevant_skill",
                "name": "Technical Support and Troubleshooting",
                "sourceText": f"{first} {second}",
            }
        ),
    )

    assert len(result["criteria"]) == 1
    criterion = result["criteria"][0]
    assert criterion["sourceText"] == f"{first} | {second}"
    assert criterion["sourceIds"] == ["responsibilities-1", "responsibilities-2"]
    assert criterion["groundingScores"] == [1.0, 1.0]
    assert result["audit"]["sectionDiagnostics"]["responsibilities"][
        "multiSentenceGroundingCount"
    ] == 1


def test_unrelated_sentence_is_not_added_to_grounding() -> None:
    first = "Provide technical support to users."
    unrelated = "Prepare monthly payroll reports."
    result = run_case(
        [first, unrelated],
        section_output(
            {
                "type": "relevant_skill",
                "name": "Technical Support and Troubleshooting",
                "sourceText": f"{first} {unrelated}",
            }
        ),
    )

    for criterion in result["criteria"]:
        assert criterion["sourceIds"] != [
            "responsibilities-1",
            "responsibilities-2",
        ]
        assert unrelated not in criterion["sourceText"]

    diagnostics = result["audit"]["sectionDiagnostics"]["responsibilities"]
    assert diagnostics.get("multiSentenceGroundingCount", 0) == 0
