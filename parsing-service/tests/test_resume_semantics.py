import json

from app.schemas.resume import EvidenceRecord
from app.services import resume_semantics
from app.services.resume_semantics import QwenResumeSemanticClient, configured_resume_semantic_client


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _evidence() -> list[EvidenceRecord]:
    return [
        EvidenceRecord(
            sourceId="experience-1",
            sourceSection="Work Experience",
            sourceText="Built React applications for internal users.",
        )
    ]


def test_openai_qwen_response_is_unwrapped_and_validated(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"primaryDomain":"frontend engineering"}\n```'
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(resume_semantics, "urlopen", fake_urlopen)
    client = QwenResumeSemanticClient(
        "https://qwen.example.test/v1/chat/completions",
        api_key="secret",
        model="Qwen/Qwen2.5-3B-Instruct",
    )

    result = client.understand(
        resume_text="Built React applications.",
        sections={"experience": "Built React applications."},
        evidence_index=_evidence(),
    )

    request_payload = json.loads(captured["request"].data.decode("utf-8"))
    assert request_payload["model"] == "Qwen/Qwen2.5-3B-Instruct"
    assert request_payload["temperature"] == 0
    assert request_payload["response_format"] == {"type": "json_object"}
    assert request_payload["messages"][0]["role"] == "system"
    assert result.primaryDomain == "frontend engineering"
    assert captured["timeout"] == 90.0


def test_runpod_qwen_response_uses_input_envelope(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return _Response({"output": {"primaryDomain": "frontend engineering"}})

    monkeypatch.setattr(resume_semantics, "urlopen", fake_urlopen)
    client = QwenResumeSemanticClient("https://runpod.example.test", protocol="runpod")

    result = client.understand(
        resume_text="Built React applications.",
        sections={"experience": "Built React applications."},
        evidence_index=_evidence(),
    )

    request_payload = json.loads(captured["request"].data.decode("utf-8"))
    assert request_payload["input"]["task"] == "resume_semantic_understanding"
    assert request_payload["input"]["evidenceIndex"][0]["sourceId"] == "experience-1"
    assert result.primaryDomain == "frontend engineering"


def test_qwen_response_accepts_model_prose_around_json(monkeypatch):
    def fake_urlopen(request, timeout):
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "Here is the requested JSON:\n"
                                '{"primaryDomain":"frontend engineering"}\n'
                                "This is the complete result."
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(resume_semantics, "urlopen", fake_urlopen)
    client = QwenResumeSemanticClient("https://qwen.example.test/v1/chat/completions")

    result = client.understand(
        resume_text="Built React applications.",
        sections={"experience": "Built React applications."},
        evidence_index=_evidence(),
    )

    assert result.primaryDomain == "frontend engineering"


def test_configured_client_reuses_existing_runpod_environment(monkeypatch):
    monkeypatch.delenv("RESUME_QWEN_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("RESUME_QWEN_API_KEY", raising=False)
    monkeypatch.delenv("RESUME_QWEN_PROTOCOL", raising=False)
    monkeypatch.delenv("RESUME_QWEN_MODEL", raising=False)
    monkeypatch.setenv(
        "RUNPOD_CRITERIA_ENDPOINT_URL",
        "https://api.runpod.ai/v2/shared-endpoint/runsync",
    )
    monkeypatch.setenv("RUNPOD_API_KEY", "shared-key")
    monkeypatch.setenv("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")

    client = configured_resume_semantic_client()

    assert client is not None
    assert client.endpoint_url.endswith("/runsync")
    assert client.api_key == "shared-key"
    assert client.protocol == "runpod"
    assert client.model == "Qwen/Qwen2.5-3B-Instruct"
