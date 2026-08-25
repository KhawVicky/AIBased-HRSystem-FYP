"""Public request and response contracts for candidate scoring."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class CandidateScoringRequest(BaseModel):
    jobId: int = Field(gt=0)
    applicationId: int = Field(gt=0)
    forceRescore: bool = False


class ScoringEvidence(BaseModel):
    sourceId: str
    sourceSection: str
    sourceText: str
    sourceType: Literal["resume", "application_form"] = "resume"


class CriterionScore(BaseModel):
    criterionId: int
    criterionName: str
    criterionType: str
    weight: float
    jdEvidence: list[str] = Field(default_factory=list)
    rawScore: float
    weightedContribution: float
    explanation: str
    grounded: bool
    evidenceIds: list[str] = Field(default_factory=list)
    matchedResumeEvidence: list[ScoringEvidence] = Field(default_factory=list)
    matchLevel: Literal["strong_match", "matched", "partial", "weak", "none"]
    qwenStatus: Literal["live", "not_used_no_evidence", "rejected_grounding"]

    @field_validator("rawScore")
    @classmethod
    def validate_raw_score(cls, value: float) -> float:
        if not 0 <= value <= 10:
            raise ValueError("rawScore must be between 0 and 10")
        return round(float(value), 2)


class EligibilityResult(BaseModel):
    eligible: bool
    filteredOut: bool
    reasons: list[dict[str, Any]] = Field(default_factory=list)


class ScoringDiagnostics(BaseModel):
    qwenStatus: Literal["live", "not_used_no_evidence"]
    qwenUsed: bool
    fallbackUsed: bool = False
    criterionCount: int
    scoredCriterionCount: int
    zeroEvidenceCriterionCount: int
    groundingRejectedCount: int
    totalWeight: float
    overallScore: float
    scoringVersion: str
    model: str | None = None
    runtimeTask: str = "candidate_criterion_scoring"
    criteriaSnapshotHash: str
    profileSnapshotHash: str
    requestHash: str
    profileAvailable: bool


class CandidateScoringData(BaseModel):
    applicationId: int
    jobId: int
    candidateId: int
    runId: int
    eligibility: EligibilityResult
    overallScore: float
    totalWeight: float
    rank: int | None = None
    rankingReady: bool
    scoreBreakdown: list[CriterionScore]
    diagnostics: ScoringDiagnostics


class CandidateScoringResponse(BaseModel):
    success: bool = True
    data: CandidateScoringData
    warnings: list[str] = Field(default_factory=list)
