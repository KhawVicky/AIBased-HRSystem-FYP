INSERT INTO job_qualifications (job_id, qualification, sort_order)
SELECT j.id, j.required_qualification, 1
FROM jobs j
WHERE j.required_qualification IS NOT NULL
  AND TRIM(j.required_qualification) <> ''
  AND NOT EXISTS (
    SELECT 1
    FROM job_qualifications jq
    WHERE jq.job_id = j.id
  );

ALTER TABLE jobs
  DROP COLUMN required_qualification,
  DROP COLUMN required_experience;
