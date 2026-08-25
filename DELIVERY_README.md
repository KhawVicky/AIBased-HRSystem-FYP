# UWC HR Decision Support System — Source Delivery

This folder is the clean source handoff for the UWC HR Decision Support System. It contains the web UI, PHP API, parser service, optional Qwen/RunPod service, database schema and migrations, Railway deployment files, focused contract tests, and the comments audit.

## Included runtime pieces

- React + TypeScript + Vite frontend under `app/`, `styles/`, and `public/`.
- PHP API and asynchronous application-analysis worker under `server/`.
- FastAPI resume/JD parsing and scoring service under `parsing-service/`.
- Optional criteria/scoring model service under `llm_criteria_api/`.
- MySQL/MariaDB schema, seed data, and ordered migrations under `database/`.
- Railway service definitions under `deploy/railway/`.

## Local setup outline

1. Install Node.js and run `npm ci` at the package root.
2. Import `database/schema.sql`, then apply the files in `database/migrations/` in filename order. Use the seed files only for a demo environment.
3. Copy `server/.env.local.example` to the runtime API environment and fill in local values. Copy `server/mail-config.example.php` only when email is required. Never commit local secrets.
4. Start the PHP API through XAMPP/Apache or the supplied Docker/Railway configuration.
5. Install the Python dependencies listed in each service's `requirements.txt` and start `parsing-service` when resume/JD parsing is needed.
6. Configure and start `llm_criteria_api` only when the remote/local model path is enabled; the frontend/API retain the documented fallback behavior.
7. Run `npm run build` for the production frontend build.

The existing root `README.md` and service READMEs contain the detailed environment variables, route notes, Docker commands, and deployment-specific instructions.

## Verification commands used for this delivery

- `npm run build`
- `npm run test:jd-criteria-fallback`
- `npm run test:candidates`
- `npm run test:deployment-config`
- PHP application-analysis and scoring contract tests under `server/tests/`
- `python -m compileall -q parsing-service\\app llm_criteria_api\\app`

The exact result is recorded in `DELIVERY_MANIFEST.md`.

## Important exclusions

Local secrets, real runtime uploads, logs, build output, dependency folders, Python environments/caches, generated benchmark results, experiments, internal planning files, and the pre-existing presentation deliverables are intentionally excluded. The original workspace contents remain in place outside this delivery folder.
