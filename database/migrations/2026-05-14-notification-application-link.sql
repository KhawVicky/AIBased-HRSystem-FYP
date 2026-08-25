USE uwc_hr_decision_support;

ALTER TABLE notifications
  ADD COLUMN IF NOT EXISTS related_application_id INT UNSIGNED NULL AFTER user_id,
  ADD CONSTRAINT fk_notifications_application FOREIGN KEY (related_application_id) REFERENCES applications(id) ON DELETE SET NULL;

UPDATE notifications n
JOIN jobs j ON n.title = CONCAT('New Application for ', j.title)
JOIN applications a ON a.job_id = j.id
SET n.related_application_id = a.id
WHERE n.notification_type = 'new_application'
  AND a.submitted_at = (
    SELECT MAX(a2.submitted_at)
    FROM applications a2
    WHERE a2.job_id = j.id
  );
