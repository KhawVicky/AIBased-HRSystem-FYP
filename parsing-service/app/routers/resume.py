"""Resume parsing API endpoints."""

import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.resume import ResumeDiagnostics, ResumeParseData, ResumeParseResponse
from app.services.resume_parser import parse_resume_text
from app.services.resume_pdf import ResumePdfError, extract_pdf_text
from app.services.resume_semantics import (
    ResumeSemanticError,
    configured_resume_semantic_client,
)


router = APIRouter(prefix="/api/resume", tags=["resume"])
MAX_RESUME_BYTES = 10 * 1024 * 1024


def _application_data(value: str | None) -> dict[str, Any] | None:
    if not value or not value.strip():
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_APPLICATION_DATA", "message": "application_data must be valid JSON"},
        ) from error
    if decoded is None:
        return None
    if not isinstance(decoded, dict):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_APPLICATION_DATA", "message": "application_data must be a JSON object"},
        )
    return decoded


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(
    file: UploadFile = File(...),
    candidate_id: str | None = Form(default=None),
    application_data: str | None = Form(default=None),
    require_semantic: bool = Form(default=False),
) -> ResumeParseResponse:
    """Validate, extract, parse, optionally enrich, and return one resume profile."""

    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FILE_TYPE", "message": "Only PDF resume files are supported"},
        )

    content = await file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "Resume files must not exceed 10 MB"},
        )

    try:
        extraction = extract_pdf_text(content)
    except ResumePdfError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "PDF_TEXT_EXTRACTION_FAILED", "message": str(error)},
        ) from error

    try:
        profile, sections, diagnostic_values = parse_resume_text(
            extraction.cleaned_text,
            candidate_id=candidate_id,
            application_data=_application_data(application_data),
            semantic_client=configured_resume_semantic_client(),
            require_semantic=require_semantic,
            extraction_diagnostics=extraction.diagnostics,
        )
    except ResumeSemanticError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "SEMANTIC_PARSING_FAILED", "message": str(error)},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "RESUME_PARSING_FAILED", "message": str(error)},
        ) from error

    diagnostic_values["pageCount"] = extraction.page_count
    diagnostic_values["extractionMethod"] = extraction.method
    diagnostic_values.update(extraction.diagnostics)
    diagnostics = ResumeDiagnostics.model_validate(diagnostic_values)
    warnings = diagnostic_values.get("warnings", [])
    return ResumeParseResponse(
        data=ResumeParseData(
            rawText=extraction.raw_text,
            sections=dict(sections),
            profile=profile,
            diagnostics=diagnostics,
        ),
        warnings=warnings,
    )
