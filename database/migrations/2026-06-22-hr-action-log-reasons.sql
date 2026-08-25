ALTER TABLE hr_action_logs
  ADD COLUMN IF NOT EXISTS reason_type VARCHAR(120) NULL AFTER action_label,
  ADD COLUMN IF NOT EXISTS reason_details TEXT NULL AFTER reason_type;

ALTER TABLE hr_action_logs
  DROP COLUMN IF EXISTS details;
