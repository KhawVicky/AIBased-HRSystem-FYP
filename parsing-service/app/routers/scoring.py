"""Candidate scoring API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.scoring import CandidateScoringRequest, CandidateScoringResponse
from app.services.candidate_scoring import CandidateScoringError, build_default_scoring_engine


router = APIRouter()


@router.post("/api/scoring/candidate", response_model=CandidateScoringResponse)
def score_candidate(payload: CandidateScoringRequest) -> CandidateScoringResponse:
    """Score one stored application against the current HR criteria snapshot."""

    try:
        engine = build_default_scoring_engine()
        result = engine.score(
            payload.jobId,
            payload.applicationId,
            force_rescore=payload.forceRescore,
        )
        return CandidateScoringResponse(success=True, data=result)
    except CandidateScoringError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
