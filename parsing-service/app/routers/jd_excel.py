"""Provides Excel worksheet parsing routes."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.jd import ErrorResponse, ExtractResponse, SheetsResponse
from app.services.jd_excel_parser import (
    JDParsingError,
    extract_worksheet,
    list_worksheets,
)


router = APIRouter(prefix="/api/jd/excel", tags=["JD Excel"])


def _error_response(error: JDParsingError) -> JSONResponse:
    # Keep parser errors in one public API shape.
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": {"code": error.code, "message": error.message},
        },
    )


@router.post(
    "/sheets",
    response_model=SheetsResponse,
    responses={400: {"model": ErrorResponse}},
)
async def get_excel_sheets(file: UploadFile | None = File(default=None)):
    """List non-empty worksheets so the HR wizard can ask for one explicit sheet."""

    if file is None:
        return _error_response(
            JDParsingError("FILE_REQUIRED", "An Excel file is required.")
        )
    # Read the file once and return only worksheet summaries.
    try:
        return list_worksheets(await file.read(), file.filename)
    except JDParsingError as error:
        return _error_response(error)


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def extract_excel_sheet(
    file: UploadFile | None = File(default=None),
    sheet_name: str | None = Form(default=None),
):
    """Extract only the worksheet selected by HR and preserve the stable response envelope."""

    if file is None:
        return _error_response(
            JDParsingError("FILE_REQUIRED", "An Excel file is required.")
        )
    # Extract only the worksheet selected by HR.
    try:
        return extract_worksheet(await file.read(), file.filename, sheet_name or "")
    except JDParsingError as error:
        return _error_response(error)
