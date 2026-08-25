# Railway Candidate Deployment

This setup keeps the HR website and full PHP API local while putting the
Candidate website, Candidate-only PHP API, uploads, and shared MySQL database
online.

## Services

Create these services in one Railway project:

1. `MySQL`
2. `candidate-api`
3. `hr-api`
4. `parsing-service`
5. `candidate-web`

The local HR API connects to the same MySQL service through Railway's public
TCP proxy.

## 1. Create MySQL

Add Railway's MySQL database service. Enable its TCP proxy so the local HR API
can connect from this computer.

Export the existing local database when XAMPP MySQL is available:

```powershell
& C:\xampp\mysql\bin\mysqldump.exe `
  --host=127.0.0.1 `
  --port=3306 `
  --user=root `
  --single-transaction `
  --routines `
  --triggers `
  --result-file=C:\uwc_hr_decision_support.sql `
  uwc_hr_decision_support
```

Import the dump using the public TCP proxy values shown by Railway:

```powershell
& C:\xampp\mysql\bin\mysql.exe `
  --host=<public-host> `
  --port=<public-port> `
  --user=root `
  --password `
  --database=railway `
  --execute="source C:/uwc_hr_decision_support.sql"
```

## 2. Deploy Candidate API

Create an empty Railway service and deploy this local repository with Railway
CLI. Set:

```text
RAILWAY_DOCKERFILE_PATH=/deploy/railway/candidate-api/Dockerfile
API_SURFACE=candidate
DB_HOST=${{MySQL.MYSQLHOST}}
DB_PORT=${{MySQL.MYSQLPORT}}
DB_USER=${{MySQL.MYSQLUSER}}
DB_PASSWORD=${{MySQL.MYSQLPASSWORD}}
DB_NAME=${{MySQL.MYSQLDATABASE}}
CORS_ORIGINS=https://<candidate-web-domain>
PUBLIC_API_BASE_URL=https://<candidate-api-domain>
RESUME_PARSING_API_URL=https://<parsing-service-domain>/api/resume/parse
RESUME_PARSING_TIMEOUT_SECONDS=240
RESUME_REQUIRE_SEMANTIC=true
CANDIDATE_SCORING_API_URL=https://<parsing-service-domain>/api/scoring/candidate
CANDIDATE_SCORING_TIMEOUT_SECONDS=300
# HTTPS mail providers avoid the SMTP egress restriction on Railway Free/Hobby.
# Current setup: verify a SendGrid Single Sender before using these variables.
MAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=<sendgrid-api-key>
SENDGRID_FROM_EMAIL=<verified-single-sender>
SENDGRID_FROM_NAME=UWC Recruitment
# SENDGRID_API_URL=https://api.sendgrid.com/v3/mail/send
# Resend remains supported if a verified sender/domain is configured instead:
# MAIL_PROVIDER=resend
# RESEND_API_KEY=<resend-api-key>
# RESEND_FROM_EMAIL=<verified-sender>
# RESEND_FROM_NAME=UWC Recruitment
# RESEND_API_URL=https://api.resend.com/emails
# SMTP settings remain available for local or Pro deployments.
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<smtp-account>
SMTP_PASSWORD=<smtp-app-password>
SMTP_ENCRYPTION=tls
SMTP_FROM_EMAIL=<smtp-account>
SMTP_FROM_NAME=UWC Recruitment
SMTP_VERIFY_PEER=true
# Optional; enabled by the candidate-api image by default.
APPLICATION_ANALYSIS_WORKER_ENABLED=true
APPLICATION_ANALYSIS_WORKER_POLL_SECONDS=2
```

`RESUME_PARSING_API_URL` and `CANDIDATE_SCORING_API_URL` must point to the
existing FastAPI parsing service. The PHP submission route persists the
candidate/application/resume first and returns the submission response with
`analysisStatus=pending`. The existing candidate-api container's CLI worker
then calls these routes independently of the candidate HTTP connection. If
the FastAPI service is unavailable, the saved application and resume remain in
Railway DB and the application analysis status is marked pending or failed for
retry.

The worker uses the existing `applications.analysis_status` column and
`scoring_diagnostics_json.analysisWorker` as a small durable queue/claim
marker. It is enabled only on `candidate-api`; `hr-api` keeps the worker
disabled so both services do not process the same application concurrently.

Generate a public domain for the API. Attach a Railway Volume with this exact
mount path:

```text
/var/www/html/uploads
```

Use this health check:

```text
/api.php?route=health
```

The `API_SURFACE=candidate` boundary returns 404 for HR routes even though both
local and online services use the same PHP source.

## 2a. Deploy the shared parsing service

Create a Railway service named `parsing-service` and deploy the
`parsing-service` directory as its Docker build context:

```powershell
railway up parsing-service --path-as-root --service parsing-service --environment production
```

Configure the service with the Railway database variables, the existing shared
RunPod inference variables, and:

```text
RESUME_QWEN_PROTOCOL=runpod
RESUME_QWEN_MODEL=Qwen/Qwen2.5-3B-Instruct
RESUME_QWEN_TIMEOUT_SECONDS=240
CANDIDATE_QWEN_PROTOCOL=runpod
CANDIDATE_QWEN_MODEL=Qwen/Qwen2.5-3B-Instruct
CANDIDATE_QWEN_TIMEOUT_SECONDS=240
RUNPOD_CRITERIA_ENDPOINT_URL=https://api.runpod.ai/v2/<existing-endpoint-id>/runsync
RUNPOD_API_KEY=<secret>
```

The parser and scorer are separate routes on this service, but they reuse the
same Qwen worker runtime. Do not create a second RunPod endpoint for either
route.

## 3. Deploy Candidate Web

Create another empty service and set:

```text
RAILWAY_DOCKERFILE_PATH=/deploy/railway/candidate-web/Dockerfile
VITE_API_BASE_URL=https://<candidate-api-domain>/api.php
```

Generate its public domain. Then update the Candidate API's `CORS_ORIGINS` to
that exact HTTPS origin and redeploy the API.

The Candidate build contains only Careers, Apply, Candidate account, Candidate
applications, and Employment Form routes. HR routes remain in the local build.

## 4. Connect Local HR API

Copy `server/.env.local.example` to `server/.env.local`, then replace the
database values with Railway's public TCP proxy values. Keep:

```text
API_SURFACE=full
```

Run `npm run dev:api` to copy the updated PHP API and the private local
environment file into XAMPP. The HR React app keeps using:

```text
http://localhost/uwc-hr-api/api.php
```

Only the database moves online; the local HR workflow and UWC interface remain
unchanged.
