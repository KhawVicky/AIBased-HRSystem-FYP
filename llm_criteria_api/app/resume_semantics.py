"""Isolated resume semantic task for the shared Qwen RunPod worker."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .model_loader import ModelLoader


RESUME_SEMANTIC_SYSTEM_PROMPT = """You are the semantic understanding stage of a resume parser.
Return JSON only. Do not write a summary and do not rewrite a candidate profile.
Every item must reference one sourceId from the supplied evidenceIndex. Use only
evidence records whose sourceType is resume; application-form records are not
resume evidence for this task.

Only identify capabilities, skills, domains, or education/project semantics that
are supported by the referenced sourceText. Do not invent dates, employers,
education, CGPA, languages, certifications, experience years, or personal
attributes. If a claim is not supported by a sourceText, omit it. Copy the
referenced sourceText exactly when you provide it.

Use this JSON shape:
{
  "primaryDomain": null,
  "primaryDomainSourceIds": [],
  "experienceEvidence": [],
  "skillEvidence": [],
  "educationSemantics": [],
  "projectEvidence": []
}

Each experienceEvidence, educationSemantics, and projectEvidence item has
sourceId, semanticCapabilities (an array of concise labels), and sourceText.
Each skillEvidence item has sourceId, skills (an array of concise labels), and
sourceText.
"""


class ResumeEvidence(BaseModel):
    """Minimal evidence record sent to the shared worker."""

    model_config = ConfigDict(extra="ignore")

    sourceId: str
    sourceSection: str
    sourceText: str
    normalizedConcepts: list[str] = Field(default_factory=list)
    sourceType: Literal["resume", "application_form"] = "resume"


class ResumeSemanticRequest(BaseModel):
    """RunPod input contract for resume-only semantic enrichment."""

    model_config = ConfigDict(extra="ignore")

    task: Literal["resume_semantic_understanding"]
    resumeText: str
    sections: dict[str, str] = Field(default_factory=dict)
    evidenceIndex: list[ResumeEvidence] = Field(default_factory=list)
    # Accepted for adapter compatibility, but the worker always uses the
    # fixed safety prompt above rather than a caller-supplied system prompt.
    systemPrompt: str | None = None


class ResumeSemanticEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sourceId: str
    semanticCapabilities: list[str] = Field(default_factory=list)
    sourceText: str | None = None


class ResumeSemanticSkillEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sourceId: str
    skills: list[str] = Field(default_factory=list)
    sourceText: str | None = None


class ResumeSemanticOutput(BaseModel):
    """Narrow JSON returned to the parsing service for grounding."""

    model_config = ConfigDict(extra="ignore")

    primaryDomain: str | None = None
    primaryDomainSourceIds: list[str] = Field(default_factory=list)
    experienceEvidence: list[ResumeSemanticEvidence] = Field(default_factory=list)
    skillEvidence: list[ResumeSemanticSkillEvidence] = Field(default_factory=list)
    educationSemantics: list[ResumeSemanticEvidence] = Field(default_factory=list)
    projectEvidence: list[ResumeSemanticEvidence] = Field(default_factory=list)


def build_resume_semantic_messages(request: ResumeSemanticRequest) -> list[dict[str, str]]:
    """Build deterministic chat messages without logging resume contents."""

    context = {
        "resumeText": request.resumeText,
        "sections": request.sections,
        "evidenceIndex": [item.model_dump() for item in request.evidenceIndex],
    }
    return [
        {"role": "system", "content": RESUME_SEMANTIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(context, ensure_ascii=False),
        },
    ]


def generate_resume_semantics(
    loader: ModelLoader,
    request: ResumeSemanticRequest,
) -> dict[str, Any]:
    """Run Qwen through the shared loader and validate the resume contract."""

    if not loader.loaded:
        raise RuntimeError("Model is not ready")
    raw_output = loader.generate(build_resume_semantic_messages(request))
    return ResumeSemanticOutput.model_validate(_extract_json_payload(raw_output)).model_dump(
        exclude_none=True
    )


def _extract_json_payload(value: Any) -> Any:
    """Unwrap RunPod/chat envelopes and tolerate harmless model prose."""

    if isinstance(value, str):
        content = value.strip()
        fenced = re.fullmatch(
            r"""\s*```(?:json)?\s*(.*?)\s*```\s*""",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced:
            content = fenced.group(1).strip()
        return _decode_json_text(content)

    if isinstance(value, list):
        for item in value:
            try:
                return _extract_json_payload(item)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        raise ValueError("No semantic JSON object found in response list")

    if not isinstance(value, Mapping):
        raise TypeError("Resume semantic response must be an object")

    choices = value.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and "content" in message:
                return _extract_json_payload(message["content"])
            if "text" in first:
                return _extract_json_payload(first["text"])

    for key in ("output", "data", "result", "semantic"):
        if key in value:
            try:
                return _extract_json_payload(value[key])
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

    return value


def _decode_json_text(content: str) -> Any:
    """Decode JSON even when the model adds a short preamble or suffix."""

    try:
        return json.loads(content)
    except json.JSONDecodeError as first_error:
        decoder = json.JSONDecoder()
        for match in re.finditer(r"[\[{]", content):
            try:
                candidate, _ = decoder.raw_decode(content[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, Mapping):
                return candidate
        raise first_error
