"""Run the six Gold Standard JDs through the production PHP proxy.

The runner uses the exact request shape sent by the React client. It never
calls local port 8001/8002 and it stores only safe response fields plus a
request hash. There is deliberately no automatic retry: a failed attempt is
kept as a failed attempt, as required by the baseline protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark_schema import load_fixtures, request_body


DEFAULT_ENDPOINT = "https://hr-api-production-b5d3.up.railway.app/api.php?route=jd-criteria-llm"
EXPECTED_PIPELINE_VERSION = "complete-jd-candidate-extraction-v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def post_json(endpoint: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any] | None, str | None]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return response.status, None, "Production response was not valid JSON."
            return response.status, parsed if isinstance(parsed, dict) else None, None
    except urllib.error.HTTPError as error:
        try:
            raw = error.read()
            parsed = json.loads(raw.decode("utf-8"))
            return error.code, parsed if isinstance(parsed, dict) else None, None
        except (OSError, json.JSONDecodeError):
            return error.code, None, f"HTTP {error.code} from production endpoint."
    except urllib.error.URLError as error:
        return 0, None, f"Transport error: {error.reason}"
    except TimeoutError:
        return 0, None, "Production request timed out."


def safe_extract_response(response: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"criteria": [], "eligibilitySuggestions": {}, "warnings": [], "audit": {}}
    data = response.get("data")
    if not isinstance(data, dict):
        output = response.get("output")
        data = output if isinstance(output, dict) else {}
    criteria = data.get("criteria")
    return {
        "criteria": criteria if isinstance(criteria, list) else [],
        "eligibilitySuggestions": data.get("eligibilitySuggestions") if isinstance(data.get("eligibilitySuggestions"), dict) else {},
        "warnings": response.get("warnings") if isinstance(response.get("warnings"), list) else [],
        "audit": data.get("audit") if isinstance(data.get("audit"), dict) else {},
    }


def make_run_record(
    fixture: dict[str, Any],
    run_number: int,
    request_payload: dict[str, Any],
    started: str,
    finished: str,
    duration_ms: int,
    status: int,
    response: dict[str, Any] | None,
    transport_error: str | None,
) -> dict[str, Any]:
    safe = safe_extract_response(response)
    deployment = safe["audit"].get("deployment", {}) if isinstance(safe["audit"], dict) else {}
    return {
        "benchmarkId": fixture["benchmarkId"],
        "runNumber": run_number,
        "requestTimestamp": started,
        "responseTimestamp": finished,
        "durationMs": duration_ms,
        "httpStatus": status,
        "requestBodyHash": hashlib.sha256(
            json.dumps(request_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "deployment": deployment if isinstance(deployment, dict) else {},
        "criteria": safe["criteria"],
        "eligibilitySuggestions": safe["eligibilitySuggestions"],
        "warnings": safe["warnings"],
        "audit": safe["audit"],
        "transportError": transport_error,
        "responseError": response.get("error") if isinstance(response, dict) else None,
        "responseSuccess": response.get("success") if isinstance(response, dict) else None,
    }


def smoke_gate(record: dict[str, Any]) -> list[str]:
    failures = []
    deployment = record.get("deployment", {})
    trace = record.get("audit", {}).get("debugTrace", [])
    stages = [item.get("stage") for item in trace if isinstance(item, dict)]
    if record.get("httpStatus") != 200:
        failures.append(f"HTTP status is {record.get('httpStatus')}")
    if record.get("transportError"):
        failures.append(str(record["transportError"]))
    if deployment.get("pipelineVersion") != EXPECTED_PIPELINE_VERSION:
        failures.append(f"pipelineVersion={deployment.get('pipelineVersion')!r}")
    if not deployment.get("imageTag"):
        failures.append("imageTag is missing")
    if deployment.get("gitCommitHash") in {None, "", "unknown", "local-build"}:
        failures.append(f"gitCommitHash={deployment.get('gitCommitHash')!r}")
    if "qwen_generation:complete_jd" not in stages:
        failures.append("qwen_generation:complete_jd is missing")
    if "qwen_generation:responsibilities" in stages or "qwen_generation:requirements" in stages:
        failures.append("legacy section extraction stage is present")
    if sum(item.get("weight", 0) for item in record.get("criteria", []) if isinstance(item, dict)) != 100:
        failures.append("criterion weights do not total 100")
    return failures


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run_benchmark(endpoint: str, fixtures_dir: Path, results_dir: Path, timeout: int, runs: int) -> dict[str, Any]:
    fixtures = load_fixtures(fixtures_dir)
    fixtures.sort(
        key=lambda fixture: (
            0 if fixture["benchmarkId"] == "hr-manager-001" else 1,
            fixture["benchmarkId"],
        )
    )
    attempted = 0
    successful = 0
    failed = 0
    aborted = False
    abort_reason: list[str] = []
    for fixture in fixtures:
        payload = request_body(fixture)
        fixture_dir = results_dir / "raw" / fixture["benchmarkId"]
        for run_number in range(1, runs + 1):
            attempted += 1
            started_at = utc_now()
            started_clock = time.perf_counter()
            # The PHP proxy accepts the same raw JSON body as the React client.
            # It adds the RunPod {"input": ...} envelope on the server side.
            status, response, error = post_json(endpoint, payload, timeout)
            duration_ms = int((time.perf_counter() - started_clock) * 1000)
            finished_at = utc_now()
            record = make_run_record(
                fixture,
                run_number,
                payload,
                started_at,
                finished_at,
                duration_ms,
                status,
                response,
                error,
            )
            if status == 200 and not error and record["responseSuccess"] is not False:
                successful += 1
            else:
                failed += 1
            write_json(fixture_dir / f"run-{run_number}.json", record)
            if attempted == 1:
                gate_failures = smoke_gate(record)
                if gate_failures:
                    aborted = True
                    abort_reason = gate_failures
                    print("BENCHMARK_GATE_FAILED")
                    for failure in gate_failures:
                        print(f"- {failure}")
                    break
            print(json.dumps({
                "benchmarkId": fixture["benchmarkId"],
                "runNumber": run_number,
                "httpStatus": status,
                "durationMs": duration_ms,
                "criteriaCount": len(record["criteria"]),
                "deployment": record["deployment"],
                "transportError": error,
            }, ensure_ascii=False))
        if aborted:
            break
    summary = {
        "endpoint": endpoint,
        "fixtureCount": len(fixtures),
        "runsPerFixture": runs,
        "totalRequestsAttempted": attempted,
        "successfulRequests": successful,
        "failedRequests": failed,
        "aborted": aborted,
        "abortReason": abort_reason,
        "runDate": utc_now(),
    }
    write_json(results_dir / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=os.getenv("GOLD_BENCHMARK_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--fixtures-dir", type=Path, default=Path(__file__).parent / "fixtures")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=int(os.getenv("GOLD_BENCHMARK_TIMEOUT", "300")))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()

    fixtures = load_fixtures(args.fixtures_dir)
    if args.smoke_only:
        smoke_fixture = next(
            (fixture for fixture in fixtures if fixture["benchmarkId"] == "hr-manager-001"),
            fixtures[0],
        )
        payload = request_body(smoke_fixture)
        started = time.perf_counter()
        status, response, error = post_json(args.endpoint, payload, args.timeout)
        record = make_run_record(smoke_fixture, 0, payload, utc_now(), utc_now(), int((time.perf_counter() - started) * 1000), status, response, error)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        failures = smoke_gate(record)
        if failures:
            print("SMOKE_GATE_FAILED")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("SMOKE_GATE_PASSED")
        return 0

    if args.runs != 3:
        raise SystemExit("Gold Standard v1 requires exactly three runs per fixture.")
    summary = run_benchmark(args.endpoint, args.fixtures_dir, args.results_dir, args.timeout, args.runs)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failedRequests"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
