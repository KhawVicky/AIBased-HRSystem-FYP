ALTER TABLE eligibility_filter_definitions
  ADD COLUMN IF NOT EXISTS filter_type ENUM('dropdown', 'text', 'number') NOT NULL DEFAULT 'dropdown' AFTER filter_name;

UPDATE eligibility_filter_definitions
SET filter_type = 'number'
WHERE filter_key = 'minCGPA';

UPDATE eligibility_filter_definitions
SET filter_type = 'dropdown'
WHERE filter_type IS NULL OR filter_type = '';
