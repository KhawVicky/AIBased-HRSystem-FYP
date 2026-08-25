import json

from app.resume_semantics import (
    ResumeSemanticRequest,
    build_resume_semantic_messages,
    generate_resume_semantics,
)


class FakeLoader:
    loaded = True

    def __init__(self, raw_output):
        self.raw_output = raw_output
        self.messages = None

    def generate(self, messages):
        self.messages = messages
        return self.raw_output


def _request() -> ResumeSemanticRequest:
    return ResumeSemanticRequest.model_validate(
        {
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
        }
    )


def test_resume_semantic_messages_are_evidence_scoped():
    messages = build_resume_semantic_messages(_request())

    assert messages[0]["role"] == "system"
    assert "sourceId" in messages[0]["content"]
    context = json.loads(messages[1]["content"])
    assert context["evidenceIndex"][0]["sourceId"] == "experience-1"
    assert "application-form" in messages[0]["content"]


def test_resume_semantic_loader_output_is_unwrapped_and_validated():
    loader = FakeLoader(
        """```json
        {"primaryDomain":"frontend engineering","primaryDomainSourceIds":["experience-1"]}
        ```"""
    )

    result = generate_resume_semantics(loader, _request())

    assert result["primaryDomain"] == "frontend engineering"
    assert result["primaryDomainSourceIds"] == ["experience-1"]
    assert loader.messages[0]["role"] == "system"


def test_resume_semantic_loader_accepts_model_prose_around_json():
    loader = FakeLoader(
        "Here is the requested JSON:\n"
        '{"primaryDomain":"frontend engineering","primaryDomainSourceIds":["experience-1"]}\n'
        "This is the complete result."
    )

    result = generate_resume_semantics(loader, _request())

    assert result["primaryDomain"] == "frontend engineering"
    assert result["primaryDomainSourceIds"] == ["experience-1"]
