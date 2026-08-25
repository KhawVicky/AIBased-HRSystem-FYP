-- Persist whether an internal user must replace their temporary password at login.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS must_change_password TINYINT(1) NOT NULL DEFAULT 0
  AFTER password_hash;
