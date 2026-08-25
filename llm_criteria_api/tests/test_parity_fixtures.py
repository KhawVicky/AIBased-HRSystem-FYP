"""Exact-output parity harness for exported frozen notebook fixtures.

The fixture file deliberately contains no invented model responses. Populate it
only through the frozen notebook's cache export before enabling this test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import frozen_pipeline


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "frozen_cached_outputs.json"


def exact_snapshot(result: dict) -> dict:
    return {
        "criteria": result["criteria"],
        "ignoredTexts": result["ignoredTexts"],
        "warnings": result["warnings"],
        "weightTotal": result["weightTotal"],
        "audit": result["audit"],
    }


def run_frozen_pipeline(fixture: dict) -> dict:
    """Run only the original frozen entrypoint against cached model strings."""

    # The production adapter injects these globals at runtime. Keep the
    # parity harness isolated when it is run as a standalone test process.
    original_model = getattr(frozen_pipeline, "model", None)
    original_tokenizer = getattr(frozen_pipeline, "tokenizer", None)
    original_generator = frozen_pipeline.generate_model_output
    cached_outputs = iter(fixture["rawModelOutputs"])

    def cached_generator(_messages: list[dict[str, str]]) -> str:
        return next(cached_outputs)

    frozen_pipeline.model = None
    frozen_pipeline.tokenizer = None
    frozen_pipeline.generate_model_output = cached_generator
    try:
        outputs, diagnostics = frozen_pipeline.extract_soft_criteria_llm(
            [fixture["input"]]
        )
    finally:
        frozen_pipeline.model = original_model
        frozen_pipeline.tokenizer = original_tokenizer
        frozen_pipeline.generate_model_output = original_generator

    output = outputs[0]
    diagnostic = diagnostics[0]
    return {
        "criteria": output["softCriteria"],
        "ignoredTexts": output["ignoredTexts"],
        "warnings": diagnostic["warnings"],
        "weightTotal": sum(
            item["suggestedWeight"] for item in output["softCriteria"]
        ),
        "audit": {
            "fallbackRecoveries": output["fallbackRecoveries"],
            "rejectedCriteria": [
                issue
                for section in diagnostic["sectionDiagnostics"].values()
                for issue in section.get("fatalErrors", [])
            ],
            "sectionDiagnostics": diagnostic["sectionDiagnostics"],
            "consolidation": output["consolidationDiagnostics"],
        },
    }


def test_frozen_cached_output_parity():
    fixture_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    pending = [item["caseId"] for item in fixture_data if not item.get("rawModelOutputs")]
    if pending:
        pytest.skip(
            "Frozen raw-output export is pending for: " + ", ".join(pending)
        )

    for fixture in fixture_data:
        result = run_frozen_pipeline(fixture)
        assert result == fixture["expectedFinalOutput"], fixture["caseId"]
