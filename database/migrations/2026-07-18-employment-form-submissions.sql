CREATE TABLE IF NOT EXISTS employment_form_submissions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  candidate_id INT UNSIGNED NULL,
  candidate_email VARCHAR(180) NOT NULL,
  candidate_form_data LONGTEXT NOT NULL,
  hiring_department_data LONGTEXT NULL,
  hr_data LONGTEXT NULL,
  candidate_submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hiring_department_updated_at DATETIME NULL,
  hr_updated_at DATETIME NULL,
  status ENUM('candidate_submitted', 'hiring_department_completed', 'hr_completed') NOT NULL DEFAULT 'candidate_submitted',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_employment_form_submissions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE RESTRICT,
  CONSTRAINT fk_employment_form_submissions_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  INDEX idx_employment_form_submissions_job (job_id, candidate_submitted_at),
  INDEX idx_employment_form_submissions_candidate (candidate_id, candidate_submitted_at),
  INDEX idx_employment_form_submissions_email (candidate_email, candidate_submitted_at)
) ENGINE=InnoDB;
