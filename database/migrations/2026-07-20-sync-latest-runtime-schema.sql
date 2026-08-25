USE uwc_hr_decision_support;

ALTER TABLE candidates
  ADD COLUMN IF NOT EXISTS gender VARCHAR(50) NULL AFTER phone,
  ADD COLUMN IF NOT EXISTS country VARCHAR(100) NULL AFTER gender,
  ADD COLUMN IF NOT EXISTS current_location VARCHAR(160) NULL AFTER country,
  ADD COLUMN IF NOT EXISTS languages_json TEXT NULL AFTER current_location,
  ADD COLUMN IF NOT EXISTS address VARCHAR(500) NULL AFTER languages_json,
  ADD COLUMN IF NOT EXISTS education VARCHAR(500) NULL AFTER address,
  ADD COLUMN IF NOT EXISTS default_resume_file_name VARCHAR(255) NULL AFTER education,
  ADD COLUMN IF NOT EXISTS default_resume_path VARCHAR(500) NULL AFTER default_resume_file_name;

ALTER TABLE candidates
  MODIFY COLUMN gender VARCHAR(50) NULL AFTER phone,
  MODIFY COLUMN country VARCHAR(100) NULL AFTER gender,
  MODIFY COLUMN current_location VARCHAR(160) NULL AFTER country,
  MODIFY COLUMN languages_json TEXT NULL AFTER current_location,
  MODIFY COLUMN address VARCHAR(500) NULL AFTER languages_json,
  MODIFY COLUMN education VARCHAR(500) NULL AFTER address,
  MODIFY COLUMN default_resume_file_name VARCHAR(255) NULL AFTER education,
  MODIFY COLUMN default_resume_path VARCHAR(500) NULL AFTER default_resume_file_name;

ALTER TABLE applications
  MODIFY application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL DEFAULT 'new',
  ADD COLUMN IF NOT EXISTS hired_start_date DATE NULL AFTER interview_sent_at;

ALTER TABLE application_submission_history
  MODIFY previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL;
