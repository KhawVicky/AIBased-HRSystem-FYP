"""Run the audit-only Gold Standard evaluator against immutable raw results."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark_schema import evaluate_directory, load_fixtures
from stage_attribution import (
    build_stage_attribution,
    build_stage_attribution_report,
    markdown_stage_report,
    sha256_raw_files,
)


def _criterion_summary(item: dict[str, Any]) -> dict[str, Any]:
    actual = item.get("actual", item.get("criterion", item))
    evidence = actual.get("jdEvidence", actual.get("sourceText", []))
    if not isinstance(evidence, list):
        evidence = [str(evidence)] if evidence else []
    return {
        "id": actual.get("id", actual.get("criterionId")),
        "type": actual.get("type", actual.get("category")),
        "name": actual.get("name", ""),
        "importance": actual.get("importance"),
        "weight": actual.get("weight", actual.get("suggestedWeight")),
        "evidence": evidence,
        "sourceIds": actual.get("sourceIds", []),
        "groundingScores": actual.get("groundingScores", []),
        "inferredSourceIds": item.get("inferredSourceIds", []),
    }


def _eligibility_check(fixture: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    expected = fixture.get("expectedEligibility", {})
    actual = run.get("eligibilitySuggestions", {})
    if not isinstance(actual, dict):
        actual = {}
    checks = {}
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        checks[key] = {
            "expected": expected_value,
            "actual": actual_value,
            "pass": bool(actual_value) and str(expected_value).casefold() in str(actual_value).casefold(),
        }
    return {
        "checks": checks,
        "pass": all(item["pass"] for item in checks.values()) if checks else True,
        "note": "Eligibility is reported separately and is not included in the soft-criteria diagnostic score.",
    }


def _run_notes(evaluation: dict[str, Any]) -> list[str]:
    notes = []
    for key, label in (
        ("missingExpectedCriteria", "missing full expected criteria"),
        ("partialMatches", "partial expected coverage"),
        ("unexpectedCriteria", "truly unexpected criteria"),
        ("allowedAdditionalCriteria", "allowed additional criteria"),
        ("forbiddenCriteria", "must-not-generate criteria"),
        ("evidenceContamination", "evidence contamination"),
        ("wrongMerges", "wrong merges"),
        ("wrongSplits", "wrong splits"),
        ("typeErrors", "type errors"),
    ):
        if evaluation.get(key):
            notes.append(f"{label}: {len(evaluation[key])}")
    if not evaluation.get("weightTotalPass"):
        notes.append("weight total failed")
    if not evaluation.get("metadataPresencePass"):
        notes.append("enhanced metadata presence failed")
    if not evaluation.get("metadataAlignmentPass"):
        notes.append("metadata alignment not applicable or failed")
    if not evaluation.get("pipelineTracePass"):
        notes.append("pipeline trace failed")
    return notes


def _stability(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    by_benchmark: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evaluations:
        by_benchmark[item["benchmarkId"]].append(item)
    result = {}
    for benchmark_id, items in sorted(by_benchmark.items()):
        criterion_sets = [
            tuple(sorted(match["expected"]["benchmarkCriterionId"] for match in item["matchedCriteria"]))
            for item in items
        ]
        core_sets = [
            tuple(sorted(match["expected"]["benchmarkCriterionId"] for match in item["matchedCriteria"] if match["expected"].get("expectedPriority") == "core"))
            for item in items
        ]
        type_sets = [
            tuple(sorted((match["expected"]["benchmarkCriterionId"], match["actual"].get("type", match["actual"].get("category"))) for match in item["matchedCriteria"]))
            for item in items
        ]
        weights_by_expected: dict[str, list[float]] = defaultdict(list)
        for item in items:
            for match in item["matchedCriteria"]:
                value = match["actual"].get("weight", match["actual"].get("suggestedWeight"))
                if isinstance(value, (int, float)):
                    weights_by_expected[match["expected"]["benchmarkCriterionId"]].append(float(value))
        result[benchmark_id] = {
            "runCount": len(items),
            "criterionCountRange": [
                min(len(item.get("matchedCriteria", [])) + len(item.get("partialMatches", [])) + len(item.get("unexpectedCriteria", [])) for item in items),
                max(len(item.get("matchedCriteria", [])) + len(item.get("partialMatches", [])) + len(item.get("unexpectedCriteria", [])) for item in items),
            ],
            "expectedMatchedCriterionConsistency": len(set(criterion_sets)) == 1,
            "coreCriterionConsistency": len(set(core_sets)) == 1,
            "typeConsistency": len(set(type_sets)) == 1,
            "weightStandardDeviation": {
                key: round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0
                for key, values in weights_by_expected.items()
            },
            "priorityStatuses": sorted({item["priorityOrdering"]["status"] for item in items}),
        }
    return result


def build_report(
    results_dir: Path,
    fixtures_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Evaluate ``results_dir`` and write evaluated files to ``output_dir``.

    ``results_dir`` remains the immutable source.  The caller can point
    ``output_dir`` at a new evaluator-version directory so the original
    evaluated files are not overwritten.
    """
    output_dir = output_dir or results_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    fixtures = {item["benchmarkId"]: item for item in load_fixtures(fixtures_dir)}
    evaluated = evaluate_directory(results_dir, fixtures_dir)
    enriched: list[dict[str, Any]] = []
    evaluated_root = output_dir / "evaluated"
    for evaluation in evaluated["evaluations"]:
        raw_path = Path(evaluation["sourceFile"])
        with raw_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        evaluation["eligibilityCheck"] = _eligibility_check(fixtures[evaluation["benchmarkId"]], raw)
        stage = build_stage_attribution(fixtures[evaluation["benchmarkId"]], raw, evaluation)
        evaluation["requirementsCoverage"] = stage["requirementsCoverage"]
        evaluation["missingCoreAttribution"] = stage["missingCoreAttribution"]
        evaluation["fieldLifecycleSummary"] = {
            field: {
                "firstPresentStage": item.get("firstPresentStage"),
                "lossStage": item.get("lossStage"),
                "cause": item.get("cause"),
            }
            for field, item in stage["fieldLifecycle"].items()
        }
        evaluation["notes"] = _run_notes(evaluation)
        evaluation_path = evaluated_root / evaluation["benchmarkId"] / f"run-{evaluation['runNumber']}.json"
        evaluation_path.parent.mkdir(parents=True, exist_ok=True)
        with evaluation_path.open("w", encoding="utf-8") as handle:
            json.dump(evaluation, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        enriched.append(evaluation)

    scores = [item["totalDiagnosticScore"] for item in enriched]
    metrics = [item["metrics"] for item in enriched]
    priority_counts = defaultdict(int)
    for item in enriched:
        priority_counts[item["priorityOrdering"]["status"]] += 1
    summary = {
        "averageTotalScore": round(statistics.mean(scores), 2) if scores else 0.0,
        "averageCoreCriterionRecall": round(statistics.mean(item["coreCriterionRecall"] for item in metrics), 4) if metrics else 0.0,
        "averageExpectedCriterionRecall": round(statistics.mean(item["expectedCriterionRecall"] for item in metrics), 4) if metrics else 0.0,
        "averageCriterionPrecision": round(statistics.mean(item["criterionPrecision"] for item in metrics), 4) if metrics else 0.0,
        "averageSemanticCriterionPrecision": round(statistics.mean(item["semanticCriterionPrecision"] for item in metrics), 4) if metrics else 0.0,
        "averageTypeAccuracy": round(statistics.mean(item["typeAccuracy"] for item in metrics), 4) if metrics else 0.0,
        "totalPartialMatches": sum(item["partialCriterionCount"] for item in metrics),
        "totalTypeErrors": sum(len(item.get("typeErrors", [])) for item in enriched),
        "totalUnexpectedCriteria": sum(item["unexpectedCriterionCount"] for item in metrics),
        "totalAllowedAdditionalCriteria": sum(item["allowedAdditionalCriterionCount"] for item in metrics),
        "totalEvidenceContaminationCases": sum(item["evidenceContaminationCount"] for item in metrics),
        "totalWrongMerges": sum(item["wrongMergeCount"] for item in metrics),
        "totalWrongSplits": sum(item["wrongSplitCount"] for item in metrics),
        "totalGenericCriteria": sum(len(item.get("genericCriteria", [])) for item in enriched),
        "overlyGenericNameCount": sum(item["overlyGenericNameCount"] for item in metrics),
        "sentenceCopyNameCount": sum(item["sentenceCopyNameCount"] for item in metrics),
        "misleadingNameCount": sum(item["misleadingNameCount"] for item in metrics),
        "weightTotalPassCount": sum(item["weightTotalPass"] for item in metrics),
        "metadataPresencePassCount": sum(item["metadataPresencePass"] for item in metrics),
        "metadataAlignmentPassCount": sum(item["metadataAlignmentPass"] for item in metrics),
        "metadataAlignmentNotApplicableCount": sum(item["metadataAlignment"]["status"] == "not_applicable" for item in enriched),
        "eligibilityPassCount": sum(item["eligibilityCheck"]["pass"] for item in enriched),
        "priorityOrderingStatusCounts": dict(priority_counts),
    }
    deployment = {
        "endpoint": "https://hr-api-production-b5d3.up.railway.app/api.php?route=jd-criteria-llm",
        "runDate": None,
        "totalSuccessfulRequests": None,
        "totalFailedRequests": None,
    }
    summary_path = results_dir / "run_summary.json"
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as handle:
            run_summary = json.load(handle)
        deployment.update(run_summary)
        deployment["totalSuccessfulRequests"] = run_summary.get("successfulRequests", run_summary.get("totalSuccessfulRequests"))
        deployment["totalFailedRequests"] = run_summary.get("failedRequests", run_summary.get("totalFailedRequests"))
    for evaluation in enriched:
        source_path = Path(evaluation["sourceFile"])
        with source_path.open("r", encoding="utf-8") as handle:
            run = json.load(handle)
        recorded = run.get("deployment") or run.get("audit", {}).get("deployment", {})
        if isinstance(recorded, dict) and recorded:
            deployment.update(recorded)
            break
    return {
        "reportVersion": "gold_standard_evaluator_v2",
        "evaluatorVersion": "semantic-match-stage-attribution-v2",
        "fixtureVersion": "gold_standard_v1",
        "evaluationTimestamp": datetime.now(timezone.utc).isoformat(),
        "rawResultDirectory": str(results_dir / "raw"),
        "evaluatedResultDirectory": str(output_dir / "evaluated"),
        "rawFileHashes": sha256_raw_files(results_dir / "raw"),
        "deployment": deployment,
        "overallSummary": summary,
        "evaluations": enriched,
        "stability": _stability(enriched),
        "baselineDecision": "measured diagnostic only; no automatic production quality claim",
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Gold Standard Baseline Report (Evaluator v2)",
        "",
        "The original raw production responses are immutable. This report only changes deterministic evaluation.",
        "",
        f"- Raw result directory: `{report['rawResultDirectory']}`",
        f"- Evaluated result directory: `{report['evaluatedResultDirectory']}`",
        f"- Evaluator version: `{report['evaluatorVersion']}`",
        f"- Raw file hash count: `{len(report['rawFileHashes'])}`",
        f"- Pipeline version: `{report['deployment'].get('pipelineVersion')}`",
        f"- Image tag: `{report['deployment'].get('imageTag')}`",
        f"- Git commit hash: `{report['deployment'].get('gitCommitHash')}`",
        "",
        "## Overall Summary",
        "",
    ]
    for key, value in report["overallSummary"].items():
        lines.append(f"- {key}: `{value}`")
    for evaluation in report["evaluations"]:
        lines.extend(["", f"## {evaluation['benchmarkId']} Run {evaluation.get('runNumber')}", ""])
        lines.append(f"- Diagnostic score: `{evaluation['totalDiagnosticScore']}/100`")
        lines.append(f"- Priority ordering: `{evaluation['priorityOrdering']['status']}` ({evaluation['priorityOrdering']['reason']})")
        lines.append(f"- Notes: `{'; '.join(evaluation.get('notes', [])) or 'none'}`")
        lines.append("")
        lines.append("| Criterion | Type | Weight | Match | Name quality | Inferred source IDs |")
        lines.append("|---|---|---:|---|---|---|")
        for match in evaluation["matchedCriteria"] + evaluation.get("partialMatches", []):
            actual = _criterion_summary(match)
            lines.append(
                f"| {actual['name']} | {actual['type']} | {actual['weight']} | {match['classification']} / {match['typeStatus']} | {match['nameQuality']['status']} | {', '.join(actual['inferredSourceIds'])} |"
            )
        for item in evaluation.get("allowedAdditionalCriteria", []):
            actual = _criterion_summary(item)
            lines.append(f"| {actual['name']} | {actual['type']} | {actual['weight']} | allowed_additional | {item['nameQuality']['status']} | {', '.join(actual['inferredSourceIds'])} |")
        for item in evaluation.get("unexpectedCriteria", []):
            actual = _criterion_summary(item)
            lines.append(f"| {actual['name']} | {actual['type']} | {actual['weight']} | truly_unexpected | {item['nameQuality']['status']} | {', '.join(actual['inferredSourceIds'])} |")
        lines.extend([
            "",
            f"- Partial expected criteria: `{', '.join(item['benchmarkCriterionId'] for item in evaluation.get('partialExpectedCriteria', [])) or 'none'}`",
            f"- Missing core criteria with no meaningful candidate: `{', '.join(item['benchmarkCriterionId'] for item in evaluation['missingCoreCriteria']) or 'none'}`",
            f"- Wrong splits: `{len(evaluation.get('wrongSplits', []))}`",
            f"- Type errors: `{len(evaluation.get('typeErrors', []))}`",
            f"- Metadata presence: `{evaluation['metadataPresence']['fields']}`",
            f"- Metadata alignment: `{evaluation['metadataAlignment']['fields']}`",
            f"- Requirements coverage rows: `{len(evaluation.get('requirementsCoverage', []))}`",
        ])
    lines.extend(["", "## Baseline Decision", "", report["baselineDecision"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True, help="immutable directory containing raw/")
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory for evaluator output")
    parser.add_argument("--fixtures-dir", type=Path, default=Path(__file__).parent / "fixtures")
    args = parser.parse_args()
    report = build_report(args.results_dir, args.fixtures_dir, args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "baseline_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "baseline_report.md").write_text(markdown_report(report), encoding="utf-8")
    stage_report = build_stage_attribution_report(args.results_dir, args.fixtures_dir, report["evaluations"])
    (args.output_dir / "stage_attribution_report.json").write_text(json.dumps(stage_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "stage_attribution_report.md").write_text(markdown_stage_report(stage_report), encoding="utf-8")
    print(json.dumps({
        "resultsDir": str(args.results_dir),
        "outputDir": str(args.output_dir),
        "runCount": report["overallSummary"].get("totalSuccessfulRequests", report["deployment"].get("totalSuccessfulRequests")),
        "evaluatedRuns": len(report["evaluations"]),
        "summary": report["overallSummary"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
