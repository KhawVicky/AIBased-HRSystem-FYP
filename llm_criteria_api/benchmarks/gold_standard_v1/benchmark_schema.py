"""Deterministic Gold Standard evaluator for the saved v1.0.7 responses.

This module evaluates immutable production records only.  It does not call a
model and it deliberately does not import the production criteria pipeline.
Semantic matching is performed before type matching so that a meaningful
criterion with the wrong type is reported as a type error rather than as an
unrelated output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


ALLOWED_TYPES = {
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
}

FULL_COVERAGE_THRESHOLD = 0.75
PARTIAL_COVERAGE_THRESHOLD = 0.25

REQUIRED_FIXTURE_FIELDS = {
    "benchmarkId",
    "jobFamily",
    "referenceJd",
    "expectedCriteria",
    "mustMerge",
    "mustNotMerge",
    "mustNotGenerate",
    "expectedEligibility",
}

NON_SEMANTIC_WORDS = {
    "a",
    "an",
    "any",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "and",
    "minimum",
    "required",
    "preferred",
    "strong",
    "excellent",
    "relevant",
}

# The benchmark compares capability meaning, so common derivational forms
# should not become separate topics.  This is intentionally small and
# deterministic; it is not fuzzy matching.
MORPHOLOGY = {
    "recruitment": "recruit",
    "recruiting": "recruit",
    "recruited": "recruit",
    "recruits": "recruit",
    "supervisory": "supervise",
    "supervision": "supervise",
    "supervised": "supervise",
    "supervises": "supervise",
    "compliance": "comply",
    "compliant": "comply",
    "complies": "comply",
    "reconciliation": "reconcile",
    "reconciliations": "reconcile",
    "administration": "administrate",
    "administrative": "administrate",
    "development": "develop",
    "maintains": "maintain",
    "maintenance": "maintain",
    "maintained": "maintain",
    "monitoring": "monitor",
    "monitors": "monitor",
    "managed": "manage",
    "management": "manage",
    "manages": "manage",
    "quality": "quality",
    "assurance": "assure",
    "analyses": "analyse",
    "analysis": "analyse",
    "investigation": "investigate",
    "investigations": "investigate",
    "documentation": "document",
    "documents": "document",
    "coordination": "coordinate",
    "coordinating": "coordinate",
    "quotations": "quotation",
    "invoices": "invoice",
    "payments": "payment",
    "runs": "run",
    "apis": "api",
    "customers": "customer",
    "accounts": "account",
    "systems": "system",
    "applications": "application",
    "standards": "standard",
    "regulations": "regulation",
    "requirements": "requirement",
    "years": "year",
    "sales": "sale",
    "suppliers": "supplier",
    "vendors": "vendor",
    "records": "record",
    "reports": "report",
    "databases": "database",
    "arrangements": "arrangement",
    "discrepancies": "discrepancy",
    "retrieved": "retrieve",
    "retrieval": "retrieve",
    "payments": "payment",
    "employees": "employee",
    "workers": "worker",
    "laws": "law",
    "policies": "policy",
    "procedures": "procedure",
    "processes": "process",
}

WEAK_NAME_WORDS = {
    "management",
    "monitoring",
    "coordination",
    "compliance",
    "report",
    "development",
    "frontend",
    "security",
    "administration",
    "support",
    "process",
    "system",
    "quotation",
}


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _stem_token(token: str) -> str:
    token = MORPHOLOGY.get(token, token)
    if token.endswith("ies") and len(token) > 4:
        token = f"{token[:-3]}y"
    elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return MORPHOLOGY.get(token, token)


def _tokens(value: Any) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", _normalise_text(value).replace("e-invoice", "einvoice"))
    return {
        _stem_token(token)
        for token in tokens
        if token not in NON_SEMANTIC_WORDS and len(token) > 1
    }


def _topic_variants(value: Any) -> list[set[str]]:
    """Return deterministic alternatives for an evidence topic."""
    text = _normalise_text(value)
    pieces = re.split(r"\s+(?:or|and)\s+|\s*/\s*", text)
    variants = [_tokens(piece) for piece in pieces if _tokens(piece)]
    return variants or [_tokens(text)]


def _topic_tokens(value: Any) -> set[str]:
    return _tokens(value)


def validate_fixture(fixture: dict[str, Any]) -> None:
    missing = REQUIRED_FIXTURE_FIELDS - set(fixture)
    if missing:
        raise ValueError(f"{fixture.get('benchmarkId', '<unknown>')} missing {sorted(missing)}")
    reference = fixture["referenceJd"]
    for field in ("jobTitle", "department", "description", "qualifications", "responsibilities", "requirements"):
        if field not in reference:
            raise ValueError(f"{fixture['benchmarkId']} referenceJd missing {field}")
    if not reference["responsibilities"]:
        raise ValueError(f"{fixture['benchmarkId']} needs responsibilities")
    if not fixture["expectedCriteria"]:
        raise ValueError(f"{fixture['benchmarkId']} needs expected criteria")
    for criterion in fixture["expectedCriteria"]:
        required = {
            "benchmarkCriterionId",
            "acceptedNames",
            "requiredEvidenceTopics",
            "forbiddenEvidenceTopics",
            "expectedSourceIds",
            "expectedImportance",
            "expectedPriority",
            "targetWeight",
            "acceptableWeightRange",
        }
        missing_criterion = required - set(criterion)
        if missing_criterion:
            raise ValueError(f"{fixture['benchmarkId']} criterion missing {sorted(missing_criterion)}")
        allowed_types = criterion.get("allowedTypes")
        criterion_type = criterion.get("type")
        if criterion_type is None and not allowed_types:
            raise ValueError(f"{fixture['benchmarkId']} criterion has no type/allowedTypes")
        if criterion_type is not None and criterion_type not in ALLOWED_TYPES:
            raise ValueError(f"{fixture['benchmarkId']} uses unsupported type {criterion_type}")
        if allowed_types and not set(allowed_types) <= ALLOWED_TYPES:
            raise ValueError(f"{fixture['benchmarkId']} uses unsupported allowed type")
        if not criterion["acceptedNames"]:
            raise ValueError(f"{fixture['benchmarkId']} criterion has no acceptedNames")


def load_fixtures(fixtures_dir: Path) -> list[dict[str, Any]]:
    fixtures = []
    for path in sorted(fixtures_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            fixture = json.load(handle)
        validate_fixture(fixture)
        fixtures.append(fixture)
    return fixtures


def request_body(fixture: dict[str, Any]) -> dict[str, Any]:
    reference = fixture["referenceJd"]
    return {
        "jobTitle": reference["jobTitle"],
        "department": reference["department"],
        "description": reference.get("description", ""),
        "qualifications": [item["text"] for item in reference["qualifications"]],
        "responsibilities": [item["text"] for item in reference["responsibilities"]],
        "requirements": [item["text"] for item in reference["requirements"]],
    }


def _reference_entries(fixture: dict[str, Any]) -> list[tuple[str, str, str]]:
    reference = fixture["referenceJd"]
    entries = []
    for section in ("responsibilities", "requirements", "qualifications"):
        for item in reference.get(section, []):
            entries.append((section, str(item["id"]), str(item["text"])))
    return entries


def _source_id_map(fixture: dict[str, Any]) -> dict[str, str]:
    """Map explicit IDs and unambiguous source aliases for compatibility."""
    result: dict[str, str] = {}
    for section in ("responsibilities", "requirements", "qualifications"):
        entries = fixture["referenceJd"].get(section, [])
        for index, item in enumerate(entries):
            item_id = str(item["id"])
            result[_normalise_text(item_id).replace(" ", "")] = item_id
            result[f"{section}-{index}"] = item_id
            result[f"{section[:-1] if section.endswith('s') else section}-{index}"] = item_id
    return result


def _evidence_values(actual: dict[str, Any]) -> list[str]:
    values = actual.get("jdEvidence", actual.get("sourceText", []))
    if isinstance(values, list):
        return [str(item) for item in values if str(item).strip()]
    return [str(values)] if values else []


def _source_ids_for_actual(fixture: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    entries = _reference_entries(fixture)
    known_ids = {item_id for _, item_id, _ in entries}
    source_map = _source_id_map(fixture)
    result: list[str] = []
    raw_ids = actual.get("sourceIds", [])
    if isinstance(raw_ids, list):
        for raw in raw_ids:
            value = str(raw).strip()
            if value in known_ids:
                result.append(value)
                continue
            key = _normalise_text(value).replace(" ", "")
            if key in source_map:
                result.append(source_map[key])

    evidence = [_normalise_text(item) for item in _evidence_values(actual)]
    # Exact evidence is the strongest available provenance in final PHP
    # responses, where sourceIds may have been dropped by serialization.
    for _, item_id, text in entries:
        if _normalise_text(text) in evidence and item_id not in result:
            result.append(item_id)

    if evidence:
        evidence_tokens = set().union(*(_tokens(item) for item in evidence))
        for _, item_id, text in entries:
            source_tokens = _tokens(text)
            if item_id in result or not source_tokens:
                continue
            overlap = len(evidence_tokens & source_tokens) / len(source_tokens)
            if overlap >= 0.88:
                result.append(item_id)
    return result


def mapped_source_ids(fixture: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    return _source_ids_for_actual(fixture, actual)


def criterion_text(actual: dict[str, Any]) -> str:
    evidence_text = " | ".join(_evidence_values(actual))
    return f"{actual.get('name', '')} {evidence_text}"


def _accepted_name_score(actual_name: str, accepted_names: Iterable[str]) -> tuple[float, float]:
    actual_tokens = _tokens(actual_name)
    if not actual_tokens:
        return 0.0, 0.0
    best_overlap = 0.0
    exact = 0.0
    actual_normalised = _normalise_text(actual_name)
    for accepted in accepted_names:
        if actual_normalised == _normalise_text(accepted):
            exact = 100.0
        expected_tokens = _tokens(accepted)
        if expected_tokens:
            overlap = len(actual_tokens & expected_tokens) / len(expected_tokens)
            best_overlap = max(best_overlap, overlap)
    return exact, best_overlap


def _topic_coverage(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[float, list[str]]:
    text_tokens = _topic_tokens(criterion_text(actual))
    matched: list[str] = []
    for topic in expected["requiredEvidenceTopics"]:
        variants = _topic_variants(topic)
        if any(variant and variant <= text_tokens for variant in variants):
            matched.append(topic)
    total = len(expected["requiredEvidenceTopics"])
    return (len(matched) / total if total else 1.0, matched)


def _source_score(fixture: dict[str, Any], actual: dict[str, Any], expected: dict[str, Any]) -> float:
    actual_sources = set(mapped_source_ids(fixture, actual))
    expected_sources = set(expected.get("expectedSourceIds", []))
    if not expected_sources:
        return 0.0
    return len(actual_sources & expected_sources) / len(expected_sources)


def _type_value(actual: dict[str, Any]) -> str | None:
    value = actual.get("type", actual.get("category"))
    return str(value) if value is not None else None


def _type_status(actual: dict[str, Any], expected: dict[str, Any]) -> str:
    actual_type = _type_value(actual)
    allowed = expected.get("allowedTypes") or [expected.get("type")]
    if actual_type in allowed:
        return "correct"
    if actual_type in set(expected.get("acceptableAlternatives", [])):
        return "allowed_alternative"
    return "wrong"


def _semantic_candidate(
    fixture: dict[str, Any],
    actual: dict[str, Any],
    expected: dict[str, Any],
    expected_index: int,
    actual_index: int,
) -> dict[str, Any]:
    exact, overlap = _accepted_name_score(str(actual.get("name", "")), expected["acceptedNames"])
    coverage, matched_topics = _topic_coverage(actual, expected)
    source_score = _source_score(fixture, actual, expected)
    text_tokens = _topic_tokens(criterion_text(actual))
    forbidden = [
        topic
        for topic in expected.get("forbiddenEvidenceTopics", [])
        if any(variant and variant <= text_tokens for variant in _topic_variants(topic))
    ]
    semantic = bool(
        coverage >= PARTIAL_COVERAGE_THRESHOLD
        or source_score >= 0.5
        or overlap >= 0.5
        or exact
    )
    score = exact + overlap * 35.0 + coverage * 50.0 + source_score * 25.0 - len(forbidden) * 40.0
    return {
        "expected": expected,
        "actual": actual,
        "expectedIndex": expected_index,
        "actualIndex": actual_index,
        "score": round(score, 3),
        "nameOverlap": round(overlap, 3),
        "topicCoverage": round(coverage, 3),
        "matchedTopics": matched_topics,
        "sourceScore": round(source_score, 3),
        "inferredSourceIds": mapped_source_ids(fixture, actual),
        "forbiddenTopics": forbidden,
        "semanticCandidate": semantic,
        "typeStatus": _type_status(actual, expected),
    }


def _combined_candidate_text(criteria: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: list[str] = []
    for item in criteria:
        for value in _evidence_values(item):
            if _normalise_text(value) not in {_normalise_text(existing) for existing in evidence}:
                evidence.append(value)
    return {"name": " ".join(str(item.get("name", "")) for item in criteria), "jdEvidence": evidence}


def _split_group_for_target(
    fixture: dict[str, Any],
    target: dict[str, Any],
    target_index: int,
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = [item for item in candidates if item["semanticCandidate"]]
    expected_sources = set(target.get("expectedSourceIds", []))
    if len(expected_sources) < 2 or len(candidates) < 2:
        return None
    best: dict[str, Any] | None = None
    # Benchmark cases have small output sets; pairs are enough to detect the
    # documented wrong splits without joining unrelated criteria.
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            if left["actualIndex"] == right["actualIndex"]:
                continue
            source_union = set(left["inferredSourceIds"]) | set(right["inferredSourceIds"])
            if not source_union & expected_sources:
                continue
            combined_actual = _combined_candidate_text([left["actual"], right["actual"]])
            combined_coverage, combined_topics = _topic_coverage(combined_actual, target)
            individual_max = max(left["topicCoverage"], right["topicCoverage"])
            if combined_coverage < FULL_COVERAGE_THRESHOLD or combined_coverage <= individual_max:
                continue
            expected_overlap = len(source_union & expected_sources)
            score = combined_coverage * 100 + expected_overlap * 15 - individual_max * 5
            if best is None or score > best["_score"]:
                primary, fragment = sorted(
                    (left, right),
                    key=lambda item: (-item["score"], item["actualIndex"]),
                )
                best = {
                    "expected": target,
                    "expectedIndex": target_index,
                    "primary": primary,
                    "fragments": [fragment],
                    "combinedCoverage": round(combined_coverage, 3),
                    "combinedTopics": combined_topics,
                    "combinedSourceIds": sorted(source_union & expected_sources),
                    "combinedWeight": sum(
                        float(item["actual"].get("weight", item["actual"].get("suggestedWeight", 0)) or 0)
                        for item in (left, right)
                    ),
                    "_score": score,
                }
    if best:
        best.pop("_score", None)
    return best


def _candidate_sort(item: dict[str, Any]) -> tuple[float, float, float, int]:
    return (-item["score"], -item["topicCoverage"], -item["sourceScore"], item["actualIndex"])


def match_actual_criteria(fixture: dict[str, Any], actual_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    expected = fixture["expectedCriteria"]
    candidate_by_expected: dict[int, list[dict[str, Any]]] = {
        expected_index: [
            _semantic_candidate(fixture, actual, target, expected_index, actual_index)
            for actual_index, actual in enumerate(actual_criteria)
        ]
        for expected_index, target in enumerate(expected)
    }

    split_groups: list[dict[str, Any]] = []
    used_expected: set[int] = set()
    used_actual: set[int] = set()
    for expected_index, target in enumerate(expected):
        group = _split_group_for_target(
            fixture,
            target,
            expected_index,
            candidate_by_expected[expected_index],
        )
        if not group:
            continue
        split_groups.append(group)
        used_expected.add(expected_index)
        used_actual.add(group["primary"]["actualIndex"])
        used_actual.update(item["actualIndex"] for item in group["fragments"])

    full_matches: list[dict[str, Any]] = []
    for expected_index, candidates in candidate_by_expected.items():
        if expected_index in used_expected:
            continue
        available = [
            item
            for item in candidates
            if item["semanticCandidate"]
            and item["topicCoverage"] >= FULL_COVERAGE_THRESHOLD
            and item["actualIndex"] not in used_actual
        ]
        if not available:
            continue
        candidate = sorted(available, key=_candidate_sort)[0]
        full_matches.append(candidate)
        used_expected.add(expected_index)
        used_actual.add(candidate["actualIndex"])

    partial_matches: list[dict[str, Any]] = []
    partial_expected: set[int] = set()
    for expected_index, candidates in candidate_by_expected.items():
        if expected_index in used_expected:
            continue
        available = [
            item
            for item in candidates
            if item["semanticCandidate"]
            and item["topicCoverage"] >= PARTIAL_COVERAGE_THRESHOLD
            and item["actualIndex"] not in used_actual
        ]
        if not available:
            continue
        candidate = sorted(available, key=_candidate_sort)[0]
        partial_matches.append(candidate)
        partial_expected.add(expected_index)
        used_actual.add(candidate["actualIndex"])

    semantic_matches = list(full_matches) + [group["primary"] for group in split_groups] + partial_matches
    missing = [
        item
        for index, item in enumerate(expected)
        if index not in used_expected and index not in partial_expected
    ]
    partial_expected_items = [expected[index] for index in sorted(partial_expected)]
    missing_full = [
        item
        for index, item in enumerate(expected)
        if index not in used_expected
    ]
    unmatched_actual = [
        {"criterion": item, "actualIndex": index}
        for index, item in enumerate(actual_criteria)
        if index not in used_actual
    ]
    return {
        "matches": full_matches + [group["primary"] for group in split_groups],
        "partialMatches": partial_matches,
        "partialExpectedCriteria": partial_expected_items,
        "missingFullCriteria": missing_full,
        "splitGroups": split_groups,
        "semanticMatches": semantic_matches,
        "missing": missing,
        "unmatchedActual": unmatched_actual,
        "usedExpected": sorted(used_expected),
        "usedActual": sorted(used_actual),
    }


def _joined_actual_text(actual: dict[str, Any]) -> str:
    return " ".join(_evidence_values(actual))


def _must_not_text_matches(fixture: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    text = _topic_tokens(f"{actual.get('name', '')} {_joined_actual_text(actual)}")
    return [
        forbidden
        for forbidden in fixture.get("mustNotGenerate", [])
        if any(variant and variant <= text for variant in _topic_variants(forbidden))
    ]


def forbidden_criteria(
    fixture: dict[str, Any],
    actual: list[dict[str, Any]],
    ignored_indices: set[int] | None = None,
) -> list[dict[str, Any]]:
    ignored_indices = ignored_indices or set()
    result = []
    for index, item in enumerate(actual):
        if index in ignored_indices:
            continue
        for forbidden in _must_not_text_matches(fixture, item):
            result.append({"criterion": item, "actualIndex": index, "forbidden": forbidden})
    return result


def evidence_contamination(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in matches if item.get("forbiddenTopics")]


def wrong_merges(fixture: dict[str, Any], actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(actual):
        text = _topic_tokens(f"{item.get('name', '')} {_joined_actual_text(item)}")
        for pair in fixture.get("mustNotMerge", []):
            if isinstance(pair, dict):
                pair = pair.get("value", [])
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            if all(any(variant and variant <= text for variant in _topic_variants(topic)) for topic in pair):
                result.append({"criterion": item, "actualIndex": index, "domains": pair})
    return result


def weight_total_valid(actual: list[dict[str, Any]]) -> bool:
    weights = [item.get("weight", item.get("suggestedWeight")) for item in actual]
    return bool(weights) and all(isinstance(value, (int, float)) for value in weights) and sum(weights) == 100


def metadata_presence(actual: list[dict[str, Any]], enhanced_expected: bool = True) -> dict[str, Any]:
    fields = ("sourceIds", "groundingScores", "sourceCriterionIds", "mergedFromIds", "importance")
    result: dict[str, str] = {}
    for field in fields:
        present_count = sum(
            1
            for item in actual
            if field in item and item.get(field) not in (None, [], "")
        )
        if not actual or present_count == 0:
            result[field] = "absent"
        elif present_count == len(actual):
            result[field] = "complete"
        else:
            result[field] = "partial"
    return {
        "fields": result,
        "expected": enhanced_expected,
        "pass": all(value == "complete" for value in result.values()) if enhanced_expected else True,
    }


def metadata_alignment(actual: list[dict[str, Any]]) -> dict[str, Any]:
    field_results: dict[str, str] = {}
    for field in ("sourceIds", "groundingScores"):
        present = [item.get(field) for item in actual if field in item and item.get(field) not in (None, [])]
        if not present:
            field_results[field] = "not_applicable"
            continue
        passed = True
        for item in actual:
            values = item.get(field)
            evidence_count = len(_evidence_values(item))
            if values is None:
                continue
            if not isinstance(values, list) or len(values) != evidence_count:
                passed = False
        field_results[field] = "pass" if passed else "fail"
    for field in ("sourceCriterionIds", "mergedFromIds"):
        present = [item.get(field) for item in actual if field in item and item.get(field) not in (None, [])]
        if not present:
            field_results[field] = "not_applicable"
        else:
            field_results[field] = "pass" if all(isinstance(value, list) for value in present) else "fail"
    return {
        "fields": field_results,
        "pass": bool(field_results) and all(value == "pass" for value in field_results.values()),
        "status": "not_applicable" if all(value == "not_applicable" for value in field_results.values()) else "evaluated",
    }


def assess_name_quality(actual: dict[str, Any], expected: dict[str, Any] | None = None) -> dict[str, Any]:
    name = str(actual.get("name", "")).strip()
    tokens = _tokens(name)
    normalised = _normalise_text(name)
    evidence = _normalise_text(_joined_actual_text(actual))
    reasons: list[str] = []
    status = "good"
    if len(tokens) >= 10 or (len(tokens) >= 7 and ("year" in tokens or "." in name)) or (
        normalised.startswith("minimum ") and "year" in tokens and "experience" in tokens
    ):
        status = "sentence_copy"
        reasons.append("name is a long sentence-like restatement")
    elif normalised in WEAK_NAME_WORDS or len(tokens) == 1 and normalised in WEAK_NAME_WORDS:
        status = "overly_generic"
        reasons.append("name is too broad to identify one independently scorable capability")
    elif normalised in {"crm system", "ci cd", "e invoice"}:
        status = "overly_generic"
        reasons.append("name identifies a tool or shorthand without the capability")
    elif normalised == "product presentation" and any(word in evidence for word in ("negotiate", "commercial terms", "close sales")):
        status = "misleading_focus"
        reasons.append("name omits the negotiation and closing capability in its evidence")
    if expected and status == "good":
        coverage, _ = _topic_coverage(actual, expected)
        if coverage < PARTIAL_COVERAGE_THRESHOLD:
            status = "incomplete_scope"
            reasons.append("name/evidence covers little of the expected capability")
    if not reasons and status == "good":
        status = "acceptable" if len(tokens) <= 2 else "good"
    return {"status": status, "reasons": reasons}


def _allowed_additional(
    fixture: dict[str, Any],
    actual: dict[str, Any],
    actual_index: int,
    candidate_by_expected: dict[int, list[dict[str, Any]]],
) -> bool:
    quality = assess_name_quality(actual)
    if quality["status"] in {"overly_generic", "sentence_copy", "misleading_focus"}:
        return False
    if not _evidence_values(actual) or not mapped_source_ids(fixture, actual):
        return False
    if _must_not_text_matches(fixture, actual):
        return False
    best_coverage = max(
        (item["topicCoverage"] for candidates in candidate_by_expected.values() for item in candidates if item["actualIndex"] == actual_index),
        default=0.0,
    )
    return best_coverage < FULL_COVERAGE_THRESHOLD


def pipeline_trace_pass(run: dict[str, Any]) -> bool:
    deployment = run.get("deployment") or run.get("audit", {}).get("deployment", {})
    audit = run.get("audit", {})
    trace = audit.get("debugTrace", []) if isinstance(audit, dict) else []
    stages = [item.get("stage") for item in trace if isinstance(item, dict)]
    return bool(
        deployment.get("imageTag")
        and deployment.get("pipelineVersion") == "complete-jd-candidate-extraction-v2"
        and deployment.get("gitCommitHash") not in {None, "", "unknown", "local-build"}
        and "qwen_generation:complete_jd" in stages
        and "qwen_generation:responsibilities" not in stages
        and "qwen_generation:requirements" not in stages
        and deployment.get("roleContextEnabled") is True
        and deployment.get("finalEvidenceSafetyEnabled") is True
    )


def _priority_status(
    fixture: dict[str, Any],
    matching: dict[str, Any],
    actual: list[dict[str, Any]],
) -> dict[str, Any]:
    core = [item for item in fixture["expectedCriteria"] if item.get("expectedPriority") == "core"]
    core_ids = {item["benchmarkCriterionId"] for item in core}
    matched_core = [
        item for item in matching["matches"]
        if item["expected"]["benchmarkCriterionId"] in core_ids
    ]
    recall = len(matched_core) / len(core) if core else 1.0
    if recall == 0 or recall < 0.5:
        return {"status": "not_assessable", "reason": "too many core capabilities are absent"}
    minimum = [
        item for item in matching["semanticMatches"]
        if item["expected"].get("expectedPriority") == "minimum_supporting"
    ]
    core_weights = [
        item["actual"].get("weight", item["actual"].get("suggestedWeight"))
        for item in matched_core
        if isinstance(item["actual"].get("weight", item["actual"].get("suggestedWeight")), (int, float))
    ]
    minimum_weights = [
        item["actual"].get("weight", item["actual"].get("suggestedWeight"))
        for item in minimum
        if isinstance(item["actual"].get("weight", item["actual"].get("suggestedWeight")), (int, float))
    ]
    if minimum_weights and (not core_weights or max(minimum_weights) >= max(core_weights)):
        return {"status": "fail", "reason": "minimum-threshold experience is not lower than present core criteria"}
    if minimum_weights and max(minimum_weights) >= 25:
        return {"status": "fail", "reason": "minimum-threshold experience receives a dominant weight"}
    if core_weights and minimum_weights and max(core_weights) > max(minimum_weights):
        return {"status": "pass", "reason": "present core capabilities outrank supporting experience"}
    return {"status": "not_assessable", "reason": "insufficient comparable importance or weights"}


def _criterion_match_record(candidate: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    expected = candidate["expected"]
    actual = candidate["actual"]
    record = dict(candidate)
    record["nameQuality"] = assess_name_quality(actual, expected)
    record["classification"] = "full_match" if candidate["topicCoverage"] >= FULL_COVERAGE_THRESHOLD else "partial_match"
    return record


def evaluate_run(fixture: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    actual = run.get("criteria", []) if isinstance(run.get("criteria", []), list) else []
    matching = match_actual_criteria(fixture, actual)
    matches = [_criterion_match_record(item, fixture) for item in matching["matches"]]
    partial_matches = [_criterion_match_record(item, fixture) for item in matching["partialMatches"]]
    split_groups = []
    split_fragment_indices: set[int] = set()
    for group in matching["splitGroups"]:
        primary = _criterion_match_record(group["primary"], fixture)
        fragments = [_criterion_match_record(item, fixture) for item in group["fragments"]]
        split_fragment_indices.update(item["actualIndex"] for item in group["fragments"])
        split_groups.append({**group, "primary": primary, "fragments": fragments})

    semantic_matches = matches + partial_matches
    type_errors = [item for item in semantic_matches if item["typeStatus"] == "wrong"]
    allowed_type_matches = [item for item in semantic_matches if item["typeStatus"] == "allowed_alternative"]
    contamination = evidence_contamination(matches + partial_matches)
    wrong_merge = wrong_merges(fixture, actual)
    used_indices = set(matching["usedActual"])
    forbidden = forbidden_criteria(fixture, actual, used_indices)
    additional: list[dict[str, Any]] = []
    unexpected: list[dict[str, Any]] = []
    candidate_by_expected: dict[int, list[dict[str, Any]]] = {}
    for expected_index, target in enumerate(fixture["expectedCriteria"]):
        candidate_by_expected[expected_index] = [
            _semantic_candidate(fixture, item, target, expected_index, actual_index)
            for actual_index, item in enumerate(actual)
        ]
    forbidden_indices = {item["actualIndex"] for item in forbidden}
    for item in matching["unmatchedActual"]:
        index = item["actualIndex"]
        criterion = item["criterion"]
        if index in forbidden_indices:
            continue
        classification = "allowed_additional" if _allowed_additional(fixture, criterion, index, candidate_by_expected) else "truly_unexpected"
        record = {
            "criterion": criterion,
            "actual": criterion,
            "actualIndex": index,
            "classification": classification,
            "nameQuality": assess_name_quality(criterion),
            "inferredSourceIds": mapped_source_ids(fixture, criterion),
        }
        if classification == "allowed_additional":
            additional.append(record)
        else:
            unexpected.append(record)

    split_fragment_records = []
    for group in split_groups:
        for fragment in group["fragments"]:
            split_fragment_records.append({
                **fragment,
                "classification": "split_fragment",
                "splitExpectedCriterionId": group["expected"]["benchmarkCriterionId"],
            })

    core_expected = [item for item in fixture["expectedCriteria"] if item.get("expectedPriority") == "core"]
    core_ids = {item["benchmarkCriterionId"] for item in core_expected}
    matched_core = [item for item in matches if item["expected"]["benchmarkCriterionId"] in core_ids]
    full_count = len(matches)
    expected_count = len(fixture["expectedCriteria"])
    partial_count = len(partial_matches)
    semantic_count = len(semantic_matches)
    scorable_actual_count = max(1, len(actual) - len(forbidden))
    core_recall = len(matched_core) / len(core_expected) if core_expected else 1.0
    recall = full_count / expected_count if expected_count else 1.0
    criterion_precision = full_count / scorable_actual_count
    semantic_precision = semantic_count / scorable_actual_count
    missing_core = [item for item in matching["missingFullCriteria"] if item.get("expectedPriority") == "core"]
    type_accuracy = (
        sum(1 for item in semantic_matches if item["typeStatus"] in {"correct", "allowed_alternative"}) / semantic_count
        if semantic_count
        else 0.0
    )
    weights_in_range = []
    for item in matches:
        value = item["actual"].get("weight", item["actual"].get("suggestedWeight"))
        low, high = item["expected"]["acceptableWeightRange"]
        weights_in_range.append(low <= value <= high if isinstance(value, (int, float)) else False)
    priority = _priority_status(fixture, matching, actual)
    name_records = [item["nameQuality"] for item in matches + partial_matches]
    name_records += [item["nameQuality"] for item in additional + unexpected]
    overly_generic = [item for item in name_records if item["status"] == "overly_generic"]
    sentence_copy = [item for item in name_records if item["status"] == "sentence_copy"]
    misleading = [item for item in name_records if item["status"] == "misleading_focus"]
    metadata = metadata_presence(actual)
    alignment = metadata_alignment(actual)
    evidence_cleanliness = max(
        0.0,
        1.0 - (len(contamination) + len(wrong_merge)) / max(1, len(matches) + len(partial_matches)),
    )
    control = max(0.0, 1.0 - (len(forbidden) + len(unexpected)) / max(1, len(actual)))
    total_score = round(
        core_recall * 30
        + recall * 15
        + type_accuracy * 15
        + evidence_cleanliness * 15
        + control * 10
        + (10 if priority["status"] == "pass" else 0)
        + (5 if weight_total_valid(actual) and metadata["pass"] else 0),
        2,
    )
    return {
        "benchmarkId": fixture["benchmarkId"],
        "runNumber": run.get("runNumber"),
        "matchedCriteria": matches,
        "partialMatches": partial_matches,
        "partialExpectedCriteria": matching["partialExpectedCriteria"],
        "splitGroups": split_groups,
        "splitFragments": split_fragment_records,
        "missingExpectedCriteria": matching["missing"],
        "missingFullCriteria": matching["missingFullCriteria"],
        "missingCoreCriteria": missing_core,
        "unexpectedCriteria": unexpected,
        "allowedAdditionalCriteria": additional,
        "forbiddenCriteria": forbidden,
        "typeErrors": type_errors,
        "allowedTypeMatches": allowed_type_matches,
        "evidenceContamination": contamination,
        "wrongMerges": wrong_merge,
        "wrongSplits": split_groups,
        "genericCriteria": [
            item for item in matches + partial_matches + additional + unexpected
            if item["nameQuality"]["status"] == "overly_generic"
        ],
        "nameQuality": {
            "overlyGeneric": overly_generic,
            "sentenceCopy": sentence_copy,
            "misleading": misleading,
        },
        "priorityOrdering": priority,
        "priorityOrderingPass": priority["status"] == "pass",
        "weightRangePass": all(weights_in_range) if weights_in_range else False,
        "weightTotalPass": weight_total_valid(actual),
        "metadataPresence": metadata,
        "metadataAlignment": alignment,
        "metadataPresencePass": metadata["pass"],
        "metadataAlignmentPass": alignment["pass"],
        "pipelineTracePass": pipeline_trace_pass(run),
        "fallbackRecoveries": run.get("audit", {}).get("fallbackRecoveries", []),
        "metrics": {
            "expectedCriterionRecall": round(recall, 4),
            "coreCriterionRecall": round(core_recall, 4),
            "criterionPrecision": round(criterion_precision, 4),
            "semanticCriterionPrecision": round(semantic_precision, 4),
            "partialCriterionCount": partial_count,
            "fullCriterionMatchCount": full_count,
            "semanticMatchCount": semantic_count,
            "typeAccuracy": round(type_accuracy, 4),
            "missingCoreCriterionCount": len(missing_core),
            "missingSupportingCriterionCount": len(matching["missingFullCriteria"]) - len(missing_core),
            "unexpectedCriterionCount": len(unexpected),
            "allowedAdditionalCriterionCount": len(additional),
            "forbiddenCriterionCount": len(forbidden),
            "evidenceContaminationCount": len(contamination),
            "wrongMergeCount": len(wrong_merge),
            "wrongSplitCount": len(split_groups),
            "overlyGenericNameCount": len(overly_generic),
            "sentenceCopyNameCount": len(sentence_copy),
            "misleadingNameCount": len(misleading),
            "weightRangePass": all(weights_in_range) if weights_in_range else False,
            "weightTotalPass": weight_total_valid(actual),
            "metadataPresencePass": metadata["pass"],
            "metadataAlignmentPass": alignment["pass"],
        },
        "scoreComponents": {
            "coreCriterionRecall": round(core_recall * 30, 2),
            "overallExpectedCriterionRecall": round(recall * 15, 2),
            "typeAccuracy": round(type_accuracy * 15, 2),
            "evidenceCleanliness": round(evidence_cleanliness * 15, 2),
            "forbiddenUnexpectedControl": round(control * 10, 2),
            "priorityOrdering": 10 if priority["status"] == "pass" else 0,
            "weightAndMetadata": 5 if weight_total_valid(actual) and metadata["pass"] else 0,
        },
        "totalDiagnosticScore": total_score,
    }


def evaluate_directory(results_dir: Path, fixtures_dir: Path) -> dict[str, Any]:
    fixtures = {item["benchmarkId"]: item for item in load_fixtures(fixtures_dir)}
    evaluations: list[dict[str, Any]] = []
    for path in sorted((results_dir / "raw").glob("*/*.json")):
        with path.open("r", encoding="utf-8") as handle:
            run = json.load(handle)
        fixture = fixtures[run["benchmarkId"]]
        evaluation = evaluate_run(fixture, run)
        evaluation["sourceFile"] = str(path)
        evaluations.append(evaluation)
    return {
        "resultsDir": str(results_dir),
        "fixtureCount": len(fixtures),
        "runCount": len(evaluations),
        "evaluations": evaluations,
    }


__all__ = [
    "ALLOWED_TYPES",
    "FULL_COVERAGE_THRESHOLD",
    "PARTIAL_COVERAGE_THRESHOLD",
    "assess_name_quality",
    "evaluate_directory",
    "evaluate_run",
    "forbidden_criteria",
    "load_fixtures",
    "mapped_source_ids",
    "match_actual_criteria",
    "metadata_alignment",
    "metadata_presence",
    "request_body",
    "validate_fixture",
    "weight_total_valid",
    "wrong_merges",
]
