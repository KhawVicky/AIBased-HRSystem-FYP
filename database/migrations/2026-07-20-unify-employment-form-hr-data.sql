ALTER TABLE employment_form_submissions
  ADD COLUMN IF NOT EXISTS hr_form_data LONGTEXT NULL AFTER candidate_form_data;

UPDATE employment_form_submissions
SET hr_form_data = CASE
  WHEN hiring_department_data IS NOT NULL AND hr_data IS NOT NULL THEN JSON_MERGE_PATCH(hiring_department_data, hr_data)
  WHEN hiring_department_data IS NOT NULL THEN hiring_department_data
  WHEN hr_data IS NOT NULL THEN hr_data
  ELSE hr_form_data
END
WHERE hr_form_data IS NULL
  AND (
    hiring_department_data IS NOT NULL
    OR hr_data IS NOT NULL
  );

ALTER TABLE employment_form_submissions
  DROP COLUMN IF EXISTS hiring_department_data,
  DROP COLUMN IF EXISTS hr_data,
  DROP COLUMN IF EXISTS hiring_department_updated_at;

ALTER TABLE employment_form_submissions
  DROP COLUMN IF EXISTS status;
