# E14 Frozen Holdout Human Review

Reviewed at `2026-08-08T21:43:48.3924474+08:00` against the permanent human
references originally locked before the E12 request.

## Verdict

E14 passes the permanent holdout gate and is accepted for canonical release.

All three roles exceed the 80% core threshold, so the required two-of-three
gate passes and no role approaches the 60% catastrophic-failure floor. The
unchanged evaluator-v2 reports 100% core recall, semantic precision and type
accuracy, with no split, merge, contamination, unexpected, or generic-name
finding. Human review found no material hallucination, destructive merge, or
bare generic criterion.

These fixtures are permanent regressions after the original E12 evaluation;
they are not described as fresh unseen holdouts. E14 was frozen before this
official three-role run, and no production source, prompt, rule, image content,
or endpoint configuration changed between the freeze and these requests.

## Frozen execution boundary

- runtime commit: `f8ec1968e06bbb9101f4dc64f76bcc02684eb1f5`
- runtime tree: `3f3631129827bb9376bab0133e24db87268e3cdf`
- image: `vkwk/llm-criteria-api:v1.0.11-e14`
- pipeline: `complete-jd-normalised-grounding-e14`
- registry digest: `sha256:5a419b35da63689127c7ec68245bf688bd4dbdf023eb9ebb63520bb0be2085bc`
- RunPod release: #45
- requests: exactly one per locked fixture; 3/3 HTTP 200 and exact metadata
- weights and aligned evidence metadata: 3/3
- evaluator: unchanged evaluator-v2 with the locked holdout fixture directory

## Automated results

| Role | Core coverage | Expected recall | Semantic precision | Type accuracy | Safety |
|---|---:|---:|---:|---:|---|
| Data Analyst | 100% (7/7) | 100% | 100% | 100% | 0 split/merge/contamination/unexpected/generic |
| Production Supervisor | 100% (8/8) | 100% | 100% | 100% | 0 split/merge/contamination/unexpected/generic |
| Recruitment Executive | 100% (6/6) | 90% | 100% | 100% | 0 split/merge/contamination/unexpected/generic |

Aggregate core recall, semantic precision, criterion precision, and type
accuracy are 100%. Average expected recall is 96.67%; all outputs total 100
weight and pass metadata presence and alignment checks.

## Human semantic and evidence review

### Data Analyst

- All seven central capabilities are independently represented: data
  gathering/validation, cleaning/transformation, dashboards/reporting,
  statistical analysis, analytical requirements/recommendations, Python
  automation, and SQL querying/dataset construction.
- The E13 omission is resolved by `Sql Query Dataset`, grounded directly to the
  SQL-query and reusable-dataset responsibility; it is not inferred from a
  role title or qualification.
- Data dictionaries and access/confidentiality controls share one explicit
  source responsibility. Their combined criterion is supported and does not
  erase a separately assessable central capability.
- Experience, tool experience, and education remain separately typed and
  grounded. There is no assigned-activities boilerplate or hallucinated item.

### Production Supervisor

- All eight central capabilities and all three supporting references are
  represented with direct evidence.
- Quality/nonconformance and maintenance/breakdown work remain separate.
  Production scheduling, output monitoring, operator leadership, material
  flow/records, handover, and improvement work are independently assessable.
- `Standard Work Enforcement Safety` and `Shift Handover Issue` are stylistically
  awkward but concrete, source-supported, and non-misleading. Neither is a bare
  generic label.
- Types, evidence arrays, lineage metadata, and the 100-point weight total are
  defensible; there is no destructive cross-domain merge.

### Recruitment Executive

- Vacancy/job-description planning, candidate sourcing, candidate screening,
  interview coordination, offer/check work, and recruitment pipeline/ATS
  reporting are represented as distinct capabilities.
- The E12 sourcing/screening and interview/offer collapses are no longer
  present. `Recruitment Process` is grounded to ATS records plus pipeline and
  time-to-fill reporting, so it remains substantive despite its broad label.
- Education, recruitment experience, Malaysian employment legislation, and
  ATS/job-portal experience are separately typed and supported.
- Employer-branding/career-fair work is not emitted, which explains 90%
  expected rather than core recall; the locked human reference treats it as
  non-core. Its absence does not create a safety or catastrophic-coverage
  failure.

## Release decision

E14 satisfies the mandatory generalisation gate and the stronger quality bar:
three of three roles are at 100% core recall, no role is below 60%, semantic
precision and type accuracy are 100%, all structural and evidence-safety counts
are zero, and every response totals 100 weight. The next allowed runtime change
is packaging the same frozen source tree with the canonical Dockerfile under a
new immutable production tag, followed by a fresh-worker and end-to-end smoke
check.
