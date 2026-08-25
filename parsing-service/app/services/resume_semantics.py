"""Configurable Qwen adapter for grounded resume semantics."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.resume import EvidenceRecord, SemanticResumeOutput


class ResumeSemanticError(RuntimeError):
    """Raised when the configured semantic provider cannot return valid JSON."""


class ResumeSemanticClient(Protocol):
    def understand(
        self,
        *,
        resume_text: str,
        sections: Mapping[str, str],
        evidence_index: list[EvidenceRecord],
    ) -> SemanticResumeOutput:
        ...


SEMANTIC_SYSTEM_PROMPT = """You are the semantic understanding stage of a resume parser.
Return JSON only. Do not write a summary and do not rewrite a candidate profile.
Every item must reference one sourceId from the supplied evidenceIndex.
Only identify capabilities, skills, domains, or education/project semantics that are
supported by the referenced source text. Do not invent dates, employers, education,
CGPA, languages, certifications, experience years, or personal attributes.
Python will validate every sourceId and sourceText before using your output.

Use this JSON shape:
{
  "primaryDomain": null,
  "primaryDomainSourceIds": [],
  "experienceEvidence": [],
  "skillEvidence": [],
  "educationSemantics": [],
  "projectEvidence": []
}
"""


class QwenResumeSemanticClient:
    """Call an OpenAI-compatible or RunPod JSON endpoint without model prose."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str | None = None,
        model: str = "Qwen/Qwen2.5-3B-Instruct",
        protocol: str = "openai_chat",
        timeout_seconds: float = 90.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key or ""
        self.model = model
        self.protocol = protocol
        self.timeout_seconds = timeout_seconds

    def understand(
        self,
        *,
        resume_text: str,
        sections: Mapping[str, str],
        evidence_index: list[EvidenceRecord],
    ) -> SemanticResumeOutput:
        """Request narrow evidence-grounded semantics; deterministic parsing remains authoritative."""

        evidence_payload = [item.model_dump() for item in evidence_index]
        context = {
            "resumeText": resume_text,
            "sections": dict(sections),
            "evidenceIndex": evidence_payload,
        }
        if self.protocol.lower() == "runpod":
            payload: dict[str, Any] = {
                "input": {
                    "task": "resume_semantic_understanding",
                    "systemPrompt": SEMANTIC_SYSTEM_PROMPT,
                    **context,
                }
            }
        else:
            payload = {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SEMANTIC_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(context, ensure_ascii=False),
                    },
                ],
            }

        request = Request(
            self.endpoint_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise ResumeSemanticError("The configured Qwen resume request failed") from error

        try:
            decoded = json.loads(response_data)
            semantic_payload = _extract_json_payload(decoded)
            return SemanticResumeOutput.model_validate(semantic_payload)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ResumeSemanticError("The Qwen resume response was not valid semantic JSON") from error

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def configured_resume_semantic_client() -> QwenResumeSemanticClient | None:
    # The parsing service may reuse the existing JD RunPod deployment. A
    # resume-specific value still wins when a separate provider is desired.
    resume_endpoint = os.getenv("RESUME_QWEN_ENDPOINT_URL", "").strip()
    endpoint = resume_endpoint or os.getenv("RUNPOD_CRITERIA_ENDPOINT_URL", "").strip()
    if not endpoint:
        return None
    try:
        timeout = float(os.getenv("RESUME_QWEN_TIMEOUT_SECONDS", "90"))
    except ValueError:
        timeout = 90.0
    protocol = os.getenv("RESUME_QWEN_PROTOCOL", "").strip()
    if not protocol:
        protocol = "runpod" if "api.runpod.ai" in endpoint.lower() else "openai_chat"
    model = os.getenv("RESUME_QWEN_MODEL", "").strip()
    if not model:
        model = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct").strip()
    return QwenResumeSemanticClient(
        endpoint_url=endpoint,
        api_key=(
            os.getenv("RESUME_QWEN_API_KEY", "").strip()
            or os.getenv("RUNPOD_API_KEY", "").strip()
            or None
        ),
        model=model,
        protocol=protocol,
        timeout_seconds=max(1.0, min(timeout, 300.0)),
    )


def _extract_json_payload(value: Any) -> Any:
    """Unwrap common chat/RunPod envelopes and tolerate harmless model prose."""

    if isinstance(value, str):
        content = value.strip()
        fence = chr(96) * 3
        content = re.sub(r"^" + fence + r"(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*" + fence + r"$", "", content)
        return _decode_json_text(content)

    if isinstance(value, list):
        for item in value:
            try:
                return _extract_json_payload(item)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        raise ValueError("No JSON object found in response list")

    if not isinstance(value, Mapping):
        raise TypeError("Semantic response must be an object")

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
            candidate = value[key]
            if isinstance(candidate, Mapping) and key == "data" and "profile" in candidate:
                continue
            try:
                return _extract_json_payload(candidate)
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
