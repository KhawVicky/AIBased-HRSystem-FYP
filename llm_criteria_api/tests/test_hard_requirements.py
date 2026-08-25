from app.source_accounting import build_source_records
from app.hard_requirements import extract_hard_requirements


def _extract(job):
    return extract_hard_requirements(job, build_source_records(job))


def test_level_only_education_is_hard_requirement_and_soft_signal_without_field():
    result = _extract(
        {
            "jobTitle": "Operations Coordinator",
            "department": "Operations",
            "responsibilities": [],
            "requirements": ["Minimum STPM / Diploma / Degree"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "STPM / Foundation / Matriculation"
    assert result.eligibility_suggestions["enabledFilters"] == ["educationLevel"]
    assert result.has_kind("Q1", "education_level")
    assert result.has_scoring_signal("Q1", "education_evidence")
    assert not result.has_scoring_signal("Q1", "education_field")
    assert not result.is_hard_only("Q1")


def test_preferred_education_is_soft_only_and_not_an_eligibility_threshold():
    result = _extract(
        {
            "jobTitle": "Developer",
            "department": "Technology",
            "responsibilities": [],
            "requirements": ["Degree in Computer Science is preferred."],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] is None
    assert result.has_scoring_signal("Q1", "education_evidence")
    assert result.has_scoring_signal("Q1", "education_field")
    assert not result.has_kind("Q1", "education_level")


def test_education_field_is_preserved_as_scoring_evidence():
    result = _extract(
        {
            "jobTitle": "People Partner",
            "department": "People",
            "responsibilities": [],
            "requirements": [
                "Degree in Human Resources, Business Administration or related field"
            ],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "Bachelor Degree"
    assert result.has_kind("Q1", "education_level")
    assert result.has_scoring_signal("Q1", "education_field")
    assert not result.is_hard_only("Q1")


def test_experience_threshold_and_scope_remain_separate_dimensions():
    result = _extract(
        {
            "jobTitle": "People Manager",
            "department": "People",
            "responsibilities": [],
            "requirements": ["Minimum 5 years HR experience"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["minExperience"] == "5+ years"
    assert result.eligibility_suggestions["enabledFilters"] == ["minExperience"]
    assert result.exact_values["minExperience"] == 5
    assert result.has_kind("Q1", "minimum_experience")
    assert result.has_scoring_signal("Q1", "experience_scope")
    assert not result.is_hard_only("Q1")


def test_combined_education_and_experience_sentence_keeps_scopes_separate():
    result = _extract(
        {
            "jobTitle": "HR Manager",
            "department": "People",
            "responsibilities": [],
            "requirements": [
                "Min. STPM/Diploma or Degree with min. 5 years experience in HR field."
            ],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "STPM / Foundation / Matriculation"
    assert result.eligibility_suggestions["minExperience"] == "5+ years"
    assert result.eligibility_suggestions["enabledFilters"] == [
        "minExperience",
        "educationLevel",
    ]
    assert result.has_scoring_signal("Q1", "education_evidence")
    assert result.has_scoring_signal("Q1", "experience_scope")


def test_explicit_cgpa_language_and_mandatory_certification_are_hard_requirements():
    result = _extract(
        {
            "jobTitle": "Safety Coordinator",
            "department": "Operations",
            "responsibilities": [],
            "requirements": [
                "Minimum CGPA of 3.20",
                "English is required for this role",
                "A valid First Aid certification is mandatory",
            ],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["minCGPA"] == 3.2
    assert result.eligibility_suggestions["requiredLanguage"] == "English"
    assert result.has_kind("Q3", "mandatory_certification")
    assert result.is_hard_only("Q3")
    assert result.safe_audit()["requirements"][-1]["kind"] == "mandatory_certification"


def test_minimum_degree_is_an_education_filter_without_experience():
    result = _extract(
        {
            "jobTitle": "Coordinator",
            "department": "Operations",
            "responsibilities": [],
            "requirements": ["Minimum Degree"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "Bachelor Degree"
    assert result.eligibility_suggestions["minExperience"] is None
    assert result.eligibility_suggestions["enabledFilters"] == ["educationLevel"]


def test_or_and_slash_education_thresholds_use_the_lowest_accepted_level():
    cases = (
        ("Diploma or Degree", "Diploma"),
        ("Diploma or Bachelor's Degree", "Diploma"),
        ("Diploma / Degree", "Diploma"),
        ("Bachelor's Degree", "Bachelor Degree"),
        ("Bachelor's Degree or above", "Bachelor Degree"),
        ("Degree required", "Bachelor Degree"),
    )

    for wording, expected in cases:
        result = _extract(
            {
                "jobTitle": "Specialist",
                "department": "Operations",
                "responsibilities": [],
                "requirements": [wording],
                "qualifications": [],
            }
        )

        assert result.eligibility_suggestions["educationLevel"] == expected


def test_hr_or_education_expression_extracts_diploma_and_five_years():
    result = _extract(
        {
            "jobTitle": "HR Manager",
            "department": "People",
            "responsibilities": [],
            "requirements": [
                "Diploma or Degree with min. 5 years experience in HR field."
            ],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "Diploma"
    assert result.eligibility_suggestions["minExperience"] == "5+ years"
    assert result.exact_values["minExperience"] == 5


def test_common_experience_shorthands_extract_numeric_minimums():
    for wording in (
        "At least 5 years experience",
        "5+ years experience",
        "3 years' experience",
        "3 years of experience",
        "Minimum of 3 years relevant experience",
    ):
        result = _extract(
            {
                "jobTitle": "Specialist",
                "department": "Operations",
                "responsibilities": [],
                "requirements": [wording],
                "qualifications": [],
            }
        )

        expected = 3 if "3" in wording else 5
        assert result.exact_values["minExperience"] == expected
        assert result.eligibility_suggestions["minExperience"] == (
            "3 years" if expected == 3 else "5+ years"
        )
        assert result.eligibility_suggestions["enabledFilters"] == ["minExperience"]


def test_preferred_degree_does_not_create_a_hard_filter():
    result = _extract(
        {
            "jobTitle": "Developer",
            "department": "Technology",
            "responsibilities": [],
            "requirements": ["Degree preferred"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] is None
    assert result.eligibility_suggestions["enabledFilters"] == []
    assert not result.has_kind("Q1", "education_level")


def test_preferred_numeric_experience_remains_soft_only():
    result = _extract(
        {
            "jobTitle": "Engineer",
            "department": "Manufacturing",
            "responsibilities": [],
            "requirements": ["5 years experience preferred"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["minExperience"] is None
    assert result.eligibility_suggestions["enabledFilters"] == []
    assert not result.has_kind("Q1", "minimum_experience")


def test_non_numeric_preferred_experience_has_no_minimum_filter():
    result = _extract(
        {
            "jobTitle": "Engineer",
            "department": "Manufacturing",
            "responsibilities": [],
            "requirements": ["Experience in manufacturing environment preferred"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["minExperience"] is None
    assert result.eligibility_suggestions["enabledFilters"] == []


def test_education_and_experience_are_separated_in_a_plain_compound_sentence():
    result = _extract(
        {
            "jobTitle": "HR Manager",
            "department": "People",
            "responsibilities": [],
            "requirements": ["Degree with 5 years experience in HR field"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] == "Bachelor Degree"
    assert result.eligibility_suggestions["minExperience"] == "5+ years"
    assert result.eligibility_suggestions["enabledFilters"] == [
        "minExperience",
        "educationLevel",
    ]
    assert result.has_kind("Q1", "education_level")
    assert result.has_kind("Q1", "minimum_experience")
    assert result.has_scoring_signal("Q1", "experience_scope")
    assert not result.has_scoring_signal("Q1", "education_field")


def test_no_education_or_experience_requirement_keeps_filters_empty():
    result = _extract(
        {
            "jobTitle": "Assistant",
            "department": "Administration",
            "responsibilities": ["Coordinate calendars and meeting rooms"],
            "requirements": ["Strong communication and organisation skills"],
            "qualifications": [],
        }
    )

    assert result.eligibility_suggestions["educationLevel"] is None
    assert result.eligibility_suggestions["minExperience"] is None
    assert result.eligibility_suggestions["enabledFilters"] == []
