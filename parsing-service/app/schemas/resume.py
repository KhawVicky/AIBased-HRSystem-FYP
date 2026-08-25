"""Stable contracts for evidence-preserving resume parsing."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRecord(BaseModel):
    """A traceable excerpt from the resume or application form."""

    sourceId: str
    sourceSection: str
    sourceText: str
    normalizedConcepts: list[str] = Field(default_factory=list)
    sourceType: Literal["resume", "application_form"] = "resume"


class PersonalInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class EvidenceReference(BaseModel):
    sourceId: str
    text: str
    sourceSection: str | None = None


class EducationEntry(BaseModel):
    id: str
    level: str | None = None
    rawQualification: str | None = None
    qualification: str | None = None
    field: str | None = None
    institution: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    graduationYear: int | None = None
    cgpa: float | None = None
    sourceId: str
    sourceText: str
    sourceSection: str = "Education"


class ExperienceEntry(BaseModel):
    id: str
    jobTitle: str | None = None
    company: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    isCurrent: bool = False
    durationMonths: int | None = None
    durationConfidence: Literal["month", "year", "unresolved"] = "unresolved"
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    skillsEvidence: list[EvidenceReference] = Field(default_factory=list)
    workDomain: str | None = None
    sourceId: str
    sourceText: str
    sourceSection: str = "Work Experience"


class SkillEntry(BaseModel):
    id: str
    name: str
    normalizedName: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    id: str
    name: str
    issuer: str | None = None
    issueDate: str | None = None
    expiryDate: str | None = None
    credentialId: str | None = None
    sourceId: str
    sourceText: str
    sourceSection: str = "Certifications"


class LanguageEntry(BaseModel):
    id: str
    language: str
    proficiency: str | None = None
    sourceId: str
    sourceText: str
    sourceSection: str = "Languages"


class ProjectEntry(BaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    sourceId: str
    sourceText: str
    sourceSection: str = "Projects"


class AchievementEntry(BaseModel):
    id: str
    text: str
    sourceId: str
    sourceText: str
    sourceSection: str = "Achievements"


class ApplicationData(BaseModel):
    """Trusted application-form values supplied alongside a resume."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    cgpa: float | None = None
    noticePeriod: str | None = None
    yearsExperience: float | None = None
    languages: list[dict[str, str]] = Field(default_factory=list)


class DataConflict(BaseModel):
    field: str
    resumeValue: Any = None
    applicationValue: Any = None
    resolution: str


class CandidateProfile(BaseModel):
    """Canonical profile consumed by later eligibility and scoring layers."""

    candidateId: int | str | None = None
    personalInfo: PersonalInfo = Field(default_factory=PersonalInfo)
    profileSummary: str | None = None
    primaryDomain: str | None = None
    keyStrengths: list[str] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    achievements: list[AchievementEntry] = Field(default_factory=list)
    cgpa: float | None = None
    noticePeriod: str | None = None
    totalExperienceYears: float | None = None
    totalExperienceMonths: int | None = None
    highestEducationLevel: str | None = None
    applicationData: ApplicationData | None = None
    dataConflicts: list[DataConflict] = Field(default_factory=list)
    candidateSummary: str | None = None
    evidenceIndex: list[EvidenceRecord] = Field(default_factory=list)


class SemanticEvidence(BaseModel):
    sourceId: str
    semanticCapabilities: list[str] = Field(default_factory=list)
    sourceText: str | None = None


class SemanticSkillEvidence(BaseModel):
    sourceId: str
    skills: list[str] = Field(default_factory=list)
    sourceText: str | None = None


class SemanticResumeOutput(BaseModel):
    """The intentionally narrow JSON contract accepted from Qwen."""

    primaryDomain: str | None = None
    primaryDomainSourceIds: list[str] = Field(default_factory=list)
    experienceEvidence: list[SemanticEvidence] = Field(default_factory=list)
    skillEvidence: list[SemanticSkillEvidence] = Field(default_factory=list)
    educationSemantics: list[SemanticEvidence] = Field(default_factory=list)
    projectEvidence: list[SemanticEvidence] = Field(default_factory=list)


class ResumeDiagnostics(BaseModel):
    parserVersion: str
    extractionMethod: str
    pageCount: int
    detectedSectionCount: int
    evidenceCount: int
    educationCount: int
    experienceCount: int
    normalizedSkillCount: int
    summaryGenerated: bool
    qwenStatus: Literal["completed", "skipped_no_endpoint", "skipped_not_requested", "failed"]
    groundingRejectionCount: int = 0
    stages: list[str] = Field(default_factory=list)
    qualityStatus: Literal["healthy", "review_required", "failed"] = "healthy"
    qualityWarnings: list[str] = Field(default_factory=list)
    extractionQualityScore: float | None = None
    extractionQualitySignals: list[str] = Field(default_factory=list)
    extractionUsefulTextCount: int | None = None
    spacedCharacterSequenceCount: int = 0
    controlCharacterCount: int = 0
    recognizedSectionCount: int = 0
    emailDetected: bool = False
    fallbackAttempted: bool = False
    fallbackSelected: bool = False


class ResumeParseData(BaseModel):
    rawText: str
    sections: dict[str, str] = Field(default_factory=dict)
    profile: CandidateProfile
    diagnostics: ResumeDiagnostics


class ResumeParseResponse(BaseModel):
    success: bool = True
    data: ResumeParseData
    warnings: list[str] = Field(default_factory=list)
