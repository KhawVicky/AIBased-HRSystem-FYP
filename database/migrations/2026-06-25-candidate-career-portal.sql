ALTER TABLE candidates
  ADD COLUMN IF NOT EXISTS address VARCHAR(500) NULL AFTER phone,
  ADD COLUMN IF NOT EXISTS education VARCHAR(500) NULL AFTER address,
  ADD COLUMN IF NOT EXISTS default_resume_file_name VARCHAR(255) NULL AFTER education,
  ADD COLUMN IF NOT EXISTS default_resume_path VARCHAR(500) NULL AFTER default_resume_file_name;

CREATE TABLE IF NOT EXISTS candidate_accounts (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT UNSIGNED NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
  last_login_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_candidate_accounts_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  UNIQUE KEY uq_candidate_accounts_candidate (candidate_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS candidate_sessions (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_account_id INT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_candidate_sessions_account FOREIGN KEY (candidate_account_id) REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  INDEX idx_candidate_sessions_account (candidate_account_id),
  INDEX idx_candidate_sessions_expires (expires_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS application_documents (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  stored_file_path VARCHAR(500) NOT NULL,
  file_mime_type VARCHAR(120) NOT NULL DEFAULT 'application/pdf',
  file_size_bytes INT UNSIGNED NOT NULL,
  uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_application_documents_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  INDEX idx_application_documents_application (application_id)
) ENGINE=InnoDB;

INSERT INTO application_documents (
  application_id,
  original_file_name,
  stored_file_path,
  file_mime_type,
  file_size_bytes,
  uploaded_at
)
SELECT
  r.application_id,
  r.original_file_name,
  r.stored_file_path,
  r.file_mime_type,
  r.file_size_bytes,
  r.uploaded_at
FROM resumes r
LEFT JOIN application_documents ad
  ON ad.application_id = r.application_id
 AND ad.stored_file_path = r.stored_file_path
WHERE ad.id IS NULL;

ALTER TABLE applications
  MODIFY application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'rejected', 'filtered_out', 'withdrawn') NOT NULL DEFAULT 'new';

ALTER TABLE application_submission_history
  MODIFY previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'rejected', 'filtered_out', 'withdrawn') NOT NULL;
