CREATE DATABASE IF NOT EXISTS uwc_hr_decision_support
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE uwc_hr_decision_support;

CREATE TABLE IF NOT EXISTS roles (
  id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_name VARCHAR(80) NOT NULL UNIQUE,
  description VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_id TINYINT UNSIGNED NOT NULL,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  must_change_password TINYINT(1) NOT NULL DEFAULT 0,
  department VARCHAR(120) NULL,
  phone VARCHAR(40) NULL,
  avatar_path VARCHAR(500) NULL,
  status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
  last_login_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS jobs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_code VARCHAR(30) NOT NULL UNIQUE,
  created_by_user_id INT UNSIGNED NOT NULL,
  title VARCHAR(180) NOT NULL,
  department VARCHAR(120) NOT NULL,
  location VARCHAR(180) NULL,
  salary_range VARCHAR(120) NULL,
  employment_type VARCHAR(80) NULL,
  description TEXT NULL,
  status ENUM('draft', 'active', 'closed', 'archived') NOT NULL DEFAULT 'draft',
  jd_file_name VARCHAR(255) NULL,
  jd_file_path VARCHAR(500) NULL,
  published_at DATETIME NULL,
  closed_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_jobs_created_by FOREIGN KEY (created_by_user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_responsibilities (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  responsibility TEXT NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 1,
  CONSTRAINT fk_job_responsibilities_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_responsibilities_order (job_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_required_skills (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  skill_name VARCHAR(120) NOT NULL,
  skill_type ENUM('technical', 'soft', 'language', 'tool', 'other') NOT NULL DEFAULT 'technical',
  importance ENUM('required', 'preferred') NOT NULL DEFAULT 'required',
  CONSTRAINT fk_job_required_skills_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_required_skills_name (job_id, skill_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_criteria (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  criteria_name VARCHAR(150) NOT NULL,
  criterion_type ENUM(
    'relevant_skill',
    'relevant_experience',
    'education_relevance',
    'domain_knowledge',
    'preferred_certification',
    'job_related_language'
  ) NOT NULL DEFAULT 'relevant_skill',
  weight DECIMAL(5,2) NOT NULL,
  description TEXT NULL,
  source_text TEXT NULL,
  evidence_rule TEXT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT UNSIGNED NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_job_criteria_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  INDEX idx_job_criteria_job (job_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS criteria_requirements (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  criteria_id INT UNSIGNED NOT NULL,
  requirement_text VARCHAR(255) NOT NULL,
  requirement_type ENUM('skill', 'experience', 'education', 'language', 'certification', 'other') NOT NULL DEFAULT 'skill',
  match_rule ENUM('required', 'preferred', 'related_allowed') NOT NULL DEFAULT 'required',
  CONSTRAINT fk_criteria_requirements_criteria FOREIGN KEY (criteria_id) REFERENCES job_criteria(id) ON DELETE CASCADE,
  UNIQUE KEY uq_criteria_requirements_text (criteria_id, requirement_text)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filters (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  min_cgpa DECIMAL(3,2) NULL,
  min_years_experience DECIMAL(4,1) NULL,
  internship_accepted TINYINT(1) NOT NULL DEFAULT 0,
  required_qualification VARCHAR(255) NULL,
  required_language VARCHAR(180) NULL,
  required_location VARCHAR(180) NULL,
  max_notice_period_days INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_eligibility_filters_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_eligibility_filters_job (job_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_qualifications (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  qualification TEXT NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 1,
  CONSTRAINT fk_job_qualifications_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_qualifications_order (job_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filter_definitions (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  filter_key VARCHAR(100) NOT NULL UNIQUE,
  filter_name VARCHAR(160) NOT NULL,
  filter_type ENUM('dropdown', 'text', 'number') NOT NULL DEFAULT 'dropdown',
  is_system TINYINT(1) NOT NULL DEFAULT 0,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filter_options (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  filter_id INT UNSIGNED NOT NULL,
  option_label VARCHAR(160) NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_eligibility_filter_options_definition FOREIGN KEY (filter_id) REFERENCES eligibility_filter_definitions(id) ON DELETE CASCADE,
  UNIQUE KEY uq_eligibility_filter_option (filter_id, option_label),
  INDEX idx_eligibility_filter_options_filter (filter_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filter_seed_state (
  id TINYINT UNSIGNED PRIMARY KEY,
  seeded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS job_application_questions (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  question_text VARCHAR(500) NOT NULL,
  field_type ENUM('text', 'textarea', 'number', 'dropdown') NOT NULL DEFAULT 'text',
  is_required TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_job_application_questions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  INDEX idx_job_application_questions_job (job_id, is_active, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_application_question_options (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  question_id INT UNSIGNED NOT NULL,
  option_label VARCHAR(255) NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  CONSTRAINT fk_job_application_question_options_question FOREIGN KEY (question_id) REFERENCES job_application_questions(id) ON DELETE CASCADE,
  UNIQUE KEY uq_job_application_question_option (question_id, option_label),
  INDEX idx_job_application_question_options_question (question_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS application_links (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  token VARCHAR(100) NOT NULL UNIQUE,
  public_path VARCHAR(255) NOT NULL UNIQUE,
  status ENUM('active', 'disabled', 'expired') NOT NULL DEFAULT 'active',
  expires_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_application_links_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uq_application_links_job (job_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS candidates (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(180) NOT NULL,
  phone VARCHAR(40) NULL,
  gender VARCHAR(50) NULL,
  country VARCHAR(100) NULL,
  current_location VARCHAR(160) NULL,
  languages_json TEXT NULL,
  address VARCHAR(500) NULL,
  education VARCHAR(500) NULL,
  default_resume_file_name VARCHAR(255) NULL,
  default_resume_path VARCHAR(500) NULL,
  current_cgpa DECIMAL(3,2) NULL,
  years_experience DECIMAL(4,1) NULL,
  notice_period_days INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_candidates_email (email)
) ENGINE=InnoDB;

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

CREATE TABLE IF NOT EXISTS candidate_password_resets (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_account_id INT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_candidate_password_resets_account FOREIGN KEY (candidate_account_id) REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  INDEX idx_candidate_password_resets_account (candidate_account_id),
  INDEX idx_candidate_password_resets_expiry (expires_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applications (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  candidate_id INT UNSIGNED NOT NULL,
  application_link_id INT UNSIGNED NULL,
  assigned_hr_user_id INT UNSIGNED NULL,
  application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL DEFAULT 'new',
  is_shortlisted TINYINT(1) NOT NULL DEFAULT 0,
  interview_sent_at DATETIME NULL,
  hired_start_date DATE NULL,
  eligibility_status ENUM('eligible', 'filtered_out', 'pending') NOT NULL DEFAULT 'pending',
  total_score DECIMAL(5,2) NULL,
  rank_no INT UNSIGNED NULL,
  scoring_version VARCHAR(80) NULL,
  analysis_status VARCHAR(32) NULL,
  scored_at DATETIME NULL,
  eligibility_reasons_json TEXT NULL,
  scoring_diagnostics_json LONGTEXT NULL,
  criteria_snapshot_json LONGTEXT NULL,
  ai_summary TEXT NULL,
  submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_applications_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_applications_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  CONSTRAINT fk_applications_link FOREIGN KEY (application_link_id) REFERENCES application_links(id) ON DELETE SET NULL,
  CONSTRAINT fk_applications_assigned_hr FOREIGN KEY (assigned_hr_user_id) REFERENCES users(id) ON DELETE SET NULL,
  UNIQUE KEY uq_applications_job_candidate (job_id, candidate_id),
  INDEX idx_applications_assigned_hr (assigned_hr_user_id),
  INDEX idx_applications_job_status (job_id, application_status),
  INDEX idx_applications_ranking (job_id, eligibility_status, total_score)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS application_question_answers (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  question_id INT UNSIGNED NOT NULL,
  answer_text TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_application_question_answers_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_application_question_answers_question FOREIGN KEY (question_id) REFERENCES job_application_questions(id) ON DELETE RESTRICT,
  UNIQUE KEY uq_application_question_answer (application_id, question_id),
  INDEX idx_application_question_answers_application (application_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS employment_form_submissions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_id INT UNSIGNED NOT NULL,
  candidate_id INT UNSIGNED NULL,
  candidate_email VARCHAR(180) NOT NULL,
  candidate_form_data LONGTEXT NOT NULL,
  hr_form_data LONGTEXT NULL,
  candidate_submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hr_updated_at DATETIME NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_employment_form_submissions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE RESTRICT,
  CONSTRAINT fk_employment_form_submissions_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  INDEX idx_employment_form_submissions_job (job_id, candidate_submitted_at),
  INDEX idx_employment_form_submissions_candidate (candidate_id, candidate_submitted_at),
  INDEX idx_employment_form_submissions_email (candidate_email, candidate_submitted_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS resumes (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  stored_file_path VARCHAR(500) NOT NULL,
  file_mime_type VARCHAR(120) NOT NULL DEFAULT 'application/pdf',
  file_size_bytes INT UNSIGNED NOT NULL,
  parsed_text MEDIUMTEXT NULL,
  parsed_profile_json LONGTEXT NULL,
  parse_metadata_json TEXT NULL,
  parser_version VARCHAR(80) NULL,
  parsed_at DATETIME NULL,
  parsing_status ENUM('pending', 'parsed', 'failed') NOT NULL DEFAULT 'pending',
  uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_resumes_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  INDEX idx_resumes_application (application_id)
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

CREATE TABLE IF NOT EXISTS score_breakdowns (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  criteria_id INT UNSIGNED NOT NULL,
  raw_score DECIMAL(5,2) NOT NULL,
  semantic_score DECIMAL(4,2) NULL,
  weight DECIMAL(5,2) NOT NULL,
  weighted_score DECIMAL(5,2) NOT NULL,
  explanation TEXT NULL,
  criterion_type VARCHAR(80) NULL,
  criterion_name_snapshot VARCHAR(255) NULL,
  jd_evidence_json TEXT NULL,
  matched_resume_evidence_json LONGTEXT NULL,
  evidence_ids_json TEXT NULL,
  grounded TINYINT(1) NOT NULL DEFAULT 0,
  scoring_version VARCHAR(80) NULL,
  qwen_status VARCHAR(40) NULL,
  scored_at DATETIME NULL,
  CONSTRAINT fk_score_breakdowns_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_score_breakdowns_criteria FOREIGN KEY (criteria_id) REFERENCES job_criteria(id) ON DELETE CASCADE,
  UNIQUE KEY uq_score_breakdowns_application_criteria (application_id, criteria_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS score_breakdown_items (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  score_breakdown_id INT UNSIGNED NOT NULL,
  requirement_text VARCHAR(255) NOT NULL,
  match_status ENUM('matched', 'partial', 'missing') NOT NULL,
  evidence_text TEXT NULL,
  item_score DECIMAL(5,2) NULL,
  CONSTRAINT fk_score_breakdown_items_breakdown FOREIGN KEY (score_breakdown_id) REFERENCES score_breakdowns(id) ON DELETE CASCADE,
  UNIQUE KEY uq_score_breakdown_items_requirement (score_breakdown_id, requirement_text)
) ENGINE=InnoDB;

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

CREATE TABLE IF NOT EXISTS application_submission_history (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_id INT UNSIGNED NOT NULL,
  application_id INT UNSIGNED NOT NULL,
  job_id INT UNSIGNED NOT NULL,
  submission_no INT UNSIGNED NOT NULL,
  previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL,
  previous_eligibility_status ENUM('eligible', 'filtered_out', 'pending') NOT NULL,
  previous_score DECIMAL(5,2) NULL,
  previous_rank_no INT UNSIGNED NULL,
  previous_assigned_hr_user_id INT UNSIGNED NULL,
  previous_resume_file_name VARCHAR(255) NULL,
  previous_resume_url VARCHAR(500) NULL,
  previous_ai_summary TEXT NULL,
  original_submitted_at DATETIME NULL,
  recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_submission_history_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
  CONSTRAINT fk_submission_history_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_submission_history_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_submission_history_assigned_hr FOREIGN KEY (previous_assigned_hr_user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_submission_history_application (application_id, recorded_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_templates (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  template_key VARCHAR(80) NOT NULL UNIQUE,
  template_name VARCHAR(150) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  attachment_path VARCHAR(500) NULL,
  attachment_file_name VARCHAR(255) NULL,
  logo_attachment_path VARCHAR(500) NULL,
  logo_attachment_file_name VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_by_user_id INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_email_templates_created_by FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_logs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNSIGNED NOT NULL,
  sent_by_user_id INT UNSIGNED NOT NULL,
  template_id INT UNSIGNED NULL,
  email_type ENUM('interview', 'reject', 'general') NOT NULL,
  recipient_email VARCHAR(180) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  scheduled_interview_at DATETIME NULL,
  status ENUM('draft', 'sent', 'failed') NOT NULL DEFAULT 'sent',
  sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_email_logs_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_email_logs_sent_by FOREIGN KEY (sent_by_user_id) REFERENCES users(id),
  CONSTRAINT fk_email_logs_template FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS hr_action_logs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  application_id INT UNSIGNED NULL,
  job_id INT UNSIGNED NULL,
  candidate_id INT UNSIGNED NULL,
  action_type VARCHAR(80) NOT NULL,
  action_label VARCHAR(180) NOT NULL,
  job_title VARCHAR(255) NULL,
  reason_type VARCHAR(120) NULL,
  reason_details TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hr_action_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_hr_action_logs_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL,
  CONSTRAINT fk_hr_action_logs_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
  CONSTRAINT fk_hr_action_logs_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  INDEX idx_hr_action_logs_user_created (user_id, created_at),
  INDEX idx_hr_action_logs_application_created (application_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  related_application_id INT UNSIGNED NULL,
  notification_type VARCHAR(80) NOT NULL,
  title VARCHAR(180) NOT NULL,
  message TEXT NOT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_notifications_application FOREIGN KEY (related_application_id) REFERENCES applications(id) ON DELETE SET NULL,
  INDEX idx_notifications_user_read_created (user_id, is_read, created_at),
  INDEX idx_notifications_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_records (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  attendance_date DATE NOT NULL,
  status ENUM('present', 'late', 'absent', 'leave') NOT NULL,
  check_in_time TIME NULL,
  check_out_time TIME NULL,
  remarks VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_attendance_records_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_attendance_user_date (user_id, attendance_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_settings (
  setting_id TINYINT UNSIGNED PRIMARY KEY,
  work_start_time TIME NOT NULL DEFAULT '08:00:00',
  work_end_time TIME NOT NULL DEFAULT '17:00:00',
  updated_by INT UNSIGNED NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_attendance_settings_updated_by FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

INSERT INTO attendance_settings (setting_id, work_start_time, work_end_time)
VALUES (1, '08:00:00', '17:00:00')
ON DUPLICATE KEY UPDATE
  setting_id = VALUES(setting_id);

INSERT INTO roles (id, role_name, description) VALUES
  (1, 'HR Staff', 'Can create jobs, manage applications, shortlist candidates, and send interview or reject decisions.'),
  (2, 'Hiring Manager', 'Can review shortlisted candidates, view scoring details, and manage internal users.')
ON DUPLICATE KEY UPDATE
  role_name = VALUES(role_name),
  description = VALUES(description);

INSERT INTO users (id, role_id, full_name, email, password_hash, department, phone, status) VALUES
  (2, 1, 'HR Staff Demo', 'hr@uwc.com.my', '$2y$10$jG1cXjTQxMqF0CsaKdX7nu2Ks7yLwRVuMdU16I8gJFBlDXePNmC2m', 'Human Resources', '+604-0000001', 'active'),
  (3, 2, 'Hiring Manager Demo', 'manager@uwc.com.my', '$2y$10$jG1cXjTQxMqF0CsaKdX7nu2Ks7yLwRVuMdU16I8gJFBlDXePNmC2m', 'Engineering', '+604-0000002', 'active')
ON DUPLICATE KEY UPDATE
  role_id = VALUES(role_id),
  full_name = VALUES(full_name),
  department = VALUES(department),
  phone = VALUES(phone),
  status = VALUES(status);

INSERT INTO jobs (
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description,
  status, jd_file_name, jd_file_path, published_at
) VALUES
  (
    1, 'JOB001', 2, 'Senior Frontend Developer', 'Engineering', 'Batu Kawan, Penang',
    'RM 4,500 - RM 6,500', 'Full-time',
    'Build and maintain frontend web applications, collaborate with backend teams, and improve UI quality.',
    'active', 'senior-frontend-developer.pdf', '/uploads/jd/senior-frontend-developer.pdf', NOW()
  )
ON DUPLICATE KEY UPDATE
  title = VALUES(title),
  department = VALUES(department),
  location = VALUES(location),
  salary_range = VALUES(salary_range),
  employment_type = VALUES(employment_type),
  description = VALUES(description),
  status = VALUES(status);

INSERT INTO job_responsibilities (job_id, responsibility, sort_order) VALUES
  (1, 'Develop responsive frontend features using React and TypeScript.', 1),
  (1, 'Collaborate with backend engineers to integrate APIs.', 2),
  (1, 'Improve usability, accessibility, and interface quality.', 3)
ON DUPLICATE KEY UPDATE
  responsibility = VALUES(responsibility);

INSERT INTO job_qualifications (job_id, qualification, sort_order) VALUES
  (1, 'Bachelor Degree in Computer Science or related field', 1)
ON DUPLICATE KEY UPDATE
  qualification = VALUES(qualification);

INSERT INTO job_required_skills (job_id, skill_name, skill_type, importance) VALUES
  (1, 'React', 'technical', 'required'),
  (1, 'TypeScript', 'technical', 'required'),
  (1, 'Node.js', 'technical', 'preferred'),
  (1, 'AWS', 'tool', 'preferred'),
  (1, 'English', 'language', 'required'),
  (1, 'Bahasa Malaysia', 'language', 'preferred')
ON DUPLICATE KEY UPDATE
  skill_type = VALUES(skill_type),
  importance = VALUES(importance);

INSERT INTO job_criteria (id, job_id, criteria_name, weight, description, sort_order) VALUES
  (1, 1, 'Technical Skills', 40.00, 'Match against required frontend and platform skills.', 1),
  (2, 1, 'Experience', 25.00, 'Relevant software development and frontend project experience.', 2),
  (3, 1, 'Education', 20.00, 'Relevant academic qualification and CGPA.', 3),
  (4, 1, 'Soft Skills', 15.00, 'Communication, teamwork, and collaboration indicators.', 4)
ON DUPLICATE KEY UPDATE
  criteria_name = VALUES(criteria_name),
  weight = VALUES(weight),
  description = VALUES(description),
  sort_order = VALUES(sort_order);

INSERT INTO criteria_requirements (criteria_id, requirement_text, requirement_type, match_rule) VALUES
  (1, 'React', 'skill', 'required'),
  (1, 'TypeScript', 'skill', 'required'),
  (1, 'Node.js', 'skill', 'preferred'),
  (1, 'AWS', 'skill', 'preferred'),
  (2, '3 years frontend development experience', 'experience', 'required'),
  (3, 'Bachelor Degree in Computer Science or related field', 'education', 'required'),
  (4, 'Team collaboration', 'other', 'preferred'),
  (4, 'Communication skills', 'other', 'preferred')
ON DUPLICATE KEY UPDATE
  requirement_type = VALUES(requirement_type),
  match_rule = VALUES(match_rule);

INSERT INTO eligibility_filters (
  job_id, min_cgpa, min_years_experience, internship_accepted,
  required_qualification, required_language, required_location, max_notice_period_days
) VALUES
  (1, 3.00, 2.0, 0, 'Bachelor Degree', 'English', 'Malaysia', 60)
ON DUPLICATE KEY UPDATE
  min_cgpa = VALUES(min_cgpa),
  min_years_experience = VALUES(min_years_experience),
  internship_accepted = VALUES(internship_accepted),
  required_qualification = VALUES(required_qualification),
  required_language = VALUES(required_language),
  required_location = VALUES(required_location),
  max_notice_period_days = VALUES(max_notice_period_days);

INSERT INTO application_links (job_id, token, public_path, status) VALUES
  (1, 'JOB001-DEMO-LINK', '/apply/JOB001', 'active')
ON DUPLICATE KEY UPDATE
  token = VALUES(token),
  public_path = VALUES(public_path),
  status = VALUES(status);

INSERT INTO candidates (id, full_name, email, phone, current_cgpa, years_experience, notice_period_days, current_location) VALUES
  (1, 'Alice Chen', 'alice.chen@example.com', '+6012-1111111', 3.92, 8.0, 30, 'Penang'),
  (2, 'Daniel Tan', 'daniel.tan@example.com', '+6012-2222222', 2.85, 2.0, 45, 'Kuala Lumpur')
ON DUPLICATE KEY UPDATE
  full_name = VALUES(full_name),
  phone = VALUES(phone),
  current_cgpa = VALUES(current_cgpa),
  years_experience = VALUES(years_experience),
  notice_period_days = VALUES(notice_period_days),
  current_location = VALUES(current_location);

INSERT INTO applications (
  id, job_id, candidate_id, application_link_id, application_status,
  eligibility_status, total_score, rank_no, ai_summary
) VALUES
  (
    1, 1, 1, (SELECT id FROM application_links WHERE job_id = 1), 'shortlisted',
    'eligible',
    88.50, 1,
    'Alice Chen is a highly ranked frontend candidate with strong React, TypeScript, Node.js and AWS experience. She is suitable for HR review.'
  ),
  (
    2, 1, 2, (SELECT id FROM application_links WHERE job_id = 1), 'filtered_out',
    'filtered_out',
    67.00, NULL,
    'Daniel Tan has relevant frontend exposure and can be reviewed through the score breakdown.'
  )
ON DUPLICATE KEY UPDATE
  application_status = VALUES(application_status),
  eligibility_status = VALUES(eligibility_status),
  total_score = VALUES(total_score),
  rank_no = VALUES(rank_no),
  ai_summary = VALUES(ai_summary);

UPDATE applications a
JOIN jobs j ON j.id = a.job_id
SET a.assigned_hr_user_id = j.created_by_user_id
WHERE a.assigned_hr_user_id IS NULL
  AND a.reviewed_at IS NOT NULL;

DELETE FROM resumes
WHERE original_file_name IN ('alice-chen-resume.pdf', 'daniel-tan-resume.pdf');

INSERT INTO resumes (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes, parsing_status) VALUES
  (1, 'alice-chen-resume.pdf', '/uploads/resumes/alice-chen-resume.pdf', 'application/pdf', 245760, 'parsed'),
  (2, 'daniel-tan-resume.pdf', '/uploads/resumes/daniel-tan-resume.pdf', 'application/pdf', 198240, 'parsed');

INSERT INTO score_breakdowns (id, application_id, criteria_id, raw_score, weight, weighted_score, explanation) VALUES
  (1, 1, 1, 90.00, 40.00, 36.00, 'Strong match for React and TypeScript; Node.js and AWS also mentioned.'),
  (2, 1, 2, 88.00, 25.00, 22.00, 'Relevant frontend development experience exceeds minimum requirement.'),
  (3, 1, 3, 92.00, 20.00, 18.40, 'Relevant computer science education and strong CGPA.'),
  (4, 1, 4, 80.67, 15.00, 12.10, 'Resume indicates collaboration and communication experience.'),
  (5, 2, 1, 72.00, 40.00, 28.80, 'React mentioned, TypeScript detail is limited, AWS not found.'),
  (6, 2, 2, 70.00, 25.00, 17.50, 'Experience is relevant but less senior.'),
  (7, 2, 3, 55.00, 20.00, 11.00, 'Education is relevant to the role.'),
  (8, 2, 4, 64.67, 15.00, 9.70, 'Some teamwork evidence found.')
ON DUPLICATE KEY UPDATE
  raw_score = VALUES(raw_score),
  weight = VALUES(weight),
  weighted_score = VALUES(weighted_score),
  explanation = VALUES(explanation);

INSERT INTO score_breakdown_items (score_breakdown_id, requirement_text, match_status, evidence_text, item_score) VALUES
  (1, 'React', 'matched', 'Resume includes multiple React projects.', 95.00),
  (1, 'TypeScript', 'matched', 'TypeScript used in frontend applications.', 90.00),
  (1, 'Node.js', 'matched', 'Node.js used for API integration work.', 85.00),
  (1, 'AWS', 'partial', 'AWS deployment exposure mentioned.', 75.00),
  (5, 'React', 'matched', 'React mentioned in project section.', 80.00),
  (5, 'TypeScript', 'partial', 'TypeScript mentioned without strong detail.', 60.00),
  (5, 'AWS', 'missing', 'AWS was not found in resume text.', 0.00)
ON DUPLICATE KEY UPDATE
  match_status = VALUES(match_status),
  evidence_text = VALUES(evidence_text),
  item_score = VALUES(item_score);

INSERT INTO email_templates (template_key, template_name, subject, body, created_by_user_id) VALUES
  (
    'interview_invitation',
    'Interview Invitation',
    'Interview invitation for {jobTitle}',
    'Dear {candidateName},\n\nWe would like to invite you for an interview for the {jobTitle} position.\n\nAvailable interview date and time options: {interviewDateOptions}\n\nPlease reply to this email with your preferred interview time. Also, please complete the attached file and reply to this email before attending the interview.\n\nRegards,\nUWC Berhad',
    2
  ),
  (
    'reject_application',
    'Reject Application',
    'Update on your job application',
    'Dear {candidateName},\n\nThank you for your interest in {jobTitle}. After careful review, we regret to inform you that you have not been selected for this role.\n\nWe appreciate your time and interest in {companyName}.\n\nRegards,\n{companyName}',
    2
  ),
  (
    'application_confirmation',
    'Application Confirmation',
    'Application received for {jobTitle}',
    'Dear {candidateName},\n\nThank you for applying for the {jobTitle} position at {companyName}.\n\nWe have received your application successfully. Our HR team will review your application and contact you if you are shortlisted.\n\nPlease keep this email for your records.\n\nRegards,\n{companyName}',
    2
  )
ON DUPLICATE KEY UPDATE
  template_name = VALUES(template_name),
  subject = VALUES(subject),
  body = VALUES(body),
  created_by_user_id = VALUES(created_by_user_id);

INSERT INTO notifications (user_id, related_application_id, notification_type, title, message) VALUES
  (2, 1, 'new_application', 'New Application for Senior Frontend Developer', 'A new candidate has submitted an application.'),
  (2, 1, 'email_sent', 'Interview Email Sent', 'The interview email has been sent successfully.');

INSERT INTO attendance_records (user_id, attendance_date, status, check_in_time, check_out_time, remarks) VALUES
  (2, CURRENT_DATE, 'present', '08:55:00', NULL, 'Optional attendance analytics demo record.')
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  check_in_time = VALUES(check_in_time),
  check_out_time = VALUES(check_out_time),
  remarks = VALUES(remarks);

