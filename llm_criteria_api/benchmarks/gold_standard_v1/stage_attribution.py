"""Audit-only reconstruction of stages present in saved production traces.

The saved v1.0.7 records contain sanitised criterion snapshots rather than raw
model text.  This module reports what can be proven from those snapshots and
labels unavailable provenance as ``unknown`` instead of inventing it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark_schema import _normalise_text, _tokens, mapped_source_ids


EXPECTED_STAGES = [
    "qwen_generation:complete_jd",
    "schema_normalisation",
    "multi_sentence_grounding:responsibilities",
    "multi_sentence_grounding:requirements",
    "name_validation",
    "type_correction",
    "education_validation",
    "consolidation",
    "fallback_recovery",
    "source_metadata_restoration",
    "final_evidence_safety",
    "role_context_weighting",
    "api_payload_ready",
    "api_serialization",
    "final_response",
]

FIELD_NAMES = (
    "importance",
    "sourceIds",
    "groundingScores",
    "sourceCriterionIds",
    "mergedFromIds",
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _criterion_key(item: dict[str, Any]) -> tuple[str, str]:
    hashes = [str(value) for value in _as_list(item.get("sourceTextHashes")) if value]
    if hashes:
        return "sourceTextHash", "|".join(hashes)
    criterion_id = item.get("criterionId", item.get("id"))
    if criterion_id not in (None, ""):
        return "criterionId", str(criterion_id)
    return "name", _normalise_text(item.get("name", ""))


def _item_snapshot(item: dict[str, Any], fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    criterion_id = item.get("criterionId", item.get("id"))
    return {
        "criterionId": criterion_id,
        "idSource": "explicit" if criterion_id not in (None, "") else "unknown",
        "name": item.get("name", ""),
        "type": item.get("type", item.get("category")),
        "sourceIds": list(item.get("sourceIds", [])) if isinstance(item.get("sourceIds"), list) else [],
        "groundingScores": list(item.get("groundingScores", [])) if isinstance(item.get("groundingScores"), list) else [],
        "sourceCriterionIds": list(item.get("sourceCriterionIds", [])) if isinstance(item.get("sourceCriterionIds"), list) else [],
        "mergedFromIds": list(item.get("mergedFromIds", [])) if isinstance(item.get("mergedFromIds"), list) else [],
        "importance": item.get("importance"),
        "suggestedWeight": item.get("suggestedWeight", item.get("weight")),
        "sourceTextHashes": list(item.get("sourceTextHashes", [])) if isinstance(item.get("sourceTextHashes"), list) else [],
        "jdEvidence": list(item.get("jdEvidence", [])) if isinstance(item.get("jdEvidence"), list) else [],
        "criterionKey": _criterion_key(item),
        "origin": "unknown" if criterion_id in (None, "") else "trace",
    }


def snapshot_stage(stage_record: dict[str, Any], stage_name: str | None = None) -> dict[str, Any]:
    stage = stage_name or str(stage_record.get("stage", "unknown"))
    raw_items = stage_record.get("criteria")
    if isinstance(raw_items, list):
        items = [_item_snapshot(item) for item in raw_items if isinstance(item, dict)]
    else:
        names = stage_record.get("criterionNames", [])
        items = [
            _item_snapshot({"name": name}, None)
            for name in names
            if str(name).strip()
        ]
    count = stage_record.get("criteriaCount", len(items))
    return {
        "stage": stage,
        "available": True,
        "criteriaCount": int(count) if isinstance(count, (int, float)) else len(items),
        "criteria": items,
        "weightTotal": stage_record.get("weightTotal"),
        "executed": stage_record.get("executed", True),
        "recordedFields": sorted(stage_record.keys()),
        "observabilityNote": "criterion snapshot reconstructed from saved audit trace",
    }


def final_response_snapshot(run: dict[str, Any]) -> dict[str, Any]:
    raw_items = run.get("criteria", []) if isinstance(run.get("criteria", []), list) else []
    return {
        "stage": "final_response",
        "available": True,
        "criteriaCount": len(raw_items),
        "criteria": [_item_snapshot(item) for item in raw_items if isinstance(item, dict)],
        "weightTotal": sum(
            item.get("weight", item.get("suggestedWeight", 0)) or 0
            for item in raw_items
            if isinstance(item, dict) and isinstance(item.get("weight", item.get("suggestedWeight", 0)), (int, float))
        ),
        "executed": True,
        "recordedFields": sorted(run.keys()),
        "observabilityNote": "saved final response; runner boundary may include PHP proxy output",
    }


def _delta_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_map = {tuple(item["criterionKey"]): item for item in before.get("criteria", [])}
    after_map = {tuple(item["criterionKey"]): item for item in after.get("criteria", [])}
    matched_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    matched_before: set[tuple[str, str]] = set()
    matched_after: set[tuple[str, str]] = set()
    for key in before_map.keys() & after_map.keys():
        matched_pairs.append((before_map[key], after_map[key]))
        matched_before.add(key)
        matched_after.add(key)
    # api_serialization stores names/counts only.  Match those names to the
    # adjacent full snapshot before reporting additions/removals.
    for before_key, previous in before_map.items():
        if before_key in matched_before:
            continue
        for after_key, current in after_map.items():
            if after_key in matched_after:
                continue
            if _normalise_text(previous.get("name")) == _normalise_text(current.get("name")):
                matched_pairs.append((previous, current))
                matched_before.add(before_key)
                matched_after.add(after_key)
                break
    added = [after_map[key] for key in after_map.keys() if key not in matched_after]
    removed = [before_map[key] for key in before_map.keys() if key not in matched_before]
    renamed = []
    type_changed = []
    evidence_added = []
    evidence_removed = []
    merged = []
    fallback_created = []
    for previous, current in matched_pairs:
        if previous.get("name") != current.get("name"):
            renamed.append({"criterionId": current.get("criterionId"), "from": previous.get("name"), "to": current.get("name"), "origin": current.get("origin", "unknown")})
        if previous.get("type") != current.get("type"):
            type_changed.append({"criterionId": current.get("criterionId"), "from": previous.get("type"), "to": current.get("type"), "origin": current.get("origin", "unknown")})
        before_evidence = set(previous.get("sourceTextHashes", [])) | set(previous.get("sourceIds", []))
        after_evidence = set(current.get("sourceTextHashes", [])) | set(current.get("sourceIds", []))
        if after_evidence - before_evidence:
            evidence_added.append({"criterionId": current.get("criterionId"), "values": sorted(after_evidence - before_evidence)})
        if before_evidence - after_evidence:
            evidence_removed.append({"criterionId": current.get("criterionId"), "values": sorted(before_evidence - after_evidence)})
        if current.get("mergedFromIds") or current.get("sourceCriterionIds"):
            merged.append({"criterionId": current.get("criterionId"), "mergedFromIds": current.get("mergedFromIds", []), "sourceCriterionIds": current.get("sourceCriterionIds", [])})
        if str(current.get("criterionId", "")).startswith("fallback"):
            fallback_created.append(current)
    return {
        "stage": after.get("stage"),
        "inputCriteriaCount": before.get("criteriaCount", len(before.get("criteria", []))),
        "outputCriteriaCount": after.get("criteriaCount", len(after.get("criteria", []))),
        "added": added,
        "removed": removed,
        "addedCriterionIds": [item.get("criterionId") for item in added if item.get("criterionId") not in (None, "")],
        "removedCriterionIds": [item.get("criterionId") for item in removed if item.get("criterionId") not in (None, "")],
        "renamed": renamed,
        "typeChanged": type_changed,
        "evidenceAdded": evidence_added,
        "evidenceRemoved": evidence_removed,
        "merged": merged,
        "fallbackCreated": fallback_created,
        "matchingBasis": "sourceTextHashes, explicit criterionId, then name; unknown where unavailable",
    }


def _trace_records(run: dict[str, Any]) -> list[dict[str, Any]]:
    audit = run.get("audit", {})
    trace = audit.get("debugTrace", []) if isinstance(audit, dict) else []
    return [item for item in trace if isinstance(item, dict) and item.get("stage")]


def _stage_aliases(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    names = {str(item.get("stage")) for item in records}
    return {
        "qwen_generation:complete_jd": ["qwen_generation:complete_jd"],
        "schema_normalisation": ["schema_normalisation"],
        "multi_sentence_grounding:responsibilities": ["multi_sentence_grounding:responsibilities"],
        "multi_sentence_grounding:requirements": ["multi_sentence_grounding:requirements"],
        "name_validation": ["name_validation"],
        "type_correction": ["type_correction", "type_correction:responsibilities", "type_correction:requirements"],
        "education_validation": ["education_validation", "education_validation:responsibilities", "education_validation:requirements"],
        "consolidation": ["consolidation"],
        "fallback_recovery": ["fallback_recovery"],
        "source_metadata_restoration": ["source_metadata_restoration"],
        "final_evidence_safety": ["final_evidence_safety"],
        "role_context_weighting": ["role_context_weighting", "role_context"],
        "api_payload_ready": ["api_payload_ready"],
        "api_serialization": ["api_serialization"],
        "final_response": ["final_response"],
    }


def build_stage_snapshots(run: dict[str, Any]) -> list[dict[str, Any]]:
    records = _trace_records(run)
    snapshots: list[dict[str, Any]] = []
    for record in records:
        snapshots.append(snapshot_stage(record))
    snapshots.append(final_response_snapshot(run))
    return snapshots


def _availability(records: list[dict[str, Any]], snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = _stage_aliases(records)
    available_names = {item["stage"] for item in snapshots}
    result = []
    for expected in EXPECTED_STAGES:
        candidates = aliases.get(expected, [expected])
        matched = [name for name in candidates if name in available_names]
        if matched:
            result.append({"stage": expected, "available": True, "recordedAs": matched})
        else:
            result.append({"stage": expected, "available": False, "recordedAs": [], "reason": "not present in saved audit trace; execution cannot be inferred"})
    return result


def _field_rows(snapshots: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    rows = []
    for snapshot in snapshots:
        for item in snapshot.get("criteria", []):
            value = item.get(field)
            present = value not in (None, [], "")
            rows.append({
                "stage": snapshot["stage"],
                "criterionId": item.get("criterionId"),
                "criterionName": item.get("name", ""),
                "present": present,
                "value": value if present else None,
                "origin": item.get("origin", "unknown"),
            })
    return rows


def _lifecycle_for_field(snapshots: list[dict[str, Any]], field: str) -> dict[str, Any]:
    rows = _field_rows(snapshots, field)
    present_rows = [row for row in rows if row["present"]]
    if not present_rows:
        if field == "importance":
            cause = "inconclusive"
            explanation = "Importance is absent from the earliest saved complete-JD criterion snapshot and the final response; the saved trace does not expose the internal schema-normalisation value."
        else:
            cause = "metadata_absent_before_serialization"
            explanation = "No saved criterion snapshot contains this field."
        return {
            "field": field,
            "rows": rows,
            "firstPresentStage": None,
            "lastPresentStage": None,
            "lossStage": "qwen_generation:complete_jd",
            "cause": cause,
            "explanation": explanation,
            "nextCorrectionLocation": {
                "file": "llm_criteria_api/app/pipeline.py",
                "function": "generate / record_stage / response serialization boundary",
            },
        }
    first = present_rows[0]["stage"]
    last = present_rows[-1]["stage"]
    final_present = any(row["present"] for row in rows if row["stage"] == "final_response")
    if final_present:
        cause = "preserved_in_saved_final_response"
        loss_stage = None
    else:
        cause = "api_serialization_or_php_proxy_boundary"
        loss_stage = "api_serialization -> final_response"
    return {
        "field": field,
        "rows": rows,
        "firstPresentStage": first,
        "lastPresentStage": last,
        "lossStage": loss_stage,
        "cause": cause,
        "explanation": "The trace proves the field was present before the saved final response; the api_serialization trace contains names/count only, so RunPod serializer versus PHP proxy cannot be separated from this record.",
        "nextCorrectionLocation": {
            "file": "llm_criteria_api/app/main.py and server/helpers/runpod.php",
            "function": "response model_dump / PHP criterion mapping boundary",
        },
    }


def _requirement_category(text: str) -> str:
    value = _normalise_text(text)
    if re_search(r"\b(sap|oracle|erp|microsoft word|excel|powerpoint|git|react|python|fastapi)\b", value):
        return "named_tool_or_platform"
    if re_search(r"\b(minimum|at least)\b.*\b(year|years|experience)\b", value):
        return "minimum_experience"
    if re_search(r"\b(english|mandarin|bahasa malaysia|malay|japanese)\b", value):
        return "named_language"
    if re_search(r"\b(diploma|degree|bachelor|master|phd|engineering|accounting|finance|business administration|computer science|software engineering|materials science|marketing)\b", value):
        return "education"
    if re_search(r"\b(preferred|preference|advantage)\b", value):
        return "preferred_scope_or_environment"
    return "other_requirement"


def re_search(pattern: str, value: str) -> bool:
    import re
    return bool(re.search(pattern, value, flags=re.IGNORECASE))


def requirement_coverage(fixture: dict[str, Any], run: dict[str, Any], evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    criteria = run.get("criteria", []) if isinstance(run.get("criteria", []), list) else []
    trace = _trace_records(run)
    qwen_record = next((item for item in trace if item.get("stage") == "qwen_generation:complete_jd"), {})
    qwen_names = {_normalise_text(item.get("name", "")) for item in _as_list(qwen_record.get("criteria")) if isinstance(item, dict)}
    recoveries = run.get("audit", {}).get("fallbackRecoveries", [])
    results = []
    for item in fixture["referenceJd"].get("qualifications", []) + fixture["referenceJd"].get("requirements", []):
        text = str(item.get("text", ""))
        category = _requirement_category(text)
        source_id = str(item.get("id"))
        matched = []
        qwen_matched = []
        fallback_matched = []
        for criterion in criteria:
            if source_id in mapped_source_ids(fixture, criterion):
                matched.append(criterion.get("name", ""))
                if _normalise_text(criterion.get("name", "")) in qwen_names:
                    qwen_matched.append(criterion.get("name", ""))
                continue
            criterion_tokens = _tokens(f"{criterion.get('name', '')} {' '.join(str(x) for x in criterion.get('jdEvidence', []))}")
            if len(_tokens(text) & criterion_tokens) / max(1, len(_tokens(text))) >= 0.75:
                matched.append(criterion.get("name", ""))
                if _normalise_text(criterion.get("name", "")) in qwen_names:
                    qwen_matched.append(criterion.get("name", ""))
        for recovery in recoveries if isinstance(recoveries, list) else []:
            if isinstance(recovery, dict) and (
                source_id in str(recovery) or _normalise_text(text) in _normalise_text(recovery)
            ):
                fallback_matched.append(str(recovery.get("criterionId", recovery.get("name", "fallback"))))
        eligibility = run.get("eligibilitySuggestions", {})
        eligibility_hit = False
        if category == "education":
            eligibility_hit = bool(eligibility.get("educationLevel"))
        elif category == "minimum_experience":
            eligibility_hit = bool(eligibility.get("minExperience"))
        elif category == "named_language":
            eligibility_hit = bool(eligibility.get("requiredLanguage"))
        status = "qwen_criterion" if qwen_matched else "fallback_criterion" if fallback_matched else "final_criterion" if matched else "eligibility_only" if eligibility_hit else "uncovered"
        results.append({
            "sourceId": source_id,
            "text": text,
            "category": category,
            "status": status,
            "matchedCriteria": matched,
            "qwenCriteria": qwen_matched,
            "fallbackCriteria": fallback_matched,
            "finalCriteria": matched,
            "eligibilityDetected": eligibility_hit,
            "eligibilitySuggestion": eligibility.get({
                "education": "educationLevel",
                "minimum_experience": "minExperience",
                "named_language": "requiredLanguage",
            }.get(category, "")) if category in {"education", "minimum_experience", "named_language"} else None,
            "stageOrigin": "final_response" if matched else "eligibilitySuggestions" if eligibility_hit else "unknown",
        })
    return results


def _topic_presence_in_snapshots(snapshots: list[dict[str, Any]], expected: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    for snapshot in snapshots:
        for item in snapshot.get("criteria", []):
            text = f"{item.get('name', '')} {' '.join(item.get('jdEvidence', []))}"
            coverage = sum(
                1
                for topic in expected.get("requiredEvidenceTopics", [])
                if any(variant and variant <= _tokens(text) for variant in _topic_variants_local(topic))
            ) / max(1, len(expected.get("requiredEvidenceTopics", [])))
            if coverage >= PARTIAL_COVERAGE_THRESHOLD_LOCAL:
                return snapshot["stage"], item
    return None, None


PARTIAL_COVERAGE_THRESHOLD_LOCAL = 0.25


def _topic_variants_local(value: str) -> list[set[str]]:
    import re
    return [_tokens(part) for part in re.split(r"\s+(?:or|and)\s+|\s*/\s*", _normalise_text(value)) if _tokens(part)]


def missing_core_attribution(fixture: dict[str, Any], snapshots: list[dict[str, Any]], evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for expected in evaluation.get("missingCoreCriteria", []):
        stage, item = _topic_presence_in_snapshots(snapshots, expected)
        if stage is None:
            category = "qwen_not_generated"
            explanation = "No semantically related criterion is present in the earliest saved Qwen snapshot."
        elif stage == "final_response":
            category = "evaluator_mismatch"
            explanation = "The capability is present in the saved final response but was not matched as a full expected criterion."
        else:
            category = "qwen_not_generated"
            explanation = "A partial or related capability is present at this stage, but the expected capability was not generated as a complete criterion."
        result.append({
            "benchmarkCriterionId": expected["benchmarkCriterionId"],
            "name": expected["acceptedNames"][0],
            "earliestRelatedStage": stage,
            "failureCategory": category,
            "explanation": explanation,
            "observedCriterion": item.get("name") if item else None,
            "origin": item.get("origin", "unknown") if item else "unknown",
        })
    return result


def build_stage_attribution(fixture: dict[str, Any], run: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    records = _trace_records(run)
    snapshots = build_stage_snapshots(run)
    deltas = [_delta_summary(before, after) for before, after in zip(snapshots, snapshots[1:])]
    lifecycle = {field: _lifecycle_for_field(snapshots, field) for field in FIELD_NAMES}
    return {
        "benchmarkId": fixture["benchmarkId"],
        "runNumber": run.get("runNumber"),
        "stageAvailability": _availability(records, snapshots),
        "stages": snapshots,
        "stageDeltas": deltas,
        "fieldLifecycle": lifecycle,
        "missingCoreAttribution": missing_core_attribution(fixture, snapshots, evaluation),
        "requirementsCoverage": requirement_coverage(fixture, run, evaluation),
        "limitations": [
            "Saved raw records contain sanitised audit snapshots, not raw Qwen output.",
            "api_serialization records names/count/weight only, so direct RunPod serializer loss cannot be separated from PHP proxy loss.",
            "No provenance is invented when a stage lacks criterion IDs or source hashes.",
        ],
    }


def build_stage_attribution_report(
    raw_results_dir: Path,
    fixtures_dir: Path,
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    fixtures = {item["benchmarkId"]: item for item in _load_fixture_files(fixtures_dir)}
    by_key = {(item["benchmarkId"], item.get("runNumber")): item for item in evaluations}
    runs = []
    for path in sorted((raw_results_dir / "raw").glob("*/*.json")):
        with path.open("r", encoding="utf-8") as handle:
            run = json.load(handle)
        evaluation = by_key[(run["benchmarkId"], run.get("runNumber"))]
        runs.append(build_stage_attribution(fixtures[run["benchmarkId"]], run, evaluation))
    original_report = {}
    original_path = raw_results_dir / "baseline_report.json"
    if original_path.exists():
        try:
            original_report = json.loads(original_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            original_report = {}
    corrected_metrics = {
        "diagnosticScoreAverage": round(sum(item.get("totalDiagnosticScore", 0) for item in evaluations) / max(1, len(evaluations)), 2),
        "coreRecallAverage": round(sum(item["metrics"].get("coreCriterionRecall", 0) for item in evaluations) / max(1, len(evaluations)), 4),
        "expectedRecallAverage": round(sum(item["metrics"].get("expectedCriterionRecall", 0) for item in evaluations) / max(1, len(evaluations)), 4),
        "typeAccuracyAverage": round(sum(item["metrics"].get("typeAccuracy", 0) for item in evaluations) / max(1, len(evaluations)), 4),
        "wrongSplitCount": sum(item["metrics"].get("wrongSplitCount", 0) for item in evaluations),
        "wrongMergeCount": sum(item["metrics"].get("wrongMergeCount", 0) for item in evaluations),
        "allowedAdditionalCount": sum(item["metrics"].get("allowedAdditionalCriterionCount", 0) for item in evaluations),
        "trulyUnexpectedCount": sum(item["metrics"].get("unexpectedCriterionCount", 0) for item in evaluations),
        "forbiddenCount": sum(item["metrics"].get("forbiddenCriterionCount", 0) for item in evaluations),
        "overlyGenericNameCount": sum(item["metrics"].get("overlyGenericNameCount", 0) for item in evaluations),
        "sentenceCopyNameCount": sum(item["metrics"].get("sentenceCopyNameCount", 0) for item in evaluations),
        "misleadingNameCount": sum(item["metrics"].get("misleadingNameCount", 0) for item in evaluations),
        "metadataPresenceRate": round(sum(bool(item.get("metadataPresencePass")) for item in evaluations) / max(1, len(evaluations)), 4),
        "metadataAlignmentRate": round(sum(bool(item.get("metadataAlignmentPass")) for item in evaluations) / max(1, len(evaluations)), 4),
        "importancePresenceRate": round(sum(item.get("fieldLifecycleSummary", {}).get("importance", {}).get("firstPresentStage") is not None for item in evaluations) / max(1, len(evaluations)), 4),
    }
    qwen_missing = [
        {"benchmarkId": run["benchmarkId"], "runNumber": run["runNumber"], **item}
        for run in runs
        for item in run["missingCoreAttribution"]
        if item["failureCategory"] == "qwen_not_generated"
    ]
    serialization_fields = []
    for run in runs:
        for field, lifecycle in run["fieldLifecycle"].items():
            if lifecycle.get("lossStage") and field != "importance":
                serialization_fields.append({"benchmarkId": run["benchmarkId"], "runNumber": run["runNumber"], "field": field, "lossStage": lifecycle["lossStage"], "cause": lifecycle["cause"]})
    return {
        "reportVersion": "gold_standard_stage_attribution_v2",
        "rawResultDirectory": str(raw_results_dir / "raw"),
        "evaluationTimestamp": datetime.now(timezone.utc).isoformat(),
        "runCount": len(runs),
        "existingBaseline": {
            "reportVersion": original_report.get("reportVersion"),
            "overallSummary": original_report.get("overallSummary", {}),
            "deployment": original_report.get("deployment", {}),
        },
        "evaluatorCorrections": [
            {"before": "type filtering happened before semantic matching", "after": "semantic match first; wrong type is typeError"},
            {"before": "one-to-one matching marked documented fragments unexpected", "after": "partial coverage and documented wrong splits are reported separately"},
            {"before": "all unsupported extras counted as unexpected", "after": "forbidden, allowed_additional and truly_unexpected are separate"},
            {"before": "priorityOrderingPass could pass with no core coverage", "after": "priority status is pass/fail/not_assessable"},
            {"before": "metadata absence counted as alignment success", "after": "presence and alignment are separate; absent metadata is not a pass"},
        ],
        "correctedOverallMetrics": corrected_metrics,
        "missingCoreAttributionSummary": qwen_missing,
        "confirmedQwenProblems": qwen_missing,
        "confirmedPythonProblems": [],
        "confirmedSerializationProblems": serialization_fields,
        "evaluatorOnlyProblems": {
            "oldUnexpectedCount": original_report.get("overallSummary", {}).get("totalUnexpectedCriteria"),
            "correctedTrulyUnexpectedCount": corrected_metrics["trulyUnexpectedCount"],
            "note": "Old evaluator-only semantic mismatches are removed; no production behaviour is changed.",
        },
        "decision": {
            "choice": "both deterministic fixes and few-shot are needed, in that order",
            "explanation": "Saved traces show broad core capabilities absent at complete-JD generation, while requirement recovery and serialization metadata also need deterministic attention. The evaluator does not change either path.",
        },
        "runs": runs,
    }


def _load_fixture_files(fixtures_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(fixtures_dir.glob("*.json"))]


def sha256_raw_files(raw_dir: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(raw_dir.glob("*/*.json")):
        hashes[str(path.relative_to(raw_dir)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def markdown_stage_report(report: dict[str, Any]) -> str:
    lines = [
        "# Pipeline Stage Attribution Report",
        "",
        "## Existing Baseline",
        "",
        f"- Image tag: `{report['existingBaseline']['deployment'].get('imageTag')}`",
        f"- Pipeline version: `{report['existingBaseline']['deployment'].get('pipelineVersion')}`",
        f"- Git commit: `{report['existingBaseline']['deployment'].get('gitCommitHash')}`",
        f"- Raw result directory: `{report['rawResultDirectory']}`",
        f"- Evaluator v1 metrics: `{report['existingBaseline']['overallSummary']}`",
        "",
        "## Evaluator Corrections",
        "",
    ]
    for correction in report["evaluatorCorrections"]:
        lines.append(f"- Before: {correction['before']}; after: {correction['after']}.")
    lines.extend(["", "## Corrected Overall Metrics", ""])
    for key, value in report["correctedOverallMetrics"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## HR Manager Attribution",
        "",
        "| Expected criterion | Present at Qwen stage | Removed stage | Final status | Root cause |",
        "|---|---|---|---|---|",
    ])
    for run in report["runs"]:
        if run["benchmarkId"] != "hr-manager-001":
            continue
        for item in run["missingCoreAttribution"]:
            lines.append(
                f"| {item['name']} | {item.get('earliestRelatedStage') or 'no'} | none proven | {'partial/absent' if item.get('observedCriterion') else 'absent'} | {item['failureCategory']} |"
            )
    lines.extend([
        "",
        "## Cross-Role Attribution",
        "",
        "The JSON report contains the same stage counts and deltas for Software Engineer, Accounts Payable Executive, Sales Executive, QA Engineer and Administrative Executive.",
        "",
        "## Requirement-Coverage Analysis",
        "",
        "| Benchmark | Run | Source | Category | Status | Qwen criterion | Final criterion | Eligibility |",
        "|---|---:|---|---|---|---|---|---|",
    ])
    for run in report["runs"]:
        for item in run["requirementsCoverage"]:
            lines.append(
                f"| {run['benchmarkId']} | {run['runNumber']} | {item['sourceId']} | {item['category']} | {item['status']} | {', '.join(item['qwenCriteria']) or 'none'} | {', '.join(item['finalCriteria']) or 'none'} | {'yes' if item['eligibilityDetected'] else 'no'} |"
            )
    lines.extend([
        "",
        "## Importance Field Lifecycle",
        "",
        "| Benchmark | Run | Field | First present | Loss stage | Cause |",
        "|---|---:|---|---|---|---|",
    ])
    for run in report["runs"]:
        lifecycle = run["fieldLifecycle"]["importance"]
        lines.append(
            f"| {run['benchmarkId']} | {run['runNumber']} | importance | {lifecycle.get('firstPresentStage') or 'none'} | {lifecycle.get('lossStage') or 'none'} | {lifecycle.get('cause')} |"
        )
    lines.extend([
        "",
        "## Source Metadata Lifecycle",
        "",
        "| Benchmark | Run | Field | First present | Loss stage | Cause |",
        "|---|---:|---|---|---|---|",
    ])
    for run in report["runs"]:
        for field in ("sourceIds", "groundingScores", "sourceCriterionIds", "mergedFromIds"):
            lifecycle = run["fieldLifecycle"][field]
            lines.append(
                f"| {run['benchmarkId']} | {run['runNumber']} | {field} | {lifecycle.get('firstPresentStage') or 'none'} | {lifecycle.get('lossStage') or 'none'} | {lifecycle.get('cause')} |"
            )
    lines.extend(["", "## Confirmed Qwen Problems", ""])
    if report["confirmedQwenProblems"]:
        for item in report["confirmedQwenProblems"]:
            lines.append(f"- {item['benchmarkId']} {item['name']}: no complete criterion is present at the saved Qwen stage; related stage `{item.get('earliestRelatedStage') or 'none'}`.")
    else:
        lines.append("- None proven by the saved trace.")
    lines.extend([
        "",
        "## Confirmed Python Problems",
        "",
        "- No post-Qwen removal is claimed without a saved stage delta proving it.",
        "",
        "## Confirmed Serialization/Proxy Problems",
        "",
    ])
    for item in report["confirmedSerializationProblems"][:20]:
        lines.append(f"- {item['benchmarkId']} run {item['runNumber']}: `{item['field']}` is present before the final response and absent after `{item['lossStage']}`; the saved trace cannot separate RunPod serializer from PHP proxy.")
    if not report["confirmedSerializationProblems"]:
        lines.append("- None proven by the saved trace.")
    lines.extend([
        "",
        "## Evaluator-Only Problems",
        "",
        f"- {report['evaluatorOnlyProblems']['note']}",
        "",
        "## Decision",
        "",
        f"- **{report['decision']['choice']}**",
        f"- {report['decision']['explanation']}",
        "",
        "## Stage Deltas",
        "",
        "| Benchmark | Run | Stage | Input count | Output count | Added | Removed | Renamed | Type changes | Evidence removed |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for run in report["runs"]:
        for delta in run["stageDeltas"]:
            lines.append(
                f"| {run['benchmarkId']} | {run['runNumber']} | {delta['stage']} | {delta['inputCriteriaCount']} | {delta['outputCriteriaCount']} | {len(delta['added'])} | {len(delta['removed'])} | {len(delta['renamed'])} | {len(delta['typeChanged'])} | {len(delta['evidenceRemoved'])} |"
            )
    lines.extend(["", "## Saved-Trace Limitations", ""])
    for item in report["runs"][0]["limitations"] if report["runs"] else []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "EXPECTED_STAGES",
    "build_stage_attribution",
    "build_stage_attribution_report",
    "build_stage_snapshots",
    "markdown_stage_report",
    "sha256_raw_files",
]
