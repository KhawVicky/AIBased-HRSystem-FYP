USE uwc_hr_decision_support;

ALTER TABLE resumes
  DROP INDEX uq_resumes_application,
  ADD INDEX idx_resumes_application (application_id);
