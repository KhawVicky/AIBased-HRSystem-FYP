"""Regression tests for the audit-only Gold Standard evaluator v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path


BENCHMARK_ROOT = Path(__file__).parents[1] / "benchmarks" / "gold_standard_v1"
sys.path.insert(0, str(BENCHMARK_ROOT))

from benchmark_schema import evaluate_run, load_fixtures, match_actual_criteria  # noqa: E402
from stage_attribution import build_stage_attribution  # noqa: E402


FIXTURES = {item["benchmarkId"]: item for item in load_fixtures(BENCHMARK_ROOT / "fixtures")}


def _run(benchmark_id: str, criteria: list[dict]) -> dict:
    return {
        "benchmarkId": benchmark_id,
        "runNumber": 99,
        "criteria": criteria,
        "eligibilitySuggestions": {},
        "audit": {"debugTrace": []},
    }


def _criterion(name: str, criterion_type: str, evidence: list[str], weight: int = 20) -> dict:
    return {"id": f"test-{name.casefold().replace(' ', '-')}", "name": name, "type": criterion_type, "jdEvidence": evidence, "weight": weight}


def test_payment_runs_is_a_supplier_payment_semantic_match() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    actual = _criterion("Payment Runs", "relevant_skill", [fixture["referenceJd"]["responsibilities"][4]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert any(item["expected"]["benchmarkCriterionId"] == "C" for item in result["matchedCriteria"])
    assert not result["unexpectedCriteria"]


def test_e_invoice_wrong_type_is_not_unexpected() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    actual = _criterion("E Invoice", "relevant_skill", [fixture["referenceJd"]["responsibilities"][7]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert any(item["expected"]["benchmarkCriterionId"] == "H" for item in result["matchedCriteria"])
    assert len(result["typeErrors"]) == 1
    assert not result["unexpectedCriteria"]


def test_accounts_payable_invoice_and_matching_are_a_wrong_split() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    responsibilities = fixture["referenceJd"]["responsibilities"]
    actual = [
        _criterion("Invoice Processing", "relevant_skill", [responsibilities[0]["text"]], 18),
        _criterion("Three-Way Matching", "relevant_skill", [responsibilities[1]["text"]], 12),
    ]
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], actual))
    assert result["wrongSplits"]
    assert result["wrongSplits"][0]["expected"]["benchmarkCriterionId"] == "A"
    assert not result["unexpectedCriteria"]
    assert {item["actual"]["name"] for item in result["splitFragments"]} == {"Three-Way Matching"}


def test_sales_pipeline_and_crm_are_a_wrong_split() -> None:
    fixture = FIXTURES["sales-executive-001"]
    responsibilities = fixture["referenceJd"]["responsibilities"]
    actual = [
        _criterion("Sales Pipeline Monitoring", "relevant_skill", [responsibilities[6]["text"]]),
        _criterion("CRM System", "relevant_skill", [responsibilities[5]["text"]]),
    ]
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], actual))
    assert any(group["expected"]["benchmarkCriterionId"] == "D" for group in result["wrongSplits"])
    assert not result["unexpectedCriteria"]


def test_software_testing_and_troubleshooting_are_a_wrong_split() -> None:
    fixture = FIXTURES["software-engineer-001"]
    responsibilities = fixture["referenceJd"]["responsibilities"]
    actual = [
        _criterion("Testing and Reviews", "relevant_skill", [responsibilities[4]["text"]]),
        _criterion("Troubleshooting and Performance", "relevant_skill", [responsibilities[5]["text"]]),
    ]
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], actual))
    assert any(group["expected"]["benchmarkCriterionId"] == "D" for group in result["wrongSplits"])
    assert not result["unexpectedCriteria"]


def test_market_research_is_partial_new_business_evidence_not_full() -> None:
    fixture = FIXTURES["sales-executive-001"]
    actual = _criterion("Market Research", "relevant_skill", [fixture["referenceJd"]["responsibilities"][7]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert any(item["expected"]["benchmarkCriterionId"] == "A" for item in result["partialMatches"])
    assert not any(item["expected"]["benchmarkCriterionId"] == "A" for item in result["matchedCriteria"])


def test_product_presentation_name_quality_is_separate_from_semantic_match() -> None:
    fixture = FIXTURES["sales-executive-001"]
    actual = _criterion("Product Presentation", "relevant_skill", [fixture["referenceJd"]["responsibilities"][4]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    match = next(item for item in result["matchedCriteria"] if item["expected"]["benchmarkCriterionId"] == "B")
    assert match["nameQuality"]["status"] == "misleading_focus"


def test_minimum_experience_name_is_sentence_copy_but_not_rejected() -> None:
    fixture = FIXTURES["qa-engineer-001"]
    actual = _criterion(
        "Minimum 2 Years of Quality-assurance Experience in a Manufacturing Environment",
        "relevant_experience",
        [fixture["referenceJd"]["requirements"][1]["text"]],
        32,
    )
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    match = next(item for item in result["matchedCriteria"] if item["expected"]["benchmarkCriterionId"] == "G")
    assert match["nameQuality"]["status"] == "sentence_copy"
    assert not result["unexpectedCriteria"]


def test_coordination_is_overly_generic_but_semantically_related() -> None:
    fixture = FIXTURES["hr-manager-001"]
    actual = _criterion("Coordination", "relevant_skill", [fixture["referenceJd"]["responsibilities"][3]["text"]], 79)
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert result["partialMatches"]
    assert result["partialMatches"][0]["nameQuality"]["status"] == "overly_generic"
    assert not result["unexpectedCriteria"]


def test_priority_is_not_assessable_when_hr_core_recall_is_zero() -> None:
    fixture = FIXTURES["hr-manager-001"]
    actual = _criterion("Coordination", "relevant_skill", [fixture["referenceJd"]["responsibilities"][3]["text"]], 79)
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert result["priorityOrdering"]["status"] == "not_assessable"
    assert result["priorityOrderingPass"] is False


def test_metadata_absence_is_not_alignment_success() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    actual = _criterion("Payment Runs", "relevant_skill", [fixture["referenceJd"]["responsibilities"][4]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert result["metadataPresence"]["fields"]["sourceIds"] == "absent"
    assert result["metadataPresencePass"] is False
    assert result["metadataAlignment"]["fields"]["sourceIds"] == "not_applicable"
    assert result["metadataAlignmentPass"] is False


def test_specific_jd_supported_additional_criterion_is_not_unexpected() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    actual = _criterion("General Ledger", "relevant_skill", [fixture["referenceJd"]["responsibilities"][2]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert [item["actual"]["name"] for item in result["allowedAdditionalCriteria"]] == ["General Ledger"]
    assert not result["unexpectedCriteria"]


def test_forbidden_office_support_remains_forbidden_not_allowed_additional() -> None:
    fixture = FIXTURES["administrative-executive-001"]
    actual = _criterion("Office Operations Support", "relevant_skill", [fixture["referenceJd"]["responsibilities"][7]["text"]])
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], [actual]))
    assert result["forbiddenCriteria"]
    assert not result["allowedAdditionalCriteria"]
    assert not result["unexpectedCriteria"]


def test_same_type_wrong_split_preserves_all_source_evidence() -> None:
    fixture = FIXTURES["administrative-executive-001"]
    responsibilities = fixture["referenceJd"]["responsibilities"]
    actual = [
        _criterion("Supplier Management", "relevant_skill", [responsibilities[4]["text"]]),
        _criterion("Monitoring", "relevant_skill", [responsibilities[5]["text"]]),
    ]
    result = evaluate_run(fixture, _run(fixture["benchmarkId"], actual))
    group = next(item for item in result["wrongSplits"] if item["expected"]["benchmarkCriterionId"] == "D")
    evidence = group["primary"]["actual"]["jdEvidence"] + group["fragments"][0]["actual"]["jdEvidence"]
    assert len(evidence) == 2


def test_stage_attribution_records_metadata_before_final_response() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    raw_path = BENCHMARK_ROOT / "results" / "baseline-v1.0.7-20260806-1524" / "raw" / "accounts-payable-executive-001" / "run-1.json"
    run = json.loads(raw_path.read_text(encoding="utf-8"))
    evaluation = evaluate_run(fixture, run)
    stage = build_stage_attribution(fixture, run, evaluation)
    source_lifecycle = stage["fieldLifecycle"]["sourceIds"]
    assert source_lifecycle["firstPresentStage"] == "multi_sentence_grounding:responsibilities"
    assert source_lifecycle["lossStage"] == "api_serialization -> final_response"
    assert stage["fieldLifecycle"]["importance"]["cause"] == "inconclusive"


def test_requirement_coverage_marks_missing_ap_requirements_uncovered() -> None:
    fixture = FIXTURES["accounts-payable-executive-001"]
    raw_path = BENCHMARK_ROOT / "results" / "baseline-v1.0.7-20260806-1524" / "raw" / "accounts-payable-executive-001" / "run-1.json"
    run = json.loads(raw_path.read_text(encoding="utf-8"))
    evaluation = evaluate_run(fixture, run)
    stage = build_stage_attribution(fixture, run, evaluation)
    by_source = {item["sourceId"]: item for item in stage["requirementsCoverage"]}
    assert by_source["Q1"]["category"] == "education"
    assert by_source["Q2"]["category"] == "minimum_experience"
    assert by_source["Q3"]["category"] == "named_tool_or_platform"
    assert by_source["Q1"]["status"] == "uncovered"


def test_saved_fixture_has_18_raw_records_and_expected_hashable_shape() -> None:
    raw_root = BENCHMARK_ROOT / "results" / "baseline-v1.0.7-20260806-1524" / "raw"
    files = sorted(raw_root.glob("*/*.json"))
    assert len(files) == 18
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["criteria"]
        assert payload["audit"]["debugTrace"]
