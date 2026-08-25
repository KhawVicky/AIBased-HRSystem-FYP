# Database

Local database for the UWC HR Decision Support System.

## XAMPP MySQL

Database name:

```sql
uwc_hr_decision_support
```

Schema file:

```text
database/schema.sql
```

Import command used locally:

```powershell
Get-Content -LiteralPath database\schema.sql | C:\xampp\mysql\bin\mysql.exe -u root
```

## phpMyAdmin

Open:

```text
http://localhost/phpmyadmin
```

Then select:

```text
uwc_hr_decision_support
```

## Demo Data

The schema includes demo records for:

- Roles: `1 = HR Staff`, `2 = Hiring Manager`
- Users: HR staff and hiring manager. `users.role_id` references `roles.id`.
- Job: `JOB001` Senior Frontend Developer
- Application link: `/apply/JOB001`
- Candidates: Alice Chen and Daniel Tan
- Ranking and score breakdown examples

Additional seed data:

```powershell
Get-Content -LiteralPath database\seed-demo.sql | C:\xampp\mysql\bin\mysql.exe -u root
Get-Content -LiteralPath database\seed-more.sql | C:\xampp\mysql\bin\mysql.exe -u root
```

The final schema has 20 tables and does not use `candidate_job_history`. Candidate job history is derived from `applications`; duplicate resubmission history is stored in `application_submission_history`.

## Local API

The frontend reads data through the XAMPP Apache PHP API:

```text
http://localhost/uwc-hr-api/api.php
```

Deploy API source to Apache:

```powershell
Copy-Item -LiteralPath server\api.php -Destination C:\xampp\htdocs\uwc-hr-api\api.php -Force
```

Quick checks:

```text
http://localhost/uwc-hr-api/api.php?route=dashboard
http://localhost/uwc-hr-api/api.php?route=jobs
http://localhost/uwc-hr-api/api.php?route=jobs%2F1%2Fcandidates
```
