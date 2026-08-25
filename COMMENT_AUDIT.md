# Comment and UI Coverage Audit

## Scope

The audit covers production frontend UI and logic, PHP API/worker code, both Python services, database entry points, deployment entry points, and the user-visible candidate-analysis states. The goal was to explain behavior where a maintainer could otherwise misunderstand business rules, persistence boundaries, permissions, AI/parsing/scoring decisions, retries, fallback behavior, validation, or major UI state transitions.

Trivial JSX wrappers, simple getters, direct field mappings, and every SQL column are not padded with artificial comments. Their names and surrounding types/schema are already explanatory. Non-obvious behavior is documented close to the implementation and in the relevant README files.

## File-level coverage result

The final scan looked for an opening/module comment or documentation line in each production file:

| Area | Covered | Comment/doc lines | Notes |
|---|---:|---:|---|
| Frontend UI (`app/components`) | 95/95 | 857+ | Includes HR and candidate portal screens plus shared UI primitives. |
| Frontend app/lib | 13/13 | 61+ | Includes API, status, eligibility, pagination, date, JD parsing, and fallback helpers. |
| PHP production code | 15/15 | 157+ | Includes API, worker, helpers, persistence, auth, and deployment support. |
| Resume/JD parsing service | 28/28 | 201+ | Includes routers, schemas, parser, semantic, scoring, and criteria services. |
| Qwen/RunPod service | 27/28 | 347+ | The one exception is the protected frozen pipeline described below. |
| Database SQL | 4/47 | — | Migration filenames and `database/README.md` describe the ordered schema changes; inline comments are retained where the SQL itself needs them. |

The file-level scan is a coverage check, not a claim that every trivial function needs a comment. The focused review also checked the main UI flows and backend boundaries listed below.

## Functional/UI areas checked

- HR authentication, role-aware navigation, dashboard, job creation/editing, JD upload/extraction review, criteria weights, eligibility filters, application questions, links, and job lifecycle.
- Candidate portal registration/login, application submission, resume upload, employment form, duplicate submission handling, and candidate-facing status/error states.
- Candidate list/details, eligibility display, analysis processing/failure states, score fallback wording, score breakdown, ranking, shortlist/interview/reject workflow, email, notifications, and reports.
- PHP persistence before asynchronous analysis, stable application/document identifiers, queue claiming, stale-job recovery, retry behavior, HR read models, and workflow audit/notification effects.
- Parser validation and provenance, resume semantic extraction, JD criteria generation, eligibility separation from soft scoring, Qwen/RunPod fallback, and safety checks against unsupported evidence.
- Database schema relationships, scoring snapshots, submission history, analysis status, and deployment configuration entry points.

## Focused comment completion

Comments/docstrings were added or clarified in the key non-obvious paths, including:

- `server/api.php`, `server/helpers/application_analysis.php`, `server/helpers/resume_parser.php`, and `server/application_analysis_worker.php` for persistence/queue/retry/workflow boundaries.
- `parsing-service/app/` for health, parser/JD routes, scoring evidence/eligibility separation, semantic calls, and criteria generation.
- `llm_criteria_api/app/` and its RunPod entrypoint for runtime settings, model loading, pipeline contracts, and handler purpose.
- `app/components/candidates/CandidateList.tsx` and `NewCandidates.tsx` for eligibility and persisted analysis-state display.
- `app/lib/jdCriteriaFallback.ts` for remote-to-local criteria fallback behavior.

`llm_criteria_api/app/frozen_pipeline.py` is intentionally unchanged because the project treats it as a protected/frozen implementation. It is included in the delivery and called out as the only file-level comment exception.
