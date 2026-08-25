# E12 Frozen Holdout Human Review

Reviewed at `2026-08-08T20:00:38.3221359+08:00` against the human references
locked before the first request.

## Verdict

E12 is rejected as not yet generalisable.

Two roles meet the 80% core threshold, but Recruitment Executive has automated
core coverage of 50%, below the mandatory 60% catastrophic-failure floor. Data
Analyst also contains a bare generic `Team Activities` criterion. The three
holdouts and their original results are permanent evidence for every later
candidate.

## Frozen execution boundary

- runtime commit: `b509b57670d455d4d217b892bdfefa252e62f914`
- runtime tree: `fb15aea52134f755abb7b3fd6036a87465b9c471`
- image: `vkwk/llm-criteria-api:v1.0.11-e12`
- pipeline: `complete-jd-workflow-relations-e12`
- registry digest: `sha256:75ee7de2d332aba5831deb89a7653450ed14ec458c755156a87f7715a6639e69`
- requests: exactly one per locked fixture; 3/3 HTTP 200 and exact metadata
- weights and aligned evidence metadata: 3/3
- evaluator: unchanged evaluator-v2 with the locked holdout fixture directory

## Automated results

| Role | Core coverage | Expected recall | Semantic precision | Type accuracy | Safety |
|---|---:|---:|---:|---:|---|
| Data Analyst | 85.71% (6/7) | 90% | 90% | 100% | 0 split/merge/contamination/unexpected |
| Production Supervisor | 100% (8/8) | 100% | 100% | 100% | 0 split/merge/contamination/unexpected |
| Recruitment Executive | 50% (3/6) | 60% | 100% | 100% | 0 evaluator split/merge/contamination/unexpected |

Aggregate semantic precision was 96.67%, type accuracy was 100%, evidence
contamination was zero, and every output totalled 100 weight. Those strengths
do not override the Recruitment core floor.

## Human semantic and evidence review

### Data Analyst

- Six of seven central capabilities are independently represented with direct
  evidence: collection/validation, cleaning/transformation, dashboards,
  statistical analysis, analytical requirements, and Python automation.
- SQL querying and analytical dataset development are absent despite an
  explicit responsibility and required SQL statement.
- `Team Activities` is a bare generic criterion derived from the generic
  assigned-activities sentence. It should have been ignored.
- The remaining types are defensible and evidence arrays are clean and aligned.
  The extra Power BI/Tableau experience criterion is supported but redundant
  with the dashboard capability.

### Production Supervisor

- All eight central capabilities and all three supporting references are
  represented with direct source evidence.
- Quality and maintenance remain separate; education and experience remain
  separate; there is no destructive cross-domain merge or hallucinated item.
- `Standard Work Enforcement Safety` and `Shift Handover Issue` are awkward,
  but each still conveys a concrete, evidence-grounded capability rather than a
  bare generic label.
- Types, metadata, evidence alignment, and the 100-point weight total are
  defensible. This role passes.

### Recruitment Executive

- Vacancy/job-description work is represented.
- Candidate sourcing and screening were collapsed into one `Candidate
  Screening` criterion over R2 and R3. The name no longer represents sourcing,
  so the two independently assessable capabilities cannot both be credited.
- Interview coordination, offer preparation, and onboarding handoff were
  collapsed across R4, R5, and R8. This obscures separate selection and offer
  capabilities and omits the handoff focus from the name.
- Applicant tracking was recovered only from the preferred-tool requirement;
  the substantive R6 recruitment-pipeline and time-to-fill reporting work is
  absent. Employer branding/career-fair work from R7 is also absent.
- Education, recruitment experience, and Malaysian employment legislation are
  correctly typed and grounded, but they do not replace missing central work.

## Stage attribution and next candidate boundary

Recruitment primary generation returned five items and its one focused retry
returned six. Source accounting still reported R6 as misassigned and R7 as
unaccounted; multi-sentence grounding retained five responsibility criteria,
and explicit recovery added only requirement/qualification items. No later
stage deleted a valid standalone R6 or R7 criterion because neither existed.

Any repair must be E13 or later. It must remain generic and address all three
observed classes without weakening the frozen validator or the Gold gate:

1. recover substantive responsibility sources that remain absent or attached
   only to a name that does not express their capability;
2. reject or decompose multi-source umbrellas held together only by a generic
   shared object such as `candidate`;
3. ignore collaboration/other-assigned-activity boilerplate instead of turning
   it into a criterion.

E12 must not be retested against replacement holdouts. These exact fixtures and
results remain mandatory for all future candidates.
