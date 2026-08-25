from io import BytesIO

import pytest
from openpyxl import Workbook

from app.services.jd_excel_parser import (
    JDParsingError,
    extract_worksheet,
    list_worksheets,
)


def workbook_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        worksheet = workbook.create_sheet(name)
        for row in rows:
            worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_lists_all_non_empty_worksheets() -> None:
    content = workbook_bytes(
        {
            "HR Manager": [["POSITION: MANAGER"], ["DEPARTMENT: HUMAN RESOURCE"]],
            "Accountant": [["POSITION", None, "ACCOUNTANT"]],
            "Empty": [],
        }
    )

    result = list_worksheets(content, "jobs.xlsx")

    assert result["totalSheets"] == 2
    assert [sheet["sheetName"] for sheet in result["sheets"]] == [
        "HR Manager",
        "Accountant",
    ]


def test_extracts_department_and_position_from_same_cells() -> None:
    content = workbook_bytes(
        {"HR Manager": [["POSITION : MANAGER"], ["DEPARTMENT: HUMAN RESOURCE"]]}
    )

    data = extract_worksheet(content, "jobs.xlsx", "HR Manager")["data"]

    assert data["jobTitle"] == "Manager"
    assert data["department"] == "Human resource"


def test_extracts_department_and_position_from_later_cells() -> None:
    content = workbook_bytes(
        {
            "Engineer": [
                ["POSITION", None, ": SENIOR ENGINEER"],
                ["DEPARTMENT", None, None, ": ENGINEERING"],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Engineer")["data"]

    assert data["jobTitle"] == "Senior engineer"
    assert data["department"] == "Engineering"


def test_extracts_optional_salary_from_labelled_cell() -> None:
    content = workbook_bytes(
        {
            "Officer": [
                ["POSITION", ": HR OFFICER"],
                ["DEPARTMENT", ": HUMAN RESOURCE"],
                ["Salary Range (RM)", ": RM 3,500 - RM 4,500"],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Officer")["data"]

    assert data["salary"] == "RM 3,500 - RM 4,500"


def test_extracts_multiline_qualifications_and_copies_requirements() -> None:
    content = workbook_bytes(
        {
            "Officer": [
                ["POSITION: OFFICER"],
                ["Qualifications:", "Degree in Human Resources"],
                ["At least two years of relevant experience."],
                ["Responsibilities"],
                ["Maintain employee records."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Officer")["data"]

    assert data["qualifications"] == [
        "Degree in Human Resources",
        "At least two years of relevant experience.",
    ]
    assert data["requirements"] == data["qualifications"]
    assert data["requirements"] is not data["qualifications"]


def test_extracts_job_purpose_as_description() -> None:
    content = workbook_bytes(
        {
            "Officer": [
                ["POSITION: OFFICER"],
                ["Job Purpose: Support daily HR operations."],
                ["Coordinate employee documentation."],
                ["Responsibilities"],
                ["Maintain employee records."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Officer")["data"]

    assert data["description"] == (
        "Support daily HR operations.\nCoordinate employee documentation."
    )


def test_returns_empty_description_when_section_is_missing() -> None:
    content = workbook_bytes(
        {
            "Officer": [
                ["POSITION: OFFICER"],
                ["Responsibilities"],
                ["Maintain employee records."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Officer")["data"]

    assert data["description"] == ""


def test_numbered_section_headings_keep_sections_separate() -> None:
    content = workbook_bytes(
        {
            "Security Supervisor": [
                ["POSITION", ": SECURITY GUARD (SUPERVISOR)"],
                ["Qualification", ": SPM / PMR with related experience"],
                ["At least 3-5 years of experience in security operations."],
                ["1. Job Purpose"],
                ["Oversee daily security operations across all assigned premises."],
                ["2. Key Responsibilities"],
                ["1.", "Supervise all security guards."],
            ]
        }
    )

    data = extract_worksheet(
        content, "jobs.xlsx", "Security Supervisor"
    )["data"]

    assert data["qualifications"] == [
        "SPM / PMR with related experience",
        "At least 3-5 years of experience in security operations.",
    ]
    assert data["description"] == (
        "Oversee daily security operations across all assigned premises."
    )
    assert data["responsibilities"] == ["Supervise all security guards."]


def test_recognizes_long_responsibility_heading() -> None:
    content = workbook_bytes(
        {
            "Manager": [
                ["POSITION: MANAGER"],
                ["Responsibilities as follows but not limited to :"],
                ["Coordinate recruitment activities."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Manager")["data"]

    assert data["responsibilities"] == ["Coordinate recruitment activities."]


def test_extracts_responsibility_from_heading_cell() -> None:
    content = workbook_bytes(
        {
            "Manager": [
                ["POSITION: MANAGER"],
                ["Responsibilities: Prepare monthly reports."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Manager")["data"]

    assert data["responsibilities"] == ["Prepare monthly reports."]


def test_removes_responsibility_numbering() -> None:
    content = workbook_bytes(
        {
            "Manager": [
                ["POSITION: MANAGER"],
                ["Responsibilities"],
                [1, "Report to Section Head"],
                ["2, Coordinate recruitment activities"],
                ["3."],
            ]
        }
    )

    data = extract_worksheet(content, "jobs.xlsx", "Manager")["data"]

    assert data["responsibilities"] == [
        "Report to Section Head",
        "Coordinate recruitment activities",
    ]


def test_invalid_sheet_name_returns_domain_error() -> None:
    content = workbook_bytes({"Manager": [["POSITION: MANAGER"]]})

    with pytest.raises(JDParsingError) as error:
        extract_worksheet(content, "jobs.xlsx", "Missing")

    assert error.value.code == "SHEET_NOT_FOUND"
    assert error.value.status_code == 404


def test_empty_worksheet_returns_reasonable_error() -> None:
    content = workbook_bytes({"Empty": []})

    with pytest.raises(JDParsingError) as error:
        extract_worksheet(content, "jobs.xlsx", "Empty")

    assert error.value.code == "EMPTY_WORKSHEET"
    assert error.value.status_code == 422


def test_job_title_falls_back_to_sheet_name_with_warning() -> None:
    content = workbook_bytes({"HR Manager": [["DEPARTMENT: HUMAN RESOURCE"]]})

    result = extract_worksheet(content, "jobs.xlsx", "HR Manager")

    assert result["data"]["jobTitle"] == "HR Manager"
    assert result["warnings"] == [
        "Job title was not found. Sheet name was used as fallback."
    ]
