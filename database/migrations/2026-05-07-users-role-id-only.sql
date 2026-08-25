USE uwc_hr_decision_support;

CREATE TABLE IF NOT EXISTS roles (
  id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_name VARCHAR(80) NOT NULL UNIQUE,
  description VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO roles (id, role_name, description) VALUES
  (1, 'HR Staff', 'Can create jobs, manage applications, shortlist candidates, and send interview or reject decisions.'),
  (2, 'Hiring Manager', 'Can review shortlisted candidates, view scoring details, and manage internal users.')
ON DUPLICATE KEY UPDATE
  role_name = VALUES(role_name),
  description = VALUES(description);
