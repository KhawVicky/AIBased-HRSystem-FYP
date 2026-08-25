USE uwc_hr_decision_support;

DROP TEMPORARY TABLE IF EXISTS seed_jobs_demo;
CREATE TEMPORARY TABLE seed_jobs_demo (
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

INSERT INTO seed_jobs_demo (
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, required_qualification, required_experience,
  status, jd_file_name, jd_file_path, published_at, created_at
) VALUES
  (2, 'JOB002', 2, 'Product Manager', 'Product', 'Batu Kawan, Penang', 'RM 5,500 - RM 8,000', 'Full-time', 'Lead product planning, roadmap execution, stakeholder alignment and delivery tracking.', 'Bachelor Degree in Business, IT or related field', '4 years', 'active', 'product-manager.pdf', '/uploads/jd/product-manager.pdf', NOW(), '2026-03-20 09:00:00'),
  (3, 'JOB003', 2, 'UX Designer', 'Design', 'Batu Kawan, Penang', 'RM 3,500 - RM 5,500', 'Full-time', 'Design user-friendly web experiences, create wireframes, prototypes and usability improvements.', 'Diploma or Bachelor Degree in Design or related field', '3 years', 'closed', 'ux-designer.pdf', '/uploads/jd/ux-designer.pdf', '2026-02-28 09:00:00', '2026-02-28 09:00:00'),
  (4, 'JOB004', 2, 'Backend Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,000', 'Full-time', 'Develop backend services, APIs, database structures and system integrations.', 'Bachelor Degree in Computer Science or related field', '3 years', 'draft', 'backend-engineer.pdf', '/uploads/jd/backend-engineer.pdf', NULL, '2026-03-25 09:00:00'),
  (5, 'JOB005', 2, 'DevOps Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 5,000 - RM 7,500', 'Full-time', 'Manage CI/CD pipelines, cloud deployment, monitoring and infrastructure reliability.', 'Bachelor Degree in Computer Science or related field', '3 years', 'active', 'devops-engineer.pdf', '/uploads/jd/devops-engineer.pdf', NOW(), '2026-04-01 09:00:00'),
  (6, 'JOB006', 2, 'Full Stack Developer', 'Engineering', 'Batu Kawan, Penang', 'RM 4,800 - RM 7,200', 'Full-time', 'Build full stack web features using modern frontend, backend and database technologies.', 'Bachelor Degree in Computer Science or related field', '3 years', 'active', 'full-stack-developer.pdf', '/uploads/jd/full-stack-developer.pdf', NOW(), '2026-03-28 09:00:00'),
  (7, 'JOB007', 2, 'QA Engineer', 'Engineering', 'Batu Kawan, Penang', 'RM 3,500 - RM 5,500', 'Full-time', 'Plan test cases, execute QA cycles, report defects and support release quality.', 'Diploma or Bachelor Degree in IT or related field', '2 years', 'closed', 'qa-engineer.pdf', '/uploads/jd/qa-engineer.pdf', '2026-02-15 09:00:00', '2026-02-15 09:00:00'),
  (8, 'JOB008', 2, 'Mobile Developer (iOS)', 'Engineering', 'Batu Kawan, Penang', 'RM 4,500 - RM 6,800', 'Full-time', 'Develop and maintain iOS mobile applications and integrate with backend APIs.', 'Bachelor Degree in Computer Science or related field', '2 years', 'active', 'ios-developer.pdf', '/uploads/jd/ios-developer.pdf', NOW(), '2026-04-05 09:00:00'),
  (9, 'JOB009', 2, 'UI Designer', 'Design', 'Batu Kawan, Penang', 'RM 3,200 - RM 5,000', 'Full-time', 'Create interface designs, design systems, screen layouts and visual assets.', 'Diploma or Bachelor Degree in Design', '2 years', 'active', 'ui-designer.pdf', '/uploads/jd/ui-designer.pdf', NOW(), '2026-03-18 09:00:00'),
  (10, 'JOB010', 2, 'Graphic Designer', 'Design', 'Batu Kawan, Penang', 'RM 3,000 - RM 4,800', 'Full-time', 'Produce visual assets, communication materials and brand-aligned graphics.', 'Diploma or Bachelor Degree in Design', '2 years', 'active', 'graphic-designer.pdf', '/uploads/jd/graphic-designer.pdf', NOW(), '2026-04-02 09:00:00'),
  (11, 'JOB011', 2, 'Product Designer', 'Product', 'Batu Kawan, Penang', 'RM 4,200 - RM 6,500', 'Full-time', 'Translate product requirements into usable workflows, prototypes and design specs.', 'Bachelor Degree in Design, IT or related field', '3 years', 'active', 'product-designer.pdf', '/uploads/jd/product-designer.pdf', NOW(), '2026-03-22 09:00:00'),
  (12, 'JOB012', 2, 'Business Analyst', 'Product', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,000', 'Full-time', 'Gather requirements, document processes and support product delivery decisions.', 'Bachelor Degree in Business, IT or related field', '2 years', 'draft', 'business-analyst.pdf', '/uploads/jd/business-analyst.pdf', NULL, '2026-04-08 09:00:00'),
  (13, 'JOB013', 2, 'Marketing Manager', 'Marketing', 'Batu Kawan, Penang', 'RM 5,000 - RM 7,500', 'Full-time', 'Plan and manage marketing campaigns, brand communication and performance tracking.', 'Bachelor Degree in Marketing or related field', '4 years', 'active', 'marketing-manager.pdf', '/uploads/jd/marketing-manager.pdf', NOW(), '2026-03-10 09:00:00'),
  (14, 'JOB014', 2, 'Content Writer', 'Marketing', 'Batu Kawan, Penang', 'RM 3,000 - RM 4,800', 'Full-time', 'Write recruitment, corporate and marketing content for digital channels.', 'Diploma or Bachelor Degree in Communications', '2 years', 'active', 'content-writer.pdf', '/uploads/jd/content-writer.pdf', NOW(), '2026-03-12 09:00:00'),
  (15, 'JOB015', 2, 'Social Media Manager', 'Marketing', 'Batu Kawan, Penang', 'RM 4,000 - RM 6,000', 'Full-time', 'Manage social media planning, content calendar, publishing and analytics.', 'Bachelor Degree in Marketing or related field', '3 years', 'closed', 'social-media-manager.pdf', '/uploads/jd/social-media-manager.pdf', '2026-02-20 09:00:00', '2026-02-20 09:00:00'),
  (16, 'JOB016', 2, 'Sales Manager', 'Sales', 'Batu Kawan, Penang', 'RM 5,000 - RM 8,000', 'Full-time', 'Lead sales planning, customer relationship management and sales team performance.', 'Bachelor Degree in Business or related field', '4 years', 'active', 'sales-manager.pdf', '/uploads/jd/sales-manager.pdf', NOW(), '2026-04-03 09:00:00'),
  (17, 'JOB017', 2, 'Account Executive', 'Sales', 'Batu Kawan, Penang', 'RM 3,200 - RM 5,200', 'Full-time', 'Manage client accounts, follow up sales opportunities and support revenue growth.', 'Diploma or Bachelor Degree in Business', '2 years', 'active', 'account-executive.pdf', '/uploads/jd/account-executive.pdf', NOW(), '2026-03-25 09:00:00'),
  (18, 'JOB018', 2, 'HR Manager', 'Human Resources', 'Batu Kawan, Penang', 'RM 5,500 - RM 8,500', 'Full-time', 'Manage HR operations, recruitment process, policies and employee support.', 'Bachelor Degree in Human Resource Management', '5 years', 'active', 'hr-manager.pdf', '/uploads/jd/hr-manager.pdf', NOW(), '2026-03-30 09:00:00'),
  (19, 'JOB019', 2, 'Recruiter', 'Human Resources', 'Batu Kawan, Penang', 'RM 3,200 - RM 5,000', 'Full-time', 'Source candidates, coordinate interviews and support recruitment administration.', 'Diploma or Bachelor Degree in HR or Business', '1 year', 'draft', 'recruiter.pdf', '/uploads/jd/recruiter.pdf', NULL, '2026-04-10 09:00:00'),
  (20, 'JOB020', 2, 'Operations Manager', 'Operations', 'Batu Kawan, Penang', 'RM 5,500 - RM 8,500', 'Full-time', 'Manage operational workflow, resource planning and department performance tracking.', 'Bachelor Degree in Operations, Engineering or Business', '5 years', 'active', 'operations-manager.pdf', '/uploads/jd/operations-manager.pdf', NOW(), '2026-04-01 09:00:00')
;

INSERT INTO jobs (
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, status, jd_file_name, jd_file_path, published_at, created_at
)
SELECT
  id, job_code, created_by_user_id, title, department, location, salary_range,
  employment_type, description, status, jd_file_name, jd_file_path, published_at, created_at
FROM seed_jobs_demo
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
FROM seed_jobs_demo
WHERE required_qualification IS NOT NULL AND TRIM(required_qualification) <> ''
ON DUPLICATE KEY UPDATE qualification = VALUES(qualification);

DROP TEMPORARY TABLE seed_jobs_demo;

INSERT INTO application_links (job_id, token, public_path, status)
SELECT id, CONCAT(job_code, '-DEMO-LINK'), CONCAT('/apply/', job_code), IF(status = 'active', 'active', 'disabled')
FROM jobs
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
WHERE j.id BETWEEN 2 AND 20
ON DUPLICATE KEY UPDATE
  weight = VALUES(weight),
  description = VALUES(description);

INSERT INTO eligibility_filters (
  job_id, min_cgpa, min_years_experience, internship_accepted,
  required_qualification, required_language, required_location, max_notice_period_days
)
SELECT id, 3.00, 2.0, 0, 'Diploma or Bachelor Degree', 'English', 'Malaysia', 60
FROM jobs
WHERE id BETWEEN 2 AND 20
ON DUPLICATE KEY UPDATE
  min_cgpa = VALUES(min_cgpa),
  min_years_experience = VALUES(min_years_experience),
  required_qualification = VALUES(required_qualification),
  required_language = VALUES(required_language),
  required_location = VALUES(required_location),
  max_notice_period_days = VALUES(max_notice_period_days);

INSERT INTO candidates (id, full_name, email, phone, current_cgpa, years_experience, notice_period_days, current_location) VALUES
  (3, 'Bob Martinez', 'bob.martinez@example.com', '+6011-23456789', 3.81, 6.0, 30, 'Penang'),
  (4, 'Carol Johnson', 'carol.johnson@example.com', '+6013-4567890', 3.68, 5.0, 30, 'Penang'),
  (5, 'David Kim', 'david.kim@example.com', '+6014-5678901', 3.45, 4.0, 30, 'Penang'),
  (6, 'Emma Wilson', 'emma.wilson@example.com', '+6016-7890123', 2.74, 3.0, 30, 'Kuala Lumpur'),
  (7, 'Farah Ahmad', 'farah.ahmad@example.com', '+6017-1010101', 3.55, 5.0, 45, 'Penang'),
  (8, 'Goh Wei Ming', 'wei.ming@example.com', '+6018-2020202', 3.33, 4.0, 30, 'Penang'),
  (9, 'Nur Aisyah', 'nur.aisyah@example.com', '+6019-3030303', 3.72, 4.0, 60, 'Kedah'),
  (10, 'Jason Lee', 'jason.lee@example.com', '+6012-4040404', 3.20, 3.0, 45, 'Penang'),
  (11, 'Mei Ling', 'mei.ling@example.com', '+6016-5050505', 3.90, 5.0, 30, 'Penang'),
  (12, 'Arjun Kumar', 'arjun.kumar@example.com', '+6017-6060606', 3.10, 3.0, 60, 'Perak')
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
  (3, 1, 3, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 83.00, 2, 'Bob Martinez is a strong frontend candidate with React, JavaScript, Python and Docker experience.', '2026-03-24 09:00:00', '2026-03-25 11:00:00'),
  (4, 1, 4, (SELECT id FROM application_links WHERE job_id = 1), 'reviewed', 'eligible', 76.00, 3, 'Carol Johnson has relevant React, Vue.js, GraphQL and MongoDB experience.', '2026-03-23 09:00:00', '2026-03-24 14:00:00'),
  (5, 1, 5, (SELECT id FROM application_links WHERE job_id = 1), 'new', 'eligible', 74.00, 4, 'David Kim has React, Angular, Java and PostgreSQL experience.', '2026-03-22 09:00:00', NULL),
  (6, 1, 6, (SELECT id FROM application_links WHERE job_id = 1), 'filtered_out', 'filtered_out', 55.00, NULL, 'Emma Wilson has frontend skills and can be reviewed through the score breakdown.', '2026-03-21 09:00:00', '2026-03-22 10:00:00'),
  (7, 2, 7, (SELECT id FROM application_links WHERE job_id = 2), 'shortlisted', 'eligible', 86.00, 1, 'Farah Ahmad shows strong product coordination and stakeholder communication.', '2026-03-25 10:00:00', '2026-03-26 10:00:00'),
  (8, 2, 8, (SELECT id FROM application_links WHERE job_id = 2), 'reviewed', 'eligible', 78.00, 2, 'Goh Wei Ming has business analysis and agile project exposure.', '2026-03-26 10:00:00', '2026-03-27 11:00:00'),
  (9, 3, 9, (SELECT id FROM application_links WHERE job_id = 3), 'interview', 'eligible', 85.00, 1, 'Nur Aisyah has strong UX and design research experience.', '2026-03-01 09:00:00', '2026-03-02 09:00:00'),
  (10, 5, 10, (SELECT id FROM application_links WHERE job_id = 5), 'reviewed', 'eligible', 79.00, 1, 'Jason Lee has cloud operations and CI/CD exposure.', '2026-04-02 09:00:00', '2026-04-03 09:00:00'),
  (11, 6, 11, (SELECT id FROM application_links WHERE job_id = 6), 'shortlisted', 'eligible', 84.00, 1, 'Mei Ling has strong full stack delivery experience.', '2026-04-02 11:00:00', '2026-04-03 14:00:00'),
  (12, 8, 12, (SELECT id FROM application_links WHERE job_id = 8), 'new', 'eligible', 77.00, 1, 'Arjun Kumar has iOS and API integration experience.', '2026-04-06 09:00:00', NULL)
ON DUPLICATE KEY UPDATE
  application_status = VALUES(application_status),
  eligibility_status = VALUES(eligibility_status),
  total_score = VALUES(total_score),
  rank_no = VALUES(rank_no),
  ai_summary = VALUES(ai_summary),
  reviewed_at = VALUES(reviewed_at);

UPDATE applications a
JOIN jobs j ON j.id = a.job_id
SET a.assigned_hr_user_id = j.created_by_user_id
WHERE a.assigned_hr_user_id IS NULL
  AND a.reviewed_at IS NOT NULL;

DELETE FROM resumes
WHERE original_file_name LIKE 'resume-application-%.pdf';

INSERT INTO resumes (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes, parsing_status)
SELECT id, CONCAT('resume-application-', id, '.pdf'), CONCAT('/uploads/resumes/resume-application-', id, '.pdf'), 'application/pdf', 180000 + (id * 1024), 'parsed'
FROM applications;

INSERT INTO score_breakdowns (application_id, criteria_id, raw_score, weight, weighted_score, explanation)
SELECT a.id, jc.id,
  CASE jc.sort_order
    WHEN 1 THEN LEAST(100, a.total_score + 6)
    WHEN 2 THEN LEAST(100, a.total_score + 1)
    WHEN 3 THEN GREATEST(0, a.total_score - 2)
    ELSE GREATEST(0, a.total_score - 5)
  END AS raw_score,
  jc.weight,
  ROUND((CASE jc.sort_order
    WHEN 1 THEN LEAST(100, a.total_score + 6)
    WHEN 2 THEN LEAST(100, a.total_score + 1)
    WHEN 3 THEN GREATEST(0, a.total_score - 2)
    ELSE GREATEST(0, a.total_score - 5)
  END / 100) * jc.weight, 2) AS weighted_score,
  CONCAT(jc.criteria_name, ' evaluated from parsed resume content and job requirements.') AS explanation
FROM applications a
JOIN job_criteria jc ON jc.job_id = a.job_id
WHERE a.id BETWEEN 3 AND 12
ON DUPLICATE KEY UPDATE
  raw_score = VALUES(raw_score),
  weight = VALUES(weight),
  weighted_score = VALUES(weighted_score),
  explanation = VALUES(explanation);

INSERT INTO score_breakdown_items (score_breakdown_id, requirement_text, match_status, evidence_text, item_score)
SELECT sb.id, jc.criteria_name,
  CASE WHEN sb.raw_score >= 80 THEN 'matched' WHEN sb.raw_score >= 60 THEN 'partial' ELSE 'missing' END,
  CONCAT('Parsed resume contains evidence related to ', jc.criteria_name, '.'),
  sb.raw_score
FROM score_breakdowns sb
JOIN job_criteria jc ON jc.id = sb.criteria_id
WHERE sb.application_id BETWEEN 3 AND 12
ON DUPLICATE KEY UPDATE
  match_status = VALUES(match_status),
  evidence_text = VALUES(evidence_text),
  item_score = VALUES(item_score);

