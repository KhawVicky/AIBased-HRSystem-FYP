"""Authoritative candidate scoring, grounding, eligibility, and persistence.

This module is intentionally independent from PDF parsing.  It consumes the
profile/evidence JSON already persisted by the resume parser, calls the shared
RunPod semantic task for criterion relevance, and keeps every deterministic
decision in Python.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import logging
import os
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from app.schemas.scoring import (
    CandidateScoringData,
    CriterionScore,
    EligibilityResult,
    ScoringDiagnostics,
    ScoringEvidence,
)
from app.services.candidate_scoring_qwen import (
    CandidateScoringQwenClient,
    CandidateScoringQwenError,
    QwenCriterionResult,
    configured_candidate_scoring_client,
)


SCORING_VERSION = "candidate-scoring-v2-semantic-bands"
GROUNDING_REJECTION_EXPLANATION = "No grounded candidate evidence was accepted for this criterion."
logger = logging.getLogger(__name__)
ALLOWED_CRITERION_TYPES = {
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "years",
    "year",
    "experience",
    "knowledge",
    "ability",
    "skills",
    "skill",
    "candidate",
    "source",
    "text",
    "current",
    "application",
    "system",
    "project",
    "support",
    "work",
    "using",
    "use",
    "team",
    "related",
    "resume",
    "should",
    "show",
    "this",
    "direct",
    "directly",
    "evidence",
    "record",
    "records",
    "demonstrated",
    "demonstrate",
    "requirement",
    "requirements",
    "stated",
    "matching",
    "relevant",
}
EVIDENCE_PRIORITY = {
    "experience": 100,
    "achievement": 96,
    "project": 82,
    "skill": 68,
    "certification": 56,
    "education": 45,
    "language": 42,
    "summary": 20,
    "application": 10,
    "other": 5,
}
EVIDENCE_POOL_BY_TYPE = {
    # Criterion type is a routing hint, not a single-section restriction. The
    # ranking layer below still requires criterion-specific semantic signal.
    "relevant_skill": {"experience", "achievement", "project", "skill", "certification", "summary", "application"},
    "relevant_experience": {"experience", "achievement", "project", "skill", "summary", "application"},
    "education_relevance": {"education", "application", "project", "experience", "skill", "summary"},
    "domain_knowledge": {"experience", "achievement", "project", "skill", "certification", "education", "summary", "application"},
    "preferred_certification": {"certification", "experience", "project", "skill", "summary", "application"},
    "job_related_language": {"language", "application", "experience", "skill", "summary"},
}
TOP_K_BY_TYPE = {
    "education_relevance": 4,
    "preferred_certification": 3,
    "job_related_language": 3,
}
DEFAULT_EVIDENCE_TOP_K = 5
# Qwen supplies semantic labels only. These ranges are the only place where
# those labels become the existing 0-10 score. Relationship is an explicit
# gate: adjacent evidence can never enter a direct capability band.
CAPABILITY_SCORE_BANDS = {
    "mentioned": (3.0, 4.0),
    "trained": (4.0, 5.0),
    "supported": (5.0, 6.0),
    "performed": (7.0, 8.0),
    "managed": (8.0, 9.0),
    "supervised": (9.0, 10.0),
}
ADJACENT_SCORE_BAND = (1.0, 3.0)
SCORE_BAND_POSITIONS = {
    ("partial", "weak"): 0.0,
    ("partial", "moderate"): 0.5,
    ("partial", "strong"): 0.75,
    ("complete", "weak"): 0.5,
    ("complete", "moderate"): 0.75,
    ("complete", "strong"): 1.0,
}

# These are generic capability/technology associations used only to order
# already-persisted evidence. They do not create evidence or make a score.
SEMANTIC_QUERY_ALIASES = {
    "web": {"web", "website", "html", "css", "react", "vue", "angular", "bootstrap", "frontend", "backend"},
    "frontend": {"frontend", "react", "vue", "angular", "html", "css", "typescript", "javascript", "bootstrap"},
    "backend": {"backend", "api", "fastapi", "django", "flask", "node", "nodejs", "php", "java", "python", "dotnet", "net"},
    "testing": {"test", "testing", "qa", "quality", "bug", "debug", "validation", "valid", "verification", "pytest", "jest", "selenium", "issue", "layout", "cross", "device", "responsive"},
    "database": {"database", "databas", "sql", "mysql", "mariadb", "sqlite", "postgresql", "postgres", "mongodb", "oracle", "query", "storage"},
    "version_control": {"git", "github", "gitlab", "bitbucket", "mercurial", "subversion", "svn", "repository", "commit", "branch"},
    "documentation": {"documentation", "document", "docs", "readme", "specification", "technical", "writeup"},
}
PROGRAMMING_LANGUAGE_ALIASES = {
    "python": {"python"},
    "java": {"java"},
    "javascript": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "php": {"php"},
    "csharp": {"csharp", "dotnet", "net"},
    "cplusplus": {"cplusplus"},
    "ruby": {"ruby"},
    "go": {"golang", "go"},
    "kotlin": {"kotlin"},
    "swift": {"swift"},
    "rust": {"rust"},
    "dart": {"dart"},
    "sql": {"sql"},
}
GENERIC_RETRIEVAL_TOKENS = {
    "develop", "development", "build", "built", "maintain", "maintained",
    "application", "system", "project", "experience", "support", "work",
    "task", "tasks", "feature", "features", "data", "information", "use",
    "using", "manage", "managed", "responsibility", "responsibilities",
    "technical",
}


class CandidateScoringError(RuntimeError):
    """A safe, user-facing scoring error with an HTTP-compatible status."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class CandidateNotFoundError(CandidateScoringError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message, 404)


class CandidateSemanticOutput(BaseModel):
    """The local validation boundary around a provider response."""

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
        return value.strip().casefold().replace(" ", "_")

    @field_validator("usedEvidenceIds")
    @classmethod
    def evidence_ids_must_be_clean(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("usedEvidenceIds must not contain duplicates")
        return cleaned


class ScoringRepository(Protocol):
    def load_context(self, job_id: int, application_id: int) -> dict[str, Any]:
        ...

    def persist_result(self, context: dict[str, Any], payload: dict[str, Any]) -> tuple[int, int | None]:
        ...


@dataclass(frozen=True)
class EvidenceCandidate:
    source_id: str
    source_section: str
    source_text: str
    source_type: str
    category: str
    priority: int
    concepts: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "sourceSection": self.source_section,
            "sourceText": self.source_text,
            "sourceType": self.source_type if self.source_type in {"resume", "application_form"} else "resume",
        }


@dataclass(frozen=True)
class ValidatedSemanticResult:
    semantic: CandidateSemanticOutput
    criterion_rejected: bool = False
    rejection_reason: str | None = None
    invalid_evidence_ids: tuple[str, ...] = ()
    rejected_evidence_ids: tuple[str, ...] = ()


def _safe_grounding_rejection_semantic(criterion_id: int | str) -> CandidateSemanticOutput:
    return CandidateSemanticOutput(
        criterionId=criterion_id,
        relationship="unrelated",
        capabilityLevel="mentioned",
        coverage="partial",
        evidenceStrength="weak",
        usedEvidenceIds=[],
        reason=GROUNDING_REJECTION_EXPLANATION,
    )


def _clean_provider_evidence_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        values: list[Any] = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return [item.strip() for item in values if isinstance(item, str) and item.strip()]


def _log_criterion_grounding_rejection(
    *,
    application_id: int,
    criterion_id: int | str,
    rejection_reason: str,
    invalid_evidence_ids: list[str],
    rejected_evidence_ids: list[str],
    allowed_evidence_id_count: int,
    semantic_relationship: str,
    criterion_rejected: bool,
) -> None:
    logger.warning(
        "criterion_grounding_rejected application_id=%s criterion_id=%s "
        "rejection_reason=%s invalid_evidence_ids=%s rejected_evidence_ids=%s "
        "allowed_evidence_id_count=%d semantic_relationship=%s "
        "criterion_rejected=%s scoring_run_id=%s",
        application_id,
        criterion_id,
        rejection_reason,
        json.dumps(sorted(set(invalid_evidence_ids))),
        json.dumps(sorted(set(rejected_evidence_ids))),
        allowed_evidence_id_count,
        semantic_relationship,
        str(criterion_rejected).lower(),
        "unavailable",
    )


class CandidateScoringEngine:
    """Score a candidate against the current HR criteria snapshot."""

    def __init__(
        self,
        repository: ScoringRepository,
        qwen_client: CandidateScoringQwenClient | None,
        *,
        scoring_version: str = SCORING_VERSION,
    ) -> None:
        self.repository = repository
        self.qwen_client = qwen_client
        self.scoring_version = scoring_version

    def score(self, job_id: int, application_id: int, *, force_rescore: bool = False) -> CandidateScoringData:
        """Load the authoritative DB snapshot before running the traceable scoring pass."""

        context = self.repository.load_context(job_id, application_id)
        return self.score_context(context, force_rescore=force_rescore)

    def score_context(
        self,
        context: dict[str, Any],
        *,
        force_rescore: bool = False,
    ) -> CandidateScoringData:
        """Keep eligibility, evidence grounding, arithmetic, and persistence in Python."""

        del force_rescore  # Rescores intentionally create a new trace run.
        job_id = int(context["job"]["id"])
        application_id = int(context["application"]["id"])
        candidate_id = int(context["application"]["candidateId"])
        criteria = self._authoritative_criteria(context.get("criteria", []))
        profile = context.get("profile") if isinstance(context.get("profile"), Mapping) else {}
        profile = dict(profile)
        profile_available = bool(context.get("profileAvailable", False))
        evidence = _build_evidence_index(profile, context)

        criteria_hash = _stable_hash(criteria)
        profile_hash = _stable_hash({
            "candidate": _candidate_identity_snapshot(context.get("candidate", {})),
            "profile": profile,
        })
        request_hash = _stable_hash({
            "jobId": job_id,
            "applicationId": application_id,
            "criteriaSnapshotHash": criteria_hash,
            "profileSnapshotHash": profile_hash,
            "scoringVersion": self.scoring_version,
        })

        eligibility = _evaluate_eligibility(context, profile)
        breakdown: list[CriterionScore] = []
        overall = Decimal("0")
        scored_criterion_count = 0
        zero_evidence_count = 0
        grounding_rejected_count = 0
        qwen_models: set[str] = set()

        for criterion in criteria:
            selected = _select_evidence(criterion, evidence)
            if not selected:
                zero_evidence_count += 1
                criterion_score = CriterionScore(
                    criterionId=int(criterion["id"]),
                    criterionName=criterion["name"],
                    criterionType=criterion["type"],
                    weight=float(criterion["weight"]),
                    jdEvidence=criterion["jdEvidence"],
                    rawScore=0,
                    weightedContribution=0,
                    explanation="No valid persisted resume evidence was retrieved for this criterion.",
                    grounded=False,
                    evidenceIds=[],
                    matchedResumeEvidence=[],
                    matchLevel="none",
                    qwenStatus="not_used_no_evidence",
                )
                breakdown.append(criterion_score)
                continue

            if self.qwen_client is None:
                raise CandidateScoringError(
                    "QWEN_NOT_CONFIGURED",
                    "Live Qwen candidate scoring is not configured; no semantic fallback is allowed.",
                    503,
                )

            scored_criterion_count += 1
            try:
                provider_criterion = dict(criterion)
                # evidenceRule is a Python retrieval instruction, not a
                # semantic fact. Keeping it in the worker prompt can make the
                # small shared model return an invalid candidate result for
                # otherwise valid evidence (notably language criteria).
                provider_criterion.pop("evidenceRule", None)
                # MySQL DECIMAL values are loaded as Decimal for exact local
                # arithmetic; convert only the wire payload sent to Qwen.
                provider_criterion["weight"] = float(criterion["weight"])
                provider_result = self.qwen_client.score(
                    criterion=provider_criterion,
                    candidate_evidence=[item.as_payload() for item in selected],
                )
            except CandidateScoringQwenError as error:
                raise CandidateScoringError("QWEN_UNAVAILABLE", str(error), 503) from error

            qwen_models.add(provider_result.model)
            if not provider_result.qwen_used or provider_result.mock_mode:
                raise CandidateScoringError(
                    "QWEN_MOCK_OR_FALLBACK",
                    "Candidate scoring did not use live Qwen inference; no semantic fallback is allowed.",
                    503,
                )

            try:
                validation = self._validate_semantic_output(
                    provider_result,
                    criterion,
                    selected,
                )
                semantic = validation.semantic
                if validation.rejection_reason:
                    _log_criterion_grounding_rejection(
                        application_id=application_id,
                        criterion_id=criterion["id"],
                        rejection_reason=validation.rejection_reason,
                        invalid_evidence_ids=list(validation.invalid_evidence_ids),
                        rejected_evidence_ids=list(validation.rejected_evidence_ids),
                        allowed_evidence_id_count=len(selected),
                        semantic_relationship=semantic.relationship,
                        criterion_rejected=validation.criterion_rejected,
                    )
                if validation.criterion_rejected:
                    grounding_rejected_count += 1
                qwen_status = "rejected_grounding" if validation.criterion_rejected else "live"
                grounded = semantic.relationship != "unrelated" and bool(semantic.usedEvidenceIds)
            except ValueError as error:
                grounding_rejected_count += 1
                provider_payload = provider_result.payload if isinstance(provider_result.payload, Mapping) else {}
                raw_ids = _clean_provider_evidence_ids(provider_payload.get("usedEvidenceIds"))
                allowed_ids = {item.source_id for item in selected}
                _log_criterion_grounding_rejection(
                    application_id=application_id,
                    criterion_id=criterion["id"],
                    rejection_reason="local_semantic_validation_failed:"
                    + "_".join(str(error).split())[:240],
                    invalid_evidence_ids=[source_id for source_id in raw_ids if source_id not in allowed_ids],
                    rejected_evidence_ids=raw_ids,
                    allowed_evidence_id_count=len(selected),
                    semantic_relationship=str(provider_payload.get("relationship") or "unknown"),
                    criterion_rejected=True,
                )
                semantic = _safe_grounding_rejection_semantic(criterion["id"])
                qwen_status = "rejected_grounding"
                grounded = False

            score = Decimal(str(_score_from_semantics(semantic))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            weighted = (score / Decimal("10") * criterion["weight"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            overall += weighted
            evidence_by_id = {item.source_id: item for item in selected}
            matched = [
                ScoringEvidence(**evidence_by_id[source_id].as_payload())
                for source_id in semantic.usedEvidenceIds
                if source_id in evidence_by_id
            ]
            breakdown.append(
                CriterionScore(
                    criterionId=int(criterion["id"]),
                    criterionName=criterion["name"],
                    criterionType=criterion["type"],
                    weight=float(criterion["weight"]),
                    jdEvidence=criterion["jdEvidence"],
                    rawScore=float(score),
                    weightedContribution=float(weighted),
                    explanation=semantic.reason.strip(),
                    grounded=grounded,
                    evidenceIds=list(semantic.usedEvidenceIds),
                    matchedResumeEvidence=matched,
                    matchLevel=_match_level_for_score(float(score)),
                    qwenStatus=qwen_status,  # type: ignore[arg-type]
                )
            )

        overall = overall.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_weight = sum((item["weight"] for item in criteria), Decimal("0"))
        qwen_used = scored_criterion_count > 0
        diagnostics = ScoringDiagnostics(
            qwenStatus="live" if qwen_used else "not_used_no_evidence",
            qwenUsed=qwen_used,
            fallbackUsed=False,
            criterionCount=len(criteria),
            scoredCriterionCount=scored_criterion_count,
            zeroEvidenceCriterionCount=zero_evidence_count,
            groundingRejectedCount=grounding_rejected_count,
            totalWeight=float(total_weight),
            overallScore=float(overall),
            scoringVersion=self.scoring_version,
            model=next(iter(qwen_models), None),
            runtimeTask="candidate_criterion_scoring",
            criteriaSnapshotHash=criteria_hash,
            profileSnapshotHash=profile_hash,
            requestHash=request_hash,
            profileAvailable=profile_available,
        )
        eligibility_model = EligibilityResult(**eligibility)
        payload = {
            "applicationId": application_id,
            "jobId": job_id,
            "candidateId": candidate_id,
            "runId": 0,
            "eligibility": eligibility_model.model_dump(),
            "overallScore": float(overall),
            "totalWeight": float(total_weight),
            "rank": None,
            "rankingReady": False,
            "scoreBreakdown": [item.model_dump() for item in breakdown],
            "diagnostics": diagnostics.model_dump(),
        }
        run_id, rank = self.repository.persist_result(context, payload)
        payload["runId"] = int(run_id)
        effective_rank = rank if eligibility_model.eligible else None
        payload["rank"] = effective_rank
        payload["rankingReady"] = bool(eligibility_model.eligible and effective_rank is not None)
        return CandidateScoringData.model_validate(payload)

    @staticmethod
    def _authoritative_criteria(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            raise CandidateScoringError("CRITERIA_NOT_CONFIGURED", "No active HR criteria exist for this job.")

        normalized: list[dict[str, Any]] = []
        total = Decimal("0")
        for row in rows:
            criterion_type = str(row.get("type") or row.get("criterionType") or "").strip()
            if criterion_type not in ALLOWED_CRITERION_TYPES:
                raise CandidateScoringError("INVALID_CRITERION_TYPE", "An active criterion has an unsupported type.")
            try:
                criterion_id = int(row["id"])
                weight = Decimal(str(row.get("weight")))
            except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                raise CandidateScoringError("INVALID_CRITERION", "An active criterion is malformed.") from error
            if criterion_id <= 0 or weight < 0 or weight > 100:
                raise CandidateScoringError("INVALID_WEIGHT", "Each active criterion weight must be between 0 and 100.")
            name = str(row.get("name") or row.get("criteria_name") or "").strip()
            if not name:
                raise CandidateScoringError("INVALID_CRITERION", "Every active criterion must have a name.")
            jd_evidence = _split_jd_evidence(
                str(row.get("sourceText") or row.get("source_text") or "").strip()
            )
            normalized_row = {
                "id": criterion_id,
                "name": name,
                "type": criterion_type,
                "weight": weight,
                "jdEvidence": jd_evidence,
                "description": str(row.get("description") or "").strip(),
                "evidenceRule": str(row.get("evidenceRule") or row.get("evidence_rule") or "").strip(),
                "sortOrder": int(row.get("sortOrder") or row.get("sort_order") or 0),
            }
            total += weight
            normalized.append(normalized_row)

        if total != Decimal("100"):
            raise CandidateScoringError(
                "INVALID_WEIGHT_TOTAL",
                "Active HR criterion weights must total exactly 100; they were not normalized.",
            )
        return normalized

    @staticmethod
    def _validate_semantic_output(
        provider_result: QwenCriterionResult,
        criterion: dict[str, Any],
        selected: list[EvidenceCandidate],
    ) -> ValidatedSemanticResult:
        """Reject unsupported evidence claims before a model result affects the score."""

        semantic = CandidateSemanticOutput.model_validate(provider_result.payload)
        if str(semantic.criterionId) != str(criterion["id"]):
            raise ValueError("criterion id mismatch")
        known_ids = {item.source_id for item in selected}
        used_ids = semantic.usedEvidenceIds
        invalid_ids = [source_id for source_id in used_ids if source_id not in known_ids]
        valid_ids = [source_id for source_id in used_ids if source_id in known_ids]
        if semantic.relationship == "unrelated":
            if used_ids:
                return ValidatedSemanticResult(
                    semantic=_safe_grounding_rejection_semantic(criterion["id"]),
                    criterion_rejected=True,
                    rejection_reason="unrelated_assessment_cited_evidence",
                    invalid_evidence_ids=tuple(invalid_ids),
                    rejected_evidence_ids=tuple(used_ids),
                )
            if semantic.reason.strip() == GROUNDING_REJECTION_EXPLANATION:
                return ValidatedSemanticResult(
                    semantic=semantic,
                    criterion_rejected=True,
                    rejection_reason="provider_grounding_rejection",
                )
            return ValidatedSemanticResult(semantic=semantic)
        if invalid_ids:
            if not valid_ids:
                return ValidatedSemanticResult(
                    semantic=_safe_grounding_rejection_semantic(criterion["id"]),
                    criterion_rejected=True,
                    rejection_reason="invalid_evidence_ids_no_valid_evidence",
                    invalid_evidence_ids=tuple(invalid_ids),
                    rejected_evidence_ids=tuple(invalid_ids),
                )
            semantic = semantic.model_copy(update={"usedEvidenceIds": valid_ids})
            used_ids = valid_ids
        if not used_ids or not semantic.reason.strip():
            raise ValueError("grounded assessment has no evidence or explanation")
        selected_text = " ".join(
            item.source_text for item in selected if item.source_id in set(used_ids)
        )
        if not _has_grounded_reason(semantic.reason, selected_text):
            raise ValueError("explanation has no meaningful overlap with selected evidence")
        return ValidatedSemanticResult(
            semantic=semantic,
            rejection_reason="invalid_evidence_ids_removed" if invalid_ids else None,
            invalid_evidence_ids=tuple(invalid_ids),
            rejected_evidence_ids=tuple(invalid_ids),
        )


class MySQLScoringRepository:
    """MySQL repository used by the Python scoring service."""

    def __init__(self, configuration: dict[str, Any] | None = None) -> None:
        self.configuration = configuration or database_configuration()

    def _connect(self) -> Any:
        try:
            from mysql.connector import connect
        except ImportError as error:
            raise CandidateScoringError(
                "DB_DRIVER_MISSING",
                "The scoring service database driver is not installed.",
                503,
            ) from error
        try:
            return connect(**self.configuration)
        except Exception as error:
            raise CandidateScoringError("DB_UNAVAILABLE", "The scoring database could not be reached.", 503) from error

    @staticmethod
    def _fetchone(cursor: Any, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        cursor.execute(query, params)
        value = cursor.fetchone()
        return dict(value) if isinstance(value, Mapping) else value

    @staticmethod
    def _fetchall(cursor: Any, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        cursor.execute(query, params)
        values = cursor.fetchall()
        return [dict(value) for value in values]

    def load_context(self, job_id: int, application_id: int) -> dict[str, Any]:
        connection = self._connect()
        cursor = connection.cursor(dictionary=True)
        try:
            application = self._fetchone(
                cursor,
                """SELECT a.id, a.job_id AS jobId, a.candidate_id AS candidateId,
                          a.application_status AS applicationStatus,
                          a.eligibility_status AS eligibilityStatus,
                          c.full_name AS candidateName, c.current_cgpa AS candidateCgpa,
                          c.years_experience AS candidateYearsExperience,
                          c.notice_period_days AS candidateNoticePeriodDays,
                          c.education AS candidateEducation,
                          c.current_location AS candidateLocation,
                          c.languages_json AS candidateLanguagesJson
                   FROM applications a
                   JOIN candidates c ON c.id = a.candidate_id
                   WHERE a.id = %s AND a.job_id = %s
                   LIMIT 1""",
                (application_id, job_id),
            )
            if not application:
                raise CandidateNotFoundError("Application was not found for this job.")

            job = self._fetchone(
                cursor,
                "SELECT id, title, department FROM jobs WHERE id = %s LIMIT 1",
                (job_id,),
            )
            if not job:
                raise CandidateNotFoundError("Job was not found.")

            criteria = self._fetchall(
                cursor,
                """SELECT id, criteria_name AS name, criterion_type AS type,
                          weight, description, source_text AS sourceText,
                          evidence_rule AS evidenceRule, sort_order AS sortOrder
                   FROM job_criteria
                   WHERE job_id = %s AND is_active = 1
                   ORDER BY sort_order, id""",
                (job_id,),
            )
            eligibility = self._fetchone(
                cursor,
                """SELECT min_cgpa AS minCgpa, min_years_experience AS minYearsExperience,
                          internship_accepted AS internshipAccepted,
                          required_qualification AS requiredQualification,
                          required_language AS requiredLanguage,
                          required_location AS requiredLocation,
                          max_notice_period_days AS maxNoticePeriodDays
                   FROM eligibility_filters WHERE job_id = %s LIMIT 1""",
                (job_id,),
            )
            eligibility_values = self._fetchall(
                cursor,
                """SELECT filter_key AS filterKey, filter_label AS filterLabel,
                          filter_value AS filterValue
                   FROM job_eligibility_filter_values
                   WHERE job_id = %s ORDER BY sort_order, id""",
                (job_id,),
            )
            resume = self._fetchone(
                cursor,
                """SELECT id, parsed_profile_json AS profileJson, parsing_status AS parsingStatus,
                          parser_version AS parserVersion, parsed_at AS parsedAt
                   FROM resumes
                   WHERE application_id = %s
                   ORDER BY uploaded_at DESC, id DESC
                   LIMIT 1""",
                (application_id,),
            )
        finally:
            cursor.close()
            connection.close()

        profile: dict[str, Any] = {}
        profile_available = False
        if resume and str(resume.get("parsingStatus") or "") == "parsed":
            raw_profile = resume.get("profileJson")
            if isinstance(raw_profile, str) and raw_profile.strip():
                try:
                    decoded = json.loads(raw_profile)
                except json.JSONDecodeError as error:
                    raise CandidateScoringError("PROFILE_INVALID", "The persisted candidate profile is not valid JSON.") from error
                if not isinstance(decoded, dict):
                    raise CandidateScoringError("PROFILE_INVALID", "The persisted candidate profile is not an object.")
                profile = decoded
                profile_available = True

        return {
            "job": job,
            "application": application,
            "candidate": application,
            "criteria": criteria,
            "eligibility": eligibility,
            "eligibilityValues": eligibility_values,
            "profile": profile,
            "profileAvailable": profile_available,
            "resume": resume or {},
        }

    def persist_result(self, context: dict[str, Any], payload: dict[str, Any]) -> tuple[int, int | None]:
        connection = self._connect()
        cursor = connection.cursor(dictionary=True)
        application_id = int(payload["applicationId"])
        job_id = int(payload["jobId"])
        candidate_id = int(payload["candidateId"])
        diagnostics = payload["diagnostics"]
        try:
            response_json = _json_dump(payload)
            cursor.execute(
                """INSERT INTO candidate_scoring_runs
                   (application_id, job_id, candidate_id, scoring_version,
                    criteria_snapshot_hash, profile_snapshot_hash, request_hash,
                    qwen_status, qwen_used, fallback_used, total_weight,
                    overall_score, diagnostics_json, response_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    application_id,
                    job_id,
                    candidate_id,
                    diagnostics["scoringVersion"],
                    diagnostics["criteriaSnapshotHash"],
                    diagnostics["profileSnapshotHash"],
                    diagnostics["requestHash"],
                    diagnostics["qwenStatus"],
                    1 if diagnostics["qwenUsed"] else 0,
                    1 if diagnostics["fallbackUsed"] else 0,
                    diagnostics["totalWeight"],
                    diagnostics["overallScore"],
                    _json_dump(diagnostics),
                    response_json,
                ),
            )
            run_id = int(cursor.lastrowid)
            eligibility = payload["eligibility"]
            cursor.execute(
                """UPDATE applications
                   SET total_score = %s,
                       rank_no = NULL,
                       eligibility_status = %s,
                       scoring_version = %s,
                       analysis_status = 'completed',
                       scored_at = NOW(),
                       eligibility_reasons_json = %s,
                       scoring_diagnostics_json = %s,
                       criteria_snapshot_json = %s
                   WHERE id = %s AND job_id = %s""",
                (
                    payload["overallScore"],
                    "eligible" if eligibility["eligible"] else "filtered_out",
                    diagnostics["scoringVersion"],
                    _json_dump(eligibility["reasons"]),
                    _json_dump(diagnostics),
                    _json_dump(context["criteria"]),
                    application_id,
                    job_id,
                ),
            )

            for item in payload["scoreBreakdown"]:
                # rawScore is the authoritative semantic score on a 0-10
                # scale. Older rows may still contain legacy 0-100 values;
                # the read API keeps a compatibility path for those rows.
                display_score = round(float(item["rawScore"]), 2)
                cursor.execute(
                    """INSERT INTO score_breakdowns
                       (application_id, criteria_id, raw_score, semantic_score,
                        weight, weighted_score, explanation, criterion_type,
                        criterion_name_snapshot, jd_evidence_json,
                        matched_resume_evidence_json, evidence_ids_json, grounded,
                        scoring_version, qwen_status, scored_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                       ON DUPLICATE KEY UPDATE
                         raw_score = VALUES(raw_score),
                         semantic_score = VALUES(semantic_score),
                         weight = VALUES(weight),
                         weighted_score = VALUES(weighted_score),
                         explanation = VALUES(explanation),
                         criterion_type = VALUES(criterion_type),
                         criterion_name_snapshot = VALUES(criterion_name_snapshot),
                         jd_evidence_json = VALUES(jd_evidence_json),
                         matched_resume_evidence_json = VALUES(matched_resume_evidence_json),
                         evidence_ids_json = VALUES(evidence_ids_json),
                         grounded = VALUES(grounded),
                         scoring_version = VALUES(scoring_version),
                         qwen_status = VALUES(qwen_status),
                         scored_at = NOW()""",
                    (
                        application_id,
                        item["criterionId"],
                        display_score,
                        item["rawScore"],
                        item["weight"],
                        item["weightedContribution"],
                        item["explanation"],
                        item["criterionType"],
                        item["criterionName"],
                        _json_dump(item["jdEvidence"]),
                        _json_dump(item["matchedResumeEvidence"]),
                        _json_dump(item["evidenceIds"]),
                        1 if item["grounded"] else 0,
                        diagnostics["scoringVersion"],
                        item["qwenStatus"],
                    ),
                )
                breakdown = self._fetchone(
                    cursor,
                    "SELECT id FROM score_breakdowns WHERE application_id = %s AND criteria_id = %s",
                    (application_id, item["criterionId"]),
                )
                if not breakdown:
                    raise CandidateScoringError("PERSISTENCE_FAILED", "The score breakdown row could not be loaded.", 500)
                breakdown_id = int(breakdown["id"])
                cursor.execute("DELETE FROM score_breakdown_items WHERE score_breakdown_id = %s", (breakdown_id,))
                match_status = (
                    "matched"
                    if item["rawScore"] >= 7
                    else "partial"
                    if item["rawScore"] >= 5
                    else "missing"
                )
                evidence_text = item["explanation"] or "No valid evidence."
                cursor.execute(
                    """INSERT INTO score_breakdown_items
                       (score_breakdown_id, requirement_text, match_status, evidence_text, item_score)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (breakdown_id, item["criterionName"], match_status, evidence_text, display_score),
                )

            rank = self._update_ranks(cursor, job_id, application_id)
            stored_response = dict(payload)
            stored_response["runId"] = run_id
            stored_response["rank"] = rank
            stored_response["rankingReady"] = bool(
                payload["eligibility"]["eligible"] and rank is not None
            )
            cursor.execute(
                "UPDATE candidate_scoring_runs SET response_json = %s WHERE id = %s",
                (_json_dump(stored_response), run_id),
            )
            connection.commit()
            return run_id, rank
        except CandidateScoringError:
            connection.rollback()
            raise
        except Exception as error:
            connection.rollback()
            raise CandidateScoringError("PERSISTENCE_FAILED", "Candidate scoring could not be persisted.", 500) from error
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def _update_ranks(cursor: Any, job_id: int, application_id: int) -> int | None:
        cursor.execute(
            """UPDATE applications
               SET rank_no = NULL
               WHERE job_id = %s
                 AND (eligibility_status <> 'eligible'
                      OR application_status IN ('filtered_out', 'rejected', 'withdrawn'))""",
            (job_id,),
        )
        cursor.execute(
            """SELECT id
               FROM applications
               WHERE job_id = %s
                 AND eligibility_status = 'eligible'
                 AND total_score IS NOT NULL
                 AND scoring_version IS NOT NULL
                 AND application_status NOT IN ('filtered_out', 'rejected', 'withdrawn')
               ORDER BY total_score DESC, submitted_at ASC, id ASC""",
            (job_id,),
        )
        ranked = cursor.fetchall()
        for index, row in enumerate(ranked, start=1):
            cursor.execute("UPDATE applications SET rank_no = %s WHERE id = %s", (index, int(row["id"])))
        cursor.execute("SELECT rank_no FROM applications WHERE id = %s LIMIT 1", (application_id,))
        row = cursor.fetchone()
        if not isinstance(row, Mapping) or row.get("rank_no") is None:
            return None
        return int(row["rank_no"])


def database_configuration() -> dict[str, Any]:
    """Read the same DB variables used by the PHP application."""

    host = os.getenv("DB_HOST", "").strip() or os.getenv("MYSQLHOST", "127.0.0.1").strip()
    user = os.getenv("DB_USER", "").strip() or os.getenv("MYSQLUSER", "root").strip()
    password = os.getenv("DB_PASSWORD", "")
    if password == "":
        password = os.getenv("MYSQLPASSWORD", "")
    database = os.getenv("DB_NAME", "").strip() or os.getenv("MYSQLDATABASE", "uwc_hr_decision_support").strip()
    try:
        port = int(os.getenv("DB_PORT", "") or os.getenv("MYSQLPORT", "3306"))
    except ValueError:
        port = 3306
    configuration: dict[str, Any] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "autocommit": False,
        "connection_timeout": max(3, min(int(os.getenv("SCORING_DB_TIMEOUT_SECONDS", "15")), 60)),
    }
    ssl_ca = os.getenv("DB_SSL_CA", "").strip()
    ssl_verify = os.getenv("DB_SSL_VERIFY", "false").lower() == "true"
    if ssl_ca:
        configuration["ssl_ca"] = ssl_ca
        configuration["ssl_verify_cert"] = ssl_verify
    else:
        # Match the existing PHP mysqli connection: Railway's MySQL proxy is
        # used without TLS unless this project explicitly supplies a CA.
        configuration["ssl_disabled"] = not ssl_verify
    return configuration


def build_default_scoring_engine() -> CandidateScoringEngine:
    return CandidateScoringEngine(
        MySQLScoringRepository(),
        configured_candidate_scoring_client(),
    )


def _build_evidence_index(
    profile: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> list[EvidenceCandidate]:
    category_by_id: dict[str, str] = {}
    for key, category in (
        ("education", "education"),
        ("experience", "experience"),
        ("projects", "project"),
        ("skills", "skill"),
        ("certifications", "certification"),
        ("languages", "language"),
        ("achievements", "achievement"),
    ):
        values = profile.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, Mapping):
                continue
            source_id = str(value.get("sourceId") or "").strip()
            if source_id:
                # Keep the canonical section category. A skill entry often
                # references the same work/project sourceId; it must not
                # reclassify that source as a standalone skill record.
                category_by_id.setdefault(source_id, category)
            nested = value.get("evidence") or value.get("skillsEvidence")
            if isinstance(nested, list):
                for reference in nested:
                    if isinstance(reference, Mapping):
                        reference_id = str(reference.get("sourceId") or "").strip()
                        if reference_id:
                            category_by_id.setdefault(reference_id, category)

    records = profile.get("evidenceIndex")
    if isinstance(records, list):
        records = list(records)
    else:
        records = _fallback_structured_evidence(profile)
    records.extend(_application_context_evidence(profile, context))
    result: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        source_id = str(record.get("sourceId") or "").strip()
        source_text = str(record.get("sourceText") or record.get("text") or "").strip()
        if not source_id or not source_text or source_id in seen:
            continue
        source_type = str(record.get("sourceType") or "resume").strip()
        section = str(record.get("sourceSection") or record.get("sourceSectionName") or "").strip()
        category = category_by_id.get(source_id) or _category_from_text(source_id, section)
        if source_type == "application_form" and _looks_like_language_evidence(source_id, section, source_text):
            category = "language"
        concepts = record.get("normalizedConcepts")
        normalized_concepts = tuple(
            str(item).strip().lower() for item in concepts if str(item).strip()
        ) if isinstance(concepts, list) else ()
        result.append(
            EvidenceCandidate(
                source_id=source_id,
                source_section=section,
                source_text=source_text[:5000],
                source_type=source_type,
                category=category,
                priority=_evidence_priority(category, source_type),
                concepts=normalized_concepts,
            )
        )
        seen.add(source_id)
    return result


def _fallback_structured_evidence(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Recover only explicit stored sourceId/sourceText pairs; never invent IDs."""

    records: list[dict[str, Any]] = []
    for key in ("education", "experience", "projects", "skills", "certifications", "languages", "achievements"):
        values = profile.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, Mapping):
                continue
            if value.get("sourceId") and value.get("sourceText"):
                records.append({
                    "sourceId": value["sourceId"],
                    "sourceSection": value.get("sourceSection", key),
                    "sourceText": value["sourceText"],
                    "sourceType": "resume",
                })
            for nested_key in ("evidence", "skillsEvidence"):
                nested = value.get(nested_key)
                if not isinstance(nested, list):
                    continue
                for reference in nested:
                    if isinstance(reference, Mapping) and reference.get("sourceId") and reference.get("text"):
                        records.append({
                            "sourceId": reference["sourceId"],
                            "sourceSection": reference.get("sourceSection", key),
                            "sourceText": reference["text"],
                            "sourceType": "resume",
                        })
    return records


def _select_evidence(criterion: Mapping[str, Any], evidence: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    criterion_type = str(criterion["type"])
    query_text = " ".join(
        [
            str(criterion.get("name", "")),
            *criterion.get("jdEvidence", []),
            str(criterion.get("sourceText", "")),
            str(criterion.get("description", "")),
            str(criterion.get("evidenceRule", "")),
        ]
    )
    query_tokens = _meaningful_tokens(query_text)
    expanded_tokens = _expanded_query_tokens(query_text, criterion_type)
    allowed = EVIDENCE_POOL_BY_TYPE[criterion_type]
    candidates = [item for item in evidence if item.category in allowed]

    if criterion_type == "job_related_language":
        typed_language = [item for item in evidence if _is_language_evidence(item)]
        if typed_language:
            # Explicit application/resume language evidence wins over project
            # or technology text. Do not let a technical sentence substitute
            # for a language record.
            candidates = typed_language
    elif criterion_type == "education_relevance":
        typed_education = [item for item in evidence if item.category in {"education", "application"}]
        if typed_education:
            # Education is primarily assessed from education/application facts;
            # projects and work can be fallback evidence only when those facts
            # are absent.
            candidates = typed_education

    ranked: list[tuple[float, int, EvidenceCandidate]] = []
    for item in candidates:
        evidence_tokens = _meaningful_tokens(" ".join([item.source_text, *item.concepts]))
        direct_overlap = query_tokens & evidence_tokens
        semantic_overlap = (expanded_tokens - query_tokens) & evidence_tokens
        if not _has_retrieval_signal(
            criterion_type,
            query_text,
            str(criterion.get("name") or ""),
            item,
            direct_overlap,
            semantic_overlap,
        ):
            continue

        category_bonus = _criterion_category_bonus(criterion_type, item.category)
        application_bonus = 12 if criterion_type == "job_related_language" and item.source_type == "application_form" else 0
        rank = (
            (len(direct_overlap) * 14)
            + (len(semantic_overlap) * 10)
            + category_bonus
            + application_bonus
            + (item.priority / 100)
        )
        ranked.append((rank, len(direct_overlap) + len(semantic_overlap), item))

    if criterion_type == "preferred_certification":
        # A generic work-history record is not certification evidence merely
        # because the criterion is about a certification. Keep it only when it
        # has a typed certification record or an explicit lexical signal.
        has_typed_certification = any(item.category == "certification" for item in evidence)
        if not has_typed_certification:
            ranked = [entry for entry in ranked if entry[1] > 0]

    ranked.sort(key=lambda value: (-value[0], -value[1], -value[2].priority, value[2].source_id))
    top_k = TOP_K_BY_TYPE.get(criterion_type, DEFAULT_EVIDENCE_TOP_K)
    return _diverse_top_k(ranked, top_k)


def _application_context_evidence(
    profile: Mapping[str, Any],
    context: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Add explicit structured application facts missing from older profiles."""

    candidate = context.get("candidate") if isinstance(context, Mapping) else None
    candidate = candidate if isinstance(candidate, Mapping) else {}
    application = profile.get("applicationData")
    application = application if isinstance(application, Mapping) else {}
    records: list[dict[str, Any]] = []

    languages = application.get("languages")
    if not isinstance(languages, list):
        languages = _parse_application_languages(candidate.get("candidateLanguagesJson"))
    for index, value in enumerate(languages or [], start=1):
        if isinstance(value, str):
            language = value.strip()
            proficiency = ""
        elif isinstance(value, Mapping):
            language = str(value.get("language") or "").strip()
            proficiency = str(value.get("level") or value.get("proficiency") or "").strip()
        else:
            continue
        if not language:
            continue
        records.append(
            {
                "sourceId": f"application-language-{index}",
                "sourceSection": "Application Form",
                "sourceText": " | ".join(part for part in (language, proficiency) if part),
                "sourceType": "application_form",
                "normalizedConcepts": [language, proficiency] if proficiency else [language],
            }
        )

    cgpa = application.get("cgpa")
    if cgpa is None:
        cgpa = candidate.get("candidateCgpa")
    if cgpa not in (None, ""):
        records.append(
            {
                "sourceId": "application-cgpa-1",
                "sourceSection": "Application Form",
                "sourceText": f"CGPA: {cgpa}",
                "sourceType": "application_form",
                "normalizedConcepts": ["cgpa", str(cgpa)],
            }
        )

    education = str(candidate.get("candidateEducation") or "").strip()
    if education:
        records.append(
            {
                "sourceId": "application-education-1",
                "sourceSection": "Application Form",
                "sourceText": education,
                "sourceType": "application_form",
                "normalizedConcepts": [education],
            }
        )

    years = application.get("yearsExperience")
    if years is None:
        years = candidate.get("candidateYearsExperience")
    if years not in (None, ""):
        records.append(
            {
                "sourceId": "application-experience-1",
                "sourceSection": "Application Form",
                "sourceText": f"Years of experience: {years}",
                "sourceType": "application_form",
                "normalizedConcepts": ["experience", str(years)],
            }
        )
    return records


def _parse_application_languages(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        return [value]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(decoded, list):
        return decoded
    if isinstance(decoded, Mapping):
        return [decoded]
    return []


def _diverse_top_k(
    ranked: list[tuple[float, int, EvidenceCandidate]],
    top_k: int,
) -> list[EvidenceCandidate]:
    if not ranked:
        return []
    selected: list[tuple[float, int, EvidenceCandidate]] = []
    selected_ids: set[str] = set()
    categories: set[str] = set()
    # Preserve at least one strong record from each useful source category.
    for entry in ranked:
        if len(selected) >= top_k:
            break
        item = entry[2]
        if item.category in categories:
            continue
        selected.append(entry)
        selected_ids.add(item.source_id)
        categories.add(item.category)
    for entry in ranked:
        if len(selected) >= top_k:
            break
        if entry[2].source_id not in selected_ids:
            selected.append(entry)
            selected_ids.add(entry[2].source_id)
    selected.sort(key=lambda value: (-value[0], -value[1], -value[2].priority, value[2].source_id))
    return [entry[2] for entry in selected]


def _has_retrieval_signal(
    criterion_type: str,
    query_text: str,
    criterion_name: str,
    item: EvidenceCandidate,
    direct_overlap: set[str],
    semantic_overlap: set[str],
) -> bool:
    evidence_tokens = _meaningful_tokens(" ".join([item.source_text, *item.concepts]))
    lowered_name = criterion_name.casefold()
    if re.search(r"\btest(?:ing)?\b|\bqa\b|quality assurance", lowered_name):
        return bool(evidence_tokens & SEMANTIC_QUERY_ALIASES["testing"])
    if re.search(r"documentation|technical writing|readme", lowered_name):
        return bool(evidence_tokens & SEMANTIC_QUERY_ALIASES["documentation"])
    specific_direct = direct_overlap - GENERIC_RETRIEVAL_TOKENS
    if specific_direct or semantic_overlap:
        return True
    if criterion_type == "education_relevance":
        return item.category in {"education", "application"}
    if criterion_type == "relevant_experience":
        # A broad experience criterion can be evaluated from a work record,
        # but named-language/technology requirements need an explicit match.
        named_languages = _named_programming_languages(query_text)
        return item.category == "experience" and not named_languages
    return False


def _criterion_category_bonus(criterion_type: str, category: str) -> int:
    preferences = {
        "relevant_skill": {"experience": 12, "project": 11, "skill": 10, "achievement": 8, "application": 4},
        "relevant_experience": {"experience": 14, "project": 12, "skill": 10, "achievement": 8, "application": 6},
        "education_relevance": {"education": 18, "application": 15, "project": 6, "experience": 5, "skill": 4},
        "domain_knowledge": {"experience": 13, "project": 12, "skill": 9, "education": 6, "application": 4},
        "preferred_certification": {"certification": 20, "experience": 9, "project": 8, "skill": 7, "application": 4},
        "job_related_language": {"language": 20, "application": 18, "experience": 3, "skill": 2},
    }
    return preferences.get(criterion_type, {}).get(category, 0)


def _expanded_query_tokens(query_text: str, criterion_type: str) -> set[str]:
    tokens = _meaningful_tokens(query_text)
    lowered = query_text.casefold()
    triggers = {
        "web": r"\bweb\b|\bwebsite\b|\bweb\s+application",
        "frontend": r"front[\s-]?end|user interface|ui",
        "backend": r"back[\s-]?end|api",
        "testing": r"test|bug|quality|verification|validation",
        "database": r"database|sql|mysql|mariadb|sqlite|postgres|storage",
        "version_control": r"version control|git|github|repository|branch|commit",
        "documentation": r"document|technical writing|readme|report",
    }
    for key, pattern in triggers.items():
        if re.search(pattern, lowered):
            tokens.update(SEMANTIC_QUERY_ALIASES[key])
    if criterion_type == "relevant_experience" or re.search(r"program(?:ming|mer).*language", lowered):
        for language in _named_programming_languages(query_text):
            tokens.update(PROGRAMMING_LANGUAGE_ALIASES.get(language, {language}))
    return tokens


def _named_programming_languages(value: str) -> set[str]:
    lowered = value.casefold()
    matches: set[str] = set()
    for canonical, aliases in PROGRAMMING_LANGUAGE_ALIASES.items():
        for alias in aliases:
            if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
                matches.add(canonical)
                break
    return matches


def _is_language_evidence(item: EvidenceCandidate) -> bool:
    return item.category == "language" or _looks_like_language_evidence(
        item.source_id,
        item.source_section,
        item.source_text,
    )


def _looks_like_language_evidence(source_id: str, section: str, source_text: str) -> bool:
    value = f"{source_id} {section} {source_text}".casefold()
    return "language" in value or "languages" in value or "application form" in section.casefold() and "|" in source_text


def _evidence_priority(category: str, source_type: str) -> int:
    if category == "language" and source_type == "application_form":
        return 130
    if category == "language":
        return 110
    if category == "application" and source_type == "application_form":
        return 100
    return EVIDENCE_PRIORITY.get(category, EVIDENCE_PRIORITY["other"])


def _evaluate_eligibility(context: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    """Apply HR-configured mandatory filters separately from soft criterion scoring."""

    filters = dict(context.get("eligibility") or {})
    values = {
        str(item.get("filterKey")): item.get("filterValue")
        for item in context.get("eligibilityValues", [])
        if isinstance(item, Mapping) and str(item.get("filterKey") or "").strip()
    }
    candidate = context.get("candidate") if isinstance(context.get("candidate"), Mapping) else {}
    reasons: list[dict[str, Any]] = []

    min_cgpa = _number_or_none(filters.get("minCgpa"))
    if min_cgpa is None:
        min_cgpa = _number_from_text(values.get("minCGPA"))
    actual_cgpa = _number_or_none(profile.get("cgpa"))
    if actual_cgpa is None:
        actual_cgpa = _number_or_none(candidate.get("candidateCgpa"))
    if min_cgpa is not None:
        _append_eligibility_reason(reasons, "minimum_cgpa", min_cgpa, actual_cgpa, actual_cgpa is not None and actual_cgpa >= min_cgpa)

    min_years = _number_or_none(filters.get("minYearsExperience"))
    if min_years is None:
        min_years = _number_from_text(values.get("minExperience"))
    actual_years = _number_or_none(profile.get("totalExperienceYears"))
    if actual_years is None:
        months = _number_or_none(profile.get("totalExperienceMonths"))
        actual_years = months / 12 if months is not None else None
    if actual_years is None:
        actual_years = _number_or_none(candidate.get("candidateYearsExperience"))
    if min_years is not None:
        _append_eligibility_reason(reasons, "minimum_experience", min_years, actual_years, actual_years is not None and actual_years >= min_years)

    required_qualification = str(filters.get("requiredQualification") or values.get("educationLevel") or "").strip()
    if required_qualification:
        education_values = [str(profile.get("highestEducationLevel") or ""), str(candidate.get("candidateEducation") or "")]
        for entry in profile.get("education", []) if isinstance(profile.get("education"), list) else []:
            if isinstance(entry, Mapping):
                education_values.extend(str(entry.get(key) or "") for key in ("level", "qualification", "field", "rawQualification"))
        actual_qualification = " | ".join(item for item in education_values if item.strip())
        passed = _qualification_meets(actual_qualification, required_qualification)
        _append_eligibility_reason(reasons, "required_qualification", required_qualification, actual_qualification or None, passed)

    required_language = str(filters.get("requiredLanguage") or values.get("requiredLanguage") or "").strip()
    if required_language:
        language_values = [str(candidate.get("candidateLanguagesJson") or "")]
        for entry in profile.get("languages", []) if isinstance(profile.get("languages"), list) else []:
            if isinstance(entry, Mapping):
                language_values.extend(str(entry.get(key) or "") for key in ("language", "proficiency"))
        actual_languages = " | ".join(language_values)
        passed = _contains_requirement(actual_languages, required_language)
        _append_eligibility_reason(reasons, "required_language", required_language, actual_languages or None, passed)

    required_location = str(filters.get("requiredLocation") or values.get("requiredLocation") or "").strip()
    if required_location:
        personal_info = profile.get("personalInfo")
        if not isinstance(personal_info, Mapping):
            personal_info = {}
        actual_location = str(personal_info.get("location") or candidate.get("candidateLocation") or "").strip()
        _append_eligibility_reason(reasons, "required_location", required_location, actual_location or None, _contains_requirement(actual_location, required_location))

    max_notice = _number_or_none(filters.get("maxNoticePeriodDays"))
    if max_notice is None:
        max_notice = _number_from_text(values.get("maxNoticePeriod"))
    actual_notice = _number_or_none(candidate.get("candidateNoticePeriodDays"))
    if actual_notice is None:
        actual_notice = _notice_period_days(profile.get("noticePeriod"))
    if max_notice is not None:
        _append_eligibility_reason(reasons, "maximum_notice_period", max_notice, actual_notice, actual_notice is not None and actual_notice <= max_notice)

    failed = [item for item in reasons if not item["passed"]]
    return {
        "eligible": not failed,
        "filteredOut": bool(failed),
        "reasons": reasons,
    }


def _append_eligibility_reason(reasons: list[dict[str, Any]], code: str, required: Any, actual: Any, passed: bool) -> None:
    reasons.append({"code": code, "required": required, "actual": actual, "passed": bool(passed)})


def _qualification_meets(actual: str, required: str) -> bool:
    actual_tokens = _meaningful_tokens(actual)
    required_tokens = _meaningful_tokens(required)
    if required_tokens and required_tokens.issubset(actual_tokens):
        return True
    levels = {
        "spm": 1,
        "certificate": 2,
        "diploma": 3,
        "associate": 3,
        "bachelor": 4,
        "master": 5,
        "phd": 6,
        "doctorate": 6,
    }
    actual_level = max((value for key, value in levels.items() if key in actual.lower()), default=0)
    required_level = max((value for key, value in levels.items() if key in required.lower()), default=0)
    return required_level > 0 and actual_level >= required_level


def _contains_requirement(actual: str, required: str) -> bool:
    required_tokens = _meaningful_tokens(required)
    actual_tokens = _meaningful_tokens(actual)
    return bool(required_tokens) and required_tokens.issubset(actual_tokens)


def _has_grounded_reason(reason: str, evidence_text: str) -> bool:
    reason_tokens = _meaningful_tokens(reason)
    evidence_tokens = _meaningful_tokens(evidence_text)
    return bool(reason_tokens & evidence_tokens)


def _score_from_semantics(semantic: CandidateSemanticOutput) -> float:
    """Map the validated semantic assessment to the existing 0-10 contract."""

    if semantic.relationship == "unrelated":
        return 0.0

    lower, upper = (
        ADJACENT_SCORE_BAND
        if semantic.relationship == "adjacent"
        else CAPABILITY_SCORE_BANDS[semantic.capabilityLevel]
    )
    position = SCORE_BAND_POSITIONS[(semantic.coverage, semantic.evidenceStrength)]
    return round(lower + ((upper - lower) * position), 2)


def _match_level_for_score(score: float) -> str:
    if score <= 0:
        return "none"
    if score < 5:
        return "weak"
    if score < 7:
        return "partial"
    if score < 9:
        return "matched"
    return "strong_match"


def _category_from_text(source_id: str, section: str) -> str:
    value = f"{source_id} {section}".lower()
    for marker, category in (
        ("experience", "experience"),
        ("work", "experience"),
        ("responsib", "experience"),
        ("achievement", "achievement"),
        ("project", "project"),
        ("skill", "skill"),
        ("cert", "certification"),
        ("education", "education"),
        ("language", "language"),
        ("summary", "summary"),
        ("application", "application"),
    ):
        if marker in value:
            return category
    return "other"


def _meaningful_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", value.lower()):
        if token in STOP_WORDS or len(token) < 3:
            continue
        tokens.add(_stem(token))
    return tokens


def _stem(token: str) -> str:
    for suffix in ("ization", "ations", "ation", "ments", "ment", "ingly", "ing", "ers", "er", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _split_jd_evidence(value: str) -> list[str]:
    if not value:
        return []
    pieces = [part.strip() for part in re.split(r"\s*\|\s*|\r?\n+", value) if part.strip()]
    return pieces or [value]


def _number_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _number_from_text(value: Any) -> Decimal | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return _number_or_none(match.group(0)) if match else None


def _notice_period_days(value: Any) -> Decimal | None:
    text = str(value or "").lower()
    number = _number_from_text(text)
    if number is None:
        return None
    if "month" in text:
        return number * 30
    if "week" in text:
        return number * 7
    return number


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _candidate_identity_snapshot(value: Any) -> dict[str, Any]:
    """Keep the profile hash stable when scoring mutates application status."""

    if not isinstance(value, Mapping):
        return {}
    keys = (
        "candidateId",
        "candidateName",
        "candidateCgpa",
        "candidateYearsExperience",
        "candidateNoticePeriodDays",
        "candidateEducation",
        "candidateLocation",
        "candidateLanguagesJson",
    )
    return {key: value.get(key) for key in keys}


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
