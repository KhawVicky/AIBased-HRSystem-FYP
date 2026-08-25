import json

from app.extraction_schema import normalise_extraction_output


def _normalise(raw_item, source_ref, source_text):
    result = normalise_extraction_output(
        json.dumps(
            {
                "candidateCriteria": [raw_item],
                "ignoredSourceRefs": [],
            }
        ),
        source_lookup={source_ref: source_text},
        required_source_refs={source_ref},
    )
    return result, json.loads(result.legacy_json)["criteria"]


def test_invalid_responsibility_type_is_safely_corrected_to_relevant_skill():
    result, criteria = _normalise(
        {
            "type": "practical_responsibility",
            "name": "Grievance Investigations",
            "sourceRefs": ["R1"],
            "importance": "high",
        },
        "R1",
        "Investigate employee grievances and disciplinary cases.",
    )
    assert result.parse_error is None
    assert criteria[0]["type"] == "relevant_skill"
    assert any("corrected" in warning.casefold() for warning in result.warnings)


def test_invalid_type_with_scoped_experience_is_corrected_to_relevant_experience():
    result, criteria = _normalise(
        {
            "type": "core_capability",
            "name": "HR Experience",
            "sourceRefs": ["Q1"],
            "importance": "medium",
        },
        "Q1",
        "Minimum 5 years HR experience.",
    )

    assert result.parse_error is None
    assert criteria[0]["type"] == "relevant_experience"


def test_allowed_taxonomy_remains_exactly_six_types_after_correction():
    from app.extraction_prompt import ALLOWED_CRITERION_TYPES

    assert ALLOWED_CRITERION_TYPES == (
        "relevant_skill",
        "relevant_experience",
        "education_relevance",
        "domain_knowledge",
        "preferred_certification",
        "job_related_language",
    )
