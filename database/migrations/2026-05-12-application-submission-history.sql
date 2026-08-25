USE uwc_hr_decision_support;

DROP TABLE IF EXISTS candidate_job_history;

CREATE TABLE IF NOT EXISTS application_submission_history (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT UNSIGNED NOT NULL,
  application_id INT UNSIGNED NOT NULL,
  job_id INT UNSIGNED NOT NULL,
  submission_no INT UNSIGNED NOT NULL,
  previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'rejected', 'filtered_out') NOT NULL,
  previous_eligibility_status ENUM('eligible', 'filtered_out', 'pending') NOT NULL,
  previous_score DECIMAL(5,2) NULL,
  previous_rank_no INT UNSIGNED NULL,
  previous_resume_file_name VARCHAR(255) NULL,
  previous_resume_url VARCHAR(500) NULL,
  previous_ai_summary TEXT NULL,
  original_submitted_at DATETIME NULL,
  recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_submission_history_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  CONSTRAINT fk_submission_history_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_submission_history_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  INDEX idx_submission_history_application (application_id, recorded_at)
) ENGINE=InnoDB;
