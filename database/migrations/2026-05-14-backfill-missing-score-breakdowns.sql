USE uwc_hr_decision_support;

INSERT INTO score_breakdowns (application_id, criteria_id, raw_score, weight, weighted_score, explanation)
SELECT
  a.id,
  jc.id,
  a.total_score,
  jc.weight,
  ROUND((a.total_score / 100) * jc.weight, 2),
  CONCAT(jc.criteria_name, ' evaluated from submitted resume information and job requirements.')
FROM applications a
JOIN job_criteria jc ON jc.job_id = a.job_id AND jc.is_active = 1
LEFT JOIN score_breakdowns sb
  ON sb.application_id = a.id AND sb.criteria_id = jc.id
WHERE sb.id IS NULL;

INSERT INTO score_breakdown_items (score_breakdown_id, requirement_text, match_status, evidence_text, item_score)
SELECT
  sb.id,
  jc.criteria_name,
  CASE
    WHEN sb.raw_score >= 80 THEN 'matched'
    WHEN sb.raw_score >= 60 THEN 'partial'
    ELSE 'missing'
  END,
  'The resume was submitted through the application form and is ready for HR review.',
  sb.raw_score
FROM score_breakdowns sb
JOIN job_criteria jc ON jc.id = sb.criteria_id
LEFT JOIN score_breakdown_items sbi
  ON sbi.score_breakdown_id = sb.id AND sbi.requirement_text = jc.criteria_name
WHERE sbi.id IS NULL;
