UPDATE hr_action_logs
SET action_label = 'Sent Rejected Email'
WHERE action_type = 'reject_candidate';
