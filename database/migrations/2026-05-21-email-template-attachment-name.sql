USE uwc_hr_decision_support;

ALTER TABLE email_templates
  ADD COLUMN IF NOT EXISTS attachment_file_name VARCHAR(255) NULL AFTER attachment_path;

UPDATE email_templates
SET attachment_file_name = SUBSTRING_INDEX(attachment_path, '/', -1)
WHERE attachment_file_name IS NULL
  AND attachment_path IS NOT NULL
  AND attachment_path <> '';
