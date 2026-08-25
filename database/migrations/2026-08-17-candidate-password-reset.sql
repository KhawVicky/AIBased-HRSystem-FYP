CREATE TABLE IF NOT EXISTS candidate_password_resets (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  candidate_account_id INT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_candidate_password_resets_account FOREIGN KEY (candidate_account_id) REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  INDEX idx_candidate_password_resets_account (candidate_account_id),
  INDEX idx_candidate_password_resets_expiry (expires_at)
) ENGINE=InnoDB;
