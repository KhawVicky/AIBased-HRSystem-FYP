UPDATE hr_action_logs hal
SET
  hal.action_type = 'send_rejection_email',
  hal.action_label = 'Rejection Email Sent'
WHERE hal.action_type = 'reject_candidate'
  AND EXISTS (
    SELECT 1
    FROM email_logs el
    WHERE el.application_id = hal.application_id
      AND el.email_type = 'reject'
      AND el.status = 'sent'
      AND el.sent_at >= hal.created_at - INTERVAL 5 SECOND
  );

UPDATE hr_action_logs
SET action_label = 'Rejected'
WHERE action_type = 'reject_candidate';

INSERT INTO hr_action_logs (
  user_id,
  application_id,
  job_id,
  candidate_id,
  action_type,
  action_label,
  reason_type,
  reason_details,
  created_at
)
SELECT
  hal.user_id,
  hal.application_id,
  hal.job_id,
  hal.candidate_id,
  'rejection_reason',
  'Added Rejection Reason',
  hal.reason_type,
  hal.reason_details,
  DATE_ADD(hal.created_at, INTERVAL 1 SECOND)
FROM hr_action_logs hal
WHERE hal.action_type IN ('reject_candidate', 'send_rejection_email')
  AND (hal.reason_type IS NOT NULL OR hal.reason_details IS NOT NULL)
  AND NOT EXISTS (
    SELECT 1
    FROM hr_action_logs existing_reason
    WHERE existing_reason.application_id = hal.application_id
      AND existing_reason.action_type = 'rejection_reason'
      AND existing_reason.reason_type <=> hal.reason_type
      AND existing_reason.reason_details <=> hal.reason_details
  );

UPDATE hr_action_logs
SET reason_type = NULL,
    reason_details = NULL
WHERE action_type IN ('reject_candidate', 'send_rejection_email');
