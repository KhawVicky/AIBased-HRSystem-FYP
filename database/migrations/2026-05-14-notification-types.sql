USE uwc_hr_decision_support;

DELETE FROM notifications
WHERE notification_type NOT IN ('new_application', 'email_sent');

UPDATE notifications
SET title = CASE
    WHEN notification_type = 'new_application' THEN 'New Application for Senior Frontend Developer'
    ELSE title
  END,
  message = CASE
    WHEN notification_type = 'new_application' THEN 'A new candidate has submitted an application.'
    ELSE message
  END
WHERE notification_type = 'new_application';
