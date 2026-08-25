CREATE TABLE IF NOT EXISTS job_qualifications (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  qualification TEXT NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 1,
  CONSTRAINT fk_job_qualifications_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_qualifications_order (job_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_eligibility_filter_values (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  filter_key VARCHAR(100) NOT NULL,
  filter_label VARCHAR(160) NOT NULL,
  filter_value VARCHAR(500) NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  CONSTRAINT fk_job_eligibility_values_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_eligibility_value (job_id, filter_key),
  INDEX idx_job_eligibility_values_job (job_id)
) ENGINE=InnoDB;
