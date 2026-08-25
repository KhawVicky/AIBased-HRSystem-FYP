# Gold Standard v1

This is a production baseline for the current complete-JD criteria pipeline.
It does not change the extraction prompt, criteria rules, grounding, validation,
consolidation, evidence safety, role-context weighting, or eligibility logic.

The six fixture files are the exact benchmark JDs and human reference
definitions supplied for this baseline. The runner sends each request three
times through the production chain:

```text
runner -> Railway HR API -> PHP RunPod proxy -> RunPod criteria worker
```

It does not call local ports 8001 or 8002 and does not retry failed requests.
Each raw run stores safe response fields, a request-body hash, deployment
metadata, timing, and transport status. Raw Qwen output, secrets, and a full
request body are not stored.

## Validate fixtures

From `llm_criteria_api`:

```powershell
python -c "from pathlib import Path; from benchmarks.gold_standard_v1.benchmark_schema import load_fixtures; print(len(load_fixtures(Path('benchmarks/gold_standard_v1/fixtures'))))"
```

## Smoke test

Run this only after the new image is deployed and the endpoint has a fresh
worker:

```powershell
python benchmarks/gold_standard_v1/run_production_benchmark.py `
  --smoke-only `
  --results-dir benchmarks/gold_standard_v1/results/smoke
```

The gate requires HTTP 200, the expected pipeline version, a non-placeholder
Git hash, total weight 100, `qwen_generation:complete_jd`, no legacy section
stages, and both enhanced deployment flags.

## Run 6 x 3 baseline

Use a timestamped local result directory. The endpoint can be overridden with
`GOLD_BENCHMARK_ENDPOINT`; the default is the production PHP route.

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
python benchmarks/gold_standard_v1/run_production_benchmark.py `
  --results-dir "benchmarks/gold_standard_v1/results/$stamp"
```

The command attempts exactly 18 requests. A failed request is saved and is not
silently replaced by a retry.

## Evaluate

```powershell
python benchmarks/gold_standard_v1/evaluate_results.py `
  --results-dir "benchmarks/gold_standard_v1/results/$stamp"
```

The evaluator is deterministic. It matches names, types, evidence topics,
source IDs, forbidden topics, weights, metadata alignment, and pipeline trace.
Exact target weights are not required; the fixture ranges are secondary to
criterion correctness and evidence cleanliness.

Production response artifacts under `results/` are ignored by Git. Fixtures,
the runner, evaluator, schema, and this README are the reviewable benchmark
definition.
