import os
from dataclasses import replace

os.environ["MOCK_LLM"] = "true"

from app.runpod_handler import handler
from app import runpod_handler
from app.pipeline import CriteriaPipeline
from app.model_output import normalise_model_output
from app import config
from pathlib import Path
import json
import re


class FencedRawLoader:
    def __init__(self, raw_outputs):
        from types import SimpleNamespace

        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._raw_outputs = iter(raw_outputs)

    def raw_output_generator(self, _messages):
        return next(self._raw_outputs)


class EnhancedRawLoader:
    def __init__(self, raw_output):
        from types import SimpleNamespace

        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._raw_output = raw_output

    def triage_raw_output_generator(self, messages):
        refs = list(
            dict.fromkeys(
                re.findall(
                    r'"sourceRef"\s*:\s*"([RQ]\d+)"',
                    messages[1]["content"],
                )
            )
        )
        return json.dumps(
            {
                "sourceDispositions": [
                    {
                        "sourceRef": source_ref,
                        "disposition": "CORE" if source_ref.startswith("R") else "SUPPORTING",
                        "resumeAssessable": True,
                        "importance": "high" if source_ref.startswith("R") else "medium",
                        "criterionUse": "STANDALONE_ELIGIBLE",
                        "reason": "Material resume-assessable role evidence.",
                    }
                    for source_ref in refs
                ]
            }
        )

    def enhanced_raw_output_generator(self, _messages):
        return self._raw_output


def test_runpod_health_and_mock_generation():
    health = handler({"id": "health-1", "input": {"action": "health"}})
    assert health["status"] == "success"
    assert health["output"]["mockMode"] is True
    deployment = health["output"]["deployment"]
    assert deployment["imageTag"]
    assert deployment["pipelineVersion"]
    assert "gitCommitHash" in deployment
    assert deployment["roleContextEnabled"] is True
    assert deployment["finalEvidenceSafetyEnabled"] is True

    result = handler(
        {
            "id": "generation-1",
            "input": {
                "jobTitle": "Process Engineer",
                "department": "Engineering",
                "responsibilities": ["Analyse process data."],
                "requirements": [],
                "qualifications": ["A degree in Engineering is required."],
            },
        }
    )
    assert result["status"] == "success"
    assert result["requestId"] == "generation-1"
    assert result["output"]["weightTotal"] == 100
    assert result["output"]["criteria"]
    stages = [
        item["stage"]
        for item in result["output"]["audit"]["debugTrace"]
    ]
    assert any(stage.startswith("qwen_generation:") for stage in stages)
    assert any(stage.startswith("multi_sentence_grounding:") for stage in stages)
    assert any(stage.startswith("education_validation:") for stage in stages)
    assert "role_context" in stages
    assert "final_evidence_safety" in stages
    assert "role_context_weighting" in stages
    assert "api_payload_ready" in stages
    assert stages[-1] == "api_serialization"


def test_runpod_rejects_empty_evidence():
    result = handler(
        {
            "input": {
                "jobTitle": "Process Engineer",
                "department": "Engineering",
                "responsibilities": [],
                "requirements": [],
            }
        }
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_input"


def test_runpod_resume_task_uses_isolated_shared_model_dispatch(monkeypatch):
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

    def fake_resume_generation(job, request_id):
        captured["job"] = job
        captured["request_id"] = request_id
        return {"primaryDomain": "frontend engineering"}

    monkeypatch.setattr(runpod_handler.runtime, "generate_resume_semantics", fake_resume_generation)
    result = handler(
        {
            "id": "resume-semantic-1",
            "input": {
                "task": "resume_semantic_understanding",
                "resumeText": "Built React applications for internal users.",
                "sections": {"experience": "Built React applications for internal users."},
                "evidenceIndex": [
                    {
                        "sourceId": "experience-1",
                        "sourceSection": "Work Experience",
                        "sourceText": "Built React applications for internal users.",
                        "sourceType": "resume",
                    }
                ],
            },
        }
    )

    assert result["status"] == "success"
    assert result["requestId"] == "resume-semantic-1"
    assert result["output"]["primaryDomain"] == "frontend engineering"
    assert captured["job"]["task"] == "resume_semantic_understanding"
    assert captured["request_id"] == "resume-semantic-1"


def test_runpod_resume_task_rejects_mock_mode():
    result = handler(
        {
            "input": {
                "task": "resume_semantic_understanding",
                "resumeText": "Built React applications for internal users.",
                "evidenceIndex": [
                    {
                        "sourceId": "experience-1",
                        "sourceSection": "Work Experience",
                        "sourceText": "Built React applications for internal users.",
                        "sourceType": "resume",
                    }
                ],
            }
        }
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "mock_mode_disabled"


def test_real_runpod_fenced_outputs_reach_frozen_validation():
    fixture_path = Path(__file__).parent / "fixtures" / "runpod_fenced_outputs.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = CriteriaPipeline(FencedRawLoader(fixture["rawModelOutputs"])).generate(fixture["input"])

    assert result["criteria"]
    sections = result["audit"]["sectionDiagnostics"]
    assert sections["responsibilities"]["invalidOutput"] is False
    assert sections["requirements"]["invalidOutput"] is False
    assert sections["responsibilities"]["fenceNormalisationApplied"] is True
    assert sections["requirements"]["fenceNormalisationApplied"] is True
    assert sections["responsibilities"]["originalRawModelOutput"].startswith("```json")
    assert sections["requirements"]["originalRawModelOutput"].startswith("```JSON")
    assert sections["responsibilities"]["finalRawModelOutput"].startswith("{")
    assert sections["requirements"]["finalRawModelOutput"].startswith("{")
    assert "Malformed JSON" not in sections["responsibilities"]["issues"]
    assert "Malformed JSON" not in sections["requirements"]["issues"]


def test_enhanced_path_reports_one_complete_jd_generation():
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Process Data Analysis",
                    "sourceText": "Analyse process data.",
                    "importance": "high",
                }
            ],
            "ignoredTexts": [],
        }
    )
    result = CriteriaPipeline(
        EnhancedRawLoader(raw_output)
    ).generate(
        {
            "jobTitle": "Process Engineer",
            "department": "Engineering",
            "responsibilities": ["Analyse process data."],
            "requirements": ["Knowledge of statistical process control is required."],
        }
    )

    stages = [item["stage"] for item in result["audit"]["debugTrace"]]
    assert "qwen_generation:complete_jd" in stages
    assert "qwen_generation:requirements" not in stages
    complete_stage = next(
        item for item in result["audit"]["debugTrace"]
        if item["stage"] == "qwen_generation:complete_jd"
    )
    assert complete_stage["executed"] is True
    assert complete_stage["sourceSections"] == [
        "responsibilities",
        "requirements",
        "qualifications",
    ]


def test_deployment_metadata_uses_supplied_build_values(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(
            config.settings,
            image_tag="v-test",
            pipeline_version="complete-jd-candidate-extraction-v2",
            git_commit_hash="abc1234",
        ),
    )

    metadata = config.deployment_metadata()
    assert metadata == {
        "imageTag": "v-test",
        "pipelineVersion": "complete-jd-candidate-extraction-v2",
        "gitCommitHash": "abc1234",
        "roleContextEnabled": True,
        "finalEvidenceSafetyEnabled": True,
    }
