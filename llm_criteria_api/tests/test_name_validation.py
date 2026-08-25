from __future__ import annotations

import json
from types import SimpleNamespace

from app import frozen_pipeline
from app.name_validation import CriterionNameValidationAdapter
from app.pipeline import CriteriaPipeline


def _validate(name: str, source: str):
    adapter = CriterionNameValidationAdapter(frozen_pipeline)
    return adapter.validate(
        frozen_pipeline.validate_section_output,
        json.dumps(
            {
                "criteria": [
                    {
                        "type": "relevant_skill",
                        "name": name,
                        "sourceText": source,
                    }
                ]
            }
        ),
        [source],
        "responsibilities",
    )


def test_morphological_variants_are_supported():
    adapter = CriterionNameValidationAdapter(frozen_pipeline)
    assert adapter.normalised_detector(
        "Employee Record Monitoring", "Monitor employee records"
    ) == []
    assert adapter.normalised_detector(
        "Policy Compliance", "Comply with company policies"
    ) == []
    assert adapter.normalised_detector(
        "Employee Management", "Manage employee records"
    ) == []
    assert adapter.normalised_detector(
        "Staff Supervision", "Supervise staff"
    ) == []


def test_supported_morphological_names_are_not_changed():
    criteria, diagnostics = _validate(
        "Employee Management",
        "Manage employee records",
    )
    assert criteria[0]["name"] == "Employee Management"
    assert diagnostics.get("nameCorrections", []) == []


def test_unsupported_name_is_repaired_using_grounded_evidence():
    criteria, diagnostics = _validate(
        "Employee Welfare Astrophysics",
        "Manage employee welfare",
    )
    assert criteria[0]["name"] == "Employee Welfare Management"
    assert criteria[0]["sourceText"] == "Manage employee welfare"
    assert diagnostics["nameCorrections"]
    assert "Employee Welfare" in diagnostics["nameCorrections"][0]


def test_genuinely_unsupported_name_is_still_rejected():
    criteria, diagnostics = _validate(
        "Quantum Physics",
        "the",
    )
    assert criteria == []
    assert any("unsupported concepts" in warning for warning in diagnostics["warnings"])


class _CachedLoader:
    def __init__(self, outputs: list[str]) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._outputs = iter(outputs)

    def raw_output_generator(self, _messages: list[dict[str, str]]) -> str:
        return next(self._outputs)


def test_pipeline_uses_name_adapter_without_changing_grounded_evidence():
    result = CriteriaPipeline(
        _CachedLoader(
            [
                json.dumps(
                    {
                        "criteria": [
                            {
                                "type": "relevant_skill",
                                "name": "Employee Record Monitoring",
                                "sourceText": "Monitor employee records",
                            }
                        ]
                    }
                ),
                '{"criteria": []}',
            ]
        )
    ).generate(
        {
            "jobTitle": "HR Executive",
            "department": "Human Resources",
            "responsibilities": ["Monitor employee records"],
            "requirements": [],
        }
    )
    assert result["criteria"][0]["name"] == "Employee Record Monitoring"
    assert result["criteria"][0]["sourceText"] == "Monitor employee records"


def test_multisentence_fallback_keeps_the_main_capability_and_all_evidence():
    first = "Handle foreign worker recruitment and manpower sourcing."
    second = (
        "Arrange permits, immigration matters, hostel, facilities, "
        "transportation and departure arrangements."
    )
    result = CriteriaPipeline(
        _CachedLoader(
            [
                json.dumps(
                    {
                        "criteria": [
                            {
                                "type": "relevant_skill",
                                "name": "Foreign Worker Facilities Management Oversight",
                                "sourceText": second,
                            }
                        ]
                    }
                ),
            ]
        )
    ).generate(
        {
            "jobTitle": "HR Manager",
            "department": "Human Resource",
            "responsibilities": [first, second],
            "requirements": [],
        }
    )

    assert len(result["criteria"]) == 1
    criterion = result["criteria"][0]
    assert criterion["name"] == "Foreign Worker Management"
    assert criterion["sourceText"] == f"{first} | {second}"
    assert criterion["sourceIds"] == ["responsibilities-1", "responsibilities-2"]
    assert criterion["groundingScores"] == [1.0, 1.0]
