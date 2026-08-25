# Frozen JD Criteria API

This folder packages the frozen JD post-processing pipeline as two independent deployment surfaces:

- `app.main:app`: FastAPI, for local API testing.
- `runpod_handler.py`: RunPod Serverless worker, for CUDA inference.

It does not connect to React, PHP, a database, or the production rule-based criteria service. The frozen decision logic is contained in `app/frozen_pipeline.py` and is intentionally not changed by the deployment wrapper.

The live non-mock path uses `app/extraction_prompt.py` for one complete Job
Description extraction request. `app/extraction_schema.py` converts the
`candidateCriteria`/`importance` response into the frozen validator's internal
shape; grounding, validation, fallbacks, safe merging, evidence safety and
final weights remain Python-controlled. Mock and cached fixture loaders retain
the legacy path so frozen parity tests remain isolated from the live prompt.

## Local Mock Verification

```powershell
cd C:\HR System\llm_criteria_api
$env:MOCK_LLM='true'
python -m pytest -q tests\test_api.py tests\test_pipeline.py tests\test_runpod_handler.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`, then use `GET /health`, `GET /ready`, or `POST /api/jd/criteria/generate`. Mock mode never loads a model or requires a GPU.

## Environment Variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MODEL_NAME` | No | `Qwen/Qwen2.5-3B-Instruct` | Hugging Face model ID. |
| `HF_TOKEN` | For gated/private models | empty | Hugging Face access token. Configure it as a RunPod secret. |
| `MOCK_LLM` | No | `false` | Set `true` only for local/mock tests. |
| `DEVICE` | No | `cuda` | Inference device. Use `cuda` on RunPod. |
| `MAX_NEW_TOKENS` | No | `900` | Maximum generated tokens for the live model response. |
| `INFERENCE_TIMEOUT_SECONDS` | No | `180` | Worker response timeout. |
| `LOG_LEVEL` | No | `INFO` | Python logging level. Full JD text is not logged. |
| `DEBUG` | No | `false` | Enables debug-only schema warnings, including ignored model weight fields. |
| `HF_HOME` | No | `/runpod-volume/huggingface` | Optional persistent Hugging Face model cache. |

The deployment trace values are injected immutably at image build time. Pass
`APP_IMAGE_TAG`, `PIPELINE_VERSION`, and `GIT_COMMIT_HASH` as Docker build
arguments; the worker does not read the `.git` directory at runtime.

## Build The CUDA Image

The Docker image is based on CUDA 12.1 and installs the matching PyTorch wheel. It starts the RunPod worker by default.

```powershell
cd C:\HR System\llm_criteria_api
docker build `
  --build-arg APP_IMAGE_TAG=v1.0.7 `
  --build-arg PIPELINE_VERSION=complete-jd-candidate-extraction-v2 `
  --build-arg GIT_COMMIT_HASH=$(git rev-parse HEAD) `
  -t uwc-jd-criteria-runpod:v1.0.7 .
```

Test the built container without a GPU by enabling mock mode:

```powershell
docker run --rm -e MOCK_LLM=true uwc-jd-criteria-runpod:v1.0.7 `
  python -c "import json; from app.runpod_handler import handler; print(json.dumps(handler({'input': {'jobTitle': 'Process Engineer', 'department': 'Engineering', 'responsibilities': ['Analyse process data.'], 'requirements': ['A degree in Engineering is required.']}})))"
```

To run the HTTP API rather than the worker for a container-level API check, override the command:

```powershell
docker run --rm -p 8000:8000 -e MOCK_LLM=true uwc-jd-criteria-runpod:v1.0.7 `
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## RunPod Serverless Deployment

1. Build the image and push it to a registry RunPod can pull from, for example:

   ```powershell
   docker tag uwc-jd-criteria-runpod:v1.0.7 <registry-user>/uwc-jd-criteria-runpod:v1.0.7
   docker push <registry-user>/uwc-jd-criteria-runpod:v1.0.7
   ```

2. In RunPod, create a **Serverless Endpoint** using the pushed custom image. The image command already starts `runpod.serverless.start`; do not add a web-server command.
3. Select a CUDA GPU worker with enough VRAM for the configured model. Qwen2.5-3B uses 4-bit loading on CUDA and the tested 24 GB worker is suitable.
4. Add the environment variables above. Set `DEVICE=cuda`, `MOCK_LLM=false`, and set `HF_TOKEN` as a secret when required by the model. Attach a network volume mounted at `/runpod-volume` to retain Hugging Face downloads between worker starts.
5. Set the endpoint job timeout to at least `INFERENCE_TIMEOUT_SECONDS`, with a little extra time for transport. The handler returns `timeout` or `out_of_memory` responses without exposing JD text.
6. Deploy, then call the endpoint synchronous run URL provided by RunPod with the normal Serverless envelope below.

### Readiness Check

```json
{
  "input": {
    "action": "ready"
  }
}
```

Expected shape:

```json
{
  "status": "success",
  "requestId": "...",
  "output": {
    "status": "ok",
    "ready": true,
    "model": "Qwen/Qwen2.5-3B-Instruct",
    "mockMode": false
  }
}
```

### Generate Criteria

```json
{
  "input": {
    "jobTitle": "Process Engineer",
    "department": "Engineering",
    "responsibilities": [
      "Analyse process data to identify yield and cycle-time losses.",
      "Plan and conduct controlled process trials."
    ],
    "requirements": [
      "A degree in Engineering is required.",
      "Knowledge of statistical process control is required."
    ]
  }
}
```

### Resume Semantic Enrichment On The Same Endpoint

The worker also accepts a separate `resume_semantic_understanding` task. It
uses the same persistent `Qwen/Qwen2.5-3B-Instruct` model loader and CUDA
runtime, but bypasses `CriteriaPipeline` and returns only the narrow resume
semantic contract. The parsing service performs the final evidence grounding
and rejects unsupported claims.

```json
{
  "input": {
    "task": "resume_semantic_understanding",
    "resumeText": "Built React applications for internal users.",
    "sections": {
      "experience": "Built React applications for internal users."
    },
    "evidenceIndex": [
      {
        "sourceId": "experience-1",
        "sourceSection": "Work Experience",
        "sourceText": "Built React applications for internal users.",
        "sourceType": "resume"
      }
    ]
  }
}
```

Keep `MOCK_LLM=false` for this task. The existing JD criteria request shape
and pipeline remain unchanged.

The successful result is wrapped in `output` and contains the same frozen API payload:

```json
{
  "status": "success",
  "requestId": "...",
  "output": {
    "criteria": [{"criterionId": "criterion-1", "type": "relevant_skill", "name": "...", "sourceText": "...", "suggestedWeight": 20}],
    "ignoredTexts": [],
    "warnings": [],
    "weightTotal": 100,
    "model": "Qwen/Qwen2.5-3B-Instruct",
    "audit": {}
  }
}
```

## Exact Parity

`tests/fixtures/frozen_cached_outputs.json` contains five real cached Kaggle raw-output fixtures. The frozen runtime self-parity and local API exact fixture suite both passed 5/5 before this deployment packaging. Run the parity suite without loading a real model:

```powershell
$env:MOCK_LLM='false'
python -m pytest -q tests\test_parity_fixtures.py tests\test_literal_export.py
```
