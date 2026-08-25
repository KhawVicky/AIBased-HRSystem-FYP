USE uwc_hr_decision_support;

ALTER TABLE applications
  DROP COLUMN IF EXISTS eligibility_reason;
