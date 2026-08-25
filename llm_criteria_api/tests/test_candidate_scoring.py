import json
import os
from dataclasses import replace

import pytest

os.environ["MOCK_LLM"] = "true"

from app import runpod_handler
from app.candidate_scoring import (
    CandidateCriterionScoringRequest,
    build_candidate_scoring_messages,
    generate_candidate_criterion_score,
)


class FakeLoader:
    loaded = True

    def __init__(self, output):
        self.output = output

    def generate(self, messages):
        self.messages = messages
        return self.output


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


def test_candidate_worker_contract_returns_semantic_labels_and_does_not_calculate_weight():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={
            "id": 101,
            "name": "Foreign Worker Management",
            "type": "relevant_skill",
            "jdEvidence": ["Manage foreign worker matters."],
        },
        candidateEvidence=[
            {
                "sourceId": "experience-1",
                "sourceSection": "Work Experience",
                "sourceText": "Managed foreign workers and work permits.",
            }
        ],
    )
    loader = FakeLoader(
        json.dumps(
            _semantic(101, ["experience-1"], "Managed foreign workers and work permits.", capability="managed")
        )
    )

    result = generate_candidate_criterion_score(loader, request)

    assert result["criterionId"] == 101
    assert result["relationship"] == "direct"
    assert result["capabilityLevel"] == "managed"
    assert result["coverage"] == "complete"
    assert result["evidenceStrength"] == "strong"
    assert "score" not in result
    assert "matchLevel" not in result
    assert "weight" not in result
    assert loader.messages[0]["role"] == "system"
    assert "candidateEvidence" in json.loads(loader.messages[1]["content"])


def test_candidate_worker_converts_only_invalid_evidence_ids_to_safe_grounding_rejection(caplog):
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 1, "name": "Language", "type": "job_related_language"},
        candidateEvidence=[
            {"sourceId": "language-1", "sourceSection": "Languages", "sourceText": "English"}
        ],
    )
    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(1, ["fabricated-1"], "Candidate speaks the required language.")
            )
        ),
        request,
    )

    assert result["relationship"] == "unrelated"
    assert result["usedEvidenceIds"] == []
    assert result["reason"] == "No grounded candidate evidence was accepted for this criterion."
    assert "criterion_grounding_rejected" in caplog.text
    assert "fabricated-1" in caplog.text


def test_candidate_worker_keeps_only_compatible_valid_ids_from_mixed_grounding(caplog):
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 2, "name": "Language", "type": "job_related_language"},
        candidateEvidence=[
            {"sourceId": "language-1", "sourceSection": "Languages", "sourceText": "English"}
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(2, ["language-1", "fabricated-1"], "English is listed in the candidate's languages.")
            )
        ),
        request,
    )

    assert result["relationship"] == "direct"
    assert result["usedEvidenceIds"] == ["language-1"]
    assert "fabricated-1" not in result["usedEvidenceIds"]
    assert "invalid_evidence_ids_removed" in caplog.text


def test_candidate_worker_normalizes_unrelated_assessment_with_evidence_to_zero(caplog):
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 3, "name": "Language", "type": "job_related_language"},
        candidateEvidence=[
            {"sourceId": "language-1", "sourceSection": "Languages", "sourceText": "English"}
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(
                    3,
                    ["language-1"],
                    "The evidence is unrelated.",
                    relationship="unrelated",
                    capability="mentioned",
                    coverage="partial",
                    strength="weak",
                )
            )
        ),
        request,
    )

    assert result["relationship"] == "unrelated"
    assert result["usedEvidenceIds"] == []
    assert result["reason"] == "No grounded candidate evidence was accepted for this criterion."
    assert "unrelated_assessment_cited_evidence" in caplog.text


def test_candidate_worker_normalizes_semantic_label_case():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 1, "name": "Python", "type": "relevant_skill"},
        candidateEvidence=[
            {"sourceId": "skill-1", "sourceSection": "Skills", "sourceText": "Python"}
        ],
    )
    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(1, ["skill-1"], "Python", capability="PERFORMED", coverage="COMPLETE", strength="STRONG")
            )
        ),
        request,
    )

    assert result["capabilityLevel"] == "performed"
    assert result["coverage"] == "complete"
    assert result["evidenceStrength"] == "strong"


def test_candidate_worker_normalizes_axis_swapped_training_relationship():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={
            "id": 901,
            "name": "ISO 9001 and OHSAS Quality Standards",
            "type": "domain_knowledge",
        },
        candidateEvidence=[
            {
                "sourceId": "case-d-1",
                "sourceSection": "Training",
                "sourceText": "Completed ISO 9001 awareness training.",
            }
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(
                    901,
                    ["case-d-1"],
                    "Completed ISO 9001 awareness training.",
                    relationship="mentioned",
                    capability="trained",
                    coverage="partial",
                    strength="moderate",
                )
            )
        ),
        request,
    )

    assert result["relationship"] == "direct"
    assert result["capabilityLevel"] == "trained"
    assert result["coverage"] == "partial"
    assert result["evidenceStrength"] == "moderate"
    assert result["usedEvidenceIds"] == ["case-d-1"]


def test_candidate_worker_returns_safe_unrelated_result_for_unspecified_no_match():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={
            "id": 902,
            "name": "Kubernetes Administration",
            "type": "relevant_skill",
        },
        candidateEvidence=[
            {
                "sourceId": "case-e-1",
                "sourceSection": "Skills",
                "sourceText": "Processed invoices using Microsoft Excel.",
            }
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(
                    902,
                    [],
                    "",
                    relationship="unrelated",
                    capability="unspecified",
                )
            )
        ),
        request,
    )

    assert result["relationship"] == "unrelated"
    assert result["capabilityLevel"] == "mentioned"
    assert result["coverage"] == "partial"
    assert result["evidenceStrength"] == "weak"
    assert result["usedEvidenceIds"] == []
    assert result["reason"] == "No valid candidate evidence supports this criterion."


def test_candidate_worker_does_not_upgrade_uncertain_axis_to_positive_match():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 903, "name": "Kubernetes Administration", "type": "relevant_skill"},
        candidateEvidence=[
            {
                "sourceId": "case-e-1",
                "sourceSection": "Skills",
                "sourceText": "Processed invoices using Microsoft Excel.",
            }
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(
                    903,
                    ["case-e-1"],
                    "The evidence is not specific to Kubernetes.",
                    relationship="mentioned",
                    capability="unspecified",
                )
            )
        ),
        request,
    )

    assert result["relationship"] == "unrelated"
    assert result["usedEvidenceIds"] == []
    assert result["reason"] == "No valid candidate evidence supports this criterion."


def test_candidate_worker_rejects_retrieved_id_from_unspecified_unrelated_result():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 904, "name": "Kubernetes Administration", "type": "relevant_skill"},
        candidateEvidence=[
            {
                "sourceId": "case-e-1",
                "sourceSection": "Skills",
                "sourceText": "Processed invoices using Microsoft Excel.",
            }
        ],
    )

    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                _semantic(
                    904,
                    ["case-e-1"],
                    "No Kubernetes evidence is present.",
                    relationship="unrelated",
                    capability="unspecified",
                )
            )
        ),
        request,
    )

    assert result["relationship"] == "unrelated"
    assert result["usedEvidenceIds"] == []
    assert result["reason"] == "No grounded candidate evidence was accepted for this criterion."


def test_candidate_worker_rejects_invalid_semantic_label():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 2, "name": "Database", "type": "relevant_skill"},
        candidateEvidence=[
            {"sourceId": "skill-2", "sourceSection": "Skills", "sourceText": "MySQL"}
        ],
    )
    with pytest.raises(ValueError, match="validation|literal|valid"):
        generate_candidate_criterion_score(
            FakeLoader(
                json.dumps(
                    {
                        "criterionId": 2,
                        "usedEvidenceIds": ["skill-2"],
                        "reason": "MySQL is listed in the candidate's skills.",
                        "relationship": "unrelated-but-high",
                        "capabilityLevel": "mentioned",
                        "coverage": "partial",
                        "evidenceStrength": "moderate",
                    }
                )
            ),
            request,
        )


def test_candidate_worker_binds_redundant_criterion_id_to_request():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={"id": 3, "name": "Database", "type": "relevant_skill"},
        candidateEvidence=[
            {"sourceId": "skill-3", "sourceSection": "Skills", "sourceText": "MySQL"}
        ],
    )
    result = generate_candidate_criterion_score(
        FakeLoader(
            json.dumps(
                {
                    "criterionId": 999,
                    "usedEvidenceIds": ["skill-3"],
                    "reason": "MySQL is listed in the candidate's skills.",
                    "relationship": "direct",
                    "capabilityLevel": "mentioned",
                    "coverage": "partial",
                    "evidenceStrength": "moderate",
                }
            )
        ),
        request,
    )

    assert result["criterionId"] == 3


def test_runpod_candidate_task_has_an_isolated_dispatch(monkeypatch):
    monkeypatch.setattr(
        runpod_handler.runtime,
        "config",
        replace(runpod_handler.runtime.config, mock_llm=False),
    )
    monkeypatch.setattr(
        runpod_handler,
        "settings",
        replace(runpod_handler.settings, mock_llm=False),
    )
    captured = {}

    def fake_generation(job, request_id):
        captured["job"] = job
        captured["request_id"] = request_id
        return {
            "criterionId": 101,
            "relationship": "direct",
            "capabilityLevel": "managed",
            "coverage": "complete",
            "evidenceStrength": "strong",
            "usedEvidenceIds": ["experience-1"],
            "reason": "Managed foreign workers.",
        }

    monkeypatch.setattr(runpod_handler.runtime, "generate_candidate_criterion_score", fake_generation)
    result = runpod_handler.handler(
        {
            "id": "candidate-score-1",
            "input": {
                "task": "candidate_criterion_scoring",
                "criterion": {
                    "id": 101,
                    "name": "Foreign Worker Management",
                    "type": "relevant_skill",
                },
                "candidateEvidence": [
                    {
                        "sourceId": "experience-1",
                        "sourceSection": "Work Experience",
                        "sourceText": "Managed foreign workers.",
                    }
                ],
            },
        }
    )

    assert result["status"] == "success"
    assert result["output"]["qwenUsed"] is True
    assert result["output"]["mockMode"] is False
    assert result["output"]["runtimeTask"] == "candidate_criterion_scoring"
    assert captured["job"]["task"] == "candidate_criterion_scoring"
    assert captured["request_id"] == "candidate-score-1"


def test_candidate_scoring_prompt_contains_structured_grounded_assessment_rules():
    request = CandidateCriterionScoringRequest(
        task="candidate_criterion_scoring",
        criterion={
            "id": 7,
            "name": "Computing Education",
            "type": "education_relevance",
            "jdEvidence": ["Bachelor of Computer Science"],
        },
        candidateEvidence=[
            {
                "sourceId": "education-1",
                "sourceSection": "Education",
                "sourceText": "Bachelor of Computer Science",
            }
        ],
    )
    system_prompt = build_candidate_scoring_messages(request)[0]["content"]
    assert '"relationship": "direct | adjacent | unrelated"' in system_prompt
    assert '"capabilityLevel": "mentioned | trained | supported | performed | managed | supervised"' in system_prompt
    assert '"evidenceStrength": "weak | moderate | strong"' in system_prompt
    assert "Python calculates those fields deterministically" in system_prompt
    assert "Assess the relationship before the capability level" in system_prompt
    assert "Windows Server" in system_prompt
    assert "Use only the supplied candidateEvidence" in system_prompt
    assert '"score":' not in system_prompt
    assert '"matchLevel":' not in system_prompt
