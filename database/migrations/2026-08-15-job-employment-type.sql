-- Add the explicit job type column for existing installations.
SET @has_employment_type_column := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'jobs'
    AND COLUMN_NAME = 'employment_type'
);

SET @add_employment_type_sql := IF(
  @has_employment_type_column = 0,
  'ALTER TABLE jobs ADD COLUMN employment_type VARCHAR(80) NULL',
  'SELECT 1'
);

PREPARE add_employment_type_statement FROM @add_employment_type_sql;
EXECUTE add_employment_type_statement;
DEALLOCATE PREPARE add_employment_type_statement;

UPDATE jobs j
SET j.employment_type = CASE
  WHEN EXISTS (
    SELECT 1
    FROM eligibility_filters ef
    WHERE ef.job_id = j.id
      AND ef.internship_accepted = 1
  )
    OR EXISTS (
      SELECT 1
      FROM job_eligibility_filter_values jv
      WHERE jv.job_id = j.id
        AND jv.filter_key = 'internshipAccepted'
        AND LOWER(TRIM(COALESCE(jv.filter_value, ''))) = 'yes'
    )
    THEN 'Internship'
  ELSE 'Full-time'
END
WHERE j.employment_type IS NULL OR TRIM(j.employment_type) = '';
