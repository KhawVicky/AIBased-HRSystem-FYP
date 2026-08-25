"""Defines rule-based criteria request and response data."""

from typing import Literal

from pydantic import BaseModel, Field


class JDCriteriaRequest(BaseModel):
    jobTitle: str = ""
    department: str = ""
    description: str = ""
    qualifications: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)


JDCriterionType = Literal[
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
]


class GeneratedCriterion(BaseModel):
    id: str
    category: str
    type: JDCriterionType
    name: str
    weight: int
    status: str = "active"
    jdEvidence: list[str] = Field(default_factory=list)
    explanation: str
    resumeEvidenceToCheck: str
    isAutoDetected: bool = True


class EligibilitySuggestions(BaseModel):
    minCGPA: float | None = None
    minExperience: str | None = None
    educationLevel: str | None = None
    requiredLanguage: str | None = None
    requiredLocation: str | None = None
    enabledFilters: list[str] = Field(default_factory=list)


class CriteriaGenerationData(BaseModel):
    criteria: list[GeneratedCriterion]
    eligibilitySuggestions: EligibilitySuggestions


class CriteriaGenerationResponse(BaseModel):
    success: bool = True
    data: CriteriaGenerationData
    warnings: list[str] = Field(default_factory=list)
