INSERT INTO hr_action_logs (
  user_id, application_id, job_id, candidate_id, action_type, action_label, details, created_at
)
SELECT
  a.assigned_hr_user_id,
  a.id,
  a.job_id,
  a.candidate_id,
  CASE
    WHEN a.application_status = 'shortlisted' THEN 'shortlist_candidate'
    WHEN a.application_status = 'interview' THEN 'send_interview_email'
    WHEN a.application_status = 'rejected' THEN 'reject_candidate'
    WHEN a.application_status = 'filtered_out' THEN 'filter_out_candidate'
    ELSE 'review_candidate'
  END,
  CASE
    WHEN a.application_status = 'shortlisted' THEN 'Shortlisted Candidate'
    WHEN a.application_status = 'interview' THEN 'Sent Interview Email'
    WHEN a.application_status = 'rejected' THEN 'Sent Rejected Email'
    WHEN a.application_status = 'filtered_out' THEN 'Filtered Out Candidate'
    ELSE 'Reviewed Candidate'
  END,
  CONCAT('Backfilled from existing application status: ', a.application_status, '.'),
  COALESCE(a.reviewed_at, a.updated_at, a.submitted_at, NOW())
FROM applications a
WHERE a.assigned_hr_user_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM hr_action_logs hal
    WHERE hal.application_id = a.id
      AND hal.user_id = a.assigned_hr_user_id
      AND hal.action_type IN (
        'review_candidate',
        'shortlist_candidate',
        'send_interview_email',
        'reject_candidate',
        'filter_out_candidate'
      )
  );

INSERT INTO hr_action_logs (
  user_id, application_id, job_id, candidate_id, action_type, action_label, details, created_at
)
SELECT
  el.sent_by_user_id,
  el.application_id,
  a.job_id,
  a.candidate_id,
  CASE
    WHEN el.email_type = 'interview' THEN 'send_interview_email'
    WHEN el.email_type = 'reject' THEN 'reject_candidate'
    ELSE 'send_email'
  END,
  CASE
    WHEN el.email_type = 'interview' THEN 'Sent Interview Email'
    WHEN el.email_type = 'reject' THEN 'Sent Rejected Email'
    ELSE 'Sent Email'
  END,
  CONCAT('Backfilled from email log. Subject: ', el.subject),
  COALESCE(el.sent_at, NOW())
FROM email_logs el
JOIN applications a ON a.id = el.application_id
WHERE NOT EXISTS (
  SELECT 1
  FROM hr_action_logs hal
  WHERE hal.user_id = el.sent_by_user_id
    AND hal.application_id = el.application_id
    AND hal.action_type = CASE
      WHEN el.email_type = 'interview' THEN 'send_interview_email'
      WHEN el.email_type = 'reject' THEN 'reject_candidate'
      ELSE 'send_email'
    END
    AND ABS(TIMESTAMPDIFF(SECOND, hal.created_at, COALESCE(el.sent_at, NOW()))) <= 2
);
