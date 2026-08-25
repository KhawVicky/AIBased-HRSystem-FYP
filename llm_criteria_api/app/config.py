"""Runtime settings and scoring-type defaults for the frozen Qwen service."""

from __future__ import annotations

import os
from dataclasses import dataclass


SOFT_CRITERIA_TYPES = {
    "relevant_skill": 30,
    "relevant_experience": 25,
    "domain_knowledge": 20,
    "education_relevance": 10,
    "preferred_certification": 8,
    "job_related_language": 7,
}


@dataclass(frozen=True)
class Settings:
    model_name: str = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")
    image_tag: str = os.getenv("APP_IMAGE_TAG") or os.getenv("IMAGE_TAG", "local")
    pipeline_version: str = os.getenv(
        "PIPELINE_VERSION", "complete-jd-candidate-extraction-v2"
    )
    git_commit_hash: str = os.getenv("GIT_COMMIT_HASH", "local-build")
    hf_token: str | None = os.getenv("HF_TOKEN") or None
    mock_llm: bool = os.getenv("MOCK_LLM", "false").lower() == "true"
    device: str = os.getenv("DEVICE", "cuda")
    max_new_tokens: int = int(os.getenv("MAX_NEW_TOKENS", "900"))
    inference_timeout_seconds: int = int(os.getenv("INFERENCE_TIMEOUT_SECONDS", "180"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()


def deployment_metadata() -> dict[str, str | bool]:
    return {
        "imageTag": settings.image_tag,
        "pipelineVersion": settings.pipeline_version,
        "gitCommitHash": settings.git_commit_hash,
        "roleContextEnabled": True,
        "finalEvidenceSafetyEnabled": True,
    }
