import os

os.environ["MOCK_LLM"] = "true"

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_ready():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        ready = client.get("/ready").json()
        assert ready["ready"] is True
        assert ready["mockMode"] is True


def test_generation_and_empty_input():
    with TestClient(app) as client:
        response = client.post("/api/jd/criteria/generate", json={"jobTitle": "Process Engineer", "department": "Engineering", "responsibilities": ["Analyse process data."], "requirements": ["A degree in Engineering is required."]})
        assert response.status_code == 200
        payload = response.json()
        assert payload["weightTotal"] == 100
        assert payload["criteria"]
        invalid = client.post("/api/jd/criteria/generate", json={"jobTitle": "A", "department": "B", "responsibilities": [], "requirements": []})
        assert invalid.status_code == 400
