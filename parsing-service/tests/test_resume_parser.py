from datetime import date

from app.schemas.resume import SemanticEvidence, SemanticResumeOutput, SemanticSkillEvidence
from app.services.candidate_summary import build_candidate_summary
from app.services.resume_parser import parse_resume_text


BASE_RESUME = """Alice Chen
alice.chen@example.com
+6012-1111111
Location: Penang

Career Summary
Software developer with 8 years of experience in software development.

Academic Background
Master of Computer Science
Stanford University
2020 - 2022
CGPA: 3.92

Diploma in Information Technology
Penang College
2016 - 2018

Employment History
Frontend Engineer | ABC Sdn Bhd
Jan 2018 - Dec 2020
- Developed frontend applications using React and TypeScript.
- Integrated Node.js APIs and AWS deployments.

Product Engineer | XYZ Berhad
2020 - Present
- Built services with Python and FastAPI.
- Improved processing time by 30%.

Technical Competencies
React.js, ReactJS, JavaScript, Java, hardworking

Certificates
AWS Certified Cloud Practitioner - Amazon Web Services
Credential ID: AWS-123

Spoken Languages
English - Fluent, Mandarin - Conversational

Selected Projects
Applicant Portal
Built a portal using React and TypeScript.

Awards and Achievements
Improved processing time by 30%.
"""


def _all_reference_ids(profile):
    valid_ids = {item.sourceId for item in profile.evidenceIndex}
    references = []
    for skill in profile.skills:
        references.extend(item.sourceId for item in skill.evidence)
    for experience in profile.experience:
        references.extend(item.sourceId for item in experience.skillsEvidence)
    references.extend(item.sourceId for item in profile.education)
    references.extend(item.sourceId for item in profile.experience)
    references.extend(item.sourceId for item in profile.projects)
    references.extend(item.sourceId for item in profile.certifications)
    references.extend(item.sourceId for item in profile.languages)
    references.extend(item.sourceId for item in profile.achievements)
    return valid_ids, references


def test_parses_sections_personal_fields_and_structured_records():
    profile, sections, diagnostics = parse_resume_text(
        BASE_RESUME,
        as_of=date(2026, 8, 9),
    )

    assert set(["education", "experience", "skills", "languages", "projects", "achievements"]).issubset(sections)
    assert profile.personalInfo.name == "Alice Chen"
    assert profile.personalInfo.email == "alice.chen@example.com"
    assert profile.personalInfo.phone == "+6012-1111111"
    assert profile.personalInfo.location == "Penang"
    assert profile.education[0].level == "Master Degree"
    assert profile.education[0].field == "Computer Science"
    assert profile.education[0].institution == "Stanford University"
    assert profile.education[0].cgpa == 3.92
    assert profile.certifications[0].name.startswith("AWS Certified")
    assert profile.languages[0].proficiency == "Fluent"
    assert profile.projects[0].technologies == ["React", "TypeScript"]
    assert diagnostics["summaryGenerated"] is True


def test_overlapping_roles_are_not_double_counted():
    text = """Alex Tan
Work Experience
Engineer | One Company
2020 - 2022
- Built internal tools.
Consultant | Two Company
2021 - 2023
- Delivered API integration.
"""

    profile, _, _ = parse_resume_text(text, as_of=date(2023, 12, 1))

    assert [entry.durationMonths for entry in profile.experience] == [36, 36]
    assert profile.totalExperienceMonths == 48
    assert profile.totalExperienceYears == 4.0


def test_month_range_includes_start_and_end_months():
    text = BASE_RESUME.replace("Jan 2018 - Dec 2020", "Jan 2026 - May 2026")

    profile, _, _ = parse_resume_text(text, as_of=date(2026, 8, 11))

    assert profile.experience[0].durationMonths == 5


def test_year_only_and_current_dates_are_normalized_safely():
    text = """Jamie Lee
Professional Experience
HR Executive
2022 - Current
- Managed recruitment and onboarding.
"""

    profile, _, _ = parse_resume_text(text, as_of=date(2024, 6, 1))

    assert profile.experience[0].startDate == "2022"
    assert profile.experience[0].endDate is None
    assert profile.experience[0].isCurrent is True
    assert profile.experience[0].durationConfidence == "year"
    assert profile.experience[0].durationMonths == 30


def test_generic_soft_skills_are_not_scoring_skills():
    profile, _, _ = parse_resume_text(
        "Taylor Wong\nSkills\nhardworking, responsible, Python\n",
    )

    assert [skill.normalizedName for skill in profile.skills] == ["Python"]


def test_missing_language_section_does_not_infer_language_from_location():
    profile, _, _ = parse_resume_text(
        "Morgan Lim\nLocation: Kuala Lumpur\nEducation\nBachelor of Science\nABC University\n",
    )

    assert profile.languages == []


def test_application_values_are_preserved_with_cgpa_conflict():
    profile, _, _ = parse_resume_text(
        BASE_RESUME,
        application_data={
            "cgpa": 3.50,
            "noticePeriod": "30 days",
            "languages": [{"language": "Bahasa Malaysia", "level": "Fluent"}],
        },
    )

    assert profile.cgpa == 3.50
    assert profile.noticePeriod == "30 days"
    assert profile.dataConflicts[0].field == "cgpa"
    assert [entry.language for entry in profile.languages] == ["Bahasa Malaysia"]


class FakeSemanticClient:
    def understand(self, *, resume_text, sections, evidence_index):
        experience_source = next(item for item in evidence_index if item.sourceId == "experience-1")
        return SemanticResumeOutput(
            primaryDomain="frontend engineering",
            primaryDomainSourceIds=["experience-1"],
            experienceEvidence=[
                SemanticEvidence(
                    sourceId="experience-1",
                    sourceText=experience_source.sourceText,
                    semanticCapabilities=["Modern frontend engineering"],
                )
            ],
            skillEvidence=[
                SemanticSkillEvidence(
                    sourceId="experience-1",
                    skills=["Kubernetes"],
                )
            ],
        )


def test_qwen_semantics_are_grounded_before_merge():
    profile, _, diagnostics = parse_resume_text(
        BASE_RESUME,
        semantic_client=FakeSemanticClient(),
        require_semantic=True,
    )

    assert "Modern frontend engineering" in profile.keyStrengths
    assert "Kubernetes" not in [skill.normalizedName for skill in profile.skills]
    assert diagnostics["qwenStatus"] == "completed"
    assert diagnostics["groundingRejectionCount"] == 1
    valid_ids, references = _all_reference_ids(profile)
    assert set(references).issubset(valid_ids)


def test_candidate_summary_is_fixed_neutral_and_has_no_placeholders():
    profile, _, _ = parse_resume_text(BASE_RESUME)
    summary = profile.candidateSummary or ""

    assert summary.startswith("Alice Chen has ")
    assert "Stanford University" in summary
    assert "React" in summary
    assert "30 days" not in summary
    assert not any(value in summary for value in ("[Unknown]", "[N/A]", "strong fit", "highly ranked"))


def test_summary_falls_back_without_experience_or_education():
    profile, _, _ = parse_resume_text(
        "Sarah Lim\nLanguages\nEnglish - Fluent\n",
    )

    assert build_candidate_summary(profile) == "Sarah Lim is proficient in English (Fluent)."
