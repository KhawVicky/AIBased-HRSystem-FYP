ALTER TABLE email_templates
  ADD COLUMN IF NOT EXISTS logo_attachment_path VARCHAR(500) NULL AFTER attachment_file_name,
  ADD COLUMN IF NOT EXISTS logo_attachment_file_name VARCHAR(255) NULL AFTER logo_attachment_path;
