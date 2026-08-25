UPDATE hr_action_logs
SET action_type = 'send_interview_email',
    action_label = 'Sent Interview Email',
    details = CASE
      WHEN details IS NULL OR details = '' THEN 'Sent interview email to the candidate.'
      ELSE details
    END
WHERE action_type = 'move_to_interview';
