"""Regression tests for the v1.0.8 deterministic foundation."""

from __future__ import annotations

import json
from pathlib import Path

from app.explicit_requirement_recovery import recover_explicit_requirements
from app.response_safety import safe_api_output
from app.schemas import GenerateCriteriaResponse


FIXTURES = Path(__file__).parents[1] / "benchmarks" / "gold_standard_v1" / "fixtures"


def _texts(values):
    return [item.get("text", item) if isinstance(item, dict) else item for item in values]


def test_explicit_recovery_keeps_level_only_education_neutral_and_grounded():
    criteria, recoveries, _ = recover_explicit_requirements(
        [],
        [
            "Minimum STPM, Diploma or Degree.",
            "A Diploma or Degree in Accounting, Finance or a related field is required.",
        ],
    )

    assert [item["name"] for item in criteria] == [
        "Education",
        "Accounting and Finance Education",
    ]
    assert [item["type"] for item in criteria] == [
        "education_relevance",
        "education_relevance",
    ]
    assert recoveries[0]["recoveryType"] == "explicit_education_level"
    assert "sourceText" not in recoveries[0]
    assert recoveries[0]["sourceTextHashes"]


def test_explicit_recovery_boundaries_for_all_categories():
    criteria, recoveries, _ = recover_explicit_requirements(
        [],
        [
            "Minimum 2 years of accounts payable experience.",
            "Written and spoken English is required for technical reporting.",
            "ACCA certification is preferred.",
            "CISA certification is required.",
            "Knowledge of Malaysia e-Invoice requirements is required.",
            "Good communication skills are required.",
            "Relevant certification is an advantage.",
        ],
    )

    assert {(item["type"], item["name"]) for item in criteria} == {
        ("relevant_experience", "Accounts Payable Experience"),
        ("job_related_language", "English Language"),
        ("preferred_certification", "ACCA Certification"),
        ("domain_knowledge", "Malaysia e-Invoice Compliance"),
    }
    assert {item["recoveryType"] for item in recoveries} == {
        "explicit_experience",
        "explicit_language",
        "explicit_certification",
        "explicit_law_or_standard",
    }
    assert not any(item["name"] == "CISA Certification" for item in criteria)
    assert all(item["sourceIds"] and item["sourceTextHashes"] for item in recoveries)


def test_six_gold_standard_fixtures_recover_only_explicit_requirements():
    expected = {
        "accounts_payable_executive_001": {
            "Accounting and Finance Education",
            "Accounts Payable Experience",
            "Malaysia e-Invoice Compliance",
        },
        "administrative_executive_001": {
            "Business Administration Education",
            "Administrative Experience",
        },
        "hr_manager_001": {"HR Field Experience", "Malaysian Labour Law"},
        "qa_engineer_001": {
            "Engineering Education",
            "Manufacturing Quality Experience",
            "ISO 9001 Quality Standards",
        },
        "sales_executive_001": {
            "Business and Marketing Education",
            "B2B Sales or Business Development Experience",
            "Mandarin Language",
        },
        "software_engineer_001": {
            "Computing Education",
        },
    }

    for fixture_path in sorted(FIXTURES.glob("*.json")):
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        reference = fixture["referenceJd"]
        criteria = []
        recoveries = []
        for section, values in (
            (
                "requirements",
                _texts(reference["qualifications"] + reference["requirements"]),
            ),
            ("responsibilities", _texts(reference["responsibilities"])),
        ):
            criteria, section_recoveries, _ = recover_explicit_requirements(
                criteria,
                values,
                source_section=section,
            )
            recoveries.extend(section_recoveries)

        names = {item["name"] for item in criteria}
        assert expected[fixture_path.stem] <= names
        if fixture_path.stem == "software_engineer_001":
            assert names & {
                "Software Development Experience",
                "Production Web Application Experience",
            }
        assert all(item["sourceText"] for item in criteria)
        assert all(item["sourceIds"] for item in criteria)
        assert all(item["groundingScores"] == [1.0] for item in criteria)
        assert all(item["recoveryType"] in {
            "explicit_education_field",
            "explicit_education_level",
            "explicit_experience",
            "explicit_language",
            "explicit_certification",
            "explicit_law_or_standard",
            "explicit_tool_or_system",
        } for item in recoveries)

    hr = json.loads((FIXTURES / "hr_manager_001.json").read_text(encoding="utf-8"))
    hr_requirements = _texts(hr["referenceJd"]["qualifications"])
    level_only, _, _ = recover_explicit_requirements([], hr_requirements)
    assert [item["name"] for item in level_only] == ["Education"]


def test_safe_serialization_preserves_observability_metadata():
    output = {
        "criteria": [{
            "criterionId": "criterion-1",
            "type": "relevant_skill",
            "name": "Process Data Analysis",
            "description": "description",
            "evidenceRule": "resume evidence",
            "sourceText": "Analyse process data.",
            "sourceIds": ["responsibilities-1"],
            "groundingScores": [0.98],
            "sourceCriterionIds": ["responsibilities-criterion-1"],
            "mergedFromIds": ["criterion-1"],
            "importance": "high",
            "suggestedWeight": 100,
        }],
        "ignoredTexts": [],
        "warnings": [],
        "weightTotal": 100,
        "audit": {
            "deployment": {"imageTag": "v1.0.8", "pipelineVersion": "foundation", "gitCommitHash": "abc", "roleContextEnabled": True, "finalEvidenceSafetyEnabled": True},
            "debugTrace": [{"stage": "api_payload_ready", "rawModelOutput": "must not leak"}],
            "fallbackRecoveries": [{
                "recoveryId": "explicit-experience-1",
                "recoveryType": "explicit_experience",
                "criterionType": "relevant_experience",
                "criterionName": "Accounts Payable Experience",
                "sourceIds": ["requirements-1"],
                "sourceTextHashes": ["hash"],
                "sourceText": "private JD text",
                "importance": "low",
            }],
            "evidenceSafety": {"removedSourceText": ["private JD text"]},
        },
    }

    safe = safe_api_output(output)
    response = GenerateCriteriaResponse(**safe, model="test")
    serialised = response.model_dump(exclude_none=True)
    criterion = serialised["criteria"][0]
    assert criterion["importance"] == "high"
    assert criterion["sourceIds"] == ["responsibilities-1"]
    assert criterion["groundingScores"] == [0.98]
    assert criterion["sourceCriterionIds"] == ["responsibilities-criterion-1"]
    assert criterion["mergedFromIds"] == ["criterion-1"]
    assert serialised["audit"]["deployment"]["imageTag"] == "v1.0.8"
    assert serialised["audit"]["fallbackRecoveries"][0]["sourceTextHashes"] == ["hash"]
    encoded = json.dumps(serialised)
    assert "must not leak" not in encoded
    assert "private JD text" not in encoded


def test_absent_optional_metadata_stays_absent():
    output = {
        "criteria": [{
            "criterionId": "criterion-1",
            "type": "relevant_skill",
            "name": "Process Data Analysis",
            "description": "description",
            "evidenceRule": "resume evidence",
            "sourceText": "Analyse process data.",
            "suggestedWeight": 100,
        }],
        "ignoredTexts": [],
        "warnings": [],
        "weightTotal": 100,
        "audit": {},
    }
    serialised = GenerateCriteriaResponse(
        **safe_api_output(output),
        model="test",
    ).model_dump(exclude_none=True)
    criterion = serialised["criteria"][0]
    for key in ("importance", "sourceIds", "groundingScores", "sourceCriterionIds", "mergedFromIds"):
        assert key not in criterion


def test_metadata_arrays_are_truncated_only_at_trailing_values():
    output = {
        "criteria": [{
            "criterionId": "criterion-1",
            "type": "relevant_skill",
            "name": "Process Data Analysis",
            "description": "description",
            "evidenceRule": "resume evidence",
            "sourceText": "First sentence. | Second sentence.",
            "sourceIds": ["r-1", "r-2", "stale"],
            "groundingScores": [0.9, 0.8, 0.1],
            "suggestedWeight": 100,
        }],
        "ignoredTexts": [],
        "warnings": [],
        "weightTotal": 100,
        "audit": {},
    }
    criterion = safe_api_output(output)["criteria"][0]
    assert criterion["sourceIds"] == ["r-1", "r-2"]
    assert criterion["groundingScores"] == [0.9, 0.8]


def test_runpod_handler_serializes_metadata_without_raw_audit(monkeypatch):
    from app import runpod_handler

    class FakeRuntime:
        ready = True

        def generate(self, _job, _request_id):
            return {
                "criteria": [{
                    "criterionId": "criterion-1",
                    "type": "relevant_skill",
                    "name": "Process Data Analysis",
                    "description": "description",
                    "evidenceRule": "resume evidence",
                    "sourceText": "Analyse process data.",
                    "sourceIds": ["responsibilities-1"],
                    "groundingScores": [1.0],
                    "sourceCriterionIds": ["r-criterion-1"],
                    "mergedFromIds": ["criterion-1"],
                    "importance": "high",
                    "suggestedWeight": 100,
                }],
                "ignoredTexts": [],
                "warnings": [],
                "weightTotal": 100,
                "audit": {
                    "deployment": {"imageTag": "v1.0.8"},
                    "debugTrace": [{"stage": "api_payload_ready", "rawModelOutput": "secret"}],
                    "fallbackRecoveries": [],
                    "evidenceSafety": {},
                },
            }

    monkeypatch.setattr(runpod_handler, "runtime", FakeRuntime())
    result = runpod_handler.handler({
        "id": "metadata-handler-test",
        "input": {
            "jobTitle": "Process Engineer",
            "department": "Engineering",
            "responsibilities": ["Analyse process data."],
            "requirements": [],
        },
    })
    assert result["status"] == "success"
    criterion = result["output"]["criteria"][0]
    assert criterion["importance"] == "high"
    assert criterion["sourceIds"] == ["responsibilities-1"]
    assert criterion["groundingScores"] == [1.0]
    encoded = json.dumps(result)
    assert "secret" not in encoded
