"""Defines Excel parsing request and response data."""

from pydantic import BaseModel, Field


class SheetSummary(BaseModel):
    sheetName: str
    jobTitle: str
    department: str


class SheetsResponse(BaseModel):
    success: bool = True
    fileName: str
    totalSheets: int
    sheets: list[SheetSummary]


class JDData(BaseModel):
    sheetName: str
    jobTitle: str
    department: str
    salary: str = ""
    description: str = ""
    qualifications: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    rawText: str


class ExtractResponse(BaseModel):
    success: bool = True
    data: JDData
    warnings: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
