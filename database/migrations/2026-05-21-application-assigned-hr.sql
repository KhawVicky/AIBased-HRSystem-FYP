USE uwc_hr_decision_support;

ALTER TABLE applications
  ADD COLUMN IF NOT EXISTS assigned_hr_user_id INT UNSIGNED NULL AFTER application_link_id,
  ADD INDEX IF NOT EXISTS idx_applications_assigned_hr (assigned_hr_user_id),
  ADD CONSTRAINT fk_applications_assigned_hr FOREIGN KEY (assigned_hr_user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE application_submission_history
  ADD COLUMN IF NOT EXISTS previous_assigned_hr_user_id INT UNSIGNED NULL AFTER previous_rank_no,
  ADD CONSTRAINT fk_submission_history_assigned_hr FOREIGN KEY (previous_assigned_hr_user_id) REFERENCES users(id) ON DELETE SET NULL;

UPDATE applications a
JOIN jobs j ON j.id = a.job_id
SET a.assigned_hr_user_id = j.created_by_user_id
WHERE a.assigned_hr_user_id IS NULL
  AND a.reviewed_at IS NOT NULL;
