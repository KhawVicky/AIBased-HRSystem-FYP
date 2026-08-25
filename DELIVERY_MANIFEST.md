# Delivery Manifest

Package name: `HR-System-Source-Delivery-2026-08-25.zip`

This manifest describes the contents of this folder and the matching ZIP. Paths are relative to the delivery root.

## Included

```text
README.md
package.json
package-lock.json
index.html
tsconfig.json
tsconfig.app.json
tsconfig.node.json
vite.config.ts
.dockerignore
.gitignore
.railwayignore
app/
styles/
public/
server/.dockerignore
server/.env.local.example
server/mail-config.example.php
server/api.php
server/application_analysis_worker.php
server/bootstrap.php
server/Dockerfile
server/entrypoint.sh
server/helpers/
server/mock-files/job-description.xlsx
server/tests/
parsing-service/.dockerignore
parsing-service/Dockerfile
parsing-service/README.md
parsing-service/pytest.ini
parsing-service/requirements.txt
parsing-service/app/
parsing-service/tests/
llm_criteria_api/.dockerignore
llm_criteria_api/.env.example
llm_criteria_api/Dockerfile
llm_criteria_api/PARITY_AUDIT.md
llm_criteria_api/README.md
llm_criteria_api/kaggle_frozen_pipeline_manifest.json
llm_criteria_api/requirements.txt
llm_criteria_api/runpod_handler.py
llm_criteria_api/app/
llm_criteria_api/benchmarks/gold_standard_v1/
llm_criteria_api/benchmarks/holdout_v1/
llm_criteria_api/tests/
database/README.md
database/schema.sql
database/seed-demo.sql
database/seed-more.sql
database/migrations/
deploy/railway/
tools/test_jd_criteria_fallback.mjs
tools/candidates_real_data.test.mjs
DELIVERY_README.md
COMMENT_AUDIT.md
DELIVERY_MANIFEST.md
```

The parser regression PDFs and model/parser JSON fixtures remain because the supplied tests reference them. They are test fixtures, not runtime upload storage.

## Explicitly excluded

- `.env.local`, local mail configuration, real `server/uploads/`, and all runtime logs/errors.
- `node_modules/`, `dist/`, Python virtual environments, `__pycache__/`, pytest cache directories, and other generated caches.
- Generated benchmark/test results and diagnostics.
- `experiments/`, `imports/`, `jd_criteria_service/`, unused historical tooling, and internal planning/project-memory files.
- `.git/`, `.agents/`, `.codex/`, `.planning/`, and workspace scratch files.
- The pre-existing `deliverables/` PowerPoint files and assets; they are preserved in the workspace but are not nested into this source package.
- `src/`, because the active TypeScript configuration includes `app/` and `styles/` and the production Vite build does not reference `src/`.

## Verification record

- Frontend production build: passed.
- JD criteria fallback contract: passed (5/5 cases).
- Candidate real-data integration contract: passed.
- PHP deployment configuration and application-analysis contracts: passed.
- PHP qualification and RunPod response-mapping contracts: passed.
- Python bytecode compilation for both services: passed.
- ZIP verification: the final response supplies the generated archive path and SHA-256 hash after the archive is created.
