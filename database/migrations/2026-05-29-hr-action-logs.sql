CREATE TABLE IF NOT EXISTS hr_action_logs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  application_id INT UNSIGNED NULL,
  job_id INT UNSIGNED NULL,
  candidate_id INT UNSIGNED NULL,
  action_type VARCHAR(80) NOT NULL,
  action_label VARCHAR(180) NOT NULL,
  details TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hr_action_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_hr_action_logs_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL,
  CONSTRAINT fk_hr_action_logs_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
  CONSTRAINT fk_hr_action_logs_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  INDEX idx_hr_action_logs_user_created (user_id, created_at),
  INDEX idx_hr_action_logs_application_created (application_id, created_at)
) ENGINE=InnoDB;
