"""Safe API-boundary serialization for criteria observability data."""

from __future__ import annotations

from typing import Any


ALLOWED_IMPORTANCE = {"high", "medium", "low"}
ALLOWED_HARD_REQUIREMENT_KINDS = {
    "minimum_experience",
    "education_level",
    "minimum_cgpa",
    "required_language",
    "mandatory_certification",
}
_BLOCKED_AUDIT_KEYS = {
    "apikey",
    "hf_token",
    "hftoken",
    "rawmodeloutput",
    "originalrawmodeloutput",
    "finalrawmodeloutput",
    "retryrawmodeloutput",
    "originalretryrawmodeloutput",
    "rawoutput",
    "rawtext",
    "sourcetext",
    "keptsourcetext",
    "removedsourcetext",
    "responsibilities",
    "requirements",
    "jobdescription",
}


def _safe_audit_value(value: Any, key: str | None = None) -> Any:
    if key is not None and key.casefold() in _BLOCKED_AUDIT_KEYS:
        return None
    if isinstance(value, list):
        return [
            cleaned
            for item in value
            if (cleaned := _safe_audit_value(item)) is not None
        ]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for child_key, child_value in value.items():
            child_key_text = str(child_key)
            if child_key_text.casefold() in _BLOCKED_AUDIT_KEYS:
                continue
            cleaned = _safe_audit_value(child_value, child_key_text)
            if cleaned is not None:
                result[child_key] = cleaned
        return result
    return value


def _safe_deployment(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "imageTag": str(value.get("imageTag", "")),
        "pipelineVersion": str(value.get("pipelineVersion", "")),
        "gitCommitHash": str(value.get("gitCommitHash", "")),
        "roleContextEnabled": value.get("roleContextEnabled") is True,
        "finalEvidenceSafetyEnabled": value.get("finalEvidenceSafetyEnabled") is True,
    }


def _safe_evidence_safety(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key in {"removedSourceText", "criteria"} and isinstance(item, list):
            if key == "removedSourceText":
                result["removedSourceTextCount"] = len(item)
                continue
            safe_criteria: list[dict[str, Any]] = []
            for criterion in item:
                if not isinstance(criterion, dict):
                    continue
                safe_criteria.append(
                    {
                        "criterion": criterion.get("criterion"),
                        "keptSourceCount": len(criterion.get("keptSourceText", []))
                        if isinstance(criterion.get("keptSourceText"), list)
                        else 0,
                        "removedSourceCount": len(criterion.get("removedSourceText", []))
                        if isinstance(criterion.get("removedSourceText"), list)
                        else 0,
                    }
                )
            result["criteria"] = safe_criteria
            continue
        cleaned = _safe_audit_value(item, key)
        if cleaned is not None:
            result[key] = cleaned
    return result


def _safe_fallback_recovery(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not value.get("recoveryType"):
        return None
    allowed = {
        "recoveryId",
        "criterionId",
        "recoveryType",
        "criterionType",
        "criterionName",
        "sourceIds",
        "sourceCriterionIds",
        "sourceTextHashes",
        "reason",
        "importance",
        "reconciledFromCriterionId",
        "reconciledFromType",
        "reconciledFromName",
    }
    result = {key: value[key] for key in allowed if key in value}
    importance = result.get("importance")
    if importance not in ALLOWED_IMPORTANCE:
        result.pop("importance", None)
    return result


def _safe_hard_requirements(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"requirements": [], "exactValues": {}}
    safe_items: list[dict[str, Any]] = []
    raw_items = value.get("requirements", [])
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind", ""))
            if kind not in ALLOWED_HARD_REQUIREMENT_KINDS:
                continue
            safe_items.append(
                {
                    "kind": kind,
                    "value": _safe_audit_value(item.get("value")),
                    "sourceRef": str(item.get("sourceRef", "")),
                    "sourceId": str(item.get("sourceId", "")),
                    "sourceHash": str(item.get("sourceHash", "")),
                }
            )
    exact_values = value.get("exactValues", {})
    return {
        "requirements": safe_items,
        "exactValues": _safe_audit_value(exact_values)
        if isinstance(exact_values, dict)
        else {},
    }


def _safe_source_accounting(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"valid": False, "sources": []}
    safe_sources: list[dict[str, Any]] = []
    raw_sources = value.get("sources", [])
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if not isinstance(item, dict):
                continue
            safe_item = {
                "sourceRef": str(item.get("sourceRef", "")),
                "sourceId": str(item.get("sourceId", "")),
                "sourceHash": str(item.get("sourceHash", "")),
                "section": str(item.get("section", "")),
                "processingOutcome": str(item.get("processingOutcome", "")),
                "mapped": item.get("mapped") is True,
                "hardRequirementKinds": [
                    str(kind)
                    for kind in item.get("hardRequirementKinds", [])
                    if str(kind).strip()
                ]
                if isinstance(item.get("hardRequirementKinds"), list)
                else [],
                "generatedCriterionIds": [
                    str(criterion_id)
                    for criterion_id in item.get("generatedCriterionIds", [])
                    if str(criterion_id).strip()
                ]
                if isinstance(item.get("generatedCriterionIds"), list)
                else [],
                "reason": str(item.get("reason", ""))[:240],
            }
            safe_sources.append(safe_item)
    return {
        "valid": value.get("valid") is True,
        "sources": safe_sources,
        "unknownSourceRefs": _safe_audit_value(value.get("unknownSourceRefs", [])),
        "duplicateSourceRefs": _safe_audit_value(value.get("duplicateSourceRefs", [])),
        "unmappedSourceRefs": _safe_audit_value(value.get("unmappedSourceRefs", [])),
    }


def safe_audit(audit: Any) -> dict[str, Any]:
    """Keep audit observability while removing raw model/JD/secrets."""

    if not isinstance(audit, dict):
        audit = {}
    fallback_values = audit.get("fallbackRecoveries", [])
    fallback_recoveries = [
        safe_item
        for item in fallback_values
        if (safe_item := _safe_fallback_recovery(item)) is not None
    ] if isinstance(fallback_values, list) else []
    return {
        "deployment": _safe_deployment(audit.get("deployment")),
        "debugTrace": _safe_audit_value(audit.get("debugTrace", [])),
        "fallbackRecoveries": fallback_recoveries,
        "evidenceSafety": _safe_evidence_safety(audit.get("evidenceSafety", {})),
        "hardRequirements": _safe_hard_requirements(
            audit.get("hardRequirements", {})
        ),
        "sourceAccounting": _safe_source_accounting(
            audit.get("sourceAccounting", {})
        ),
    }


def _safe_eligibility_suggestions(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    min_cgpa = source.get("minCGPA")
    if not isinstance(min_cgpa, (int, float)) or isinstance(min_cgpa, bool):
        min_cgpa = None
    return {
        "minCGPA": min_cgpa,
        "minExperience": str(source["minExperience"])
        if source.get("minExperience") is not None
        else None,
        "educationLevel": str(source["educationLevel"])
        if source.get("educationLevel") is not None
        else None,
        "requiredLanguage": str(source["requiredLanguage"])
        if source.get("requiredLanguage") is not None
        else None,
        "requiredLocation": str(source["requiredLocation"])
        if source.get("requiredLocation") is not None
        else None,
        "enabledFilters": [
            str(item)
            for item in source.get("enabledFilters", [])
            if str(item).strip()
        ]
        if isinstance(source.get("enabledFilters"), list)
        else [],
    }


def _safe_criterion(value: Any) -> dict[str, Any]:
    criterion = dict(value) if isinstance(value, dict) else {}
    source_text = str(criterion.get("sourceText", ""))
    evidence = [part.strip() for part in source_text.split("|") if part.strip()]
    for key in ("sourceIds", "groundingScores"):
        if key not in criterion:
            continue
        values = criterion.get(key)
        if not isinstance(values, list):
            criterion.pop(key, None)
            continue
        values = values[: len(evidence)]
        if len(values) != len(evidence):
            criterion.pop(key, None)
        else:
            criterion[key] = values
    if criterion.get("importance") not in ALLOWED_IMPORTANCE:
        criterion.pop("importance", None)
    return criterion


def safe_api_output(output: dict[str, Any]) -> dict[str, Any]:
    """Prepare a response without inventing optional observability fields."""

    safe = dict(output)
    safe["criteria"] = [
        _safe_criterion(item) for item in output.get("criteria", [])
    ]
    safe["eligibilitySuggestions"] = _safe_eligibility_suggestions(
        output.get("eligibilitySuggestions", {})
    )
    safe["audit"] = safe_audit(output.get("audit", {}))
    return safe


__all__ = ["safe_api_output", "safe_audit"]
