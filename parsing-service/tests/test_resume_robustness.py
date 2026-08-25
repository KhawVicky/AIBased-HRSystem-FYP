from pathlib import Path
import re

import pytest

from app.services.resume_parser import parse_resume_text
from app.services.resume_pdf import assess_extraction_quality, extract_pdf_text
from app.services.resume_sections import normalize_resume_line, segment_resume_sections


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str):
    result = extract_pdf_text((FIXTURE_DIR / name).read_bytes())
    profile, sections, diagnostics = parse_resume_text(
        result.cleaned_text,
        extraction_diagnostics=result.diagnostics,
    )
    return result, profile, sections, diagnostics


def test_spaced_character_heading_and_body_normalization_is_safe():
    assert normalize_resume_line("T E C H  S K I L L S") == "TECH SKILLS"
    assert normalize_resume_line("C o m p u t e r  S c i e n c e") == "Computer Science"
    assert normalize_resume_line("Big Domain Sdn Bhd") == "Big Domain Sdn Bhd"
    assert normalize_resume_line("Web Development Intern") == "Web Development Intern"


def test_control_and_bullet_characters_are_removed_without_losing_text():
    assert normalize_resume_line("\x7f Designed a parser") == "Designed a parser"
    result, profile, _, _ = _fixture("vicky_original_multicolumn.pdf")
    assert all("\x7f" not in item.sourceText for item in profile.evidenceIndex)
    assert all("\x00" not in item.sourceText for item in profile.evidenceIndex)
    assert result.quality.control_character_count == 0


def test_multicolumn_layout_fallback_is_selected_when_primary_is_suspicious():
    result, _, _, _ = _fixture("vicky_original_multicolumn.pdf")
    assert result.method == "pymupdf_layout"
    assert result.fallback_attempted is True
    assert result.fallback_selected is True
    assert result.quality is not None
    assert result.quality.spaced_character_sequence_count == 0
    assert result.quality.recognized_section_count >= 6


def test_single_column_fixture_remains_readable_after_normalization():
    result, profile, sections, _ = _fixture("vicky_single_column.pdf")
    assert profile.personalInfo.name == "VICKY KHAW WEI KEE"
    assert sections["profile"]
    assert "TECH SKILLS" not in sections["profile"].upper()
    assert result.quality is not None and result.quality.email_detected is True


def test_section_boundaries_stop_profile_before_technical_skills():
    sections = segment_resume_sections("Profile\nA summary.\nTech Skills\nPython\n")
    assert sections["profile"] == "A summary."
    assert sections["skills"] == "Python"


def test_section_boundaries_stop_experience_before_projects_and_contact():
    sections = segment_resume_sections(
        "Experience\nRole | Acme\nProjects\nApplicant Portal\nContact\nEmail: a@example.com\n"
    )
    assert sections["experience"] == "Role | Acme"
    assert sections["projects"] == "Applicant Portal"
    assert sections["contact"] == "Email: a@example.com"


def test_project_section_stops_before_experience():
    sections = segment_resume_sections(
        "Projects\nApplicant Portal\nExperience\nFrontend Engineer\n"
    )
    assert sections["projects"] == "Applicant Portal"
    assert sections["experience"] == "Frontend Engineer"


def test_programming_languages_stay_in_skills_not_spoken_languages():
    profile, sections, _ = parse_resume_text(
        "Taylor Wong\nTech Skills\nLanguages: JavaScript, PHP, Python, SQL\n"
        "Languages\nEnglish | Mandarin\n"
    )
    assert sections["skills"] == "Languages: JavaScript, PHP, Python, SQL"
    assert {skill.normalizedName for skill in profile.skills} >= {
        "JavaScript",
        "PHP",
        "Python",
        "SQL",
    }
    assert [entry.language for entry in profile.languages] == ["English", "Mandarin"]


def test_spoken_languages_are_independent_without_implicit_proficiency():
    profile, _, _ = parse_resume_text(
        "Taylor Wong\nLanguages\nEnglish | Bahasa Melayu | Mandarin\n"
    )
    assert [entry.language for entry in profile.languages] == [
        "English",
        "Bahasa Melayu",
        "Mandarin",
    ]
    assert all(entry.proficiency is None for entry in profile.languages)


def test_language_proficiency_is_only_set_when_explicit():
    profile, _, _ = parse_resume_text(
        "Taylor Wong\nLanguages\nEnglish - Fluent | Mandarin - Conversational\n"
    )
    assert [(entry.language, entry.proficiency) for entry in profile.languages] == [
        ("English", "Fluent"),
        ("Mandarin", "Conversational"),
    ]


def test_vicky_single_column_projects_are_split_into_three_records():
    _, profile, _, _ = _fixture("vicky_single_column.pdf")
    assert [project.title for project in profile.projects] == [
        "AI-Based HR Decision Support System",
        "POS-App",
        "House & Car Rental Website",
    ]
    assert len(profile.experience) == 1
    assert all("POS-App" not in entry.sourceText for entry in profile.experience)


def test_project_dates_do_not_create_fake_work_experience():
    _, profile, _, _ = _fixture("lim_sze_mei_multicolumn.pdf")
    assert len(profile.projects) == 2
    assert [entry.title for entry in profile.projects] == [
        "AI-Driven Scam Detection System",
        "Bookkeeping",
    ]
    assert len(profile.experience) == 1
    assert profile.experience[0].jobTitle == "Intern"
    assert profile.experience[0].company == "Tech Dome Penang"


def test_education_institutions_and_cgpa_are_extracted_from_both_layouts():
    _, vicky, _, _ = _fixture("vicky_single_column.pdf")
    _, lim, _, _ = _fixture("lim_sze_mei_multicolumn.pdf")
    assert [entry.institution for entry in vicky.education] == [
        "UOWM KDU PG UC",
        "SEGI College Penang",
    ]
    assert [entry.cgpa for entry in vicky.education] == [3.44, 3.47]
    assert [entry.institution for entry in lim.education] == [
        "UOWM KDU PG UC",
        "SEGI College Penang",
    ]


def test_name_cannot_be_a_section_heading_and_contact_fields_are_recovered():
    _, profile, _, _ = _fixture("lim_sze_mei_multicolumn.pdf")
    assert profile.personalInfo.name == "LIM SZE MEI"
    assert profile.personalInfo.name not in {"SKILLS", "SCORING", "EDUCATION"}
    assert profile.personalInfo.email == "smei_2002@hotmail.com"
    assert profile.personalInfo.phone == "+60 11-57715720"
    assert profile.personalInfo.location == "Penang, Malaysia"


def test_evidence_index_keeps_sections_separate_and_ids_valid():
    _, profile, _, _ = _fixture("vicky_original_multicolumn.pdf")
    valid_ids = {record.sourceId for record in profile.evidenceIndex}
    assert {record.sourceSection for record in profile.evidenceIndex} >= {
        "Education",
        "Work Experience",
        "Projects",
        "Skills",
        "Languages",
    }
    assert all(record.sourceId for record in profile.evidenceIndex)
    assert all(record.sourceText.strip() for record in profile.evidenceIndex)
    assert all(
        reference.sourceId in valid_ids
        for skill in profile.skills
        for reference in skill.evidence
    )
    for record in profile.evidenceIndex:
        if record.sourceSection == "Work Experience":
            assert not re.search(r"(?:^|\n)PROJECTS(?:$|\n)", record.sourceText, re.IGNORECASE)
            assert not re.search(r"(?:^|\n)CONTACT(?:$|\n)", record.sourceText, re.IGNORECASE)


def test_quality_diagnostics_expose_review_warning():
    quality = assess_extraction_quality("A " * 120 + "T E C H S K I L L S")
    assert quality.suspicious is True
    assert "character_spacing_corruption" in quality.signals

    _, _, diagnostics = parse_resume_text(
        "Taylor Wong\nProfile\nA summary.\n",
        extraction_diagnostics={
            "extractionQualityScore": 70,
            "extractionQualitySignals": ["character_spacing_corruption"],
        },
    )
    assert diagnostics["qualityStatus"] == "review_required"
    assert diagnostics["qualityWarnings"]


def test_quality_gate_rejects_substantial_unstructured_text():
    with pytest.raises(ValueError, match="quality gate"):
        parse_resume_text("word " * 160)


def test_original_vicky_multicolumn_fixture_no_longer_has_empty_profile():
    result, profile, sections, diagnostics = _fixture("vicky_original_multicolumn.pdf")
    assert result.method == "pymupdf_layout"
    assert profile.personalInfo.name == "VICKY KHAW WEI KEE"
    assert profile.personalInfo.email == "khawvicky@gmail.com"
    assert {"education", "experience", "skills", "languages", "projects"}.issubset(sections)
    assert len(profile.education) == 2
    assert len(profile.experience) == 1
    assert len(profile.projects) == 3
    assert len(profile.evidenceIndex) > 0
    assert diagnostics["qualityStatus"] == "healthy"


def test_vicky_single_column_fixture_regression_contract():
    _, profile, _, diagnostics = _fixture("vicky_single_column.pdf")
    assert profile.personalInfo.name == "VICKY KHAW WEI KEE"
    assert len(profile.education) == 2
    assert len(profile.experience) == 1
    assert len(profile.projects) == 3
    assert [entry.language for entry in profile.languages] == [
        "English",
        "Bahasa Melayu",
        "Mandarin",
    ]
    assert diagnostics["qualityStatus"] == "healthy"


def test_lim_multicolumn_fixture_regression_contract():
    _, profile, _, diagnostics = _fixture("lim_sze_mei_multicolumn.pdf")
    assert profile.personalInfo.name == "LIM SZE MEI"
    assert len(profile.education) == 2
    assert len(profile.experience) == 1
    assert len(profile.projects) == 2
    assert [entry.language for entry in profile.languages] == [
        "English",
        "Mandarin",
        "Bahasa Melayu",
    ]
    assert diagnostics["qualityStatus"] == "healthy"
