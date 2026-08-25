ALTER TABLE job_criteria
  ADD COLUMN criterion_type ENUM(
    'relevant_skill',
    'relevant_experience',
    'education_relevance',
    'domain_knowledge',
    'preferred_certification',
    'job_related_language'
  ) NOT NULL DEFAULT 'relevant_skill' AFTER criteria_name,
  ADD COLUMN source_text TEXT NULL AFTER description,
  ADD COLUMN evidence_rule TEXT NULL AFTER source_text;
