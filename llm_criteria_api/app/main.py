"""FastAPI entry point for health checks and JD criteria generation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import deployment_metadata, settings
from .model_loader import ModelLoader
from .pipeline import CriteriaPipeline
from .response_safety import safe_api_output
from .schemas import GenerateCriteriaRequest, GenerateCriteriaResponse, HealthResponse, ReadyResponse

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    loader = ModelLoader(settings)
    await run_in_threadpool(loader.load)
    app.state.loader = loader
    app.state.pipeline = CriteriaPipeline(loader)
    yield


app = FastAPI(title="Frozen JD Criteria API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": "Invalid request input.", "errors": exc.errors()})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(deployment=deployment_metadata())


@app.get("/ready", response_model=ReadyResponse)
async def ready(request: Request) -> ReadyResponse:
    return ReadyResponse(
        ready=request.app.state.loader.loaded,
        model=settings.model_name,
        mockMode=settings.mock_llm,
        deployment=deployment_metadata(),
    )


@app.post(
    "/api/jd/criteria/generate",
    response_model=GenerateCriteriaResponse,
    response_model_exclude_none=True,
)
async def generate(payload: GenerateCriteriaRequest, request: Request) -> GenerateCriteriaResponse:
    if not payload.has_evidence():
        raise HTTPException(status_code=400, detail="At least one responsibility or requirement is required.")
    if not request.app.state.loader.loaded:
        raise HTTPException(status_code=503, detail="Model is not ready.")
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        output = await asyncio.wait_for(
            run_in_threadpool(
                request.app.state.pipeline.generate,
                payload.model_dump(),
                request_id,
            ),
            timeout=settings.inference_timeout_seconds,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Criteria pipeline timed out.") from exc
    except MemoryError as exc:
        _release_cuda_memory()
        logger.error("criteria pipeline out of memory request_id=%s", request_id)
        raise HTTPException(status_code=503, detail="The worker ran out of GPU memory.") from exc
    except RuntimeError as exc:
        if _is_out_of_memory_error(exc):
            _release_cuda_memory()
            logger.error("criteria pipeline out of memory request_id=%s", request_id)
            raise HTTPException(status_code=503, detail="The worker ran out of GPU memory.") from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("pipeline failure request_id=%s", request_id)
        raise HTTPException(status_code=500, detail="Unexpected criteria pipeline failure.") from exc
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
    return GenerateCriteriaResponse.model_validate(serialized)
