"""API-only weighting refinement for the enhanced post-processing layer."""

from __future__ import annotations

import re
from typing import Any

from .role_context import build_role_context, criterion_context_signals


_THRESHOLD_PATTERN = re.compile(
    r"\b(?:minimum|min\.?|at\s+least|required|years?|cgpa|gpa)\b",
    re.IGNORECASE,
)
_CONTEXT_PATTERN = re.compile(
    r"\b(?:scope|depth|environment|industry|function|process|team|lead|manage|"
    r"supervis|recruit|payroll|production|project|outcome|result|responsib)\w*\b",
    re.IGNORECASE,
)
_CORE_ACTION_PATTERN = re.compile(
    r"\b(?:manage|handle|lead|oversee|supervise|coordinate|develop|design|"
    r"prepare|process|reconcile|investigate|implement|operate|control|deliver)\w*\b",
    re.IGNORECASE,
)

IMPORTANCE_MULTIPLIERS = {
    "high": 1.15,
    "medium": 1.00,
    "low": 0.85,
}


def _is_responsibility_evidence(item: dict[str, Any]) -> bool:
    source_ids = [
        *item.get("sourceIds", []),
        *item.get("sourceCriterionIds", []),
    ]
    return any(str(source_id).lower().startswith("responsibilities-") for source_id in source_ids)


def _criterion_score(
    item: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> float:
    criterion_type = item.get("type")
    evidence = " ".join(
        [str(item.get("name", "")), str(item.get("sourceText", ""))]
    )
    evidence_count = max(1, len([part for part in str(item.get("sourceText", "")).split("|") if part.strip()]))
    is_responsibility = _is_responsibility_evidence(item)

    if criterion_type == "relevant_skill":
        score = 8.0 if is_responsibility else 4.5
        if _CORE_ACTION_PATTERN.search(evidence):
            score += 1.5
    elif criterion_type == "relevant_experience":
        # A minimum-year threshold is eligibility support, not the main job capability.
        score = 3.0 if _THRESHOLD_PATTERN.search(evidence) else 4.5
        if _CONTEXT_PATTERN.search(evidence):
            score += 1.0
    elif criterion_type == "domain_knowledge":
        score = 3.5
    elif criterion_type == "education_relevance":
        score = 2.5
    elif criterion_type in {"preferred_certification", "job_related_language"}:
        score = 1.75
    else:
        score = 1.0

    if context is not None:
        signals = criterion_context_signals(item, context)
        # Title and department are weak tie-breakers only. The JD evidence and
        # section remain the primary source of importance.
        score += min(1.5, float(signals["titleOverlap"]) * 0.5)
        score += min(0.75, float(signals["departmentOverlap"]) * 0.25)
        score += min(1.25, max(0, int(signals["jdSupportCount"]) - 1) * 0.25)
        if bool(signals["isResponsibility"]):
            score += 0.5

    # Multiple source lines demonstrate breadth, but source count alone must
    # not turn one umbrella criterion into most of the score.  A small capped
    # multiplier rewards corroboration without replacing semantic importance.
    score *= 1 + min(0.24, (min(evidence_count, 4) - 1) * 0.08)
    importance = str(item.get("importance", "medium")).casefold()
    score *= IMPORTANCE_MULTIPLIERS.get(importance, IMPORTANCE_MULTIPLIERS["medium"])
    return score


def apply_enhanced_weights(
    criteria: list[dict[str, Any]],
    job: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Weight core responsibility evidence above supporting requirements."""

    if not criteria:
        return criteria
    context = build_role_context(job) if job is not None else None
    scores = [_criterion_score(item, context) for item in criteria]
    total = sum(scores)
    exact = _bounded_percentages(scores)
    weights = [int(value) for value in exact]
    remainder = 100 - sum(weights)
    order = sorted(
        range(len(exact)),
        key=lambda index: exact[index] - weights[index],
        reverse=True,
    )
    cap = _integer_share_cap(len(criteria))
    for index in order:
        if remainder <= 0:
            break
        if weights[index] < cap:
            weights[index] += 1
            remainder -= 1
    if remainder:
        for index in range(len(weights)):
            if remainder <= 0:
                break
            weights[index] += 1
            remainder -= 1
    return [
        {**item, "suggestedWeight": weight}
        for item, weight in zip(criteria, weights, strict=True)
    ]


def _integer_share_cap(count: int) -> int:
    if count <= 1:
        return 100
    if count == 2:
        return 60
    if count == 3:
        return 45
    return 35


def _bounded_percentages(scores: list[float]) -> list[float]:
    """Normalise scores while applying a broad-set concentration guard."""

    total = sum(scores)
    if total <= 0:
        return [100.0 / len(scores)] * len(scores)
    percentages = [score * 100 / total for score in scores]
    if len(scores) <= 1:
        return percentages
    cap = float(_integer_share_cap(len(scores)))
    for _ in range(len(scores) * 3):
        over = [index for index, value in enumerate(percentages) if value > cap]
        if not over:
            break
        excess = sum(percentages[index] - cap for index in over)
        for index in over:
            percentages[index] = cap
        receivers = [
            index for index, value in enumerate(percentages) if value < cap - 1e-9
        ]
        if not receivers:
            break
        receiver_total = sum(max(percentages[index], 0.0) for index in receivers)
        if receiver_total <= 0:
            addition = excess / len(receivers)
            for index in receivers:
                percentages[index] += addition
        else:
            for index in receivers:
                percentages[index] += excess * percentages[index] / receiver_total
    correction = 100.0 - sum(percentages)
    if percentages:
        percentages[max(range(len(percentages)), key=percentages.__getitem__)] += correction
    return percentages


__all__ = ["IMPORTANCE_MULTIPLIERS", "apply_enhanced_weights"]
