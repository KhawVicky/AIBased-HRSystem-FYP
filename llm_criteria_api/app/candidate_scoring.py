"""Isolated semantic scoring task for candidate evidence.

The worker is deliberately small: it only asks Qwen for a bounded semantic
judgement.  It does not know application weights, eligibility rules, dates,
totals, ranking, or database state.  Those decisions remain in the Python
scoring service that owns the candidate record.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .model_loader import ModelLoader


ALLOWED_CRITERION_TYPES = {
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
}

logger = logging.getLogger(__name__)

_CAPABILITY_LEVELS = {
    "mentioned",
    "trained",
    "supported",
    "performed",
    "managed",
    "supervised",
}
_NO_MATCH_RELATIONSHIP_ALIASES = {
    "none",
    "no_match",
    "no_evidence",
    "not_applicable",
    "not_relevant",
    "irrelevant",
}
_CAPABILITY_ALIASES = {
    "awareness": "trained",
    "certification": "trained",
    "certified": "trained",
    "education": "trained",
    "training": "trained",
    "workshop": "trained",
}
_COVERAGE_ALIASES = {
    "full": "complete",
    "complete_match": "complete",
    "incomplete": "partial",
    "limited": "partial",
    "partial_match": "partial",
}
_EVIDENCE_STRENGTH_ALIASES = {
    "high": "strong",
    "low": "weak",
    "medium": "moderate",
}
_NO_MATCH_REASON = "No valid candidate evidence supports this criterion."
_GROUNDING_REJECTION_REASON = "No grounded candidate evidence was accepted for this criterion."


class CandidateEvidence(BaseModel):
    """An evidence record that the caller has already loaded and selected."""

    model_config = ConfigDict(extra="ignore")

    sourceId: str = Field(min_length=1, max_length=160)
    sourceSection: str = Field(default="", max_length=160)
    sourceText: str = Field(min_length=1, max_length=5000)
    sourceType: Literal["resume", "application_form"] = "resume"


class CandidateCriterion(BaseModel):
    """The authoritative criterion snapshot supplied by the scoring service."""

    model_config = ConfigDict(extra="ignore")

    id: int | str
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=80)
    jdEvidence: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=4000)
    evidenceRule: str = Field(default="", max_length=4000)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in ALLOWED_CRITERION_TYPES:
            raise ValueError("criterion type is not one of the six supported types")
        return cleaned


class CandidateCriterionScoringRequest(BaseModel):
    """RunPod input contract for one criterion semantic judgement."""

    model_config = ConfigDict(extra="ignore")

    task: Literal["candidate_criterion_scoring"]
    criterion: CandidateCriterion
    candidateEvidence: list[CandidateEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_evidence(self) -> "CandidateCriterionScoringRequest":
        ids = [item.sourceId for item in self.candidateEvidence]
        if len(ids) != len(set(ids)):
            raise ValueError("candidateEvidence sourceId values must be unique")
        return self


class CandidateCriterionScoringOutput(BaseModel):
    """Strict semantic assessment accepted from Qwen.

    Numeric scoring and presentation buckets deliberately do not belong to the
    model response. The parsing service maps these bounded labels to the
    existing score contract after it has independently validated grounding.
    """

    model_config = ConfigDict(extra="ignore")

    criterionId: int | str
    relationship: Literal["direct", "adjacent", "unrelated"]
    capabilityLevel: Literal["mentioned", "trained", "supported", "performed", "managed", "supervised"]
    coverage: Literal["partial", "complete"]
    evidenceStrength: Literal["weak", "moderate", "strong"]
    usedEvidenceIds: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=1200)

    @field_validator("relationship", "capabilityLevel", "coverage", "evidenceStrength", mode="before")
    @classmethod
    def normalize_semantic_label(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return re.sub(r"[\s-]+", "_", value.strip().casefold())

    @field_validator("usedEvidenceIds")
    @classmethod
    def evidence_ids_must_be_clean(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("usedEvidenceIds must not contain duplicates")
        return cleaned

CANDIDATE_SCORING_SYSTEM_PROMPT = """You are the semantic evidence assessor for one HR candidate criterion.
Return JSON only, using exactly this shape:
{
  "criterionId": "the supplied criterion id",
  "relationship": "direct | adjacent | unrelated",
  "capabilityLevel": "mentioned | trained | supported | performed | managed | supervised",
  "coverage": "partial | complete",
  "evidenceStrength": "weak | moderate | strong",
  "usedEvidenceIds": [],
  "reason": ""
}

Use only the supplied candidateEvidence. Never invent a skill, employer, title,
duration, qualification, certification, language, responsibility, domain, or
achievement. Every direct or adjacent assessment must cite one or more supplied
sourceId values. Copy no evidence id that is not present in candidateEvidence.
When no supplied evidence supports the criterion, return relationship unrelated,
usedEvidenceIds [], and a short reason. Do not return score, scoreOutOf10, or
matchLevel: Python calculates those fields deterministically after validation.

Assess the relationship before the capability level:
- direct: the evidence directly demonstrates the named criterion.
- adjacent: the evidence is technically or functionally related, but does not
  directly demonstrate the named criterion.
- unrelated: the evidence does not support the criterion.
High capability in an adjacent area is still adjacent. For example, Python
scripts for administrative automation are not backend development by themselves;
Windows Server, Active Directory, Microsoft 365, IT support, networking or
system administration are not backend software development by themselves.

Use capabilityLevel only when the supplied text supports it:
- mentioned: only names or mentions the capability.
- trained: education, training, workshop or certification evidence.
- supported: assisted, participated in or supported the work.
- performed: directly carried out the work.
- managed: owned or managed the work, process or function.
- supervised: supervised people, a team or the function.
Do not infer a higher level from a job title or a related technology.

coverage is complete only when the most important parts of the criterion are
directly demonstrated. Compound criteria missing a major part are partial.
evidenceStrength is weak, moderate or strong based on how explicit, specific and
credible the supplied text is. Keyword overlap alone is not evidence of a direct
relationship. Related technology is not automatically direct. Support for
recruitment is not management or supervision; ISO awareness training is not
practical implementation; mentioning payroll is not full payroll administration.

Keep usedEvidenceIds limited to the evidence that actually supports the labels.
The reason must describe only the grounded evidence. Do not calculate weights,
weighted scores, totals, eligibility or ranking.
"""


def build_candidate_scoring_messages(
    request: CandidateCriterionScoringRequest,
) -> list[dict[str, str]]:
    """Build the fixed, evidence-bounded prompt without caller prompt injection."""

    context = {
        "criterion": request.criterion.model_dump(exclude_none=True),
        "candidateEvidence": [item.model_dump() for item in request.candidateEvidence],
    }
    return [
        {"role": "system", "content": CANDIDATE_SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]


def generate_candidate_criterion_score(
    loader: ModelLoader,
    request: CandidateCriterionScoringRequest,
) -> dict[str, Any]:
    """Generate and validate one semantic criterion result through the shared loader."""

    if not loader.loaded:
        raise RuntimeError("Model is not ready")

    stage = "loader.generate"
    raw_output: Any = None
    raw_payload: Any = None
    normalized_payload: Any = None
    try:
        raw_output = loader.generate(build_candidate_scoring_messages(request))
        stage = "extract_json"
        raw_payload = _extract_json_payload(raw_output)
        if not isinstance(raw_payload, Mapping):
            raise TypeError("candidate scoring output must be an object")

        stage = "normalize_semantic_payload"
        normalized_payload = _normalize_candidate_semantic_payload(raw_payload)
        # Each request contains exactly one criterion. The identifier is a
        # redundant presentation field, so bind it to the request after parsing
        # while keeping the semantic score/evidence validation strict below.
        normalized_payload["criterionId"] = request.criterion.id
        output = CandidateCriterionScoringOutput.model_validate(normalized_payload)

        stage = "evidence_grounding_validate"
        known_ids = {item.sourceId for item in request.candidateEvidence}
        invalid_ids = [source_id for source_id in output.usedEvidenceIds if source_id not in known_ids]
        valid_ids = [source_id for source_id in output.usedEvidenceIds if source_id in known_ids]

        if output.relationship == "unrelated" and output.usedEvidenceIds:
            _log_criterion_grounding_rejection(
                request=request,
                relationship=output.relationship,
                rejection_reason="unrelated_assessment_cited_evidence",
                invalid_evidence_ids=invalid_ids,
                rejected_evidence_ids=output.usedEvidenceIds,
                criterion_rejected=True,
            )
            output = _safe_grounding_rejection_output(request)
        elif invalid_ids:
            criterion_rejected = not valid_ids
            _log_criterion_grounding_rejection(
                request=request,
                relationship=output.relationship,
                rejection_reason=(
                    "invalid_evidence_ids_no_valid_evidence"
                    if criterion_rejected
                    else "invalid_evidence_ids_removed"
                ),
                invalid_evidence_ids=invalid_ids,
                rejected_evidence_ids=invalid_ids,
                criterion_rejected=criterion_rejected,
            )
            output = (
                _safe_grounding_rejection_output(request)
                if criterion_rejected
                else output.model_copy(update={"usedEvidenceIds": valid_ids})
            )

        if output.relationship != "unrelated" and not output.usedEvidenceIds:
            _log_criterion_grounding_rejection(
                request=request,
                relationship=output.relationship,
                rejection_reason="positive_assessment_without_evidence",
                invalid_evidence_ids=[],
                rejected_evidence_ids=[],
                criterion_rejected=True,
            )
            output = _safe_grounding_rejection_output(request)
        elif output.relationship != "unrelated" and not output.reason.strip():
            _log_criterion_grounding_rejection(
                request=request,
                relationship=output.relationship,
                rejection_reason="positive_assessment_without_reason",
                invalid_evidence_ids=[],
                rejected_evidence_ids=[],
                criterion_rejected=True,
            )
            output = _safe_grounding_rejection_output(request)

        if _semantic_debug_summary(raw_payload) != _semantic_debug_summary(normalized_payload):
            logger.info(
                "candidate semantic payload normalized criterion_id=%s raw=%s normalized=%s",
                request.criterion.id,
                _semantic_debug_summary(raw_payload),
                _semantic_debug_summary(normalized_payload),
            )
        return output.model_dump(exclude_none=True)
    except Exception as error:
        message = " ".join(str(error).split())[:320]
        logger.error(
            "candidate semantic validation failed criterion_id=%s stage=%s error_type=%s error=%s raw=%s normalized=%s",
            request.criterion.id,
            stage,
            type(error).__name__,
            message,
            _semantic_debug_summary(raw_payload if raw_payload is not None else raw_output),
            _semantic_debug_summary(normalized_payload),
        )
        raise


def _safe_grounding_rejection_output(
    request: CandidateCriterionScoringRequest,
) -> CandidateCriterionScoringOutput:
    """Return the existing fail-closed semantic representation for one criterion."""

    return CandidateCriterionScoringOutput(
        criterionId=request.criterion.id,
        relationship="unrelated",
        capabilityLevel="mentioned",
        coverage="partial",
        evidenceStrength="weak",
        usedEvidenceIds=[],
        reason=_GROUNDING_REJECTION_REASON,
    )


def _log_criterion_grounding_rejection(
    *,
    request: CandidateCriterionScoringRequest,
    relationship: str,
    rejection_reason: str,
    invalid_evidence_ids: list[str],
    rejected_evidence_ids: list[str],
    criterion_rejected: bool,
) -> None:
    """Log only grounding identifiers and counts, never candidate source text."""

    logger.warning(
        "criterion_grounding_rejected application_id=%s criterion_id=%s "
        "rejection_reason=%s invalid_evidence_ids=%s rejected_evidence_ids=%s "
        "allowed_evidence_id_count=%d semantic_relationship=%s "
        "criterion_rejected=%s scoring_run_id=%s",
        "unavailable",
        request.criterion.id,
        rejection_reason,
        json.dumps(sorted(set(invalid_evidence_ids))),
        json.dumps(sorted(set(rejected_evidence_ids))),
        len(request.candidateEvidence),
        relationship,
        str(criterion_rejected).lower(),
        "unavailable",
    )


def _normalize_candidate_semantic_payload(raw_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize small-model label drift without relaxing grounding rules.

    Qwen occasionally puts a capability label in the relationship field (for
    example ``mentioned``) or uses ``unspecified`` for a no-match capability.
    These values are normalized to the bounded internal vocabulary. Positive
    results still need valid supplied evidence IDs and a reason; unrelated
    results always use the safe empty-evidence representation.
    """

    normalized = dict(raw_payload)
    for alias, canonical in (
        ("criterion_id", "criterionId"),
        ("relationshipType", "relationship"),
        ("capability", "capabilityLevel"),
        ("capability_level", "capabilityLevel"),
        ("coverageLevel", "coverage"),
        ("evidence_strength", "evidenceStrength"),
        ("evidenceIds", "usedEvidenceIds"),
        ("evidence_ids", "usedEvidenceIds"),
        ("used_evidence_ids", "usedEvidenceIds"),
    ):
        if canonical not in normalized and alias in normalized:
            normalized[canonical] = normalized[alias]

    normalized["usedEvidenceIds"] = _clean_evidence_ids(normalized.get("usedEvidenceIds"))
    relationship = _normalize_label(normalized.get("relationship"))
    capability = _normalize_label(normalized.get("capabilityLevel"))
    coverage = _normalize_label(normalized.get("coverage"))
    strength = _normalize_label(normalized.get("evidenceStrength"))

    capability = _CAPABILITY_ALIASES.get(capability, capability)
    coverage = _COVERAGE_ALIASES.get(coverage, coverage)
    strength = _EVIDENCE_STRENGTH_ALIASES.get(strength, strength)

    # The model sometimes emits one of the capability labels in the
    # relationship slot. Treat it as a direct relationship only when the
    # model supplied evidence; otherwise use the safe unrelated path.
    if relationship in _CAPABILITY_LEVELS:
        # Recover a swapped axis only when the other field still contains a
        # valid capability label. If both fields are uncertain, prefer a safe
        # no-match result over turning an invalid claim into a positive one.
        if capability in _CAPABILITY_LEVELS and normalized["usedEvidenceIds"]:
            relationship = "direct"
        else:
            relationship = "unrelated"
            normalized["usedEvidenceIds"] = []
    elif relationship in _NO_MATCH_RELATIONSHIP_ALIASES:
        relationship = "unrelated"

    normalized["relationship"] = relationship
    if relationship == "unrelated":
        # An ``unspecified``/missing capability is the small model's no-match
        # form. Preserve any cited IDs until the grounding boundary below so
        # every unrelated-with-evidence result is logged and normalized through
        # the same fail-closed path.
        normalized["capabilityLevel"] = "mentioned"
        normalized["coverage"] = "partial"
        normalized["evidenceStrength"] = "weak"
        normalized["reason"] = _NO_MATCH_REASON
        return normalized

    # Missing or unknown positive labels are deliberately conservative. They
    # can at most land in the lowest capability/coverage/strength band, and
    # direct/adjacent grounding checks below still reject missing evidence or
    # an empty explanation.
    normalized["capabilityLevel"] = capability if capability in _CAPABILITY_LEVELS else "mentioned"
    normalized["coverage"] = coverage if coverage in {"partial", "complete"} else "partial"
    normalized["evidenceStrength"] = strength if strength in {"weak", "moderate", "strong"} else "weak"
    reason = normalized.get("reason")
    normalized["reason"] = reason.strip() if isinstance(reason, str) else ""
    return normalized


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[\s-]+", "_", value.strip().casefold())


def _clean_evidence_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        values: list[Any] = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return [item.strip() for item in values if isinstance(item, str) and item.strip()]


def _semantic_debug_summary(value: Any) -> dict[str, Any]:
    """Return safe diagnostics without logging resume/source text."""

    if not isinstance(value, Mapping):
        if isinstance(value, str):
            return {"type": "string", "length": len(value)}
        return {"type": type(value).__name__}
    reason = value.get("reason")
    evidence_ids = _clean_evidence_ids(value.get("usedEvidenceIds"))
    return {
        "type": "mapping",
        "keys": sorted(str(key) for key in value.keys())[:24],
        "relationship": value.get("relationship"),
        "capabilityLevel": value.get("capabilityLevel"),
        "coverage": value.get("coverage"),
        "evidenceStrength": value.get("evidenceStrength"),
        "usedEvidenceIds": evidence_ids[:20],
        "usedEvidenceIdCount": len(evidence_ids),
        "reasonLength": len(reason) if isinstance(reason, str) else 0,
    }


def _extract_json_payload(value: Any) -> Any:
    """Accept JSON-only model text and common local test envelopes."""

    if isinstance(value, str):
        content = value.strip()
        fence = chr(96) * 3
        content = re.sub(r"^" + fence + r"(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*" + fence + r"$", "", content)
        return json.loads(content)

    if isinstance(value, list):
        for item in value:
            try:
                return _extract_json_payload(item)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        raise ValueError("No candidate scoring JSON object found in response list")

    if not isinstance(value, Mapping):
        raise TypeError("Candidate scoring response must be an object")

    choices = value.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and "content" in message:
                return _extract_json_payload(message["content"])
            if "text" in first:
                return _extract_json_payload(first["text"])

    for key in ("output", "data", "result", "score"):
        if key in value:
            try:
                return _extract_json_payload(value[key])
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

    return value
