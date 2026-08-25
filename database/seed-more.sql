USE uwc_hr_decision_support;

DROP TEMPORARY TABLE IF EXISTS seed_jobs_more;
CREATE TEMPORARY TABLE seed_jobs_more (
  id INT UNSIGNED,
  job_code VARCHAR(30),
  created_by_user_id INT UNSIGNED,
  title VARCHAR(180),
  department VARCHAR(120),
  location VARCHAR(180),
  salary_range VARCHAR(120),
  employment_type VARCHAR(80),
  description TEXT,
  required_qualification VARCHAR(255),
  required_experience VARCHAR(120),
  status VARCHAR(20),
  jd_file_name VARCHAR(255),
  jd_file_path VARCHAR(500),
  published_at DATETIME,
  created_at DATETIME
);

INSERT INTO seed_jobs_more (
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, required_qualification, required_experience,
  status, jd_file_name, jd_file_path, published_at, created_at
) VALUES
  (21, 'JOB021', 2, 'Frontend Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 4,200 - RM 6,500', 'Full-time', 'Build responsive frontend features and maintain React application modules.', 'Bachelor Degree in Computer Science or related field', '2 years', 'active', 'frontend-engineer.pdf', '/uploads/jd/frontend-engineer.pdf', NOW(), '2026-04-11 09:00:00'),
  (22, 'JOB022', 2, 'Software Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 4,500 - RM 7,000', 'Full-time', 'Develop software modules, review code and support production releases.', 'Bachelor Degree in Computer Science or related field', '3 years', 'active', 'software-engineer.pdf', '/uploads/jd/software-engineer.pdf', NOW(), '2026-04-12 09:00:00'),
  (23, 'JOB023', 2, 'Data Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 5,000 - RM 7,800', 'Full-time', 'Build data pipelines, warehouse models and reporting data flows.', 'Bachelor Degree in Computer Science, Data or related field', '3 years', 'active', 'data-engineer.pdf', '/uploads/jd/data-engineer.pdf', NOW(), '2026-04-13 09:00:00'),
  (24, 'JOB024', 2, 'Systems Analyst', 'Engineering', 'Batu Kawan, Penang', 'RM 4,200 - RM 6,800', 'Full-time', 'Analyse system requirements and translate business needs into technical specifications.', 'Bachelor Degree in IT or related field', '3 years', 'draft', 'systems-analyst.pdf', '/uploads/jd/systems-analyst.pdf', NULL, '2026-04-14 09:00:00'),
  (25, 'JOB025', 2, 'Cloud Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 5,500 - RM 8,500', 'Full-time', 'Maintain cloud infrastructure, deployment automation and monitoring practices.', 'Bachelor Degree in Computer Science or related field', '3 years', 'active', 'cloud-engineer.pdf', '/uploads/jd/cloud-engineer.pdf', NOW(), '2026-04-15 09:00:00'),
  (26, 'JOB026', 2, 'Automation Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 4,800 - RM 7,300', 'Full-time', 'Develop automation scripts, test pipelines and manufacturing system integrations.', 'Bachelor Degree in Engineering or related field', '3 years', 'active', 'automation-engineer.pdf', '/uploads/jd/automation-engineer.pdf', NOW(), '2026-04-16 09:00:00'),
  (27, 'JOB027', 2, 'Finance Analyst', 'Finance', 'Batu Kawan, Penang', 'RM 3,800 - RM 5,800', 'Full-time', 'Prepare financial analysis, budget tracking and management reporting.', 'Bachelor Degree in Finance or Accounting', '2 years', 'active', 'finance-analyst.pdf', '/uploads/jd/finance-analyst.pdf', NOW(), '2026-04-03 09:00:00'),
  (28, 'JOB028', 2, 'Accountant', 'Finance', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,000', 'Full-time', 'Handle accounting records, month-end closing and statutory reporting support.', 'Bachelor Degree in Accounting', '3 years', 'active', 'accountant.pdf', '/uploads/jd/accountant.pdf', NOW(), '2026-04-04 09:00:00'),
  (29, 'JOB029', 2, 'IT Support Specialist', 'IT Support', 'Batu Kawan, Penang', 'RM 3,200 - RM 5,200', 'Full-time', 'Provide user support, troubleshoot hardware and manage helpdesk tickets.', 'Diploma or Bachelor Degree in IT', '1 year', 'active', 'it-support-specialist.pdf', '/uploads/jd/it-support-specialist.pdf', NOW(), '2026-04-05 09:00:00'),
  (30, 'JOB030', 2, 'Network Administrator', 'IT Support', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,200', 'Full-time', 'Maintain network availability, firewall rules and infrastructure documentation.', 'Diploma or Bachelor Degree in IT or Networking', '2 years', 'active', 'network-administrator.pdf', '/uploads/jd/network-administrator.pdf', NOW(), '2026-04-06 09:00:00'),
  (31, 'JOB031', 2, 'Supply Chain Executive', 'Supply Chain', 'Batu Kawan, Penang', 'RM 3,500 - RM 5,500', 'Full-time', 'Coordinate material planning, supplier follow-up and delivery schedules.', 'Diploma or Bachelor Degree in Supply Chain or Business', '2 years', 'active', 'supply-chain-executive.pdf', '/uploads/jd/supply-chain-executive.pdf', NOW(), '2026-04-07 09:00:00'),
  (32, 'JOB032', 2, 'Logistics Coordinator', 'Supply Chain', 'Batu Kawan, Penang', 'RM 3,200 - RM 5,000', 'Full-time', 'Coordinate shipments, warehouse communication and logistics documentation.', 'Diploma in Logistics or Business', '1 year', 'active', 'logistics-coordinator.pdf', '/uploads/jd/logistics-coordinator.pdf', NOW(), '2026-04-08 09:00:00'),
  (33, 'JOB033', 2, 'Quality Inspector', 'Quality', 'Batu Kawan, Penang', 'RM 2,800 - RM 4,500', 'Full-time', 'Inspect product quality, record defects and support corrective actions.', 'Diploma in Engineering or Quality Management', '1 year', 'active', 'quality-inspector.pdf', '/uploads/jd/quality-inspector.pdf', NOW(), '2026-04-09 09:00:00'),
  (34, 'JOB034', 2, 'Quality Engineer', 'Quality', 'Batu Kawan, Penang', 'RM 4,200 - RM 6,800', 'Full-time', 'Analyse quality issues, lead improvement actions and support audit readiness.', 'Bachelor Degree in Engineering or Quality Management', '3 years', 'active', 'quality-engineer.pdf', '/uploads/jd/quality-engineer.pdf', NOW(), '2026-04-10 09:00:00'),
  (35, 'JOB035', 2, 'Production Supervisor', 'Manufacturing', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,300', 'Full-time', 'Supervise production line activities, manpower planning and output targets.', 'Diploma or Bachelor Degree in Manufacturing or Engineering', '3 years', 'active', 'production-supervisor.pdf', '/uploads/jd/production-supervisor.pdf', NOW(), '2026-04-11 09:00:00'),
  (36, 'JOB036', 2, 'Process Engineer', 'Manufacturing', 'Batu Kawan, Penang', 'RM 4,500 - RM 7,000', 'Full-time', 'Improve process efficiency, support yield improvement and troubleshoot production issues.', 'Bachelor Degree in Engineering', '3 years', 'active', 'process-engineer.pdf', '/uploads/jd/process-engineer.pdf', NOW(), '2026-04-12 09:00:00'),
  (37, 'JOB037', 2, 'Data Analyst', 'Data Team', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,200', 'Full-time', 'Analyse operational data, build reports and support business decision making.', 'Bachelor Degree in Data, Statistics, IT or related field', '2 years', 'active', 'data-analyst.pdf', '/uploads/jd/data-analyst.pdf', NOW(), '2026-04-13 09:00:00'),
  (38, 'JOB038', 2, 'BI Developer', 'Data Team', 'Batu Kawan, Penang', 'RM 4,500 - RM 7,000', 'Full-time', 'Develop dashboards, semantic models and analytics datasets for HR and operations.', 'Bachelor Degree in IT, Data or related field', '3 years', 'active', 'bi-developer.pdf', '/uploads/jd/bi-developer.pdf', NOW(), '2026-04-14 09:00:00'),
  (39, 'JOB039', 2, 'Procurement Executive', 'Procurement', 'Batu Kawan, Penang', 'RM 3,500 - RM 5,500', 'Full-time', 'Manage purchasing requests, supplier quotations and purchase order tracking.', 'Diploma or Bachelor Degree in Business or Supply Chain', '2 years', 'active', 'procurement-executive.pdf', '/uploads/jd/procurement-executive.pdf', NOW(), '2026-04-15 09:00:00'),
  (40, 'JOB040', 2, 'Vendor Management Specialist', 'Procurement', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,500', 'Full-time', 'Manage supplier performance, contract follow-up and vendor compliance records.', 'Bachelor Degree in Business or Supply Chain', '3 years', 'active', 'vendor-management-specialist.pdf', '/uploads/jd/vendor-management-specialist.pdf', NOW(), '2026-04-16 09:00:00'),
  (41, 'JOB041', 2, 'Customer Success Executive', 'Customer Success', 'Batu Kawan, Penang', 'RM 3,500 - RM 5,500', 'Full-time', 'Support customer onboarding, issue follow-up and relationship management.', 'Diploma or Bachelor Degree in Business or Communications', '2 years', 'active', 'customer-success-executive.pdf', '/uploads/jd/customer-success-executive.pdf', NOW(), '2026-04-17 09:00:00'),
  (42, 'JOB042', 2, 'Client Support Manager', 'Customer Success', 'Batu Kawan, Penang', 'RM 5,000 - RM 7,500', 'Full-time', 'Lead client support operations, escalation handling and service improvement.', 'Bachelor Degree in Business or related field', '4 years', 'active', 'client-support-manager.pdf', '/uploads/jd/client-support-manager.pdf', NOW(), '2026-04-18 09:00:00')
;

INSERT INTO jobs (
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, status, jd_file_name, jd_file_path, published_at, created_at
)
SELECT
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, status, jd_file_name, jd_file_path, published_at, created_at
FROM seed_jobs_more
ON DUPLICATE KEY UPDATE
  title = VALUES(title),
  department = VALUES(department),
  location = VALUES(location),
  salary_range = VALUES(salary_range),
  employment_type = VALUES(employment_type),
  description = VALUES(description),
  status = VALUES(status),
  published_at = VALUES(published_at);

INSERT INTO job_qualifications (job_id, qualification, sort_order)
SELECT id, required_qualification, 1
FROM seed_jobs_more
WHERE required_qualification IS NOT NULL AND TRIM(required_qualification) <> ''
ON DUPLICATE KEY UPDATE qualification = VALUES(qualification);

DROP TEMPORARY TABLE seed_jobs_more;

INSERT INTO application_links (job_id, token, public_path, status)
SELECT id, CONCAT(job_code, '-EXTRA-LINK'), CONCAT('/apply/', job_code), IF(status = 'active', 'active', 'disabled')
FROM jobs
WHERE id BETWEEN 21 AND 42
ON DUPLICATE KEY UPDATE
  token = VALUES(token),
  public_path = VALUES(public_path),
  status = VALUES(status);

INSERT INTO job_criteria (job_id, criteria_name, weight, description, sort_order)
SELECT j.id, c.criteria_name, c.weight, c.description, c.sort_order
FROM jobs j
JOIN (
  SELECT 'Technical Skills' AS criteria_name, 40.00 AS weight, 'Relevant technical or functional skills for the job.' AS description, 1 AS sort_order
  UNION ALL SELECT 'Experience', 25.00, 'Relevant years and depth of experience.', 2
  UNION ALL SELECT 'Education', 20.00, 'Relevant qualification and academic background.', 3
  UNION ALL SELECT 'Soft Skills', 15.00, 'Communication, teamwork and role fit.', 4
) c
WHERE j.id BETWEEN 21 AND 42
  AND NOT EXISTS (
    SELECT 1
    FROM job_criteria jc
    WHERE jc.job_id = j.id AND jc.criteria_name = c.criteria_name
  );

INSERT INTO eligibility_filters (
  job_id, min_cgpa, min_years_experience, internship_accepted,
  required_qualification, required_language, required_location, max_notice_period_days
)
SELECT id, 3.00, 2.0, 0, 'Diploma or Bachelor Degree', 'English', 'Malaysia', 60
FROM jobs
WHERE id BETWEEN 21 AND 42
ON DUPLICATE KEY UPDATE
  min_cgpa = VALUES(min_cgpa),
  min_years_experience = VALUES(min_years_experience),
  required_qualification = VALUES(required_qualification),
  required_language = VALUES(required_language),
  required_location = VALUES(required_location),
  max_notice_period_days = VALUES(max_notice_period_days);

INSERT INTO candidates (id, full_name, email, phone, current_cgpa, years_experience, notice_period_days, current_location) VALUES
  (100, 'Liyana Rahman', 'liyana.rahman@example.com', '+6012-7000001', 3.86, 4.0, 30, 'Penang'),
  (101, 'Marcus Tan', 'marcus.tan@example.com', '+6012-7000002', 3.58, 3.0, 45, 'Penang'),
  (102, 'Priya Nair', 'priya.nair@example.com', '+6012-7000003', 3.91, 7.0, 30, 'Kedah'),
  (103, 'Ong Jun Hao', 'ong.junhao@example.com', '+6012-7000004', 3.44, 4.0, 30, 'Penang'),
  (104, 'Nur Iman', 'nur.iman@example.com', '+6012-7000005', 3.27, 2.0, 60, 'Perak'),
  (105, 'Samantha Lim', 'samantha.lim@example.com', '+6012-7000006', 3.73, 6.0, 30, 'Penang'),
  (106, 'Kevin Goh', 'kevin.goh@example.com', '+6012-7000007', 3.19, 2.0, 45, 'Penang'),
  (107, 'Rachel Ong', 'rachel.ong@example.com', '+6012-7000008', 3.67, 5.0, 30, 'Penang'),
  (108, 'Hafiz Ismail', 'hafiz.ismail@example.com', '+6012-7000009', 3.36, 3.0, 60, 'Kuala Lumpur'),
  (109, 'Chloe Wong', 'chloe.wong@example.com', '+6012-7000010', 3.82, 5.0, 30, 'Penang'),
  (110, 'Daniel Wong', 'daniel.wong@example.com', '+6012-7000011', 3.08, 2.0, 45, 'Penang'),
  (111, 'Siti Mariam', 'siti.mariam@example.com', '+6012-7000012', 3.50, 4.0, 30, 'Kedah')
ON DUPLICATE KEY UPDATE
  full_name = VALUES(full_name),
  phone = VALUES(phone),
  current_cgpa = VALUES(current_cgpa),
  years_experience = VALUES(years_experience),
  notice_period_days = VALUES(notice_period_days),
  current_location = VALUES(current_location);

INSERT INTO applications (
  id, job_id, candidate_id, application_link_id, application_status,
  eligibility_status, total_score, rank_no, ai_summary, submitted_at, reviewed_at
) VALUES
  (100, 1, 100, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 82.40, 5, 'Liyana Rahman has strong React, TypeScript and dashboard delivery experience.', '2026-04-01 09:00:00', '2026-04-02 10:00:00'),
  (101, 1, 101, (SELECT id FROM application_links WHERE job_id = 1), 'new', 'eligible', 80.20, 6, 'Marcus Tan shows practical frontend delivery and testing experience.', '2026-04-02 09:00:00', NULL),
  (102, 1, 102, (SELECT id FROM application_links WHERE job_id = 1), 'shortlisted', 'eligible', 87.30, 2, 'Priya Nair has excellent frontend architecture and cloud integration experience.', '2026-04-03 09:00:00', '2026-04-04 11:00:00'),
  (103, 1, 103, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 78.60, 7, 'Ong Jun Hao has solid JavaScript, React and API integration experience.', '2026-04-04 09:00:00', '2026-04-05 11:00:00'),
  (104, 1, 104, (SELECT id FROM application_links WHERE job_id = 1), 'new', 'eligible', 72.50, 10, 'Nur Iman has junior-to-mid frontend experience and relevant academic background.', '2026-04-05 09:00:00', NULL),
  (105, 1, 105, (SELECT id FROM application_links WHERE job_id = 1), 'interview', 'eligible', 85.10, 3, 'Samantha Lim has strong React, UX implementation and component library experience.', '2026-04-06 09:00:00', '2026-04-07 12:00:00'),
  (106, 1, 106, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 70.80, 11, 'Kevin Goh has basic frontend experience and can support implementation tasks.', '2026-04-07 09:00:00', '2026-04-08 10:00:00'),
  (107, 1, 107, (SELECT id FROM application_links WHERE job_id = 1), 'shortlisted', 'eligible', 84.40, 4, 'Rachel Ong has strong UI engineering, TypeScript and collaboration experience.', '2026-04-08 09:00:00', '2026-04-09 11:00:00'),
  (108, 1, 108, (SELECT id FROM application_links WHERE job_id = 1), 'filtered_out', 'filtered_out', 66.20, NULL, 'Hafiz Ismail has relevant skills and can be reviewed through the score breakdown.', '2026-04-09 09:00:00', '2026-04-10 10:00:00'),
  (109, 1, 109, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 81.90, 6, 'Chloe Wong has good frontend experience with React and accessibility practices.', '2026-04-10 09:00:00', '2026-04-11 10:00:00'),
  (110, 1, 110, (SELECT id FROM application_links WHERE job_id = 1), 'new', 'eligible', 69.40, 12, 'Daniel Wong has developing frontend skills and relevant project experience.', '2026-04-11 09:00:00', NULL),
  (111, 1, 111, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 76.80, 8, 'Siti Mariam has React, CSS and basic backend integration experience.', '2026-04-12 09:00:00', '2026-04-13 10:00:00')
ON DUPLICATE KEY UPDATE
  application_status = VALUES(application_status),
  eligibility_status = VALUES(eligibility_status),
  total_score = VALUES(total_score),
  rank_no = VALUES(rank_no),
  ai_summary = VALUES(ai_summary),
  submitted_at = VALUES(submitted_at),
  reviewed_at = VALUES(reviewed_at);

UPDATE applications a
JOIN jobs j ON j.id = a.job_id
SET a.assigned_hr_user_id = j.created_by_user_id
WHERE a.assigned_hr_user_id IS NULL
  AND a.reviewed_at IS NOT NULL;

DELETE FROM resumes
WHERE original_file_name LIKE 'resume-application-%.pdf'
  AND application_id BETWEEN 100 AND 111;

INSERT INTO resumes (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes, parsing_status)
SELECT id, CONCAT('resume-application-', id, '.pdf'), CONCAT('/uploads/resumes/resume-application-', id, '.pdf'), 'application/pdf', 220000 + (id * 512), 'parsed'
FROM applications
WHERE id BETWEEN 100 AND 111;

INSERT INTO score_breakdowns (application_id, criteria_id, raw_score, weight, weighted_score, explanation)
SELECT a.id, jc.id,
  CASE jc.sort_order
    WHEN 1 THEN LEAST(100, a.total_score + 7)
    WHEN 2 THEN LEAST(100, a.total_score + 2)
    WHEN 3 THEN GREATEST(0, a.total_score - 3)
    ELSE GREATEST(0, a.total_score - 6)
  END AS raw_score,
  jc.weight,
  ROUND((CASE jc.sort_order
    WHEN 1 THEN LEAST(100, a.total_score + 7)
    WHEN 2 THEN LEAST(100, a.total_score + 2)
    WHEN 3 THEN GREATEST(0, a.total_score - 3)
    ELSE GREATEST(0, a.total_score - 6)
  END / 100) * jc.weight, 2) AS weighted_score,
  CONCAT(jc.criteria_name, ' evaluated from parsed resume content and senior frontend requirements.') AS explanation
FROM applications a
JOIN job_criteria jc ON jc.job_id = a.job_id
WHERE a.id BETWEEN 100 AND 111
ON DUPLICATE KEY UPDATE
  raw_score = VALUES(raw_score),
  weight = VALUES(weight),
  weighted_score = VALUES(weighted_score),
  explanation = VALUES(explanation);

INSERT INTO score_breakdown_items (score_breakdown_id, requirement_text, match_status, evidence_text, item_score)
SELECT sb.id, jc.criteria_name,
  CASE WHEN sb.raw_score >= 80 THEN 'matched' WHEN sb.raw_score >= 60 THEN 'partial' ELSE 'missing' END,
  CONCAT('Parsed resume contains evidence related to ', jc.criteria_name, ' for the Senior Frontend Developer role.'),
  sb.raw_score
FROM score_breakdowns sb
JOIN job_criteria jc ON jc.id = sb.criteria_id
WHERE sb.application_id BETWEEN 100 AND 111
ON DUPLICATE KEY UPDATE
  match_status = VALUES(match_status),
  evidence_text = VALUES(evidence_text),
  item_score = VALUES(item_score);

