# UWC Parsing Service

Standalone FastAPI service for extracting job description fields from `.xlsx`
workbooks and parsing normal text-layer PDF resumes into evidence-preserved
structured candidate profiles. The existing JD Excel route remains separate
from the resume-parsing route.

## Setup

```powershell
cd parsing-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

PowerShell users can run the virtual environment Python directly if script
execution policy blocks activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

Health check: `GET http://127.0.0.1:8001/health`

Interactive API documentation: `http://127.0.0.1:8001/docs`

The Create Job frontend uses `http://127.0.0.1:8001` by default. Override it
with `VITE_JD_PARSING_API_URL` when the service is hosted elsewhere. Local
frontend origins default to `http://localhost:5173` and
`http://127.0.0.1:5173`; set the comma-separated `JD_ALLOWED_ORIGINS`
environment variable to use different origins.

## API

List non-empty worksheets:

```bash
curl -X POST "http://127.0.0.1:8001/api/jd/excel/sheets" \
  -F "file=@Human Resources Job Description.xlsx"
```

Example response:

```json
{
  "success": true,
  "fileName": "Human Resources Job Description.xlsx",
  "totalSheets": 1,
  "sheets": [
    {
      "sheetName": "HR Manager",
      "jobTitle": "MANAGER",
      "department": "HUMAN RESOURCE"
    }
  ]
}
```

Extract one worksheet:

```bash
curl -X POST "http://127.0.0.1:8001/api/jd/excel/extract" \
  -F "file=@Human Resources Job Description.xlsx" \
  -F "sheet_name=HR Manager"
```

Example response:

```json
{
  "success": true,
  "data": {
    "sheetName": "HR Manager",
    "jobTitle": "MANAGER",
    "department": "HUMAN RESOURCE",
    "description": "Manage the Human Resource department.",
    "qualifications": ["Degree in Human Resources"],
    "responsibilities": ["Report to Section Head"],
    "requirements": ["Degree in Human Resources"],
    "rawText": "POSITION : MANAGER\nDEPARTMENT : HUMAN RESOURCE"
  },
  "warnings": []
}
```

Errors use a stable JSON shape and an appropriate HTTP status:

```json
{
  "success": false,
  "error": {
    "code": "SHEET_NOT_FOUND",
    "message": "The selected worksheet does not exist."
  }
}
```

## Test

```powershell
cd parsing-service
python -m pytest
```

## Resume parsing API

Parse a normal text-layer PDF resume:

```powershell
curl -X POST "http://127.0.0.1:8001/api/resume/parse" `
  -F "file=@alice-chen-resume.pdf" `
  -F 'application_data={"cgpa":3.92,"noticePeriod":"30 days"}'
```

The response contains preserved extracted text, detected sections, a
structured Candidate Profile, evidence records, a fixed Candidate Summary,
and stage diagnostics. `pypdf` is used for text extraction. OCR is
intentionally not enabled in `resume-parsing-v1`; image-only PDFs return a
clear extraction error.

When semantic understanding is configured, set
`RESUME_QWEN_ENDPOINT_URL` and optionally `RESUME_QWEN_API_KEY`,
`RESUME_QWEN_MODEL`, `RESUME_QWEN_PROTOCOL=openai_chat|runpod`, and
`RESUME_QWEN_TIMEOUT_SECONDS`. For the existing Qwen RunPod deployment, the
adapter also accepts `RUNPOD_CRITERIA_ENDPOINT_URL` and `RUNPOD_API_KEY` when
the resume-specific values are not set, and auto-selects the `runpod` protocol.
The resume task is a separate `resume_semantic_understanding` input branch in
the same worker; it does not call the JD criteria pipeline. Qwen receives
structured JSON and must reference evidence IDs. Python validates every
semantic item against resume evidence before it enters the profile, rejecting
unsupported labels or source references.

The PHP application API can call this route after storing an uploaded resume
when `RESUME_PARSING_API_URL` is configured. Parsed JSON is persisted in the
existing `resumes.parsed_profile_json` column and the deterministic summary is
copied to `applications.ai_summary`; a parser outage does not delete the
uploaded file.

The resume pipeline intentionally excludes OCR, free-form model summaries,
automatic hiring decisions, and frontend changes.

## Candidate scoring API

The backend-only scoring route is:

```powershell
curl -X POST "http://127.0.0.1:8001/api/scoring/candidate" `
  -H "Content-Type: application/json" `
  -d '{"jobId":7,"applicationId":9}'
```

It loads the active HR-saved criteria, eligibility filters, candidate fields,
and the latest persisted `resumes.parsed_profile_json` record from MySQL. It
does not open or reparse the uploaded PDF. The route returns a criterion-level
score breakdown, exact matched evidence IDs/text, eligibility reasons,
weighted total, ranking readiness, and scoring diagnostics.

Apply `database/migrations/2026-08-10-resume-parsed-profile.sql` and then
`database/migrations/2026-08-10-candidate-scoring.sql` before enabling the
route. Apply them against the active connection database (the Railway database
is named `railway`); the migrations do not select a local database name. The
scoring service uses the same database variable names as the PHP
application: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` (with
the existing `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and
`MYSQLDATABASE` fallbacks). Live semantic scoring reuses
`RUNPOD_CRITERIA_ENDPOINT_URL` and `RUNPOD_API_KEY`; optional
`CANDIDATE_QWEN_*` variables can override those values. No semantic fallback is
used when the shared Qwen endpoint is unavailable.

The PHP candidate submission endpoint orchestrates the persisted flow after
the application and resume are saved. Configure `RESUME_PARSING_API_URL` on
the PHP service and optionally `CANDIDATE_SCORING_API_URL`; when the latter is
omitted, the PHP integration derives `/api/scoring/candidate` from the parser
URL. `RESUME_REQUIRE_SEMANTIC=true` is the production default so the
application path requests live Qwen semantic enrichment. Parser/scoring
failures update the application analysis status without deleting the saved
application or resume. `POST /api.php?route=applications/{id}/analysis/retry`
retries the stored resume flow without creating a new application or resume;
send `{"stage":"score"}` to retry scoring only.

For Railway production, deploy this directory with `--path-as-root` so the
service Dockerfile and application files are included. The current project
uses `https://parsing-service-production-27f2.up.railway.app` and the existing
RunPod endpoint `4yu1obnahx02lz`; the endpoint URL and API key are injected as
secrets and are not part of the frontend configuration.
