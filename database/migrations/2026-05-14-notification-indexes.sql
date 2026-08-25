USE uwc_hr_decision_support;

ALTER TABLE notifications
  ADD INDEX IF NOT EXISTS idx_notifications_user_read_created (user_id, is_read, created_at),
  ADD INDEX IF NOT EXISTS idx_notifications_created (created_at);
