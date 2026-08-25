USE uwc_hr_decision_support;

ALTER TABLE applications
  MODIFY application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'rejected', 'filtered_out') NOT NULL DEFAULT 'new';

ALTER TABLE application_submission_history
  MODIFY previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'rejected', 'filtered_out') NOT NULL;
