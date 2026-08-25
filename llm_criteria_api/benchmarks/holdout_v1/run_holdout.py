"""Run the three locked holdout fixtures exactly once through production."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


HOLDOUT_ROOT = Path(__file__).resolve().parent
SERVICE_ROOT = HOLDOUT_ROOT.parents[1]
GOLD_ROOT = SERVICE_ROOT / "benchmarks" / "gold_standard_v1"
sys.path.insert(0, str(GOLD_ROOT))

from benchmark_schema import load_fixtures, request_body  # noqa: E402
from run_production_benchmark import (  # noqa: E402
    DEFAULT_ENDPOINT,
    make_run_record,
    post_json,
    utc_now,
    write_json,
)


def _contract_failures(
    record: dict[str, object],
    expected_image: str,
    expected_pipeline: str,
    expected_commit: str,
) -> list[str]:
    criteria = [
        item
        for item in record.get("criteria", [])
        if isinstance(item, dict)
    ]
    deployment = record.get("deployment", {})
    audit = record.get("audit", {})
    if not isinstance(deployment, dict):
        deployment = {}
    if not isinstance(audit, dict):
        audit = {}
    trace = audit.get("debugTrace", [])
    stages = {
        item.get("stage")
        for item in trace
        if isinstance(item, dict)
    }
    failures: list[str] = []
    if record.get("httpStatus") != 200:
        failures.append(f"httpStatus={record.get('httpStatus')}")
    if record.get("transportError"):
        failures.append(str(record["transportError"]))
    if record.get("responseSuccess") is False:
        failures.append("responseSuccess=false")
    if deployment.get("imageTag") != expected_image:
        failures.append(f"imageTag={deployment.get('imageTag')!r}")
    if deployment.get("pipelineVersion") != expected_pipeline:
        failures.append(
            f"pipelineVersion={deployment.get('pipelineVersion')!r}"
        )
    if deployment.get("gitCommitHash") != expected_commit:
        failures.append(
            f"gitCommitHash={deployment.get('gitCommitHash')!r}"
        )
    if deployment.get("roleContextEnabled") is not True:
        failures.append("roleContextEnabled is not true")
    if deployment.get("finalEvidenceSafetyEnabled") is not True:
        failures.append("finalEvidenceSafetyEnabled is not true")
    if not criteria:
        failures.append("criteria are empty")
    if sum(item.get("weight", 0) for item in criteria) != 100:
        failures.append("weights do not total 100")
    if any(not item.get("mergedFromIds") for item in criteria):
        failures.append("mergedFromIds missing or empty")
    if any(
        len(item.get("jdEvidence", [])) != len(item.get("sourceIds", []))
        or len(item.get("sourceIds", []))
        != len(item.get("groundingScores", []))
        for item in criteria
    ):
        failures.append("evidence/source/grounding metadata is misaligned")
    required_stages = {
        "qwen_generation:complete_jd",
        "final_evidence_safety",
        "lineage_restoration",
        "role_context_weighting",
        "api_payload_ready",
    }
    missing_stages = sorted(required_stages - stages)
    if missing_stages:
        failures.append(f"missing stages: {missing_stages}")
    if {
        "qwen_generation:responsibilities",
        "qwen_generation:requirements",
    } & stages:
        failures.append("legacy section generation stage is present")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=HOLDOUT_ROOT / "fixtures",
    )
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--expected-pipeline", required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()

    if args.results_dir.exists():
        raise SystemExit(
            f"Refusing to reuse holdout results directory: {args.results_dir}"
        )
    fixtures = load_fixtures(args.fixtures_dir)
    if len(fixtures) != 3:
        raise SystemExit(f"Holdout v1 requires exactly 3 fixtures, found {len(fixtures)}")

    started_at = utc_now()
    summaries: list[dict[str, object]] = []
    for fixture in fixtures:
        payload = request_body(fixture)
        request_started_at = utc_now()
        request_clock = time.perf_counter()
        status, response, error = post_json(
            args.endpoint,
            payload,
            args.timeout,
        )
        record = make_run_record(
            fixture,
            1,
            payload,
            request_started_at,
            utc_now(),
            int((time.perf_counter() - request_clock) * 1000),
            status,
            response,
            error,
        )
        output = (
            args.results_dir
            / "raw"
            / fixture["benchmarkId"]
            / "run-1.json"
        )
        write_json(output, record)
        failures = _contract_failures(
            record,
            args.expected_image,
            args.expected_pipeline,
            args.expected_commit,
        )
        criteria = [
            item
            for item in record.get("criteria", [])
            if isinstance(item, dict)
        ]
        summary: dict[str, object] = {
            "benchmarkId": fixture["benchmarkId"],
            "runNumber": 1,
            "httpStatus": status,
            "durationMs": record["durationMs"],
            "criteriaCount": len(criteria),
            "totalWeight": sum(item.get("weight", 0) for item in criteria),
            "deployment": record.get("deployment", {}),
            "failures": failures,
        }
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)

    run_summary = {
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "fixtureCount": len(fixtures),
        "attemptsPerFixture": 1,
        "totalRequestsAttempted": len(summaries),
        "contractPassCount": sum(
            not summary["failures"] for summary in summaries
        ),
        "runs": summaries,
    }
    write_json(args.results_dir / "run_summary.json", run_summary)
    return 1 if any(summary["failures"] for summary in summaries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
