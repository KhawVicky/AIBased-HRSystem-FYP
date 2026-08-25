UPDATE applications
SET reviewed_at = NULL,
    assigned_hr_user_id = NULL
WHERE application_status = 'new';
