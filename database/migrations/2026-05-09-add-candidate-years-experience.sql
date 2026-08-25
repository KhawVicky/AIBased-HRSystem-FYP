USE uwc_hr_decision_support;

ALTER TABLE candidates
  ADD COLUMN IF NOT EXISTS years_experience DECIMAL(4,1) NULL AFTER current_cgpa;

UPDATE candidates SET years_experience = 8.0 WHERE id = 1;
UPDATE candidates SET years_experience = 2.0 WHERE id = 2;
UPDATE candidates SET years_experience = 6.0 WHERE id = 3;
UPDATE candidates SET years_experience = 5.0 WHERE id = 4;
UPDATE candidates SET years_experience = 4.0 WHERE id = 5;
UPDATE candidates SET years_experience = 3.0 WHERE id = 6;
UPDATE candidates SET years_experience = 5.0 WHERE id = 7;
UPDATE candidates SET years_experience = 4.0 WHERE id = 8;
UPDATE candidates SET years_experience = 4.0 WHERE id = 9;
UPDATE candidates SET years_experience = 3.0 WHERE id = 10;
UPDATE candidates SET years_experience = 5.0 WHERE id = 11;
UPDATE candidates SET years_experience = 3.0 WHERE id = 12;
UPDATE candidates SET years_experience = 4.0 WHERE id = 100;
UPDATE candidates SET years_experience = 3.0 WHERE id = 101;
UPDATE candidates SET years_experience = 7.0 WHERE id = 102;
UPDATE candidates SET years_experience = 4.0 WHERE id = 103;
UPDATE candidates SET years_experience = 2.0 WHERE id = 104;
UPDATE candidates SET years_experience = 6.0 WHERE id = 105;
UPDATE candidates SET years_experience = 2.0 WHERE id = 106;
UPDATE candidates SET years_experience = 5.0 WHERE id = 107;
UPDATE candidates SET years_experience = 3.0 WHERE id = 108;
UPDATE candidates SET years_experience = 5.0 WHERE id = 109;
UPDATE candidates SET years_experience = 2.0 WHERE id = 110;
UPDATE candidates SET years_experience = 4.0 WHERE id = 111;
