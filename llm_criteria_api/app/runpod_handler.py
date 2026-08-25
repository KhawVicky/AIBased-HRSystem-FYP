"""RunPod Serverless adapter for the frozen JD criteria pipeline.

This module deliberately delegates all decision-making to ``CriteriaPipeline``
and the literal frozen pipeline it wraps. It only owns worker lifecycle,
request validation, timeout handling, and deployment-safe error responses.
"""

from __future__ import annotations

import gc
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from pydantic import ValidationError

from .candidate_scoring import (
    CandidateCriterionScoringOutput,
    CandidateCriterionScoringRequest,
    generate_candidate_criterion_score,
)
from .config import Settings, deployment_metadata, settings
from .model_loader import ModelLoader
from .pipeline import CriteriaPipeline
from .response_safety import safe_api_output
from .resume_semantics import (
    ResumeSemanticOutput,
    ResumeSemanticRequest,
    generate_resume_semantics as run_resume_semantic_inference,
)
from .schemas import GenerateCriteriaRequest, GenerateCriteriaResponse


logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


class ModelNotReadyError(RuntimeError):
    """Raised when a worker could not load its configured model."""


class RunPodRuntime:
    """Thread-safe process-level model and frozen-pipeline holder."""

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.loader = ModelLoader(config)
        self.pipeline: CriteriaPipeline | None = None
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self.loader.loaded and self.pipeline is not None

    def initialise(self) -> None:
        if self.ready:
            return
        with self._load_lock:
            if self.ready:
                return
            self.loader.load()
            if not self.loader.loaded:
                raise ModelNotReadyError("The configured model could not be loaded by this worker.")
            self.pipeline = CriteriaPipeline(self.loader)
            logger.info("runpod worker model_ready=true mock_mode=%s", self.config.mock_llm)

    def generate(self, job: dict[str, Any], request_id: str) -> dict[str, Any]:
        self.initialise()
        assert self.pipeline is not None
        # The frozen notebook module contains runtime globals. Serialising calls
        # prevents concurrent requests from changing that shared state.
        with self._generation_lock:
            return self.pipeline.generate(job, request_id)

    def generate_resume_semantics(self, job: dict[str, Any], request_id: str) -> dict[str, Any]:
        """Run the resume-only task on the same loaded model, outside the JD pipeline."""

        self.initialise()
        with self._generation_lock:
            request = ResumeSemanticRequest.model_validate(job)
            return run_resume_semantic_inference(self.loader, request)

    def generate_candidate_criterion_score(
        self,
        job: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        """Run candidate semantic scoring on the shared model, outside JD/resume pipelines."""

        self.initialise()
        with self._generation_lock:
            request = CandidateCriterionScoringRequest.model_validate(job)
            return generate_candidate_criterion_score(self.loader, request)


runtime = RunPodRuntime(settings)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="criteria-pipeline")


def _is_out_of_memory_error(error: BaseException) -> bool:
    if isinstance(error, MemoryError):
        return True
    message = str(error).lower()
    return "out of memory" in message or "cuda oom" in message or "cuda error: out of memory" in message


def _release_cuda_memory() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        logger.warning("cuda memory cleanup failed", exc_info=True)
    finally:
        gc.collect()


def _error_response(request_id: str, code: str, message: str) -> dict[str, Any]:
    return {"status": "error", "requestId": request_id, "error": {"code": code, "message": message}}


def _health_response(request_id: str) -> dict[str, Any]:
    return {
        "status": "success",
        "requestId": request_id,
        "output": {
            "status": "ok",
            "ready": runtime.ready,
            "model": settings.model_name,
            "mockMode": settings.mock_llm,
            "deployment": deployment_metadata(),
        },
    }


def _resume_semantic_response(raw_input: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Dispatch resume semantics without changing the JD request contract."""

    try:
        payload = ResumeSemanticRequest.model_validate(raw_input)
        if not payload.resumeText.strip() or not payload.evidenceIndex:
            return _error_response(
                request_id,
                "invalid_input",
                "Resume text and at least one evidence record are required.",
            )
    except ValidationError as error:
        return _error_response(request_id, "invalid_input", "Invalid resume semantic input.") | {
            "validationErrors": error.errors()
        }

    if runtime.config.mock_llm:
        return _error_response(
            request_id,
            "mock_mode_disabled",
            "Resume semantic enrichment requires MOCK_LLM=false and live Qwen inference.",
        )

    started = time.perf_counter()
    future = _executor.submit(runtime.generate_resume_semantics, payload.model_dump(), request_id)
    try:
        output = future.result(timeout=settings.inference_timeout_seconds)
    except FutureTimeoutError:
        logger.warning("runpod resume semantic timeout request_id=%s", request_id)
        return _error_response(
            request_id,
            "timeout",
            "Resume semantic enrichment exceeded the configured timeout.",
        )
    except ModelNotReadyError:
        logger.error("runpod resume semantic model not ready request_id=%s", request_id)
        return _error_response(request_id, "model_not_ready", "The model is not ready on this worker.")
    except Exception as error:
        if _is_out_of_memory_error(error):
            _release_cuda_memory()
            logger.error("runpod resume semantic out_of_memory request_id=%s", request_id)
            return _error_response(request_id, "out_of_memory", "The worker ran out of GPU memory.")
        logger.error(
            "runpod resume semantic failure request_id=%s error_type=%s error=%s",
            request_id,
            type(error).__name__,
            " ".join(str(error).split())[:320],
            exc_info=True,
        )
        return _error_response(
            request_id,
            "resume_semantic_failure",
            "Unexpected resume semantic inference failure.",
        )

    serialized = ResumeSemanticOutput.model_validate(output).model_dump(exclude_none=True)
    serialized["model"] = settings.model_name
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "runpod resume semantic complete request_id=%s duration_ms=%d evidence_count=%d",
        request_id,
        elapsed_ms,
        len(payload.evidenceIndex),
    )
    return {
        "status": "success",
        "requestId": request_id,
        "output": serialized,
    }


def _candidate_scoring_response(raw_input: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Dispatch candidate criterion scoring without changing JD/resume contracts."""

    try:
        payload = CandidateCriterionScoringRequest.model_validate(raw_input)
    except ValidationError as error:
        return _error_response(request_id, "invalid_input", "Invalid candidate scoring input.") | {
            "validationErrors": error.errors()
        }

    if runtime.config.mock_llm:
        return _error_response(
            request_id,
            "mock_mode_disabled",
            "Candidate scoring requires MOCK_LLM=false and live Qwen inference.",
        )

    started = time.perf_counter()
    future = _executor.submit(runtime.generate_candidate_criterion_score, payload.model_dump(), request_id)
    try:
        output = future.result(timeout=settings.inference_timeout_seconds)
    except FutureTimeoutError:
        logger.warning("runpod candidate scoring timeout request_id=%s", request_id)
        return _error_response(
            request_id,
            "timeout",
            "Candidate criterion scoring exceeded the configured timeout.",
        )
    except ModelNotReadyError:
        logger.error("runpod candidate scoring model not ready request_id=%s", request_id)
        return _error_response(request_id, "model_not_ready", "The model is not ready on this worker.")
    except Exception as error:
        if _is_out_of_memory_error(error):
            _release_cuda_memory()
            logger.error("runpod candidate scoring out_of_memory request_id=%s", request_id)
            return _error_response(request_id, "out_of_memory", "The worker ran out of GPU memory.")
        logger.error(
            "runpod candidate scoring failure request_id=%s error_type=%s error=%s",
            request_id,
            type(error).__name__,
            " ".join(str(error).split())[:320],
            exc_info=True,
        )
        return _error_response(
            request_id,
            "candidate_scoring_failure",
            "The candidate scoring response was invalid or inference failed.",
        )

    serialized = CandidateCriterionScoringOutput.model_validate(output).model_dump(exclude_none=True)
    serialized.update({
        "model": settings.model_name,
        "qwenUsed": True,
        "mockMode": False,
        "runtimeTask": "candidate_criterion_scoring",
    })
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "runpod candidate scoring complete request_id=%s duration_ms=%d criterion_id=%s",
        request_id,
        elapsed_ms,
        serialized.get("criterionId"),
    )
    return {
        "status": "success",
        "requestId": request_id,
        "output": serialized,
    }


def handler(event: dict[str, Any]) -> dict[str, Any]:
    """Handle a RunPod event without logging full JD content."""

    request_id = str(event.get("id") or uuid.uuid4())
    raw_input = event.get("input", event)
    if not isinstance(raw_input, dict):
        return _error_response(request_id, "invalid_input", "RunPod input must be a JSON object.")

    action = raw_input.get("action")
    if action in {"health", "ready"}:
        return _health_response(request_id)

    if raw_input.get("task") == "candidate_criterion_scoring":
        return _candidate_scoring_response(raw_input, request_id)

    if raw_input.get("task") == "resume_semantic_understanding":
        return _resume_semantic_response(raw_input, request_id)

    try:
        payload = GenerateCriteriaRequest.model_validate(raw_input)
        if not payload.has_evidence():
            return _error_response(
                request_id,
                "invalid_input",
                "At least one responsibility, requirement or qualification is required.",
            )
    except ValidationError as error:
        return _error_response(request_id, "invalid_input", "Invalid criteria-generation input.") | {
            "validationErrors": error.errors()
        }

    started = time.perf_counter()
    future = _executor.submit(runtime.generate, payload.model_dump(), request_id)
    try:
        output = future.result(timeout=settings.inference_timeout_seconds)
    except FutureTimeoutError:
        # Python cannot safely interrupt a GPU generation in-progress. Return a
        # deterministic timeout response and let the worker finish/clean up.
        logger.warning("runpod request timeout request_id=%s", request_id)
        return _error_response(request_id, "timeout", "Criteria generation exceeded the configured timeout.")
    except ModelNotReadyError:
        logger.error("runpod model not ready request_id=%s", request_id)
        return _error_response(request_id, "model_not_ready", "The model is not ready on this worker.")
    except Exception as error:
        if _is_out_of_memory_error(error):
            _release_cuda_memory()
            logger.error("runpod out_of_memory request_id=%s", request_id)
            return _error_response(request_id, "out_of_memory", "The worker ran out of GPU memory.")
        logger.exception("runpod pipeline failure request_id=%s", request_id)
        return _error_response(request_id, "pipeline_failure", "Unexpected criteria pipeline failure.")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "runpod request complete request_id=%s duration_ms=%d criteria_count=%d warnings=%d",
        request_id,
        elapsed_ms,
        len(output["criteria"]),
        len(output["warnings"]),
    )
    safe_output = safe_api_output(output)
    response = GenerateCriteriaResponse(**safe_output, model=settings.model_name)
    serialized = response.model_dump(exclude_none=True)
    serialized.setdefault("audit", {}).setdefault("debugTrace", []).append(
        {
            "stage": "api_serialization",
            "criteriaCount": len(serialized["criteria"]),
            "weightTotal": serialized["weightTotal"],
            "criterionNames": [item["name"] for item in serialized["criteria"]],
        }
    )
    logger.info(
        "criteria_stage stage=api_serialization request_id=%s criteria_count=%d",
        request_id,
        len(serialized["criteria"]),
    )
    return {
        "status": "success",
        "requestId": request_id,
        "output": serialized,
    }


def start_serverless() -> None:
    """Preload once per worker, then hand the persistent handler to RunPod."""

    runtime.initialise()
    import runpod

    runpod.serverless.start({"handler": handler})
