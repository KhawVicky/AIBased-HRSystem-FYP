ALTER TABLE resumes
  ADD COLUMN parsed_profile_json LONGTEXT NULL AFTER parsed_text,
  ADD COLUMN parse_metadata_json TEXT NULL AFTER parsed_profile_json,
  ADD COLUMN parser_version VARCHAR(80) NULL AFTER parse_metadata_json,
  ADD COLUMN parsed_at DATETIME NULL AFTER parser_version;
