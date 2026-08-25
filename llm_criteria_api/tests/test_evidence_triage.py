import json

from app.evidence_triage import (
    build_evidence_triage_messages,
    build_source_records,
    normalise_triage_output,
)
from app.hard_requirements import extract_hard_requirements


def _triage(job, payload, generic_detector=lambda _text: False):
    records = build_source_records(job)
    hard = extract_hard_requirements(job, records)
    return normalise_triage_output(
        json.dumps(payload),
        records,
        hard_requirements=hard,
        generic_duty_detector=generic_detector,
    )


def _item(
    source_ref,
    disposition,
    *,
    resume_assessable=True,
    importance="medium",
    criterion_use="STANDALONE_ELIGIBLE",
    reason="Role-relative resume evidence.",
):
    return {
        "sourceRef": source_ref,
        "disposition": disposition,
        "resumeAssessable": resume_assessable,
        "importance": importance,
        "criterionUse": criterion_use,
        "reason": reason,
    }


def test_triage_prompt_uses_complete_role_context_and_closed_internal_labels():
    job = {
        "jobTitle": "Security Operations Manager",
        "department": "Security",
        "responsibilities": [
            "Monitor CCTV and investigate security incidents.",
            "Participate in monthly departmental meeting.",
        ],
        "requirements": ["Minimum 5 years security operations experience."],
        "qualifications": [],
    }
    messages = build_evidence_triage_messages(job, build_source_records(job))
    system = messages[0]["content"]
    user = messages[1]["content"]

    assert "CORE, SUPPORTING or IGNORE" in system
    assert "resume evidence" in system.casefold()
    assert "meaningfully differentiate" in system
    assert "relative to the complete role" in system
    assert "STRENGTHEN_ONLY" in system
    assert "Security Operations Manager" in user
    assert "Security" in user
    assert "Monitor CCTV" in user
    assert "monthly departmental meeting" in user
    assert "Minimum 5 years" in user
    assert '"sourceRef": "R1"' in user
    assert '"sourceDispositions"' in user
    assert "HR Manager" not in system



def test_triage_requires_every_source_exactly_once():
    job = {
        "jobTitle": "Coordinator",
        "department": "Operations",
        "responsibilities": ["Coordinate service schedules."],
        "requirements": ["Experience with scheduling systems."],
        "qualifications": [],
    }

    result = _triage(
        job,
        {
            "sourceDispositions": [
                _item("R1", "CORE"),
                _item("R1", "CORE"),
                _item("Q9", "SUPPORTING"),
            ]
        },
    )

    assert not result.is_valid
    assert result.duplicate_source_refs == {"R1"}
    assert result.unknown_source_refs == {"Q9"}
    assert result.missing_source_refs == {"Q1"}


def test_generic_assigned_duty_is_deterministically_ignored():
    text = "Perform other duties assigned by management"
    job = {
        "jobTitle": "Coordinator",
        "department": "Operations",
        "responsibilities": [text],
        "requirements": [],
        "qualifications": [],
    }

    result = _triage(
        job,
        {"sourceDispositions": [_item("R1", "CORE")]},
        generic_detector=lambda value: value == text,
    )

    disposition = result.by_ref["R1"]
    assert result.is_valid
    assert disposition.disposition == "IGNORE"
    assert disposition.criterion_use == "NONE"
    assert not disposition.resume_assessable
    assert disposition.decision_source == "deterministic_generic_duty"


def test_cctv_significance_remains_role_aware_not_globally_hard_coded():
    responsibility = "Monitor CCTV and investigate security incidents."
    people_job = {
        "jobTitle": "People Operations Manager",
        "department": "People",
        "responsibilities": [responsibility],
        "requirements": [],
        "qualifications": [],
    }
    security_job = {
        **people_job,
        "jobTitle": "Security Operations Manager",
        "department": "Security",
    }

    people = _triage(
        people_job,
        {
            "sourceDispositions": [
                _item(
                    "R1",
                    "SUPPORTING",
                    importance="low",
                    criterion_use="NONE",
                    reason="Minor relative to the complete people role.",
                )
            ]
        },
    )
    security = _triage(
        security_job,
        {
            "sourceDispositions": [
                _item(
                    "R1",
                    "CORE",
                    importance="high",
                    reason="Central security monitoring capability.",
                )
            ]
        },
    )

    assert people.by_ref["R1"].disposition == "SUPPORTING"
    assert people.formation_source_refs == set()
    assert security.by_ref["R1"].disposition == "CORE"
    assert security.required_source_refs == {"R1"}


def test_supporting_source_policies_distinguish_strengthening_from_standalone_use():
    job = {
        "jobTitle": "Operations Lead",
        "department": "Operations",
        "responsibilities": [
            "Lead production planning and capacity decisions.",
            "Prepare planning reports for the production team.",
            "Administer a specialist scheduling platform.",
        ],
        "requirements": [],
        "qualifications": [],
    }
    result = _triage(
        job,
        {
            "sourceDispositions": [
                _item("R1", "CORE", importance="high"),
                _item(
                    "R2",
                    "SUPPORTING",
                    criterion_use="STRENGTHEN_ONLY",
                    reason="Strengthens production planning evidence.",
                ),
                _item(
                    "R3",
                    "SUPPORTING",
                    criterion_use="STANDALONE_ELIGIBLE",
                    reason="Distinct resume-assessable system capability.",
                ),
            ]
        },
    )

    assert result.is_valid
    assert result.required_source_refs == {"R1"}
    assert result.formation_source_refs == {"R1", "R2", "R3"}
    assert result.strengthen_only_source_refs == {"R2"}
    assert "R2" not in result.required_source_refs
    assert "R3" not in result.required_source_refs


def test_level_only_education_remains_scoring_evidence_for_the_new_pipeline():
    job = {
        "jobTitle": "Coordinator",
        "department": "Operations",
        "responsibilities": [],
        "requirements": ["Minimum Diploma or Degree"],
        "qualifications": [],
    }
    result = _triage(
        job,
        {"sourceDispositions": [_item("Q1", "CORE")]},
    )

    disposition = result.by_ref["Q1"]
    assert result.is_valid
    assert disposition.disposition == "CORE"
    assert disposition.processing_outcome == "criterion_required"
    assert disposition.decision_source == "qwen_role_triage"
    assert result.required_source_refs == {"Q1"}


def test_safe_audit_contains_source_identity_disposition_and_reason_without_raw_text():
    job = {
        "jobTitle": "Coordinator",
        "department": "Operations",
        "responsibilities": ["Coordinate service schedules."],
        "requirements": [],
        "qualifications": [],
    }
    result = _triage(
        job,
        {"sourceDispositions": [_item("R1", "CORE", importance="high")]},
    )

    entry = result.safe_audit()["sources"][0]
    assert entry["sourceRef"] == "R1"
    assert entry["sourceId"] == "responsibilities-1"
    assert entry["disposition"] == "CORE"
    assert entry["sourceHash"]
    assert entry["reason"]
    assert "sourceText" not in entry
