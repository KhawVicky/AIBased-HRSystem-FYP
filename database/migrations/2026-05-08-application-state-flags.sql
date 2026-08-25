USE uwc_hr_decision_support;

ALTER TABLE applications
  ADD COLUMN IF NOT EXISTS is_shortlisted TINYINT(1) NOT NULL DEFAULT 0 AFTER application_status,
  ADD COLUMN IF NOT EXISTS interview_sent_at DATETIME NULL AFTER is_shortlisted;

UPDATE applications
SET
  is_shortlisted = CASE
    WHEN application_status IN ('shortlisted', 'interview') THEN 1
    ELSE is_shortlisted
  END,
  interview_sent_at = CASE
    WHEN application_status = 'interview' THEN COALESCE(reviewed_at, submitted_at)
    ELSE interview_sent_at
  END;
