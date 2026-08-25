"""Provides rule-based criteria routes."""

from fastapi import APIRouter

from app.schemas.jd_criteria import CriteriaGenerationResponse, JDCriteriaRequest
from app.services.jd_criteria_generator import generate_jd_criteria


router = APIRouter(prefix="/api/jd/criteria", tags=["JD Criteria"])


@router.post("/generate", response_model=CriteriaGenerationResponse)
def generate_criteria(request: JDCriteriaRequest):
    """Generate deterministic, HR-reviewable criteria from the submitted JD fields."""

    return generate_jd_criteria(request)
