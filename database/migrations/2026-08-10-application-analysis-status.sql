ALTER TABLE applications
  ADD COLUMN analysis_status VARCHAR(32) NULL AFTER scoring_version,
  ADD INDEX idx_applications_analysis_status (analysis_status);
