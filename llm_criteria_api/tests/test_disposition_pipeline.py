"""Evidence-preserving production-path regression tests.

The former file tested a pre-formation importance triage contract.  The live
path now sends the complete JD to Qwen and records post-validation accounting;
these tests deliberately assert that boundary instead of reviving the retired
triage/recovery policy.
"""

import json
from types import SimpleNamespace

from app.pipeline import CriteriaPipeline


def _criteria(*items):
    return json.dumps({"candidateCriteria": list(items)})


def _criterion(criterion_type, name, source_refs, importance="medium"):
    return {
        "type": criterion_type,
        "name": name,
        "sourceRefs": source_refs,
        "importance": importance,
    }


class EvidenceLoader:
    def __init__(self, criteria_output):
        self.model = None
        self.tokenizer = None
        self.loaded = True
        self.config = SimpleNamespace(
            mock_llm=False,
            max_new_tokens=900,
            debug_mode=True,
        )
        self.criteria_output = criteria_output
        self.calls = []

    def enhanced_raw_output_generator(self, messages):
        self.calls.append(messages)
        return self.criteria_output


def _source_ids(result):
    return {
        source_id
        for criterion in result["criteria"]
        for source_id in criterion.get("sourceIds", [])
    }


def _accounting(result):
    return {
        item["sourceRef"]: item
        for item in result["audit"]["sourceAccounting"]["sources"]
    }


def test_complete_jd_is_sent_without_preformation_importance_filtering():
    job = {
        "jobTitle": "Employee Relations Lead",
        "department": "People",
        "responsibilities": [
            "Investigate employee grievances and disciplinary cases.",
            "Participate in monthly departmental meeting.",
            "Perform other duties assigned by management.",
        ],
        "requirements": [],
        "qualifications": [],
    }
    loader = EvidenceLoader(
        _criteria(
            _criterion(
                "relevant_skill",
                "Employee Grievance Investigations",
                ["R1"],
                "high",
            )
        )
    )

    result = CriteriaPipeline(loader).generate(job, "complete-evidence")

    assert len(loader.calls) == 1
    prompt = loader.calls[0][1]["content"]
    assert "Participate in monthly departmental meeting." in prompt
    assert "Perform other duties assigned by management." in prompt
    assert _source_ids(result) == {"responsibilities-1"}
    audit = _accounting(result)
    assert audit["R2"]["processingOutcome"] == "not_mapped_grounding_safeguard"
    assert audit["R3"]["processingOutcome"] == "not_mapped_grounding_safeguard"
    assert audit["R3"]["generatedCriterionIds"] == []
    assert result["weightTotal"] == 100


def test_same_source_is_not_globally_ignored_for_different_roles():
    source = "Monitor CCTV and investigate security incidents."
    raw = _criteria(_criterion("relevant_skill", "CCTV Incident Monitoring", ["R1"], "high"))
    for title, department in (
        ("People Operations Manager", "People"),
        ("Security Operations Manager", "Security"),
    ):
        result = CriteriaPipeline(EvidenceLoader(raw)).generate(
            {
                "jobTitle": title,
                "department": department,
                "responsibilities": [source],
                "requirements": [],
                "qualifications": [],
            },
            f"role-context-{department}",
        )
        assert result["criteria"]
        assert result["criteria"][0]["sourceIds"] == ["responsibilities-1"]


def test_level_only_education_is_eligibility_and_neutral_soft_evidence():
    job = {
        "jobTitle": "People Manager",
        "department": "People",
        "responsibilities": ["Manage employee grievance investigations."],
        "requirements": ["Minimum Diploma or Degree."],
        "qualifications": [],
    }
    raw = _criteria(
        _criterion("relevant_skill", "Employee Grievance Investigations", ["R1"], "high"),
        _criterion("education_relevance", "Relevant Education Field", ["Q1"], "medium"),
    )

    result = CriteriaPipeline(EvidenceLoader(raw)).generate(job, "level-only-education")

    assert result["eligibilitySuggestions"]["educationLevel"] == "Diploma"
    education = [
        item for item in result["criteria"] if item["type"] == "education_relevance"
    ]
    assert len(education) == 1
    assert education[0]["name"] == "Education"
    assert _accounting(result)["Q1"]["processingOutcome"] == "criterion_contribution"


def test_named_education_field_can_form_education_relevance():
    job = {
        "jobTitle": "People Partner",
        "department": "People",
        "responsibilities": ["Advise managers on employee relations matters."],
        "requirements": [
            "Degree in Human Resources, Business Administration or related field."
        ],
        "qualifications": [],
    }
    raw = _criteria(
        _criterion("relevant_skill", "Employee Relations Advice", ["R1"], "high"),
        _criterion("education_relevance", "Human Resources Education", ["Q1"], "low"),
    )

    result = CriteriaPipeline(EvidenceLoader(raw)).generate(job, "education-field")

    education = [item for item in result["criteria"] if item["type"] == "education_relevance"]
    assert len(education) == 1
    assert education[0]["sourceIds"] == ["requirements-1"]


def test_minimum_experience_is_hard_eligibility_and_soft_experience_evidence():
    job = {
        "jobTitle": "People Manager",
        "department": "People",
        "responsibilities": [],
        "requirements": ["Minimum 5 years HR experience."],
        "qualifications": [],
    }
    raw = _criteria(
        _criterion("relevant_experience", "HR Experience", ["Q1"], "medium")
    )

    result = CriteriaPipeline(EvidenceLoader(raw)).generate(job, "experience-split")

    assert result["eligibilitySuggestions"]["minExperience"] == "5+ years"
    assert any(item["type"] == "relevant_experience" for item in result["criteria"])
    hard = result["audit"]["hardRequirements"]["requirements"]
    assert any(item["kind"] == "minimum_experience" for item in hard)


def test_invalid_qwen_type_is_corrected_to_one_of_the_six_types():
    result = CriteriaPipeline(
        EvidenceLoader(
            _criteria(
                _criterion(
                    "core_capability",
                    "Employee Grievance Investigations",
                    ["R1"],
                    "high",
                )
            )
        )
    ).generate(
        {
            "jobTitle": "Employee Relations Lead",
            "department": "People",
            "responsibilities": ["Investigate employee grievances and disciplinary cases."],
            "requirements": [],
            "qualifications": [],
        },
        "invalid-type",
    )

    allowed = {
        "relevant_skill",
        "relevant_experience",
        "education_relevance",
        "domain_knowledge",
        "preferred_certification",
        "job_related_language",
    }
    assert result["criteria"]
    assert {item["type"] for item in result["criteria"]} <= allowed
    assert any("safely corrected" in warning for warning in result["warnings"])


def test_equivalent_formal_law_evidence_is_not_double_counted():
    job = {
        "jobTitle": "Compliance Lead",
        "department": "Operations",
        "responsibilities": ["Advise managers on compliance decisions."],
        "requirements": [
            "Knowledge of Malaysian labour laws and regulations is required.",
            "Familiarity with Malaysian labour law compliance is required.",
        ],
        "qualifications": [],
    }
    raw = _criteria(
        _criterion("relevant_skill", "Compliance Decision Advice", ["R1"], "high"),
        _criterion("domain_knowledge", "Malaysian Labour Law", ["Q1"], "medium"),
        _criterion("domain_knowledge", "Malaysian Labour Law Compliance", ["Q2"], "medium"),
    )

    result = CriteriaPipeline(EvidenceLoader(raw)).generate(job, "law-deduplication")

    labour = [item for item in result["criteria"] if item["type"] == "domain_knowledge"]
    assert len(labour) == 1
    assert set(labour[0]["sourceIds"]) == {"requirements-1", "requirements-2"}
    assert result["weightTotal"] == 100


def test_unmapped_source_does_not_fail_or_trigger_responsibility_recovery():
    job = {
        "jobTitle": "Service Reliability Lead",
        "department": "Operations",
        "responsibilities": [
            "Investigate recurring service failures.",
            "Resolve confirmed service failures and document the outcome.",
        ],
        "requirements": [],
        "qualifications": [],
    }
    result = CriteriaPipeline(
        EvidenceLoader(
            _criteria(
                _criterion("relevant_skill", "Service Failure Investigation", ["R1"], "high")
            )
        )
    ).generate(job, "unmapped-source")

    assert len(result["criteria"]) == 1
    assert _accounting(result)["R2"]["generatedCriterionIds"] == []
    assert not any(
        event["stage"] == "core_disposition_recovery"
        for event in result["audit"]["debugTrace"]
    )


def test_real_world_role_sources_have_audit_outcomes_without_role_templates():
    job = {
        "jobTitle": "People Operations Manager",
        "department": "People Operations",
        "responsibilities": [
            "Manage foreign worker permits and immigration matters.",
            "Handle employee grievances and disciplinary cases.",
            "Participate in monthly production meeting.",
            "Administer exit passes and medical chits.",
            "Monitor CCTV footage when requested.",
            "Ensure compliance with Malaysian labour laws and regulations.",
        ],
        "requirements": ["Minimum STPM, Diploma or Degree.", "Minimum 5 years HR experience."],
        "qualifications": [],
    }
    raw = _criteria(
        _criterion("relevant_skill", "Foreign Worker Permit Management", ["R1"], "high"),
        _criterion("relevant_skill", "Employee Grievance Handling", ["R2"], "high"),
        _criterion("domain_knowledge", "Malaysian Labour Law", ["R6"], "high"),
        _criterion("relevant_experience", "HR Experience", ["Q2"], "medium"),
    )

    result = CriteriaPipeline(EvidenceLoader(raw)).generate(job, "hr-regression")

    assert result["eligibilitySuggestions"]["educationLevel"] == "STPM / Foundation / Matriculation"
    assert result["eligibilitySuggestions"]["minExperience"] == "5+ years"
    assert any(item["type"] == "education_relevance" for item in result["criteria"])
    assert sum(item["type"] == "domain_knowledge" for item in result["criteria"]) == 1
    audit = _accounting(result)
    assert audit["R3"]["generatedCriterionIds"] == []
    assert audit["R4"]["generatedCriterionIds"] == []
    assert audit["R5"]["generatedCriterionIds"] == []
    assert audit["Q1"]["processingOutcome"] == "criterion_contribution"
    assert result["audit"]["sourceAccounting"]["valid"] is True
    assert result["weightTotal"] == 100
