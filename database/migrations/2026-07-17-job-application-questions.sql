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
