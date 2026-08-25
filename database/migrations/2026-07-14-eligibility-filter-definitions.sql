CREATE TABLE IF NOT EXISTS eligibility_filter_definitions (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  filter_key VARCHAR(100) NOT NULL UNIQUE,
  filter_name VARCHAR(160) NOT NULL,
  filter_type ENUM('dropdown', 'text', 'number') NOT NULL DEFAULT 'dropdown',
  is_system TINYINT(1) NOT NULL DEFAULT 0,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filter_options (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  filter_id INT UNSIGNED NOT NULL,
  option_label VARCHAR(160) NOT NULL,
  sort_order INT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_eligibility_filter_options_definition FOREIGN KEY (filter_id) REFERENCES eligibility_filter_definitions(id) ON DELETE CASCADE,
  UNIQUE KEY uq_eligibility_filter_option (filter_id, option_label),
  INDEX idx_eligibility_filter_options_filter (filter_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS eligibility_filter_seed_state (
  id TINYINT UNSIGNED PRIMARY KEY,
  seeded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'minCGPA', 'Minimum CGPA', 1, 10
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'minExperience', 'Minimum Experience', 1, 20
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'educationLevel', 'Education Level', 1, 30
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'maxNoticePeriod', 'Max Notice Period', 1, 40
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'requiredLanguage', 'Required Language', 1, 50
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'requiredLocation', 'Candidate Location', 1, 60
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_definitions (filter_key, filter_name, is_system, sort_order)
SELECT 'internshipAccepted', 'Internship Accepted', 1, 70
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT INTO eligibility_filter_options (filter_id, option_label, sort_order)
SELECT d.id, options.option_label, options.sort_order
FROM eligibility_filter_definitions d
JOIN (
  SELECT 'minExperience' AS filter_key, 'Internship' AS option_label, 10 AS sort_order UNION ALL
  SELECT 'minExperience', '0 year', 20 UNION ALL
  SELECT 'minExperience', '1 year', 30 UNION ALL
  SELECT 'minExperience', '2 years', 40 UNION ALL
  SELECT 'minExperience', '3 years', 50 UNION ALL
  SELECT 'minExperience', '4 years', 60 UNION ALL
  SELECT 'minExperience', '5+ years', 70 UNION ALL
  SELECT 'minExperience', '8+ years', 80 UNION ALL
  SELECT 'minExperience', '10+ years', 90 UNION ALL
  SELECT 'educationLevel', 'SPM', 10 UNION ALL
  SELECT 'educationLevel', 'STPM / Foundation / Matriculation', 20 UNION ALL
  SELECT 'educationLevel', 'Diploma', 30 UNION ALL
  SELECT 'educationLevel', 'Bachelor Degree', 40 UNION ALL
  SELECT 'educationLevel', 'Master Degree', 50 UNION ALL
  SELECT 'educationLevel', 'PhD', 60 UNION ALL
  SELECT 'maxNoticePeriod', 'Any', 10 UNION ALL
  SELECT 'maxNoticePeriod', 'Immediate', 20 UNION ALL
  SELECT 'maxNoticePeriod', '14 days', 30 UNION ALL
  SELECT 'maxNoticePeriod', '30 days', 40 UNION ALL
  SELECT 'maxNoticePeriod', '60 days', 50 UNION ALL
  SELECT 'maxNoticePeriod', '90 days', 60 UNION ALL
  SELECT 'requiredLanguage', 'Any', 10 UNION ALL
  SELECT 'requiredLanguage', 'English', 20 UNION ALL
  SELECT 'requiredLanguage', 'Bahasa Malaysia', 30 UNION ALL
  SELECT 'requiredLanguage', 'Mandarin', 40 UNION ALL
  SELECT 'requiredLanguage', 'Tamil', 50 UNION ALL
  SELECT 'requiredLanguage', 'Japanese', 60 UNION ALL
  SELECT 'requiredLanguage', 'Korean', 70 UNION ALL
  SELECT 'requiredLocation', 'Any', 10 UNION ALL
  SELECT 'requiredLocation', 'Penang', 20 UNION ALL
  SELECT 'requiredLocation', 'Kuala Lumpur', 30 UNION ALL
  SELECT 'requiredLocation', 'Selangor', 40 UNION ALL
  SELECT 'requiredLocation', 'Johor', 50 UNION ALL
  SELECT 'requiredLocation', 'Perak', 60 UNION ALL
  SELECT 'requiredLocation', 'Malaysia only', 70 UNION ALL
  SELECT 'requiredLocation', 'Open to relocation', 80 UNION ALL
  SELECT 'internshipAccepted', 'Any', 10 UNION ALL
  SELECT 'internshipAccepted', 'Yes', 20 UNION ALL
  SELECT 'internshipAccepted', 'No', 30
) options ON options.filter_key = d.filter_key
WHERE NOT EXISTS (SELECT 1 FROM eligibility_filter_seed_state WHERE id = 1);

INSERT IGNORE INTO eligibility_filter_seed_state (id) VALUES (1);
