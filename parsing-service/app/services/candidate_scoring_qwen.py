"""RunPod adapter for the isolated candidate criterion scoring task."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CandidateScoringQwenError(RuntimeError):
    """Raised when live semantic scoring is unavailable or invalid."""


class CandidateScoringQwenClient(Protocol):
    model: str

    def score(self, *, criterion: dict[str, Any], candidate_evidence: list[dict[str, Any]]) -> "QwenCriterionResult":
        ...


@dataclass(frozen=True)
class QwenCriterionResult:
    payload: dict[str, Any]
    model: str
    qwen_used: bool
    mock_mode: bool


class RunPodCandidateScoringClient:
    """Call the existing RunPod endpoint; no local or semantic fallback is used."""

    def __init__(
        self,
        endpoint_url: str,
        *,
        api_key: str | None = None,
        model: str = "Qwen/Qwen2.5-3B-Instruct",
        protocol: str = "runpod",
        timeout_seconds: float = 180.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key or ""
        self.model = model
        self.protocol = protocol
        self.timeout_seconds = timeout_seconds

    def score(
        self,
        *,
        criterion: dict[str, Any],
        candidate_evidence: list[dict[str, Any]],
    ) -> QwenCriterionResult:
        """Send only one criterion and retrieved evidence to the shared semantic worker."""

        context = {
            "criterion": criterion,
            "candidateEvidence": candidate_evidence,
        }
        if self.protocol.lower() == "runpod":
            request_payload: dict[str, Any] = {
                "input": {
                    "task": "candidate_criterion_scoring",
                    **context,
                }
            }
        else:
            system_prompt = (
                "Return JSON only for one candidate criterion using relationship, "
                "capabilityLevel, coverage, evidenceStrength, usedEvidenceIds and "
                "reason. Use only supplied candidateEvidence. Classify relationship "
                "before capability; adjacent evidence must not be treated as direct. "
                "Do not return a score or matchLevel. Do not calculate weights or totals."
            )
            request_payload = {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
            }

        request = Request(
            self.endpoint_url,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise CandidateScoringQwenError("The live Qwen candidate scoring request failed") from error

        try:
            decoded = json.loads(raw_body)
            if isinstance(decoded, Mapping) and decoded.get("status") == "error":
                error = decoded.get("error")
                message = error.get("message") if isinstance(error, Mapping) else "RunPod rejected the request"
                raise CandidateScoringQwenError(str(message))
            output = _extract_json_payload(decoded)
            if not isinstance(output, Mapping):
                raise TypeError("candidate scoring output must be an object")
            if output.get("status") == "error":
                error = output.get("error")
                message = error.get("message") if isinstance(error, Mapping) else "RunPod candidate scoring failed"
                raise CandidateScoringQwenError(str(message))
            payload = dict(output)
        except CandidateScoringQwenError:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise CandidateScoringQwenError("The Qwen candidate scoring response was not valid JSON") from error

        mock_mode = bool(payload.get("mockMode", False))
        if mock_mode or payload.get("qwenUsed") is False:
            raise CandidateScoringQwenError("The candidate scoring response indicates mock or fallback mode")
        return QwenCriterionResult(
            payload=payload,
            model=str(payload.get("model") or self.model),
            qwen_used=True,
            mock_mode=False,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def configured_candidate_scoring_client() -> RunPodCandidateScoringClient | None:
    """Reuse the current resume/JD endpoint configuration for candidate scoring."""

    endpoint = (
        os.getenv("CANDIDATE_QWEN_ENDPOINT_URL", "").strip()
        or os.getenv("RESUME_QWEN_ENDPOINT_URL", "").strip()
        or os.getenv("RUNPOD_CRITERIA_ENDPOINT_URL", "").strip()
    )
    if not endpoint:
        return None

    try:
        timeout = float(
            os.getenv("CANDIDATE_QWEN_TIMEOUT_SECONDS", "")
            or os.getenv("RUNPOD_CRITERIA_TIMEOUT_SECONDS", "180")
        )
    except ValueError:
        timeout = 180.0
    protocol = os.getenv("CANDIDATE_QWEN_PROTOCOL", "").strip()
    if not protocol:
        protocol = "runpod" if "api.runpod.ai" in endpoint.lower() else "openai_chat"
    model = os.getenv("CANDIDATE_QWEN_MODEL", "").strip() or os.getenv(
        "MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct"
    ).strip()
    api_key = (
        os.getenv("CANDIDATE_QWEN_API_KEY", "").strip()
        or os.getenv("RESUME_QWEN_API_KEY", "").strip()
        or os.getenv("RUNPOD_API_KEY", "").strip()
        or None
    )
    return RunPodCandidateScoringClient(
        endpoint,
        api_key=api_key,
        model=model,
        protocol=protocol,
        timeout_seconds=max(1.0, min(timeout, 600.0)),
    )


def _extract_json_payload(value: Any) -> Any:
    """Unwrap RunPod and OpenAI-compatible envelopes."""

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
        raise ValueError("No candidate scoring JSON found in response list")

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

    output = value.get("output")
    if isinstance(output, Mapping) and "output" in output:
        return _extract_json_payload(output["output"])

    for key in ("output", "data", "result", "score"):
        if key in value:
            try:
                return _extract_json_payload(value[key])
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
    return value
