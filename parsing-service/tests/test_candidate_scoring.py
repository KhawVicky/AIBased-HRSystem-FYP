from decimal import Decimal
import json

import pytest

from app.services.candidate_scoring import (
    CandidateScoringEngine,
    CandidateScoringError,
    _build_evidence_index,
    _match_level_for_score,
    _select_evidence,
)
from app.services.candidate_scoring_qwen import QwenCriterionResult


class FakeQwen:
    model = "Qwen/Qwen2.5-3B-Instruct"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def score(self, *, criterion, candidate_evidence):
        self.calls.append((criterion, candidate_evidence))
        return QwenCriterionResult(
            payload=next(self.outputs),
            model=self.model,
            qwen_used=True,
            mock_mode=False,
        )


class FakeRepository:
    def __init__(self):
        self.persisted = None

    def load_context(self, job_id, application_id):
        raise AssertionError("this test uses score_context")

    def persist_result(self, context, payload):
        self.persisted = payload
        return 17, 2


def _context(criteria=None, *, profile=None, eligibility=None):
    return {
        "job": {"id": 7, "title": "HR Executive", "department": "Human Resources"},
        "application": {"id": 9, "candidateId": 4},
        "candidate": {
            "candidateCgpa": 3.6,
            "candidateYearsExperience": 6,
            "candidateNoticePeriodDays": 30,
            "candidateEducation": "Bachelor Degree in Human Resources",
            "candidateLocation": "Kuala Lumpur",
            "candidateLanguagesJson": "[{\"language\":\"English\",\"level\":\"Fluent\"}]",
        },
        "criteria": criteria or [
            {
                "id": 101,
                "name": "Foreign Worker Management",
                "type": "relevant_skill",
                "weight": Decimal("60"),
                "sourceText": "Manage foreign worker matters.",
                "description": "",
                "evidenceRule": "Direct responsibility evidence.",
                "sortOrder": 1,
            },
            {
                "id": 102,
                "name": "HR Field Experience",
                "type": "relevant_experience",
                "weight": Decimal("40"),
                "sourceText": "Six years of HR field experience.",
                "description": "",
                "evidenceRule": "Direct HR experience.",
                "sortOrder": 2,
            },
        ],
        "eligibility": eligibility or {"minYearsExperience": 10},
        "eligibilityValues": [],
        "profile": profile or {
            "totalExperienceYears": 6,
            "personalInfo": {"location": "Kuala Lumpur"},
            "education": [{"level": "Bachelor Degree", "field": "Human Resources"}],
            "evidenceIndex": [
                {
                    "sourceId": "experience-1",
                    "sourceSection": "Work Experience",
                    "sourceText": "Managed foreign workers and work permits in an HR field role.",
                    "sourceType": "resume",
                },
                {
                    "sourceId": "experience-2",
                    "sourceSection": "Work Experience",
                    "sourceText": "Handled employee relations and HR operations for six years.",
                    "sourceType": "resume",
                },
            ],
        },
        "profileAvailable": True,
    }


def _semantic(
    criterion_id,
    evidence_ids,
    reason,
    *,
    relationship="direct",
    capability="performed",
    coverage="complete",
    strength="strong",
):
    return {
        "criterionId": criterion_id,
        "relationship": relationship,
        "capabilityLevel": capability,
        "coverage": coverage,
        "evidenceStrength": strength,
        "usedEvidenceIds": evidence_ids,
        "reason": reason,
    }


def test_scoring_keeps_eligibility_separate_and_calculates_weights_in_python():
    qwen = FakeQwen(
        [
            _semantic(101, ["experience-1"], "Managed foreign workers and work permits in an HR field role.", capability="managed"),
            _semantic(102, ["experience-2"], "Handled employee relations and HR operations for six years.", coverage="partial", strength="weak"),
        ]
    )
    repository = FakeRepository()

    result = CandidateScoringEngine(repository, qwen).score_context(_context())

    assert result.overallScore == 82
    assert result.totalWeight == 100
    assert result.eligibility.eligible is False
    assert result.eligibility.filteredOut is True
    assert result.rankingReady is False
    assert result.rank is None
    assert [item.rawScore for item in result.scoreBreakdown] == [9, 7]
    assert [item.weightedContribution for item in result.scoreBreakdown] == [54, 28]
    assert result.scoreBreakdown[0].evidenceIds == ["experience-1"]
    assert result.diagnostics.qwenUsed is True
    assert result.diagnostics.fallbackUsed is False
    assert repository.persisted["scoreBreakdown"][0]["grounded"] is True
    assert [item.matchLevel for item in result.scoreBreakdown] == ["strong_match", "matched"]


def test_match_level_boundaries_follow_the_calibrated_numeric_bands():
    assert [_match_level_for_score(value) for value in (0, 1, 4, 5, 6, 7, 8, 9, 10)] == [
        "none", "weak", "weak", "partial", "partial", "matched", "matched", "strong_match", "strong_match"
    ]


def test_candidate_qwen_payload_omits_python_only_evidence_rule():
    qwen = FakeQwen(
        [
            _semantic(101, ["experience-1"], "Managed foreign workers and work permits in an HR field role.", capability="managed"),
            _semantic(102, ["experience-2"], "Handled employee relations and HR operations for six years.", coverage="partial", strength="weak"),
        ]
    )

    CandidateScoringEngine(FakeRepository(), qwen).score_context(_context())

    assert all("evidenceRule" not in criterion for criterion, _ in qwen.calls)
    assert all("jdEvidence" in criterion for criterion, _ in qwen.calls)


def test_unsupported_semantic_claim_is_rejected_to_zero_without_fabricated_evidence():
    qwen = FakeQwen(
        [
            _semantic(101, ["experience-1"], "Administered Kubernetes clusters and Helm deployments.", capability="managed"),
            _semantic(102, [], "No grounded evidence supports the criterion.", relationship="unrelated", capability="mentioned", coverage="partial", strength="weak"),
        ]
    )

    result = CandidateScoringEngine(FakeRepository(), qwen).score_context(_context())

    assert result.scoreBreakdown[0].rawScore == 0
    assert result.scoreBreakdown[0].evidenceIds == []
    assert result.scoreBreakdown[0].grounded is False
    assert result.scoreBreakdown[0].qwenStatus == "rejected_grounding"
    assert result.diagnostics.groundingRejectedCount == 1


def test_only_invalid_evidence_ids_reject_one_criterion_and_complete_candidate_scoring(caplog):
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([
            _semantic(101, ["fabricated-1"], "Managed foreign workers and work permits.")
        ]),
    ).score_context(_context(criteria=[{**_context()["criteria"][0], "weight": Decimal("100")}]))

    breakdown = result.scoreBreakdown[0]
    assert result.runId == 17
    assert result.overallScore == 0
    assert breakdown.rawScore == 0
    assert breakdown.weightedContribution == 0
    assert breakdown.evidenceIds == []
    assert breakdown.matchedResumeEvidence == []
    assert breakdown.grounded is False
    assert breakdown.matchLevel == "none"
    assert breakdown.qwenStatus == "rejected_grounding"
    assert breakdown.explanation == "No grounded candidate evidence was accepted for this criterion."
    assert repository.persisted["scoreBreakdown"][0]["evidenceIds"] == []
    assert "criterion_grounding_rejected application_id=9 criterion_id=101" in caplog.text
    assert "fabricated-1" in caplog.text


def test_mixed_valid_and_invalid_evidence_ids_persist_only_grounded_valid_ids(caplog):
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([
            _semantic(
                101,
                ["experience-1", "fabricated-1"],
                "Managed foreign workers and work permits in an HR field role.",
                capability="managed",
            )
        ]),
    ).score_context(_context(criteria=[{**_context()["criteria"][0], "weight": Decimal("100")}]))

    breakdown = result.scoreBreakdown[0]
    assert result.overallScore == 90
    assert breakdown.evidenceIds == ["experience-1"]
    assert [item.sourceId for item in breakdown.matchedResumeEvidence] == ["experience-1"]
    assert breakdown.qwenStatus == "live"
    assert result.diagnostics.groundingRejectedCount == 0
    assert repository.persisted["scoreBreakdown"][0]["evidenceIds"] == ["experience-1"]
    assert "fabricated-1" not in repository.persisted["scoreBreakdown"][0]["evidenceIds"]
    assert "invalid_evidence_ids_removed" in caplog.text


def test_unrelated_assessment_with_evidence_ids_becomes_safe_zero_and_completes(caplog):
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([
            _semantic(
                101,
                ["experience-1"],
                "The evidence is unrelated.",
                relationship="unrelated",
                capability="mentioned",
                coverage="partial",
                strength="weak",
            )
        ]),
    ).score_context(_context(criteria=[{**_context()["criteria"][0], "weight": Decimal("100")}]))

    breakdown = result.scoreBreakdown[0]
    assert result.runId == 17
    assert result.overallScore == 0
    assert breakdown.evidenceIds == []
    assert breakdown.rawScore == 0
    assert breakdown.weightedContribution == 0
    assert breakdown.matchLevel == "none"
    assert breakdown.qwenStatus == "rejected_grounding"
    assert breakdown.explanation == "No grounded candidate evidence was accepted for this criterion."
    assert "unrelated_assessment_cited_evidence" in caplog.text


def test_one_invalid_criterion_does_not_change_other_scores_or_original_weights():
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([
            _semantic(
                101,
                ["experience-1"],
                "Managed foreign workers and work permits in an HR field role.",
                capability="managed",
            ),
            _semantic(102, ["fabricated-2"], "Handled HR operations for six years."),
        ]),
    ).score_context(_context())

    assert result.runId == 17
    assert [item.rawScore for item in result.scoreBreakdown] == [9, 0]
    assert [item.weight for item in result.scoreBreakdown] == [60, 40]
    assert [item.weightedContribution for item in result.scoreBreakdown] == [54, 0]
    assert result.overallScore == 54
    assert repository.persisted["overallScore"] == 54


def test_all_grounding_rejected_criteria_complete_with_zero_overall_score():
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([
            _semantic(101, ["fabricated-1"], "Managed foreign workers."),
            _semantic(102, ["fabricated-2"], "Handled HR operations."),
        ]),
    ).score_context(_context())

    assert result.runId == 17
    assert result.overallScore == 0
    assert result.diagnostics.groundingRejectedCount == 2
    assert all(item.rawScore == 0 for item in result.scoreBreakdown)
    assert all(item.qwenStatus == "rejected_grounding" for item in result.scoreBreakdown)
    assert repository.persisted["overallScore"] == 0
    assert len(repository.persisted["scoreBreakdown"]) == 2


def test_invalid_weight_total_is_rejected_and_not_normalized():
    criteria = _context()["criteria"]
    criteria[1]["weight"] = Decimal("30")
    with pytest.raises(CandidateScoringError, match="exactly 100"):
        CandidateScoringEngine(FakeRepository(), None).score_context(_context(criteria=criteria))


def test_live_qwen_is_required_when_valid_evidence_exists():
    with pytest.raises(CandidateScoringError, match="no semantic fallback"):
        CandidateScoringEngine(FakeRepository(), None).score_context(_context())


def test_evidence_retrieval_prioritises_direct_experience_over_lower_priority_keyword_hits():
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "summary-1",
                "sourceSection": "Summary",
                "sourceText": "Human resources professional with management knowledge.",
            },
            {
                "sourceId": "experience-1",
                "sourceSection": "Work Experience",
                "sourceText": "Managed foreign workers and work permits.",
            },
        ],
        "experience": [{"sourceId": "experience-1", "sourceText": "Managed foreign workers and work permits."}],
    }
    evidence = _build_evidence_index(profile)
    selected = _select_evidence(
        {
            "type": "relevant_skill",
            "name": "Foreign Worker Management",
            "jdEvidence": ["Manage foreign worker matters."],
            "description": "",
            "evidenceRule": "",
        },
        evidence,
    )
    assert selected[0].source_id == "experience-1"


def test_no_evidence_is_zero_without_calling_qwen():
    context = _context(
        criteria=[
            {
                "id": 201,
                "name": "Preferred SHRM Certification",
                "type": "preferred_certification",
                "weight": Decimal("100"),
                "sourceText": "SHRM certification preferred.",
                "description": "",
                "evidenceRule": "",
                "sortOrder": 1,
            }
        ],
        profile={"evidenceIndex": [{"sourceId": "experience-1", "sourceSection": "Work Experience", "sourceText": "Handled HR operations."}]},
    )
    repository = FakeRepository()
    result = CandidateScoringEngine(repository, None).score_context(context)
    assert result.overallScore == 0
    assert result.diagnostics.qwenUsed is False
    assert result.diagnostics.zeroEvidenceCriterionCount == 1


def _vicky_like_profile():
    return {
        "education": [
            {"sourceId": "education-1", "sourceText": "Bachelor of Computer Science UOWM KDU PG UC"},
        ],
        "experience": [
            {
                "sourceId": "experience-1",
                "sourceText": "Web Development Intern built responsive WordPress websites with custom CSS.",
                "skillsEvidence": [{"sourceId": "experience-1", "text": "Web Development Intern built responsive WordPress websites with custom CSS."}],
            },
        ],
        "projects": [
            {"sourceId": "project-1", "sourceText": "Built a React, PHP and FastAPI HR web application."},
            {"sourceId": "project-2", "sourceText": "Built an Android POS application using Flutter, Dart and SQLite."},
            {"sourceId": "project-3", "sourceText": "Built a full-stack PHP and MySQL rental website using JavaScript."},
        ],
        "skills": [
            {"name": "GitHub", "evidence": [{"sourceId": "skills-1", "text": "MariaDB, MySQL, SQLite, GitHub", "sourceSection": "Skills"}]},
            {"name": "Programming", "evidence": [{"sourceId": "skills-2", "text": "JavaScript, PHP, Python", "sourceSection": "Skills"}]},
        ],
        "languages": [
            {"sourceId": "language-1", "sourceText": "English", "sourceSection": "Languages"},
        ],
        "evidenceIndex": [
            {"sourceId": "education-1", "sourceSection": "Education", "sourceText": "Bachelor of Computer Science UOWM KDU PG UC", "sourceType": "resume"},
            {"sourceId": "experience-1", "sourceSection": "Work Experience", "sourceText": "Web Development Intern built responsive WordPress websites with custom CSS.", "sourceType": "resume"},
            {"sourceId": "project-1", "sourceSection": "Projects", "sourceText": "Built a React, PHP and FastAPI HR web application.", "sourceType": "resume"},
            {"sourceId": "project-2", "sourceSection": "Projects", "sourceText": "Built an Android POS application using Flutter, Dart and SQLite.", "sourceType": "resume"},
            {"sourceId": "project-3", "sourceSection": "Projects", "sourceText": "Built a full-stack PHP and MySQL rental website using JavaScript.", "sourceType": "resume"},
            {"sourceId": "skills-1", "sourceSection": "Skills", "sourceText": "MariaDB, MySQL, SQLite, GitHub", "sourceType": "resume"},
            {"sourceId": "skills-2", "sourceSection": "Skills", "sourceText": "JavaScript, PHP, Python", "sourceType": "resume"},
            {"sourceId": "language-1", "sourceSection": "Languages", "sourceText": "English", "sourceType": "resume"},
        ],
    }


def _criterion(name, criterion_type, evidence):
    return {
        "id": 701,
        "name": name,
        "type": criterion_type,
        "weight": Decimal("100"),
        "sourceText": evidence,
        "description": "",
        "evidenceRule": "",
        "sortOrder": 1,
    }


@pytest.mark.parametrize(
    ("criterion_name", "criterion_type", "jd_evidence", "source_text", "semantic", "expected_score"),
    [
        (
            "Backend Development",
            "relevant_skill",
            "Build backend APIs and services.",
            "Write small Python scripts for administrative automation.",
            _semantic(701, ["evidence-1"], "Python scripts for administrative automation are related but do not directly demonstrate backend development.", relationship="adjacent", capability="performed", coverage="complete", strength="strong"),
            3,
        ),
        (
            "Recruitment and Supervision",
            "relevant_experience",
            "Recruitment and supervision of employees.",
            "Support recruitment, onboarding and employee relations.",
            _semantic(701, ["evidence-1"], "Supported recruitment, onboarding and employee relations.", capability="supported", coverage="partial", strength="moderate"),
            5.5,
        ),
        (
            "Payroll Processing and Administration",
            "relevant_skill",
            "Process monthly payroll including wages, overtime, allowances, bonuses and deductions.",
            "Process monthly payroll for 280 employees including wages, overtime, allowances, bonuses and deductions.",
            _semantic(701, ["evidence-1"], "Process monthly payroll for 280 employees including wages, overtime, allowances, bonuses and deductions.", capability="performed", coverage="complete", strength="strong"),
            8,
        ),
        (
            "ISO 9001/OHSAS",
            "domain_knowledge",
            "Knowledge of ISO 9001 and OHSAS standards.",
            "Completed ISO 9001 awareness training.",
            _semantic(701, ["evidence-1"], "Completed ISO 9001 awareness training.", capability="trained", coverage="partial", strength="strong"),
            4.75,
        ),
        (
            "ISO 9001/OHSAS",
            "domain_knowledge",
            "Maintain ISO 9001 procedures and OHSAS compliance records.",
            "Maintained ISO 9001 procedures and OHSAS compliance records as part of regular job responsibilities.",
            _semantic(701, ["evidence-1"], "Maintained ISO 9001 procedures and OHSAS compliance records as part of regular job responsibilities.", capability="performed", coverage="complete", strength="strong"),
            8,
        ),
    ],
)
def test_semantic_relationship_and_capability_bands_reduce_overmatching(
    criterion_name,
    criterion_type,
    jd_evidence,
    source_text,
    semantic,
    expected_score,
):
    criterion = _criterion(criterion_name, criterion_type, jd_evidence)
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "evidence-1",
                "sourceSection": "Work Experience",
                "sourceText": source_text,
            }
        ]
    }
    result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([semantic]),
    ).score_context(_context(criteria=[criterion], profile=profile, eligibility={}))

    breakdown = result.scoreBreakdown[0]
    assert breakdown.rawScore == expected_score
    assert breakdown.evidenceIds == ["evidence-1"]
    assert breakdown.matchedResumeEvidence[0].sourceText == source_text
    assert breakdown.grounded is True


def test_semantic_no_match_is_unrelated_and_zero_without_evidence_ids():
    criterion = _criterion("Kubernetes Administration", "relevant_experience", "Administer Kubernetes clusters.")
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "evidence-1",
                "sourceSection": "Work Experience",
                "sourceText": "Supported Windows desktop troubleshooting and user accounts.",
            }
        ]
    }
    repository = FakeRepository()
    result = CandidateScoringEngine(
        repository,
        FakeQwen([_semantic(701, [], "No Kubernetes evidence is present.", relationship="unrelated", capability="mentioned", coverage="partial", strength="weak")]),
    ).score_context(_context(criteria=[criterion], profile=profile, eligibility={}))

    breakdown = result.scoreBreakdown[0]
    assert breakdown.rawScore == 0
    assert breakdown.evidenceIds == []
    assert breakdown.matchLevel == "none"
    assert breakdown.grounded is False
    assert breakdown.qwenStatus == "live"
    assert result.overallScore == 0
    assert result.diagnostics.groundingRejectedCount == 0
    assert repository.persisted["overallScore"] == 0


def test_evidence_categories_keep_work_and_project_sources_canonical():
    evidence = _build_evidence_index(_vicky_like_profile())
    by_id = {item.source_id: item.category for item in evidence}
    assert by_id["experience-1"] == "experience"
    assert by_id["project-1"] == "project"
    assert by_id["skills-1"] == "skill"


def test_version_control_prefers_git_over_sqlite_and_uses_small_top_k():
    evidence = _build_evidence_index(_vicky_like_profile())
    selected = _select_evidence(
        _criterion("Version Control", "relevant_skill", "Use Git for source code version control and collaboration."),
        evidence,
    )
    assert selected[0].source_id == "skills-1"
    assert all(item.source_id != "project-2" for item in selected)
    assert len(selected) <= 5


def test_language_retrieval_prioritises_application_form_and_excludes_projects():
    profile = _vicky_like_profile()
    context = {"candidate": {"candidateLanguagesJson": json.dumps([{"language": "English", "level": "Intermediate"}])}}
    evidence = _build_evidence_index(profile, context)
    selected = _select_evidence(
        _criterion("English Language", "job_related_language", "Able to communicate in English."),
        evidence,
    )
    assert selected[0].source_id == "application-language-1"
    assert {item.category for item in selected} == {"language"}
    assert all(item.category not in {"project", "skill", "experience"} for item in selected)


def test_database_and_backend_frontend_retrieval_use_multiple_relevant_sources():
    evidence = _build_evidence_index(_vicky_like_profile())
    database = _select_evidence(
        _criterion("Database", "relevant_skill", "Work with databases and validate application data."),
        evidence,
    )
    backend_frontend = _select_evidence(
        _criterion("Backend and Frontend Development", "relevant_skill", "Support frontend and backend development."),
        evidence,
    )
    database_ids = {item.source_id for item in database}
    full_stack_ids = {item.source_id for item in backend_frontend}
    assert {"skills-1", "project-2", "project-3"}.issubset(database_ids)
    assert {"project-1", "project-3", "experience-1"}.issubset(full_stack_ids)


def test_testing_retrieval_accepts_grounded_layout_issue_evidence_as_weak_signal():
    evidence = _build_evidence_index(_vicky_like_profile())
    selected = _select_evidence(
        _criterion("Testing", "relevant_skill", "Test application features and report bugs."),
        evidence,
    )
    assert "experience-1" in {item.source_id for item in selected}


def test_direct_full_stack_and_database_matches_use_direct_capability_bands():
    profile = _vicky_like_profile()
    backend_criterion = _criterion(
        "Backend and Frontend Development",
        "relevant_skill",
        "Support frontend and backend development.",
    )
    backend_result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([
            _semantic(701, ["project-3"], "The full-stack rental website uses PHP, MySQL, HTML, CSS and JavaScript.")
        ]),
    ).score_context(_context(criteria=[backend_criterion], profile=profile, eligibility={}))
    assert backend_result.scoreBreakdown[0].rawScore == 8

    database_criterion = _criterion(
        "Database",
        "relevant_skill",
        "Work with databases to retrieve and update application data.",
    )
    database_result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([
            _semantic(701, ["project-2"], "The POS application uses SQLite for offline storage and transaction processing.")
        ]),
    ).score_context(_context(criteria=[database_criterion], profile=profile, eligibility={}))
    assert database_result.scoreBreakdown[0].rawScore == 8


def test_web_application_retrieval_is_not_blocked_by_testing_text_in_same_jd():
    evidence = _build_evidence_index(_vicky_like_profile())
    selected = _select_evidence(
        _criterion(
            "Web Application Development",
            "relevant_skill",
            "Assist in developing internal web applications. Test application features and report bugs.",
        ),
        evidence,
    )
    selected_ids = {item.source_id for item in selected}
    assert {"experience-1", "project-1", "project-3"}.issubset(selected_ids)


def test_programming_language_retrieval_ignores_unlisted_dart_and_sqlite():
    evidence = _build_evidence_index(_vicky_like_profile())
    selected = _select_evidence(
        _criterion(
            "At Least One Programming Language Experience",
            "relevant_experience",
            "Experience with Python, JavaScript or PHP.",
        ),
        evidence,
    )
    selected_ids = {item.source_id for item in selected}
    assert {"skills-2", "project-1", "project-3"}.issubset(selected_ids)
    assert "project-2" not in selected_ids


def test_exact_education_match_uses_trained_capability_band():
    criterion = _criterion(
        "Computing Education",
        "education_relevance",
        "Diploma or Bachelor's Degree in Computer Science or a related field.",
    )
    qwen = FakeQwen([
        _semantic(701, ["education-1"], "Bachelor of Computer Science is directly relevant.", capability="trained")
    ])
    context = _context(
        criteria=[criterion],
        profile=_vicky_like_profile(),
        eligibility={},
    )
    result = CandidateScoringEngine(FakeRepository(), qwen).score_context(context)
    assert result.scoreBreakdown[0].rawScore == 5
    assert result.scoreBreakdown[0].matchLevel == "partial"


def test_exact_application_language_match_uses_grounded_capability_band_without_project_evidence():
    criterion = _criterion("English Language", "job_related_language", "Able to communicate in English.")
    qwen = FakeQwen([
        _semantic(701, ["application-language-1"], "English Intermediate is relevant language evidence.", coverage="partial", strength="strong")
    ])
    context = _context(
        criteria=[criterion],
        profile=_vicky_like_profile(),
        eligibility={},
    )
    context["candidate"]["candidateLanguagesJson"] = json.dumps([{"language": "English", "level": "Intermediate"}])
    result = CandidateScoringEngine(FakeRepository(), qwen).score_context(context)
    assert result.scoreBreakdown[0].rawScore == 7.75
    assert result.scoreBreakdown[0].evidenceIds == ["application-language-1"]
    assert result.scoreBreakdown[0].matchLevel == "matched"


def test_listed_programming_language_does_not_receive_a_keyword_only_floor():
    criterion = _criterion(
        "Programming Language Experience",
        "relevant_experience",
        "Experience with at least one of Python, JavaScript or PHP.",
    )
    qwen = FakeQwen([
        _semantic(701, ["skills-2"], "JavaScript, PHP and Python are explicitly listed.", capability="mentioned")
    ])
    result = CandidateScoringEngine(
        FakeRepository(),
        qwen,
    ).score_context(_context(criteria=[criterion], profile=_vicky_like_profile(), eligibility={}))
    assert result.scoreBreakdown[0].rawScore == 4
    assert result.scoreBreakdown[0].matchLevel == "weak"


def test_complete_payroll_evidence_uses_the_performed_capability_band():
    criterion = _criterion(
        "Payroll Processing and Administration",
        "relevant_skill",
        "Process wages, bonus, allowances, overtime and deductions; prepare accurate monthly payroll reports and review payroll for approval.",
    )
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "experience-payroll",
                "sourceSection": "Work Experience",
                "sourceText": "Managed payroll processing for wages, bonus, allowances, overtime and deductions. Prepared accurate monthly payroll reports, reviewed final checking and handled payroll approval.",
            }
        ]
    }
    result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([
            _semantic(701, ["experience-payroll"], "Managed payroll processing for wages, bonus, allowances, overtime and deductions and prepared accurate monthly payroll reports for approval.")
        ]),
    ).score_context(_context(criteria=[criterion], profile=profile, eligibility={}))
    assert result.scoreBreakdown[0].rawScore == 8
    assert result.scoreBreakdown[0].matchLevel == "matched"


def test_degree_wording_accepts_a_direct_bachelors_record_and_keeps_it_as_evidence():
    criterion = _criterion(
        "Education",
        "education_relevance",
        "Diploma or Degree with min. 5 years experience in HR field.",
    )
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "education-1",
                "sourceSection": "Education",
                "sourceText": "Bachelor of Human Resource Management | University | 2016 - 2020",
            }
        ]
    }
    result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([
            _semantic(701, ["education-1"], "Bachelor of Human Resource Management is a direct degree in the HR field.", capability="trained")
        ]),
    ).score_context(_context(criteria=[criterion], profile=profile, eligibility={}))
    assert result.scoreBreakdown[0].rawScore == 5
    assert result.scoreBreakdown[0].matchLevel == "partial"
    assert "education-1" in result.scoreBreakdown[0].evidenceIds


def test_candidate_scoring_keeps_qwen_evidence_selection_authoritative():
    criterion = _criterion(
        "Malaysian Labour Law",
        "domain_knowledge",
        "Familiar with Malaysian labour laws and relevant HR responsibilities.",
    )
    profile = {
        "evidenceIndex": [
            {
                "sourceId": "experience-1",
                "sourceSection": "Work Experience",
                "sourceText": "Supported Malaysian labour compliance reviews for five years.",
            },
            {
                "sourceId": "skills-1",
                "sourceSection": "Skills",
                "sourceText": "Malaysian labour law and HR policy compliance.",
            },
        ]
    }
    result = CandidateScoringEngine(
        FakeRepository(),
        FakeQwen([
            _semantic(701, ["experience-1"], "Supported Malaysian labour compliance reviews for five years.", capability="supported", coverage="partial", strength="moderate")
        ]),
    ).score_context(_context(criteria=[criterion], profile=profile, eligibility={}))
    assert result.scoreBreakdown[0].rawScore == 5.5
    assert result.scoreBreakdown[0].evidenceIds == ["experience-1"]
    assert result.scoreBreakdown[0].matchLevel == "partial"
