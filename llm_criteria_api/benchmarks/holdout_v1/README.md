# Frozen Candidate Holdout v1

These three cross-domain holdouts were created only after E12 was frozen at
`2026-08-08T19:35:30.0583280+08:00`.

Frozen candidate boundary:

- runtime commit: `b509b57670d455d4d217b892bdfefa252e62f914`
- runtime tree: `fb15aea52134f755abb7b3fd6036a87465b9c471`
- image: `vkwk/llm-criteria-api:v1.0.11-e12`
- pipeline: `complete-jd-workflow-relations-e12`
- registry digest: `sha256:75ee7de2d332aba5831deb89a7653450ed14ec458c755156a87f7715a6639e69`
- freeze record: `llm_criteria_api/diagnostics/goal-20260808-e12-candidate-freeze.json`

The JDs and human reference criteria in `fixtures/` are locked before the
first holdout request. Each role is sent exactly once through the production
Railway -> PHP -> RunPod chain. The unchanged Gold Standard evaluator-v2 is
used with `--fixtures-dir benchmarks/holdout_v1/fixtures`, followed by a
human-readable semantic and evidence review.

Success requires at least two roles at or above 80% core coverage, no role
below 60%, zero evidence contamination, and no material hallucination,
destructive cross-domain merge, bare generic name, indefensible type, or
misaligned evidence. Every response must total 100 weight.
