import os

os.environ["MOCK_LLM"] = "true"

from app.config import settings
from app.model_loader import ModelLoader
from app.pipeline import CriteriaPipeline
from app.weighting import assign_default_weights


def test_weights_and_no_maximum_six_rejection():
    loader = ModelLoader(settings)
    loader.load()
    result = CriteriaPipeline(loader).generate({"jobTitle": "Planner", "department": "Operations", "responsibilities": [f"Manage planning task {number}." for number in range(8)], "requirements": []})
    assert result["weightTotal"] == 100
    assert result["criteria"]
    criteria = [
        {"type": "relevant_skill", "name": f"Capability {number}"}
        for number in range(7)
    ]
    assign_default_weights(criteria)
    assert len(criteria) == 7
    assert sum(item["suggestedWeight"] for item in criteria) == 100
