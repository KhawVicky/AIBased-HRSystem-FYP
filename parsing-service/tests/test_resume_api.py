from fastapi.testclient import TestClient

from app.main import app
from tests.test_resume_pdf import make_text_pdf


def test_resume_parse_endpoint_returns_profile_and_diagnostics():
    client = TestClient(app)
    response = client.post(
        "/api/resume/parse",
        files={
            "file": (
                "resume.pdf",
                make_text_pdf(
                    [
                        "Alice Chen",
                        "alice.chen@example.com",
                        "Work Experience",
                        "Developer | ABC Sdn Bhd",
                        "2020 - Present",
                        "- Built React applications.",
                    ]
                ),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["profile"]["personalInfo"]["name"] == "Alice Chen"
    assert payload["data"]["diagnostics"]["extractionMethod"] == "pypdf_text"
    assert payload["data"]["diagnostics"]["qwenStatus"] == "skipped_no_endpoint"
    assert payload["data"]["profile"]["candidateSummary"]
