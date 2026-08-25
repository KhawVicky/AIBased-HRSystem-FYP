"""Focused regression tests for the remaining deterministic v1.0.8 fixes."""

from __future__ import annotations

import json

from app import frozen_pipeline
from app.explicit_requirement_recovery import (
    collapse_explicit_requirement_duplicates,
    consolidate_broad_specific_experience,
    recover_explicit_requirements,
)
from app.name_validation import CriterionNameValidationAdapter
from app.response_safety import safe_api_output


def test_mandatory_certification_is_not_recovered_as_preferred_scoring() -> None:
    criteria, recoveries, _ = recover_explicit_requirements(
        [], ["A valid First Aid certification is mandatory."]
    )

    assert not any(item["type"] == "preferred_certification" for item in criteria)
    assert not any(
        item.get("recoveryType") == "explicit_certification"
        for item in recoveries
    )


def test_new_observability_and_eligibility_are_allowlisted_without_raw_jd() -> None:
    safe = safe_api_output(
        {
            "criteria": [],
            "eligibilitySuggestions": {
                "minCGPA": 3.2,
                "minExperience": "5+ years",
                "educationLevel": "Bachelor Degree",
                "requiredLanguage": "English",
                "unexpected": "drop-me",
            },
            "audit": {
                "hardRequirements": {
                    "requirements": [
                        {
                            "kind": "minimum_experience",
                            "value": 5,
                            "sourceRef": "Q1",
                            "sourceId": "requirements-1",
                            "sourceHash": "abc123",
                            "sourceText": "private JD text",
                        }
                    ],
                    "exactValues": {"minExperience": 5},
                },
                "sourceAccounting": {
                    "valid": True,
                    "sources": [
                        {
                            "sourceRef": "Q1",
                            "sourceId": "requirements-1",
                            "sourceHash": "abc123",
                            "reason": "Central scoped experience.",
                            "processingOutcome": "criterion_contribution",
                            "mapped": True,
                            "hardRequirementKinds": [],
                            "generatedCriterionIds": ["criterion-1"],
                            "sourceText": "private JD text",
                        }
                    ],
                },
            },
        }
    )

    assert safe["eligibilitySuggestions"] == {
        "minCGPA": 3.2,
        "minExperience": "5+ years",
        "educationLevel": "Bachelor Degree",
        "requiredLanguage": "English",
        "requiredLocation": None,
        "enabledFilters": [],
    }
    assert safe["audit"]["hardRequirements"]["requirements"][0]["kind"] == (
        "minimum_experience"
    )
    assert safe["audit"]["sourceAccounting"]["sources"][0][
        "generatedCriterionIds"
    ] == ["criterion-1"]
    assert "private JD text" not in json.dumps(safe)


def test_named_standard_recovery_reconciles_a_cross_type_duplicate() -> None:
    source = "Knowledge of ISO 27001 is required."
    existing = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "ISO 27001 Knowledge",
        "sourceText": source,
        "sourceIds": ["requirements-1"],
        "sourceCriterionIds": ["requirements-criterion-1"],
        "groundingScores": [1.0],
    }

    criteria, recoveries, warnings = recover_explicit_requirements(
        [existing],
        [source],
    )

    assert len(criteria) == 1
    assert criteria[0]["type"] == "domain_knowledge"
    assert criteria[0]["name"] == "ISO 27001 Quality Standards"
    assert criteria[0]["sourceText"] == source
    assert criteria[0]["sourceIds"] == ["requirements-1"]
    assert criteria[0]["groundingScores"] == [1.0]
    assert set(criteria[0]["sourceCriterionIds"]) == {
        "requirements-criterion-1",
        "requirements-explicit-domain_knowledge-1",
    }
    assert recoveries[0]["reconciledFromType"] == "relevant_skill"
    assert recoveries[0]["reconciledFromName"] == "ISO 27001 Knowledge"
    assert warnings

    safe = safe_api_output(
        {
            "criteria": [],
            "audit": {"fallbackRecoveries": recoveries},
        }
    )
    assert safe["audit"]["fallbackRecoveries"][0]["reconciledFromType"] == (
        "relevant_skill"
    )


def test_different_named_standards_remain_separate() -> None:
    criteria, _, _ = recover_explicit_requirements(
        [],
        [
            "Knowledge of ISO 9001 is required.",
            "Knowledge of ISO 27001 is required.",
        ],
    )

    assert {item["name"] for item in criteria} == {
        "ISO 9001 Quality Standards",
        "ISO 27001 Quality Standards",
    }
    assert len(criteria) == 2


def test_education_field_recovery_covers_common_field_combinations() -> None:
    cases = {
        "A degree in Computer Science or Software Engineering is required.": (
            "Computing Education"
        ),
        "Diploma or Degree in Accounting, Finance or a related field is required.": (
            "Accounting and Finance Education"
        ),
        "Bachelor\u2019s Degree in Engineering, Materials Science or a related technical field.": (
            "Engineering Education"
        ),
        "Bachelor's Degree in Business Administration, Marketing or a related field.": (
            "Business and Marketing Education"
        ),
        "A Degree in Business Administration is required.": (
            "Business Administration Education"
        ),
    }

    for source, expected_name in cases.items():
        criteria, _, _ = recover_explicit_requirements([], [source])
        assert [item["name"] for item in criteria] == [expected_name]
        assert criteria[0]["type"] == "education_relevance"
        assert criteria[0]["sourceText"] == source


def test_education_level_without_field_is_not_recovered() -> None:
    criteria, _, _ = recover_explicit_requirements(
        [],
        ["Minimum STPM, Diploma or Degree."],
    )

    assert [item["name"] for item in criteria] == ["Education"]
    assert criteria[0]["type"] == "education_relevance"
    assert criteria[0]["sourceIds"] == ["requirements-1"]


def test_explicit_tool_system_requirement_is_a_skill_not_experience() -> None:
    source = (
        "Experience using a warehouse management system such as a leading "
        "cloud platform is preferred."
    )
    existing = {
        "criterionId": "criterion-1",
        "type": "relevant_experience",
        "name": "Warehouse Management System Experience",
        "sourceText": source,
        "sourceIds": ["requirements-1"],
        "sourceCriterionIds": ["requirements-criterion-1"],
        "groundingScores": [1.0],
    }

    criteria, recoveries, warnings = recover_explicit_requirements(
        [existing],
        [source],
    )

    assert len(criteria) == 1
    assert criteria[0]["type"] == "relevant_skill"
    assert criteria[0]["name"] == "Warehouse Management System"
    assert criteria[0]["sourceText"] == source
    assert recoveries[-1]["recoveryType"] == "explicit_tool_or_system"
    assert recoveries[-1]["reconciledFromType"] == "relevant_experience"
    assert warnings


def test_explicit_duplicate_collapse_requires_exact_type_and_evidence() -> None:
    source = "Diploma in Supply Chain Management."
    model = {
        "criterionId": "criterion-1",
        "type": "education_relevance",
        "name": "Supply Chain Diploma",
        "sourceText": source,
        "sourceIds": ["qualifications-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [0.97],
    }
    explicit = {
        "criterionId": "criterion-2",
        "type": "education_relevance",
        "name": "Supply Chain Management Education",
        "sourceText": source,
        "sourceIds": ["qualifications-1"],
        "sourceCriterionIds": [
            "qualifications-explicit-education_relevance-1"
        ],
        "groundingScores": [1.0],
    }

    criteria, warnings, audit = collapse_explicit_requirement_duplicates(
        [model, explicit]
    )

    assert len(criteria) == 1
    assert criteria[0]["name"] == "Supply Chain Management Education"
    assert set(criteria[0]["sourceCriterionIds"]) == {
        "responsibilities-criterion-1",
        "qualifications-explicit-education_relevance-1",
    }
    assert set(criteria[0]["mergedFromIds"]) == {
        "criterion-1",
        "criterion-2",
    }
    assert warnings
    assert len(audit) == 1


def _experience_criterion(
    criterion_id: str,
    name: str,
    source: str,
    source_id: str,
) -> dict:
    return {
        "criterionId": criterion_id,
        "type": "relevant_experience",
        "name": name,
        "sourceText": source,
        "sourceIds": [source_id],
        "sourceCriterionIds": [f"{source_id}-explicit"],
        "groundingScores": [1.0],
        "importance": "low",
    }


def test_broad_duration_and_preferred_delivery_experience_consolidate() -> None:
    broad = _experience_criterion(
        "criterion-1",
        "Service Development Experience",
        "Minimum 3 years of service development experience.",
        "requirements-1",
    )
    specific = _experience_criterion(
        "criterion-2",
        "Production Cloud Application Experience",
        "Experience delivering production cloud applications is preferred.",
        "requirements-2",
    )

    criteria, warnings, audit = consolidate_broad_specific_experience(
        [broad, specific]
    )

    assert len(criteria) == 1
    assert criteria[0]["name"] == "Production Cloud Application Experience"
    assert criteria[0]["sourceIds"] == ["requirements-1", "requirements-2"]
    assert criteria[0]["mergedFromIds"] == ["criterion-1", "criterion-2"]
    assert warnings
    assert len(audit) == 1


def test_preferred_industry_environment_experience_remains_separate() -> None:
    broad = _experience_criterion(
        "criterion-1",
        "People Operations Experience",
        "Minimum 5 years of people operations experience.",
        "requirements-1",
    )
    environment = _experience_criterion(
        "criterion-2",
        "Manufacturing Environment Experience",
        "Experience working in a manufacturing environment is preferred.",
        "requirements-2",
    )

    criteria, warnings, audit = consolidate_broad_specific_experience(
        [broad, environment]
    )

    assert len(criteria) == 2
    assert not warnings
    assert not audit


def _validate_name(name: str, source: str):
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


def test_name_repair_preserves_a_supported_domain_when_action_is_generic() -> None:
    source = (
        "Coordinate foreign-worker quotas, work permits, immigration documentation, "
        "hostel arrangements and transportation."
    )
    criteria, diagnostics = _validate_name("Recruitment Coordination", source)

    assert criteria
    assert criteria[0]["name"] == "Foreign Worker Coordination"
    assert criteria[0]["name"] != "Coordination"
    assert diagnostics["nameCorrections"]


def test_specific_supported_names_are_not_repaired() -> None:
    cases = [
        ("Foreign Worker Coordination", "Coordinate foreign worker permits."),
        ("Sales Pipeline Monitoring", "Monitor the sales pipeline."),
        ("Invoice Payment Processing", "Process invoice payments."),
        ("Quotation Preparation", "Prepare customer quotations."),
        ("Invoice Verification", "Verify supplier invoices."),
        ("Document Control", "Maintain document control records."),
    ]

    for name, source in cases:
        criteria, diagnostics = _validate_name(name, source)
        assert criteria
        assert criteria[0]["name"] == name
        assert diagnostics.get("nameCorrections", []) == []


def test_generic_repaired_name_is_rejected_when_no_specific_evidence_exists() -> None:
    criteria, diagnostics = _validate_name("Coordination", "the")

    assert criteria == []
    assert any("generic name" in warning for warning in diagnostics["warnings"])
