USE uwc_hr_decision_support;

ALTER TABLE score_breakdowns
  ADD COLUMN IF NOT EXISTS application_id INT UNSIGNED NULL AFTER id;

UPDATE score_breakdowns sb
JOIN candidate_scores cs ON cs.id = sb.candidate_score_id
SET sb.application_id = cs.application_id
WHERE sb.application_id IS NULL;

ALTER TABLE score_breakdowns
  DROP FOREIGN KEY fk_score_breakdowns_score;

ALTER TABLE score_breakdowns
  DROP INDEX uq_score_breakdowns_score_criteria;

ALTER TABLE score_breakdowns
  MODIFY application_id INT UNSIGNED NOT NULL,
  DROP COLUMN candidate_score_id,
  ADD CONSTRAINT fk_score_breakdowns_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  ADD UNIQUE KEY uq_score_breakdowns_application_criteria (application_id, criteria_id);

DROP TABLE IF EXISTS candidate_scores;
