"""Pydantic request and response contracts for the criteria worker API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class GenerateCriteriaRequest(BaseModel):
    jobTitle: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=200)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)

    @field_validator("responsibilities", "requirements", "qualifications")
    @classmethod
    def clean_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    def has_evidence(self) -> bool:
        return bool(
            self.responsibilities or self.requirements or self.qualifications
        )


class Criterion(BaseModel):
    criterionId: str
    type: str
    name: str
    description: str
    evidenceRule: str
    sourceText: str
    sourceIds: list[str] | None = None
    sourceCriterionIds: list[str] | None = None
    mergedFromIds: list[str] | None = None
    groundingScores: list[float] | None = None
    importance: Literal["high", "medium", "low"] | None = None
    suggestedWeight: int


class EligibilitySuggestions(BaseModel):
    minCGPA: float | None = None
    minExperience: str | None = None
    educationLevel: str | None = None
    requiredLanguage: str | None = None
    requiredLocation: str | None = None
    enabledFilters: list[str] = Field(default_factory=list)


class GenerateCriteriaResponse(BaseModel):
    criteria: list[Criterion]
    ignoredTexts: list[dict[str, Any]]
    warnings: list[str]
    weightTotal: int
    eligibilitySuggestions: EligibilitySuggestions = Field(
        default_factory=EligibilitySuggestions
    )
    model: str
    audit: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    deployment: dict[str, Any] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    ready: bool
    model: str
    mockMode: bool
    deployment: dict[str, Any] = Field(default_factory=dict)
