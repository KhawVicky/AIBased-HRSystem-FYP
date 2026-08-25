CREATE TABLE IF NOT EXISTS attendance_settings (
  setting_id TINYINT UNSIGNED PRIMARY KEY,
  work_start_time TIME NOT NULL DEFAULT '08:00:00',
  work_end_time TIME NOT NULL DEFAULT '17:00:00',
  updated_by INT UNSIGNED NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_attendance_settings_updated_by FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

INSERT INTO attendance_settings (setting_id, work_start_time, work_end_time)
VALUES (1, '08:00:00', '17:00:00')
ON DUPLICATE KEY UPDATE
  setting_id = VALUES(setting_id);
