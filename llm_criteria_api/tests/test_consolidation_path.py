"""Final regression coverage for the live LLM consolidation branch."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from app.multisentence_grounding import MultiSentenceGroundingAdapter
from app.pipeline import CriteriaPipeline


ALLOWED_TYPES = {
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
}


RESPONSIBILITIES = [
    "Manage candidate records.",
    "Manage candidate records.",
    "Prepare payroll reports.",
    "Schedule warehouse inventory.",
]

REQUIREMENTS = [
    "At least three years of payroll administration experience.",
    "Diploma in Facilities Management.",
    "Knowledge of CCTV security procedures.",
    "ISO 45001 certification is an advantage.",
    "English communication is required.",
]


def section_output(*criteria: dict[str, str]) -> str:
    return json.dumps({"criteria": list(criteria)})


def extraction_outputs() -> list[str]:
    return [
        section_output(
            {
                "type": "relevant_skill",
                "name": "Candidate Record Management",
                "sourceText": RESPONSIBILITIES[0],
            },
            {
                "type": "relevant_skill",
                "name": "Candidate Record Management",
                "sourceText": RESPONSIBILITIES[1],
            },
            {
                "type": "relevant_skill",
                "name": "Payroll Reporting",
                "sourceText": RESPONSIBILITIES[2],
            },
            {
                "type": "relevant_skill",
                "name": "Warehouse Scheduling",
                "sourceText": RESPONSIBILITIES[3],
            },
        ),
        section_output(
            {
                "type": "relevant_experience",
                "name": "Payroll Administration Experience",
                "sourceText": REQUIREMENTS[0],
            },
            {
                "type": "education_relevance",
                "name": "Facilities Management Education",
                "sourceText": REQUIREMENTS[1],
            },
            {
                "type": "domain_knowledge",
                "name": "CCTV Security Procedures",
                "sourceText": REQUIREMENTS[2],
            },
            {
                "type": "preferred_certification",
                "name": "ISO 45001 Certification",
                "sourceText": REQUIREMENTS[3],
            },
            {
                "type": "job_related_language",
                "name": "English Proficiency",
                "sourceText": REQUIREMENTS[4],
            },
        ),
    ]


class ConsolidationLoader:
    def __init__(self, invalid: bool) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self.invalid = invalid
        self.outputs = iter(extraction_outputs())
        self.consolidation_request: dict = {}
        self.consolidation_response: dict = {}

    def raw_output_generator(self, messages: list[dict[str, str]]) -> str:
        content = messages[-1]["content"]
        if "criteriaByType" not in content:
            return next(self.outputs)

        start = content.index("{", content.index("criteriaByType"))
        payload, _ = json.JSONDecoder().raw_decode(content[start:])
        self.consolidation_request = payload
        criteria = [
            item
            for items in payload["criteriaByType"].values()
            for item in items
        ]
        if self.invalid:
            response = {
                "groups": [
                    {
                        "type": "relevant_skill",
                        "name": "Invalid Group",
                        "memberIds": [criteria[0]["id"], "unknown-input-id"],
                    }
                ]
            }
        else:
            groups = []
            for type_id, items in payload["criteriaByType"].items():
                if type_id == "relevant_skill" and len(items) >= 2:
                    groups.append(
                        {
                            "type": type_id,
                            "name": "Candidate Record Management",
                            "memberIds": [items[0]["id"], items[1]["id"]],
                        }
                    )
                    items = items[2:]
                groups.extend(
                    {
                        "type": type_id,
                        "name": item["name"],
                        "memberIds": [item["id"]],
                    }
                    for item in items
                )
            response = {"groups": groups}
        self.consolidation_response = response
        return json.dumps(response)


def job() -> dict:
    return {
        "jobTitle": "Operations Manager",
        "department": "Operations",
        "responsibilities": RESPONSIBILITIES,
        "requirements": REQUIREMENTS,
    }


def input_criteria(loader: ConsolidationLoader) -> list[dict]:
    return [
        item
        for items in loader.consolidation_request["criteriaByType"].values()
        for item in items
    ]


def test_llm_consolidation_ids_and_invalid_fallback_preserve_domains() -> None:
    loader = ConsolidationLoader(invalid=True)
    # Keep the two workflow-adjacent criteria available until the explicit
    # consolidation branch; the production deduplication path is tested
    # separately by the broader suite.
    with patch("app.pipeline.safe_merge_duplicate_criteria", lambda criteria, *_args: criteria), patch.object(
        MultiSentenceGroundingAdapter, "_find_multi_source_match", return_value=None
    ):
        result = CriteriaPipeline(loader).generate(job())
    inputs = input_criteria(loader)
    input_ids = [item["id"] for item in inputs]

    assert input_ids
    assert len(input_ids) == len(set(input_ids))
    assert set(input_ids) == {f"c{number}" for number in range(1, 10)}
    assert all(item["id"] == item["id"].strip().lower() for item in inputs)
    assert loader.consolidation_response["groups"][0]["memberIds"][0] in input_ids
    assert "unknown-input-id" not in input_ids
    assert result["audit"]["consolidation"]["consolidationMethod"] == "python_fallback"
    assert result["audit"]["consolidation"]["consolidationSucceeded"] is True

    criteria = result["criteria"]
    assert set(item["type"] for item in criteria) == ALLOWED_TYPES
    assert len(criteria) > 6
    assert result["weightTotal"] == 100
    assert any("unknown" in error.casefold() for error in result["audit"]["consolidation"]["consolidationValidationErrors"])

    by_source = {source: [] for source in RESPONSIBILITIES}
    for criterion in criteria:
        assert len(criterion["sourceIds"]) == len(criterion["groundingScores"])
        for source in criterion["sourceText"].split(" | "):
            if source in by_source:
                by_source[source].append(criterion)
    assert len(by_source[RESPONSIBILITIES[2]]) == 1
    assert len(by_source[RESPONSIBILITIES[3]]) == 1
    assert by_source[RESPONSIBILITIES[2]][0] is not by_source[RESPONSIBILITIES[3]][0]


def test_valid_consolidation_response_references_only_input_ids() -> None:
    loader = ConsolidationLoader(invalid=False)
    with patch("app.pipeline.safe_merge_duplicate_criteria", lambda criteria, *_args: criteria), patch.object(
        MultiSentenceGroundingAdapter, "_find_multi_source_match", return_value=None
    ):
        result = CriteriaPipeline(loader).generate(job())
    inputs = input_criteria(loader)
    input_ids = {item["id"] for item in inputs}
    response_ids = {
        member_id
        for group in loader.consolidation_response["groups"]
        for member_id in group["memberIds"]
    }

    assert response_ids <= input_ids
    assert response_ids == input_ids
    assert result["audit"]["consolidation"]["consolidationRawModelOutput"] is not None
    assert result["audit"]["consolidation"]["consolidationValidationErrors"] == []
    assert len(result["criteria"]) > 6
    assert result["weightTotal"] == 100
