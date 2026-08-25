ALTER TABLE applications
  ADD COLUMN scoring_version VARCHAR(80) NULL AFTER rank_no,
  ADD COLUMN scored_at DATETIME NULL AFTER scoring_version,
  ADD COLUMN eligibility_reasons_json TEXT NULL AFTER scored_at,
  ADD COLUMN scoring_diagnostics_json LONGTEXT NULL AFTER eligibility_reasons_json,
  ADD COLUMN criteria_snapshot_json LONGTEXT NULL AFTER scoring_diagnostics_json;

ALTER TABLE score_breakdowns
  ADD COLUMN semantic_score DECIMAL(4,2) NULL AFTER raw_score,
  ADD COLUMN criterion_type VARCHAR(80) NULL AFTER explanation,
  ADD COLUMN criterion_name_snapshot VARCHAR(255) NULL AFTER criterion_type,
  ADD COLUMN jd_evidence_json TEXT NULL AFTER criterion_name_snapshot,
  ADD COLUMN matched_resume_evidence_json LONGTEXT NULL AFTER jd_evidence_json,
  ADD COLUMN evidence_ids_json TEXT NULL AFTER matched_resume_evidence_json,
  ADD COLUMN grounded TINYINT(1) NOT NULL DEFAULT 0 AFTER evidence_ids_json,
  ADD COLUMN scoring_version VARCHAR(80) NULL AFTER grounded,
  ADD COLUMN qwen_status VARCHAR(40) NULL AFTER scoring_version,
  ADD COLUMN scored_at DATETIME NULL AFTER qwen_status;

CREATE TABLE IF NOT EXISTS candidate_scoring_runs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  job_id INT UNSIGNED NOT NULL,
  candidate_id INT UNSIGNED NOT NULL,
  scoring_version VARCHAR(80) NOT NULL,
  criteria_snapshot_hash CHAR(64) NOT NULL,
  profile_snapshot_hash CHAR(64) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  qwen_status VARCHAR(40) NOT NULL,
  qwen_used TINYINT(1) NOT NULL DEFAULT 0,
  fallback_used TINYINT(1) NOT NULL DEFAULT 0,
  total_weight DECIMAL(5,2) NOT NULL,
  overall_score DECIMAL(5,2) NOT NULL,
  diagnostics_json LONGTEXT NOT NULL,
  response_json LONGTEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_candidate_scoring_runs_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_candidate_scoring_runs_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_candidate_scoring_runs_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  INDEX idx_candidate_scoring_runs_application (application_id, created_at),
  INDEX idx_candidate_scoring_runs_request (application_id, request_hash),
  INDEX idx_candidate_scoring_runs_job (job_id, created_at)
) ENGINE=InnoDB;
