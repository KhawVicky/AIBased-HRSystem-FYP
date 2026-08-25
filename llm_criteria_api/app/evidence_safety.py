"""Conservative evidence and same-capability guards for the API wrapper.

The frozen notebook pipeline remains the source of the decision logic.  These
helpers are installed temporarily by ``pipeline.py`` so the API can prevent a
transport-level grounding artefact from widening a criterion's evidence.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .model_output import normalise_model_output
from .name_validation import (
    morphological_root,
    normalised_unsupported_tokens,
    source_contributes_to_name,
)


ACTION_WORDS = {
    "administer", "administration", "analyse", "analysis", "analyze",
    "arrange", "assist", "coordinate", "coordination", "conduct",
    "comply", "compliance", "complete", "control", "document",
    "documentation", "ensure", "execute", "execution", "handle",
    "handling", "maintain", "maintenance", "manage", "management",
    "monitor", "monitoring", "operate", "operation", "operations",
    "perform", "prepare", "process", "processing", "provide", "reconcile",
    "reconciliation", "report", "reporting", "review", "screen",
    "screening", "source", "sourcing", "support", "supervise",
    "supervision", "troubleshoot", "use",
    "using", "work", "working",
}

GENERIC_CAPABILITY_WORDS = {
    "ability", "activities", "activity", "capability", "duties", "duty",
    "experience", "job", "knowledge", "professional", "relevant", "role",
    "skill", "skills", "task", "tasks", "the", "work",
    "a", "an", "and", "as", "at", "by", "for", "from", "in",
    "into", "of", "on", "or", "to", "with",
}

MODEL_GROUP_GENERIC_HEAD_ROOTS = {
    "administer",
    "control",
    "coordinate",
    "handle",
    "manage",
    "operate",
    "process",
    "workflow",
}

_FOREIGN_SCOPE_PATTERN = re.compile(
    r"\b(?:foreign[-\s]+workers?|expatriates?|immigration|permits?|hostel|"
    r"departure\s+arrangements?)\b",
    re.IGNORECASE,
)
_SECURITY_SCOPE_PATTERN = re.compile(
    r"\b(?:security\s+guards?|security\s+processes?|access\s+systems?|"
    r"cctv|security\s+management)\b",
    re.IGNORECASE,
)
_EMPLOYEE_RELATIONS_PATTERN = re.compile(
    r"\b(?:employee\s+relations?|grievances?|counselling|counseling|"
    r"disciplinary|motivation)\b",
    re.IGNORECASE,
)
_HR_PROCESS_PATTERN = re.compile(
    r"\b(?:recruitment|training|payroll|hr\s+process|human\s+resources?)\b",
    re.IGNORECASE,
)
_OPERATIONAL_ANCHOR_PATTERN = re.compile(
    r"\b(?:administration|operations?|housekeeping|cleanliness|canteen|"
    r"company\s+(?:cars?|vehicles?)|parking|5s)\b",
    re.IGNORECASE,
)
_COMPLIANCE_ANCHOR_PATTERN = re.compile(
    r"\b(?:iso\s*\d+|ohsas|safety|environmental|compliance|"
    r"company\s+policies?|standards?)\b",
    re.IGNORECASE,
)
_SUPPLY_PARTY_PATTERN = re.compile(
    r"\b(?:contractors?|suppliers?|vendors?)\b",
    re.IGNORECASE,
)
_STOCK_REPLENISHMENT_PATTERN = re.compile(
    r"\b(?:inventor(?:y|ies)|purchas(?:e|es|ing)|replenish\w*|"
    r"stock|supplies)\b",
    re.IGNORECASE,
)
_SUPPLY_CONTEXT_PATTERN = re.compile(
    r"\b(?:facility|office|plant|site|warehouse|workplace)\b",
    re.IGNORECASE,
)
_INVOICE_PATTERN = re.compile(r"\binvoic(?:e|es|ing)\b", re.IGNORECASE)
_VERIFICATION_PATTERN = re.compile(
    r"\b(?:check\w*|document\w*|review\w*|verif\w*)\b",
    re.IGNORECASE,
)
_MATCHING_PATTERN = re.compile(
    r"\b(?:match\w*|three[-\s]+way|two[-\s]+way)\b",
    re.IGNORECASE,
)
_COMMERCIAL_PATTERN = re.compile(
    r"\b(?:client\w*|customer\w*|lead\w*|opportunit\w*|prospect\w*|sales?)\b",
    re.IGNORECASE,
)
_SALES_PATTERN = re.compile(r"\bsales?\b", re.IGNORECASE)
_PIPELINE_PATTERN = re.compile(r"\bpipeline\b", re.IGNORECASE)
_FOLLOW_UP_PATTERN = re.compile(r"\bfollow[-\s]+up\b", re.IGNORECASE)


def _criterion_text(criterion: dict[str, Any]) -> str:
    return " ".join(
        [str(criterion.get("name", "")), *source_parts(criterion)]
    )


def _same_business_capability_domain(
    left: dict[str, Any],
    right: dict[str, Any],
) -> str | None:
    """Return a conservative domain only for adjacent, scorable capabilities."""

    left_text = _criterion_text(left)
    right_text = _criterion_text(right)
    left_foreign = bool(_FOREIGN_SCOPE_PATTERN.search(left_text))
    right_foreign = bool(_FOREIGN_SCOPE_PATTERN.search(right_text))
    if left_foreign or right_foreign:
        return "foreign_worker" if left_foreign and right_foreign else None

    left_security = bool(_SECURITY_SCOPE_PATTERN.search(left_text))
    right_security = bool(_SECURITY_SCOPE_PATTERN.search(right_text))
    if left_security or right_security:
        return "security_operations" if left_security and right_security else None

    left_employee = bool(_EMPLOYEE_RELATIONS_PATTERN.search(left_text))
    right_employee = bool(_EMPLOYEE_RELATIONS_PATTERN.search(right_text))
    left_hr = bool(_HR_PROCESS_PATTERN.search(left_text))
    right_hr = bool(_HR_PROCESS_PATTERN.search(right_text))
    if (left_employee and right_hr) or (right_employee and left_hr):
        return "hr_process_employee_relations"

    left_operations = bool(_OPERATIONAL_ANCHOR_PATTERN.search(left_text))
    right_operations = bool(_OPERATIONAL_ANCHOR_PATTERN.search(right_text))
    left_compliance = bool(_COMPLIANCE_ANCHOR_PATTERN.search(left_text))
    right_compliance = bool(_COMPLIANCE_ANCHOR_PATTERN.search(right_text))
    if (left_operations and right_compliance) or (
        right_operations and left_compliance
    ):
        return "operational_compliance"
    return None


def _merged_capability_name(
    existing: dict[str, Any],
    candidate: dict[str, Any],
    domain: str | None,
) -> str:
    if domain == "hr_process_employee_relations":
        return "HR Process and Employee Relations Management"
    if domain == "operational_compliance":
        return "Administration, ISO and Safety Compliance"
    if domain == "foreign_worker":
        return "Foreign Worker Management"
    if domain == "security_operations":
        return "Security Operations Management"
    return str(existing.get("name") or candidate.get("name") or "")


def _source_aligned_metadata(
    items: list[dict[str, Any]],
    source_texts: list[str],
) -> tuple[list[Any], list[Any]]:
    """Merge per-source IDs and scores without collapsing equal values."""

    records: list[tuple[str, Any, Any]] = []
    for item in items:
        parts = source_parts(item)
        source_ids = item.get("sourceIds")
        scores = item.get("groundingScores")
        if not (
            isinstance(source_ids, list)
            and isinstance(scores, list)
            and len(source_ids) == len(parts)
            and len(scores) == len(parts)
        ):
            return [], []
        records.extend(
            (part, source_ids[index], scores[index])
            for index, part in enumerate(parts)
        )

    by_source = {source: (source_id, score) for source, source_id, score in records}
    if any(source not in by_source for source in source_texts):
        return [], []
    return (
        [by_source[source][0] for source in source_texts],
        [by_source[source][1] for source in source_texts],
    )


def is_generic_duty_safe(
    text: str,
    frozen: Any | None = None,
    frozen_detector: Any | None = None,
) -> bool:
    """Use frozen filtering plus conservative coverage for common variants.

    The production notebook uses exact full-string patterns.  The API may
    receive harmless wording variants (for example ``form time to time`` or
    ``top management``), so this wrapper normalises only the generic-duty
    boundary.  It never classifies a sentence with a job-specific object as a
    generic duty.
    """

    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" .;:")
    if not cleaned:
        return False
    detector = frozen_detector
    if detector is None and frozen is not None:
        detector = frozen.is_generic_duty
    if detector is not None and detector(cleaned):
        return True

    lowered = cleaned.casefold()
    if re.search(
        r"\b(?:follow|adhere\s+to|comply\s+with)\b.*\b(?:company\s+)?"
        r"(?:polic(?:y|ies)|procedures?|rules?|guidelines?)\b",
        lowered,
    ):
        return True
    if re.search(
        r"\b(?:support\s+(?:the\s+)?management\s+when\s+required|"
        r"perform\s+other\s+dut(?:y|ies)\s+as\s+assigned|"
        r"complete\s+other\s+tasks?\s+as\s+instructed)\b",
        lowered,
    ):
        return True
    # Attendance at a recurring departmental/staff meeting is routine context,
    # not a standalone resume capability. Keep verbs that describe owning the
    # meeting (chairing, facilitating, organising or presenting) assessable.
    if (
        re.search(
            r"\bparticipat(?:e|es|ed|ing)\s+in\b.*\b"
            r"(?:monthly|weekly|regular|departmental|staff)\s+meeting\b",
            lowered,
        )
        and not re.search(
            r"\b(?:chair|lead|facilitat|organis|organiz|present|report)\w*\b",
            lowered,
        )
    ):
        return True
    has_generic_object = re.search(
        r"\b(?:any\s+other\s+)?(?:ad\s*hoc\s+)?"
        r"(?:dut(?:y|ies)|task(?:s)?|assignment(?:s)?|"
        r"responsibilit(?:y|ies)|activit(?:y|ies))\b",
        lowered,
    )
    has_assignment_context = re.search(
        r"\b(?:assigned|instructed|required|requested|"
        r"may\s+be\s+assigned|from\s+time\s+to\s+time|"
        r"form\s+time\s+to\s+time)\b",
        lowered,
    )
    has_management_context = re.search(
        r"\b(?:management|manager|supervisor|superior)\b", lowered
    )
    return bool(
        has_generic_object
        and (has_assignment_context or has_management_context)
    )


def is_broad_overview_source(source_text: str) -> bool:
    """Recognise a scope-list sentence used as context, not a capability."""

    return (
        source_text.count(",") >= 5
        and source_text.casefold().count(" and ") >= 2
    )


def source_parts(criterion: dict[str, Any]) -> list[str]:
    return [
        part.strip()
        for part in str(criterion.get("sourceText", "")).split("|")
        if part.strip()
    ]


_CONJUNCTIVE_NAME_SPLIT_PATTERN = re.compile(
    r"\s+(?:and|&)\s+",
    re.IGNORECASE,
)

_COMPONENT_GENERIC_WORDS = GENERIC_CAPABILITY_WORDS | {
    "candidate",
    "professional",
}


def _component_roots(value: str) -> set[str]:
    """Return the evidence-bearing roots in one criterion-name conjunct."""

    return {
        root
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in _COMPONENT_GENERIC_WORDS
        if len(root := morphological_root(token)) > 2
    }


def _source_roots(value: str) -> set[str]:
    return {
        root
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(root := morphological_root(token)) > 2
    }


def _aligned_source_records(
    criterion: dict[str, Any],
) -> list[dict[str, Any]] | None:
    parts = source_parts(criterion)
    source_ids = criterion.get("sourceIds")
    grounding_scores = criterion.get("groundingScores")
    if not (
        len(parts) >= 2
        and isinstance(source_ids, list)
        and isinstance(grounding_scores, list)
        and len(parts) == len(source_ids) == len(grounding_scores)
    ):
        return None
    return [
        {
            "sourceText": part,
            "sourceId": source_ids[index],
            "groundingScore": grounding_scores[index],
        }
        for index, part in enumerate(parts)
    ]


def _criterion_with_source_records(
    criterion: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    name: str | None = None,
    criterion_id: str | None = None,
) -> dict[str, Any]:
    updated = dict(criterion)
    if name is not None:
        updated["name"] = name
    if criterion_id is not None:
        updated["criterionId"] = criterion_id
    updated["sourceText"] = " | ".join(
        str(record["sourceText"]) for record in records
    )
    updated["sourceIds"] = [record["sourceId"] for record in records]
    updated["groundingScores"] = [
        record["groundingScore"] for record in records
    ]
    return updated


def decompose_incoherent_multisource_criteria(
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Prune misassigned sources and split evidence-partitioned umbrellas.

    A coherent multi-source criterion must retain evidence that contributes to
    its name. When no concrete object is shared across the retained sources,
    a conjunctive name is split only if each conjunct is fully supported by a
    distinct source subset. Unassigned evidence is intentionally left for the
    completeness-recovery stage instead of being hidden inside an umbrella.
    """

    result: list[dict[str, Any]] = []
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []
    used_ids = {
        str(item.get("criterionId", "")).strip().casefold()
        for item in criteria
        if str(item.get("criterionId", "")).strip()
    }

    def unique_part_id(base: str, part_index: int) -> str:
        candidate = f"{base}-part-{part_index}"
        suffix = part_index
        while candidate.casefold() in used_ids:
            suffix += 1
            candidate = f"{base}-part-{suffix}"
        used_ids.add(candidate.casefold())
        return candidate

    for criterion_index, criterion in enumerate(criteria, start=1):
        records = _aligned_source_records(criterion)
        if records is None or criterion.get("type") != "relevant_skill":
            result.append(criterion)
            continue

        name = re.sub(r"\s+", " ", str(criterion.get("name", ""))).strip()
        aligned_records = [
            record
            for record in records
            if source_contributes_to_name(name, str(record["sourceText"]))
        ]
        removed_records = [
            record for record in records if record not in aligned_records
        ]
        if not aligned_records:
            # The frozen validator accepted the criterion as a whole. Do not
            # erase it when the name is too generic for source-level routing.
            result.append(criterion)
            continue

        working = _criterion_with_source_records(criterion, aligned_records)
        if removed_records:
            warnings.append(
                f"Criterion {name} released {len(removed_records)} source "
                "fragment(s) whose concrete wording did not support its name."
            )
            audit.append(
                {
                    "kind": "source_prune",
                    "criterion": name,
                    "keptSourceIds": [record["sourceId"] for record in aligned_records],
                    "releasedSourceIds": [record["sourceId"] for record in removed_records],
                }
            )

        if len(aligned_records) < 2:
            result.append(working)
            continue

        shared_objects = set.intersection(
            *(meaningful_object_tokens(str(record["sourceText"])) for record in aligned_records)
        )
        if shared_objects:
            result.append(working)
            continue

        components = [
            component.strip(" ,")
            for component in _CONJUNCTIVE_NAME_SPLIT_PATTERN.split(name)
            if component.strip(" ,")
        ]
        if not 2 <= len(components) <= 3:
            result.append(working)
            continue

        # Preserve the first conjunct's concrete object when a following
        # conjunct is only an action head. This prevents the decomposition
        # itself from creating a bare generic name.
        first_component_objects = meaningful_object_tokens(components[0])
        if first_component_objects:
            prefix_tokens = [
                token
                for token in re.findall(r"[A-Za-z0-9-]+", components[0])
                if morphological_root(token) in first_component_objects
            ][:2]
            if prefix_tokens:
                components = [
                    components[0],
                    *[
                        (
                            " ".join([*prefix_tokens, component])
                            if not meaningful_object_tokens(component)
                            else component
                        )
                        for component in components[1:]
                    ],
                ]

        assignments: list[tuple[str, list[dict[str, Any]]]] = []
        assigned_source_ids: set[str] = set()
        for component in components:
            roots = _component_roots(component)
            if not roots:
                assignments = []
                break
            matches = [
                record
                for record in aligned_records
                if roots <= _source_roots(str(record["sourceText"]))
                and str(record["sourceId"]) not in assigned_source_ids
            ]
            if not matches:
                assignments = []
                break
            assignments.append((component, matches))
            assigned_source_ids.update(str(record["sourceId"]) for record in matches)

        if len(assignments) < 2:
            result.append(working)
            continue

        base_id = str(criterion.get("criterionId", "")).strip() or (
            f"criterion-{criterion_index}"
        )
        split_items: list[dict[str, Any]] = []
        for part_index, (component, component_records) in enumerate(assignments, start=1):
            part_id = base_id if part_index == 1 else unique_part_id(base_id, part_index)
            split_items.append(
                _criterion_with_source_records(
                    working,
                    component_records,
                    name=component,
                    criterion_id=part_id,
                )
            )
        result.extend(split_items)
        unassigned_records = [
            record
            for record in aligned_records
            if str(record["sourceId"]) not in assigned_source_ids
        ]
        warnings.append(
            f"Criterion {name} was decomposed into independently evidenced "
            "conjuncts before completeness recovery."
        )
        audit.append(
            {
                "kind": "conjunctive_decomposition",
                "criterion": name,
                "resultNames": [item["name"] for item in split_items],
                "resultSourceIds": [list(item["sourceIds"]) for item in split_items],
                "releasedSourceIds": [record["sourceId"] for record in unassigned_records],
            }
        )

    return result, warnings, audit


def meaningful_object_tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", value.casefold())
    result: set[str] = set()
    for token in tokens:
        root = morphological_root(token)
        if root in ACTION_WORDS or token in ACTION_WORDS:
            continue
        if root in GENERIC_CAPABILITY_WORDS or token in GENERIC_CAPABILITY_WORDS:
            continue
        if len(root) > 2:
            result.add(root)
    return result


def evidence_object_tokens(criterion: dict[str, Any]) -> set[str]:
    parts = source_parts(criterion)
    specific_parts = [part for part in parts if not is_broad_overview_source(part)]
    if specific_parts:
        parts = specific_parts
    text = " ".join([str(criterion.get("name", "")), *parts])
    return meaningful_object_tokens(text)


def same_capability_with_object_alignment(
    original_same: Any,
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    """Apply the frozen predicate only after a non-verb object check.

    This intentionally errs on the side of preserving separate criteria.  A
    shared action such as ``monitor`` is not a business capability; the
    criteria must also share a meaningful object or process area.
    """

    if left.get("type") != right.get("type"):
        return False

    left_sources = source_parts(left)
    right_sources = source_parts(right)
    if (
        left_sources
        and right_sources
        and {part.casefold() for part in left_sources}
        == {part.casefold() for part in right_sources}
    ):
        return original_same(left, right)

    left_text = _criterion_text(left)
    right_text = _criterion_text(right)
    for scope_pattern in (
        _FOREIGN_SCOPE_PATTERN,
        _SECURITY_SCOPE_PATTERN,
        _EMPLOYEE_RELATIONS_PATTERN,
    ):
        if bool(scope_pattern.search(left_text)) != bool(
            scope_pattern.search(right_text)
        ):
            return False

    left_objects = evidence_object_tokens(left)
    right_objects = evidence_object_tokens(right)
    shared_objects = left_objects & right_objects
    smaller_object_count = min(len(left_objects), len(right_objects))
    object_overlap = (
        len(shared_objects) / smaller_object_count
        if smaller_object_count
        else 0.0
    )
    if object_overlap >= (2 / 3) and original_same(left, right):
        return True
    return bool(
        shared_objects
        and _same_business_capability_domain(left, right)
        in {"foreign_worker", "security_operations"}
    )


def safe_merge_duplicate_criteria(
    criteria: list[dict[str, Any]],
    frozen: Any,
    same_capability: Any,
) -> list[dict[str, Any]]:
    """Use the frozen metadata merge shape with a conservative merge guard."""

    merged: list[dict[str, Any]] = []
    for candidate in criteria:
        duplicate = next(
            (
                existing
                for existing in merged
                if same_capability(existing, candidate)
                and not frozen.criterion_name_unsupported_tokens(
                    existing["name"],
                    existing["sourceText"] + " | " + candidate["sourceText"],
                )
            ),
            None,
        )
        if duplicate is None:
            merged.append(candidate.copy())
            continue
        domain = _same_business_capability_domain(duplicate, candidate)
        sources = duplicate["sourceText"].split(" | ") + candidate[
            "sourceText"
        ].split(" | ")
        merged_sources = list(dict.fromkeys(sources))
        source_ids, grounding_scores = _source_aligned_metadata(
            [duplicate, candidate],
            merged_sources,
        )
        duplicate["sourceText"] = " | ".join(merged_sources)
        if domain is not None:
            proposed_name = _merged_capability_name(
                duplicate,
                candidate,
                domain,
            )
            if not frozen.criterion_name_unsupported_tokens(
                proposed_name,
                duplicate["sourceText"],
            ):
                duplicate["name"] = proposed_name
        duplicate["sourceIds"] = source_ids
        duplicate["groundingScores"] = grounding_scores
        duplicate["sourceCriterionIds"] = list(
            dict.fromkeys(
                [
                    *duplicate.get("sourceCriterionIds", []),
                    *candidate.get("sourceCriterionIds", []),
                ]
            )
        )
    return merged


def _has_contiguous_single_sources(members: list[dict[str, Any]]) -> bool:
    if any(len(source_parts(item)) != 1 for item in members):
        return False
    source_ids = [
        str(source_id)
        for item in members
        for source_id in item.get("sourceIds", [])
    ]
    if len(source_ids) != len(members) or len(source_ids) != len(set(source_ids)):
        return False
    parsed = [
        re.fullmatch(r"(responsibilities|requirements|qualifications)-(\d+)", source_id)
        for source_id in source_ids
    ]
    if any(match is None for match in parsed):
        return False
    sections = {match.group(1) for match in parsed if match is not None}
    positions = sorted(int(match.group(2)) for match in parsed if match is not None)
    return len(sections) == 1 and positions == list(
        range(positions[0], positions[0] + len(positions))
    )


def apply_semantic_consolidation_plan(
    criteria: list[dict[str, Any]],
    raw_plan: str,
    frozen: Any,
) -> tuple[
    list[dict[str, Any]],
    list[str],
    list[dict[str, Any]],
    list[str],
]:
    """Apply only evidence-verifiable pairs and renames from an isolated review."""

    normalised, _fence_applied = normalise_model_output(raw_plan)
    try:
        payload = json.loads(normalised)
    except json.JSONDecodeError as error:
        return criteria, [], [], [f"Malformed consolidation JSON: {error.msg}"]
    if not isinstance(payload, dict) or not isinstance(payload.get("groups"), list):
        return criteria, [], [], ["Semantic consolidation groups is not a list."]
    raw_renames = payload.get("renames", [])
    if not isinstance(raw_renames, list):
        return criteria, [], [], ["Semantic consolidation renames is not a list."]

    criteria_by_id = {
        str(item.get("criterionId", "")).strip().casefold(): (index, item)
        for index, item in enumerate(criteria)
        if str(item.get("criterionId", "")).strip()
    }
    accepted_by_first_index: dict[int, dict[str, Any]] = {}
    accepted_renames_by_index: dict[int, dict[str, Any]] = {}
    consumed_indices: set[int] = set()
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []
    errors: list[str] = []

    for group_index, group in enumerate(payload["groups"], start=1):
        if not isinstance(group, dict):
            errors.append(f"Semantic group {group_index} is not an object.")
            continue
        raw_member_ids = group.get("memberIds")
        member_ids = (
            [str(value).strip().casefold() for value in raw_member_ids]
            if isinstance(raw_member_ids, list)
            else []
        )
        if len(member_ids) != 2 or len(set(member_ids)) != 2:
            errors.append(
                f"Semantic group {group_index} must contain exactly two unique IDs."
            )
            continue
        if any(member_id not in criteria_by_id for member_id in member_ids):
            errors.append(f"Semantic group {group_index} contains an unknown ID.")
            continue
        member_records = [criteria_by_id[member_id] for member_id in member_ids]
        member_indices = [record[0] for record in member_records]
        members = [record[1] for record in member_records]
        if any(index in consumed_indices for index in member_indices):
            errors.append(f"Semantic group {group_index} reuses a criterion ID.")
            continue
        if (
            str(group.get("type", "")).strip() != "relevant_skill"
            or {str(item.get("type", "")) for item in members}
            != {"relevant_skill"}
        ):
            errors.append(f"Semantic group {group_index} crosses the skill boundary.")
            continue
        if not _has_contiguous_single_sources(members):
            errors.append(
                f"Semantic group {group_index} is not an adjacent singleton-source pair."
            )
            continue

        group_name = re.sub(r"\s+", " ", str(group.get("name", ""))).strip()
        if not 2 <= len(group_name.split()) <= 8:
            errors.append(f"Semantic group {group_index} has an invalid name length.")
            continue
        shared_objects = set.intersection(
            *(evidence_object_tokens(item) for item in members)
        )
        if not shared_objects:
            errors.append(
                f"Semantic group {group_index} has no shared grounded object."
            )
            continue

        merged_sources = [part for item in members for part in source_parts(item)]
        if any(
            not source_contributes_to_name(group_name, source)
            for source in merged_sources
        ):
            errors.append(
                f"Semantic group {group_index} name is not grounded in every source."
            )
            continue
        combined_evidence = " | ".join(merged_sources)
        unsupported_group_tokens = normalised_unsupported_tokens(
            frozen.criterion_name_unsupported_tokens,
            group_name,
            combined_evidence,
        )
        if any(
            morphological_root(token) not in MODEL_GROUP_GENERIC_HEAD_ROOTS
            and morphological_root(token) not in ACTION_WORDS
            for token in unsupported_group_tokens
        ):
            errors.append(
                f"Semantic group {group_index} name introduces unsupported wording."
            )
            continue
        source_ids, grounding_scores = _source_aligned_metadata(
            members,
            merged_sources,
        )
        if not source_ids or not grounding_scores:
            errors.append(
                f"Semantic group {group_index} has misaligned source metadata."
            )
            continue

        merged = dict(members[0])
        merged["name"] = group_name
        merged["sourceText"] = combined_evidence
        merged["sourceIds"] = source_ids
        merged["groundingScores"] = grounding_scores
        merged["sourceCriterionIds"] = list(
            dict.fromkeys(
                source_id
                for item in members
                for source_id in item.get("sourceCriterionIds", [])
                if str(source_id).strip()
            )
        )
        lineage = [
            str(item.get("criterionId", "")).strip()
            for item in members
            if str(item.get("criterionId", "")).strip()
        ]
        if lineage:
            merged["mergedFromIds"] = lineage
        merged["importance"] = max(
            (str(item.get("importance", "medium")) for item in members),
            key=lambda value: {"low": 1, "medium": 2, "high": 3}.get(value, 2),
        )

        first_index = min(member_indices)
        accepted_by_first_index[first_index] = merged
        consumed_indices.update(member_indices)
        warnings.append(
            f"Consolidated adjacent grounded fragments as '{group_name}'."
        )
        audit.append(
            {
                "kind": "group",
                "name": group_name,
                "memberCriterionIds": lineage,
                "sharedObjectRoots": sorted(shared_objects),
            }
        )

    seen_rename_ids: set[str] = set()
    for rename_index, rename in enumerate(raw_renames, start=1):
        if not isinstance(rename, dict):
            errors.append(f"Semantic rename {rename_index} is not an object.")
            continue
        criterion_id = str(rename.get("id", "")).strip().casefold()
        if not criterion_id or criterion_id not in criteria_by_id:
            errors.append(f"Semantic rename {rename_index} contains an unknown ID.")
            continue
        if criterion_id in seen_rename_ids:
            errors.append(f"Semantic rename {rename_index} reuses a criterion ID.")
            continue
        seen_rename_ids.add(criterion_id)
        criterion_index, criterion = criteria_by_id[criterion_id]
        if criterion_index in consumed_indices:
            errors.append(f"Semantic rename {rename_index} targets a grouped criterion.")
            continue
        if str(criterion.get("type", "")) != "relevant_skill":
            errors.append(f"Semantic rename {rename_index} crosses the skill boundary.")
            continue
        source_texts = source_parts(criterion)
        source_ids = criterion.get("sourceIds")
        if not (
            len(source_texts) == 1
            and isinstance(source_ids, list)
            and len(source_ids) == 1
        ):
            errors.append(
                f"Semantic rename {rename_index} is not a singleton-source criterion."
            )
            continue

        proposed_name = re.sub(
            r"\s+", " ", str(rename.get("name", ""))
        ).strip()
        if not 2 <= len(proposed_name.split()) <= 8:
            errors.append(f"Semantic rename {rename_index} has an invalid name length.")
            continue
        if proposed_name.casefold() == str(criterion.get("name", "")).casefold():
            errors.append(f"Semantic rename {rename_index} does not change the name.")
            continue

        proposed_objects = meaningful_object_tokens(proposed_name)
        current_objects = meaningful_object_tokens(str(criterion.get("name", "")))
        grounded_objects = evidence_object_tokens(criterion)
        if (
            len(proposed_objects) < 2
            or not proposed_objects <= grounded_objects
            or not (proposed_objects - current_objects)
        ):
            errors.append(
                f"Semantic rename {rename_index} does not add grounded source objects."
            )
            continue
        if not source_contributes_to_name(proposed_name, source_texts[0]):
            errors.append(
                f"Semantic rename {rename_index} is not grounded in its source."
            )
            continue
        unsupported_rename_tokens = normalised_unsupported_tokens(
            frozen.criterion_name_unsupported_tokens,
            proposed_name,
            source_texts[0],
        )
        if any(
            morphological_root(token) not in MODEL_GROUP_GENERIC_HEAD_ROOTS
            and morphological_root(token) not in ACTION_WORDS
            for token in unsupported_rename_tokens
        ):
            errors.append(
                f"Semantic rename {rename_index} introduces unsupported wording."
            )
            continue

        renamed = dict(criterion)
        renamed["name"] = proposed_name
        accepted_renames_by_index[criterion_index] = renamed
        warnings.append(
            f"Expanded an under-specified grounded name to '{proposed_name}'."
        )
        audit.append(
            {
                "kind": "rename",
                "name": proposed_name,
                "criterionId": str(criterion.get("criterionId", "")).strip(),
                "addedObjectRoots": sorted(proposed_objects - current_objects),
            }
        )

    result: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if index in accepted_by_first_index:
            result.append(accepted_by_first_index[index])
        elif index in accepted_renames_by_index:
            result.append(accepted_renames_by_index[index])
        elif index not in consumed_indices:
            result.append(criterion)
    return result, warnings, audit, errors


def consolidate_adjacent_supply_operations(
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Join one vendor-facing source with its adjacent stock-replenishment source.

    The boundary is deliberately lexical and narrow: both items must be
    singleton-source skills in consecutive positions of one JD section, one
    source must name an external supply party, the other must name stock or
    replenishment, and both must repeat the same physical operating context.
    This avoids treating ordinary adjacent finance or payment stages as one
    capability.
    """

    replacements: dict[int, dict[str, Any]] = {}
    consumed_indices: set[int] = set()
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []
    context_priority = (
        "office",
        "workplace",
        "warehouse",
        "plant",
        "facility",
        "site",
    )

    for left_index in range(len(criteria) - 1):
        right_index = left_index + 1
        if left_index in consumed_indices or right_index in consumed_indices:
            continue
        members = [criteria[left_index], criteria[right_index]]
        if {str(item.get("type", "")) for item in members} != {"relevant_skill"}:
            continue
        if not _has_contiguous_single_sources(members):
            continue

        texts = [_criterion_text(item) for item in members]
        party_matches = [bool(_SUPPLY_PARTY_PATTERN.search(text)) for text in texts]
        stock_matches = [
            bool(_STOCK_REPLENISHMENT_PATTERN.search(text)) for text in texts
        ]
        if sum(party_matches) != 1 or sum(stock_matches) != 1:
            continue
        party_index = party_matches.index(True)
        stock_index = stock_matches.index(True)
        if party_index == stock_index:
            continue

        contexts = [
            {match.group(0).casefold() for match in _SUPPLY_CONTEXT_PATTERN.finditer(text)}
            for text in texts
        ]
        shared_contexts = contexts[0] & contexts[1]
        context = next(
            (value for value in context_priority if value in shared_contexts),
            None,
        )
        if context is None:
            continue

        party_text = texts[party_index]
        if re.search(r"\bsuppliers?\b", party_text, re.IGNORECASE):
            party_label = "Supplier"
        elif re.search(r"\bvendors?\b", party_text, re.IGNORECASE):
            party_label = "Vendor"
        else:
            party_label = "Contractor"
        stock_text = texts[stock_index]
        if re.search(r"\bstock\b", stock_text, re.IGNORECASE):
            stock_label = "Stock"
        elif re.search(r"\binventor(?:y|ies)\b", stock_text, re.IGNORECASE):
            stock_label = "Inventory"
        else:
            stock_label = "Supply"
        merged_name = (
            f"{context.title()} {party_label} and {stock_label} Coordination"
        )

        merged_sources = [part for item in members for part in source_parts(item)]
        source_ids, grounding_scores = _source_aligned_metadata(
            members,
            merged_sources,
        )
        if not source_ids or not grounding_scores:
            continue

        merged = dict(members[0])
        merged["name"] = merged_name
        merged["sourceText"] = " | ".join(merged_sources)
        merged["sourceIds"] = source_ids
        merged["groundingScores"] = grounding_scores
        merged["sourceCriterionIds"] = list(
            dict.fromkeys(
                source_id
                for item in members
                for source_id in item.get("sourceCriterionIds", [])
                if str(source_id).strip()
            )
        )
        lineage: list[str] = []
        for item in members:
            prior = item.get("mergedFromIds")
            if isinstance(prior, list) and prior:
                lineage.extend(str(value) for value in prior if str(value).strip())
            elif str(item.get("criterionId", "")).strip():
                lineage.append(str(item["criterionId"]).strip())
        if lineage:
            merged["mergedFromIds"] = list(dict.fromkeys(lineage))
        merged["importance"] = max(
            (str(item.get("importance", "medium")) for item in members),
            key=lambda value: {"low": 1, "medium": 2, "high": 3}.get(value, 2),
        )

        replacements[left_index] = merged
        consumed_indices.update({left_index, right_index})
        warnings.append(
            f"Consolidated adjacent grounded supply operations as '{merged_name}'."
        )
        audit.append(
            {
                "name": merged_name,
                "memberCriterionIds": list(merged.get("mergedFromIds", [])),
                "sourceIds": list(source_ids),
                "sharedContext": context,
            }
        )

    result: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if index in replacements:
            result.append(replacements[index])
        elif index not in consumed_indices:
            result.append(criterion)
    return result, warnings, audit


def consolidate_grounded_workflow_relations(
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Join two narrowly recognised, source-consecutive workflow relations.

    The supported relations are evidence-level semantics rather than role
    mappings: invoice verification followed by invoice matching, and sales
    pipeline work paired with commercial follow-up. Both items must remain
    singleton-source skills from consecutive positions in one JD section.
    """

    replacements: dict[int, dict[str, Any]] = {}
    consumed_indices: set[int] = set()
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []

    for left_index, left in enumerate(criteria):
        if left_index in consumed_indices:
            continue
        for right_index in range(left_index + 1, len(criteria)):
            if right_index in consumed_indices:
                continue
            right = criteria[right_index]
            members = [left, right]
            if {str(item.get("type", "")) for item in members} != {
                "relevant_skill"
            }:
                continue
            if not _has_contiguous_single_sources(members):
                continue

            texts = [_criterion_text(item) for item in members]
            invoice_verification = [
                bool(_INVOICE_PATTERN.search(text))
                and bool(_VERIFICATION_PATTERN.search(text))
                and not bool(_MATCHING_PATTERN.search(text))
                for text in texts
            ]
            invoice_matching = [
                bool(_INVOICE_PATTERN.search(text))
                and bool(_MATCHING_PATTERN.search(text))
                for text in texts
            ]
            pipeline = [
                bool(_PIPELINE_PATTERN.search(text))
                and bool(_COMMERCIAL_PATTERN.search(text))
                for text in texts
            ]
            follow_up = [
                bool(_FOLLOW_UP_PATTERN.search(text))
                and bool(_COMMERCIAL_PATTERN.search(text))
                for text in texts
            ]

            relation: str | None = None
            merged_name = ""
            if (
                sum(invoice_verification) == 1
                and sum(invoice_matching) == 1
                and invoice_verification.index(True) != invoice_matching.index(True)
            ):
                relation = "invoice_verification_matching"
                merged_name = "Invoice Verification and Matching"
            elif (
                sum(pipeline) == 1
                and sum(follow_up) == 1
                and pipeline.index(True) != follow_up.index(True)
                and any(_SALES_PATTERN.search(text) for text in texts)
            ):
                relation = "commercial_pipeline_follow_up"
                merged_name = "Sales Pipeline and Follow-Up Management"
            if relation is None:
                continue

            ordered_members = sorted(
                members,
                key=lambda item: int(
                    str(item.get("sourceIds", [""])[0]).rsplit("-", 1)[1]
                ),
            )
            merged_sources = [
                part for item in ordered_members for part in source_parts(item)
            ]
            source_ids, grounding_scores = _source_aligned_metadata(
                ordered_members,
                merged_sources,
            )
            if not source_ids or not grounding_scores:
                continue

            merged = dict(left)
            merged["name"] = merged_name
            merged["sourceText"] = " | ".join(merged_sources)
            merged["sourceIds"] = source_ids
            merged["groundingScores"] = grounding_scores
            merged["sourceCriterionIds"] = list(
                dict.fromkeys(
                    source_id
                    for item in ordered_members
                    for source_id in item.get("sourceCriterionIds", [])
                    if str(source_id).strip()
                )
            )
            lineage: list[str] = []
            for item in ordered_members:
                prior = item.get("mergedFromIds")
                if isinstance(prior, list) and prior:
                    lineage.extend(
                        str(value) for value in prior if str(value).strip()
                    )
                elif str(item.get("criterionId", "")).strip():
                    lineage.append(str(item["criterionId"]).strip())
            if lineage:
                merged["mergedFromIds"] = list(dict.fromkeys(lineage))
            merged["importance"] = max(
                (str(item.get("importance", "medium")) for item in members),
                key=lambda value: {
                    "low": 1,
                    "medium": 2,
                    "high": 3,
                }.get(value, 2),
            )

            replacements[left_index] = merged
            consumed_indices.update({left_index, right_index})
            warnings.append(
                f"Consolidated grounded {relation.replace('_', ' ')} workflow "
                f"as '{merged_name}'."
            )
            audit.append(
                {
                    "relation": relation,
                    "name": merged_name,
                    "memberCriterionIds": list(
                        merged.get("mergedFromIds", [])
                    ),
                    "sourceIds": list(source_ids),
                }
            )
            break

    result: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if index in replacements:
            result.append(replacements[index])
        elif index not in consumed_indices:
            result.append(criterion)
    return result, warnings, audit


def safe_can_merge_group(
    members: list[dict[str, Any]],
    same_capability: Any,
) -> bool:
    if len(members) <= 1:
        return True
    if len({item.get("type") for item in members}) != 1:
        return False
    return all(
        same_capability(left, right)
        for left_index, left in enumerate(members)
        for right in members[left_index + 1 :]
    )


def remove_generic_evidence(
    criteria: list[dict[str, Any]],
    frozen: Any,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Remove generic-duty source fragments and keep metadata aligned."""

    kept: list[dict[str, Any]] = []
    warnings: list[str] = []
    rejected: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria, start=1):
        parts = [part.strip() for part in str(criterion.get("sourceText", "")).split("|") if part.strip()]
        keep_indices = [
            index
            for index, part in enumerate(parts)
            if not is_generic_duty_safe(part, frozen)
        ]
        removed_parts = [part for index, part in enumerate(parts) if index not in keep_indices]
        if not removed_parts:
            kept.append(criterion)
            continue

        name = criterion.get("name", f"criterion-{index}")
        warnings.append(
            f"Criterion {name} had generic-duty evidence removed before final output."
        )
        if not keep_indices:
            rejected.append(
                {
                    "criterion": name,
                    "reason": "generic-duty-only evidence",
                    "sourceText": " | ".join(removed_parts),
                }
            )
            continue

        cleaned = dict(criterion)
        cleaned["sourceText"] = " | ".join(parts[index] for index in keep_indices)
        for metadata_key in ("sourceIds", "groundingScores"):
            values = cleaned.get(metadata_key)
            if isinstance(values, list) and len(values) == len(parts):
                cleaned[metadata_key] = [values[index] for index in keep_indices]
            elif values:
                # Do not leave metadata claiming support for a removed source.
                cleaned[metadata_key] = []
                warnings.append(
                    f"Criterion {name} {metadata_key} was cleared because source alignment was ambiguous."
                )
        kept.append(cleaned)
    return kept, warnings, rejected


def _name_object_tokens(criterion: dict[str, Any]) -> set[str]:
    """Return concrete objects from the name, excluding action words."""

    tokens = re.findall(r"[a-z0-9]+", str(criterion.get("name", "")).casefold())
    preserved_nouns = {
        "administration",
        "compliance",
        "control",
        "documentation",
        "management",
        "operation",
        "operations",
        "process",
    }
    result: set[str] = set()
    for token in tokens:
        root = morphological_root(token)
        if token in GENERIC_CAPABILITY_WORDS:
            continue
        if token in preserved_nouns:
            result.add(root)
            continue
        if root in ACTION_WORDS or token in ACTION_WORDS:
            continue
        if len(root) > 2:
            result.add(root)
    return result


def _nominal_source_tokens(source: str) -> set[str]:
    """Keep capability nouns that also occur as action-derived forms."""

    preserved_nouns = {
        "administration",
        "compliance",
        "control",
        "documentation",
        "management",
        "operation",
        "operations",
        "process",
    }
    return {
        morphological_root(token)
        for token in re.findall(r"[a-z0-9]+", source.casefold())
        if token in preserved_nouns
    }


def _source_supports_name(source: str, name_objects: set[str]) -> bool:
    if not name_objects:
        return True
    return bool(
        name_objects
        & (meaningful_object_tokens(source) | _nominal_source_tokens(source))
    )


_EDUCATION_EVIDENCE_PATTERN = re.compile(
    r"\b(?:academic|bachelor(?:['\u2019]s)?|degree|diploma|education|"
    r"field\s+of\s+study|major(?:ed|ing)?|master(?:['\u2019]s)?|phd|"
    r"qualification)\b",
    re.IGNORECASE,
)
_EDUCATION_FIELD_PATTERN = re.compile(
    r"\b(?:academic\s+)?(?:degree|diploma|bachelor(?:['\u2019]s)?|"
    r"master(?:['\u2019]s)?|ph\.?d\.?)\s+(?:in|of)\s+[A-Za-z]"
    r"|\b(?:field\s+of\s+study|major(?:ed|ing)?|academic\s+discipline)"
    r"\s+(?:in\s+)?[A-Za-z]",
    re.IGNORECASE,
)


def _source_has_education_field(source: str) -> bool:
    if _EDUCATION_FIELD_PATTERN.search(source):
        return True
    preceding = re.search(
        r"\b(?P<field>[A-Za-z][A-Za-z&/, -]{1,70})\s+"
        r"(?:degree|diploma)\b",
        source,
        re.IGNORECASE,
    )
    if not preceding:
        return False
    generic = {
        "a", "an", "the", "minimum", "min", "or", "and", "related",
        "relevant", "recognized", "recognised", "required", "preferred",
        "bachelor", "bachelors", "master", "masters", "diploma", "degree",
        "stpm", "spm", "qualification", "academic",
    }
    tokens = re.findall(r"[A-Za-z]+", preceding.group("field").casefold())
    return any(token not in generic for token in tokens)


def _source_supports_criterion_type(criterion_type: str, source: str) -> bool:
    """Require independently typed evidence where ambiguity is high."""

    if criterion_type == "education_relevance":
        # Qualification level is itself valid education evidence.  A field of
        # study is needed only for a field-specific name, not for the
        # education scoring dimension to exist.
        return bool(_EDUCATION_EVIDENCE_PATTERN.search(source))
    return True


def final_evidence_safety_pass(
    criteria: list[dict[str, Any]],
    frozen: Any,
    trusted_source_texts_by_criterion_id: dict[str, set[str]] | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], dict[str, Any]]:
    """Isolate final evidence by capability immediately before weighting.

    A source sentence is retained only when it is generic-safe and contains a
    concrete object supported by the criterion name.  Shared verbs such as
    ``manage`` or ``monitor`` are deliberately excluded from that decision.
    This pass is conservative for a single already-grounded source, but drops
    unrelated fragments from multi-source model output.
    """

    cleaned_criteria: list[dict[str, Any]] = []
    warnings: list[str] = []
    rejected: list[dict[str, Any]] = []
    audit: dict[str, Any] = {"criteria": [], "removedSourceText": []}
    trusted_source_texts_by_criterion_id = trusted_source_texts_by_criterion_id or {}

    for index, criterion in enumerate(criteria, start=1):
        parts = source_parts(criterion)
        if not parts:
            cleaned_criteria.append(criterion)
            continue

        generic_indices = {
            part_index
            for part_index, part in enumerate(parts)
            if is_generic_duty_safe(part, frozen)
        }
        non_generic_indices = [
            part_index
            for part_index in range(len(parts))
            if part_index not in generic_indices
        ]
        name_objects = _name_object_tokens(criterion)
        criterion_type = str(criterion.get("type", ""))
        type_compatible_indices = {
            part_index
            for part_index in non_generic_indices
            if _source_supports_criterion_type(
                criterion_type,
                parts[part_index],
            )
        }
        trusted_source_texts: set[str] = set()
        for criterion_id in criterion.get("sourceCriterionIds", []):
            trusted_source_texts.update(
                trusted_source_texts_by_criterion_id.get(str(criterion_id), set())
            )
        supported_indices = [
            part_index
            for part_index in non_generic_indices
            if (
                part_index in type_compatible_indices
                and (
                    parts[part_index] in trusted_source_texts
                    or _source_supports_name(parts[part_index], name_objects)
                )
            )
        ]

        level_only_education = (
            criterion_type == "education_relevance"
            and bool(non_generic_indices)
            and not any(
                _source_has_education_field(parts[part_index])
                for part_index in non_generic_indices
            )
        )

        # For one source, frozen grounding already established the complete
        # candidate contract. For multiple sources, require object alignment
        # so a broad model concatenation cannot widen the criterion.
        if (
            criterion_type == "education_relevance"
            and not type_compatible_indices
        ):
            keep_indices = []
        elif len(parts) == 1 and non_generic_indices:
            keep_indices = non_generic_indices
        elif supported_indices:
            keep_indices = supported_indices
        else:
            # Do not silently discard a criterion that has no concrete name
            # object. Leave it for the existing validator's decision.
            keep_indices = non_generic_indices

        removed_indices = [
            part_index
            for part_index in range(len(parts))
            if part_index not in keep_indices
        ]
        if not removed_indices:
            if level_only_education and str(criterion.get("name", "")).strip() != "Education":
                neutral = dict(criterion)
                neutral["name"] = "Education"
                cleaned_criteria.append(neutral)
            else:
                cleaned_criteria.append(criterion)
            continue

        removed_parts = [parts[part_index] for part_index in removed_indices]
        kept_parts = [parts[part_index] for part_index in keep_indices]
        name = str(criterion.get("name", f"criterion-{index}"))
        warnings.append(
            f"Criterion {name} had unrelated or generic evidence removed before final output."
        )
        audit["removedSourceText"].extend(
            {"criterion": name, "sourceText": part} for part in removed_parts
        )
        if not kept_parts:
            rejected.append(
                {
                    "criterion": name,
                    "reason": "no capability-aligned evidence after final safety pass",
                    "sourceText": " | ".join(removed_parts),
                }
            )
            audit["criteria"].append(
                {"criterion": name, "keptSourceText": [], "removedSourceText": removed_parts}
            )
            continue

        cleaned = dict(criterion)
        cleaned["sourceText"] = " | ".join(kept_parts)
        if level_only_education:
            cleaned["name"] = "Education"
        for metadata_key in ("sourceIds", "groundingScores"):
            values = cleaned.get(metadata_key)
            if isinstance(values, list) and len(values) == len(parts):
                cleaned[metadata_key] = [values[part_index] for part_index in keep_indices]
            elif values:
                cleaned[metadata_key] = []
                warnings.append(
                    f"Criterion {name} {metadata_key} was cleared because source alignment was ambiguous."
                )
        cleaned_criteria.append(cleaned)
        audit["criteria"].append(
            {
                "criterion": name,
                "keptSourceText": kept_parts,
                "removedSourceText": removed_parts,
            }
        )

    return cleaned_criteria, warnings, rejected, audit


__all__ = [
    "decompose_incoherent_multisource_criteria",
    "is_broad_overview_source",
    "source_parts",
    "same_capability_with_object_alignment",
    "safe_merge_duplicate_criteria",
    "apply_semantic_consolidation_plan",
    "consolidate_adjacent_supply_operations",
    "consolidate_grounded_workflow_relations",
    "safe_can_merge_group",
    "remove_generic_evidence",
    "is_generic_duty_safe",
    "final_evidence_safety_pass",
]
