<?php
// Routes requests for the HR and candidate systems.

declare(strict_types=1);

require_once __DIR__ . "/helpers/response.php";
require_once __DIR__ . "/helpers/environment.php";
require_once __DIR__ . "/helpers/database_queries.php";
require_once __DIR__ . "/helpers/surface.php";
require_once __DIR__ . "/helpers/runpod.php";
require_once __DIR__ . "/helpers/qualification.php";

configure_api_headers();

// End CORS preflight before opening a database connection.
if ($_SERVER["REQUEST_METHOD"] === "OPTIONS") {
    http_response_code(204);
    exit;
}

$path = trim((string) ($_GET["route"] ?? ""), "/");
if ($path === "") {
    $path = trim((string) parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH), "/");
    $path = preg_replace("#^api\.php/?#", "", $path);
}
$segments = $path === "" ? [] : explode("/", $path);
$method = $_SERVER["REQUEST_METHOD"];

// This proxy does not need a database connection; keep the RunPod secret server-side.
if ($method === "POST" && route_is($segments, ["jd-criteria-llm"])) {
    runpod_criteria_proxy();
}

// The online candidate service exposes only public candidate routes.
if (!api_surface_route_allowed($method, $segments)) {
    respond(["error" => "Route not found", "path" => $path], 404);
}

require_once __DIR__ . "/bootstrap.php";
require_once __DIR__ . "/helpers/auth.php";
require_once __DIR__ . "/helpers/files.php";
require_once __DIR__ . "/helpers/resume_parser.php";
require_once __DIR__ . "/helpers/candidate_scoring.php";
require_once __DIR__ . "/helpers/application_analysis.php";

// Keep older Railway databases compatible with the explicit job type field.
ensure_job_employment_type_schema($mysqli);

// Route each request to one handler.
try {
    if ($method === "GET" && route_is($segments, ["health"])) {
        respond([
            "ok" => true,
            "service" => strtolower(environment_value("API_SURFACE", "full") ?? "full"),
            "database" => "connected",
        ]);
    } elseif ($method === "POST" && route_is($segments, ["auth", "login"])) {
        login($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["auth", "password"])) {
        update_auth_password($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["auth", "profile", "avatar"])) {
        update_auth_profile($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["auth", "profile"])) {
        update_auth_profile($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["candidate-auth", "register"])) {
        candidate_register($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["candidate-auth", "login"])) {
        candidate_login($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["candidate-auth", "logout"])) {
        candidate_logout($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["candidate-auth", "password-reset", "request"])) {
        candidate_password_reset_request($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["candidate-auth", "password-reset", "confirm"])) {
        candidate_password_reset_confirm($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["candidate", "me"])) {
        candidate_me($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["candidate", "profile"])) {
        candidate_update_profile($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["candidate", "password"])) {
        candidate_update_password($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["career", "jobs"])) {
        career_jobs($mysqli);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "career" && $segments[1] === "jobs") {
        career_job_details($mysqli, $segments[2]);
    } elseif ($method === "GET" && route_is($segments, ["candidate", "applications"])) {
        candidate_applications($mysqli);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "candidate" && $segments[1] === "applications") {
        candidate_application_details($mysqli, (int) $segments[2]);
    } elseif ($method === "PATCH" && count($segments) === 4 && $segments[0] === "candidate" && $segments[1] === "applications" && $segments[3] === "withdraw") {
        candidate_withdraw_application($mysqli, (int) $segments[2]);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "employment-form" && $segments[1] === "submissions") {
        employment_form_submission($mysqli, (int) $segments[2]);
    } elseif ($method === "GET" && route_is($segments, ["employment-form", "submissions"])) {
        employment_form_submissions($mysqli);
    } elseif ($method === "PATCH" && count($segments) === 4 && $segments[0] === "employment-form" && $segments[1] === "submissions" && $segments[3] === "internal") {
        update_employment_form_internal($mysqli, (int) $segments[2]);
    } elseif ($method === "POST" && route_is($segments, ["employment-form", "submissions"])) {
        submit_employment_form($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["dashboard"])) {
        dashboard($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["departments"])) {
        update_department($mysqli);
    } elseif ($method === "DELETE" && route_is($segments, ["departments"])) {
        delete_department($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["jobs"])) {
        jobs($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["jobs"])) {
        create_job($mysqli);
    } elseif ($method === "POST" && count($segments) === 2 && $segments[0] === "jobs") {
        save_job($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "jobs" && $segments[2] === "jd-file") {
        job_description_file($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && route_is($segments, ["applications"])) {
        applications($mysqli);
    } elseif ($method === "GET" && count($segments) === 2 && $segments[0] === "jobs") {
        job_details($mysqli, (int) $segments[1]);
    } elseif ($method === "DELETE" && count($segments) === 2 && $segments[0] === "jobs") {
        delete_job($mysqli, (int) $segments[1]);
    } elseif ($method === "PATCH" && count($segments) === 2 && $segments[0] === "jobs") {
        update_job($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "jobs" && $segments[2] === "candidates") {
        job_candidates($mysqli, (int) $segments[1]);
    } elseif ($method === "PATCH" && count($segments) === 2 && $segments[0] === "applications") {
        update_application($mysqli, (int) $segments[1]);
    } elseif ($method === "PATCH" && count($segments) === 3 && $segments[0] === "applications" && $segments[2] === "reason") {
        update_application_action_reason($mysqli, (int) $segments[1]);
    } elseif ($method === "POST" && count($segments) === 4 && $segments[0] === "applications" && ctype_digit($segments[1]) && $segments[2] === "analysis" && $segments[3] === "retry") {
        retry_application_analysis($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && count($segments) === 2 && $segments[0] === "apply") {
        apply_job($mysqli, $segments[1]);
    } elseif ($method === "POST" && count($segments) === 2 && $segments[0] === "apply") {
        submit_application($mysqli, $segments[1]);
    } elseif ($method === "GET" && route_is($segments, ["users"])) {
        users($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["users"])) {
        create_user($mysqli);
    } elseif ($method === "PATCH" && count($segments) === 3 && $segments[0] === "users" && ctype_digit($segments[1]) && $segments[2] === "password") {
        update_user_password($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && count($segments) === 3 && $segments[0] === "users" && $segments[2] === "actions") {
        user_action_logs($mysqli, (int) $segments[1]);
    } elseif ($method === "GET" && route_is($segments, ["email-templates"])) {
        email_templates($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["email-templates"])) {
        update_email_templates($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["eligibility-filter-definitions"])) {
        eligibility_filter_definitions($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["eligibility-filter-definitions"])) {
        create_eligibility_filter_definition($mysqli);
    } elseif ($method === "PATCH" && count($segments) === 2 && $segments[0] === "eligibility-filter-definitions") {
        update_eligibility_filter_definition($mysqli, (int) $segments[1]);
    } elseif ($method === "DELETE" && count($segments) === 2 && $segments[0] === "eligibility-filter-definitions") {
        delete_eligibility_filter_definition($mysqli, (int) $segments[1]);
    } elseif ($method === "POST" && count($segments) === 3 && $segments[0] === "email-templates" && in_array($segments[2], ["attachment", "logo-attachment"], true)) {
        upload_email_template_asset($mysqli, $segments[1], $segments[2] === "logo-attachment");
    } elseif ($method === "DELETE" && count($segments) === 3 && $segments[0] === "email-templates" && in_array($segments[2], ["attachment", "logo-attachment"], true)) {
        remove_email_template_asset($mysqli, $segments[1], $segments[2] === "logo-attachment");
    } elseif ($method === "POST" && route_is($segments, ["email-templates", "interview-attachment"])) {
        upload_interview_attachment($mysqli);
    } elseif ($method === "DELETE" && route_is($segments, ["email-templates", "interview-attachment"])) {
        remove_interview_email_asset($mysqli, false);
    } elseif ($method === "POST" && route_is($segments, ["email-templates", "interview-logo-attachment"])) {
        upload_interview_logo_attachment($mysqli);
    } elseif ($method === "DELETE" && route_is($segments, ["email-templates", "interview-logo-attachment"])) {
        remove_interview_email_asset($mysqli, true);
    } elseif ($method === "GET" && route_is($segments, ["notifications"])) {
        notifications($mysqli);
    } elseif ($method === "PATCH" && route_is($segments, ["notifications", "read"])) {
        mark_notifications_read($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["hr-efficiency"])) {
        hr_efficiency($mysqli);
    } elseif ($method === "GET" && route_is($segments, ["attendance-analytics"])) {
        attendance_analytics($mysqli);
    } elseif ($method === "PUT" && route_is($segments, ["attendance-analytics", "settings"])) {
        update_attendance_settings($mysqli);
    } elseif ($method === "POST" && route_is($segments, ["attendance-analytics", "upload"])) {
        upload_attendance_file($mysqli);
    } else {
        respond(["error" => "Route not found", "path" => $path], 404);
    }
} catch (Throwable $error) {
    respond(["error" => "Server error", "detail" => $error->getMessage()], 500);
}

// Shared route and database helpers.
function route_is(array $segments, array $expected): bool
{
    return $segments === $expected;
}

function notice_period_days_from_input(mixed $value): int
{
    if (is_int($value) || is_float($value) || is_numeric($value)) {
        return max(0, (int) $value);
    }

    $label = strtolower(trim((string) $value));
    if ($label === "" || $label === "immediate") {
        return 0;
    }

    if (preg_match('/(\d+(?:\.\d+)?)\s*(day|days|week|weeks|month|months)/', $label, $matches)) {
        $amount = (float) $matches[1];
        $unit = $matches[2];
        $multiplier = str_starts_with($unit, "month")
            ? 30
            : (str_starts_with($unit, "week") ? 7 : 1);
        return max(0, (int) round($amount * $multiplier));
    }

    return 0;
}

// HR login and profile setup.
function login(mysqli $db): void
{
    ensure_user_profile_schema($db);
    $data = input_json();
    $email = trim((string) ($data["email"] ?? ""));
    $password = (string) ($data["password"] ?? "");

    if ($email === "" || $password === "") {
        respond(["error" => "Email and password are required"], 422);
    }

    $user = row(
        $db,
        "SELECT
           u.id,
           u.full_name AS name,
           u.email,
           u.phone,
           u.avatar_path AS avatarPath,
           u.department,
           u.status,
           u.role_id AS roleId,
           CASE WHEN u.role_id = 2 THEN 'hiring_manager' ELSE 'hr_staff' END AS roleKey,
           r.role_name AS roleName,
           u.password_hash AS passwordHash,
           u.must_change_password AS mustChangePassword
         FROM users u
         JOIN roles r ON r.id = u.role_id
         WHERE u.email = ? AND u.status = 'active'
         LIMIT 1",
        "s",
        [$email]
    );

    if (!$user || !password_verify($password, (string) ($user["passwordHash"] ?? ""))) {
        respond(["error" => "Invalid email or password"], 401);
    }

    unset($user["passwordHash"]);
    $user["mustChangePassword"] = (bool) ($user["mustChangePassword"] ?? false);

    exec_stmt($db, "UPDATE users SET last_login_at = NOW() WHERE id = ?", "i", [(int) $user["id"]]);
    respond(["user" => $user]);
}

function ensure_user_profile_schema(mysqli $db): void
{
    if (!table_column_exists($db, "users", "avatar_path")) {
        exec_stmt($db, "ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500) NULL AFTER phone");
    }

    if (!table_column_exists($db, "users", "must_change_password")) {
        exec_stmt($db, "ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0 AFTER password_hash");
    }
}

function update_auth_password(mysqli $db): void
{
    ensure_user_profile_schema($db);
    $data = input_json();
    $userId = (int) ($data["userId"] ?? 0);
    $currentPassword = (string) ($data["currentPassword"] ?? "");
    $newPassword = (string) ($data["newPassword"] ?? "");

    if ($userId <= 0 || $currentPassword === "" || $newPassword === "") {
        respond(["error" => "Current password and new password are required"], 422);
    }

    if (strlen($newPassword) < 8) {
        respond(["error" => "Password must be at least 8 characters"], 422);
    }

    $user = row(
        $db,
        "SELECT id, password_hash FROM users WHERE id = ? AND status = 'active' LIMIT 1",
        "i",
        [$userId]
    );

    if (!$user || !password_verify($currentPassword, (string) ($user["password_hash"] ?? ""))) {
        respond(["error" => "Current password is incorrect"], 401);
    }

    exec_stmt(
        $db,
        "UPDATE users SET password_hash = ?, must_change_password = 0, updated_at = NOW() WHERE id = ?",
        "si",
        [password_hash($newPassword, PASSWORD_DEFAULT), $userId]
    );

    respond(["ok" => true]);
}

function ensure_candidate_portal_schema(mysqli $db): void
{
    if (!table_column_exists($db, "candidates", "address")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN address VARCHAR(500) NULL AFTER phone");
    }
    if (!table_column_exists($db, "candidates", "gender")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN gender VARCHAR(50) NULL AFTER phone");
    }
    if (!table_column_exists($db, "candidates", "country")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN country VARCHAR(100) NULL AFTER gender");
    }
    if (!table_column_exists($db, "candidates", "current_location")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN current_location VARCHAR(160) NULL AFTER country");
    }
    if (!table_column_exists($db, "candidates", "languages_json")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN languages_json TEXT NULL AFTER current_location");
    }
    if (!table_column_exists($db, "candidates", "education")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN education VARCHAR(500) NULL AFTER address");
    }
    if (!table_column_exists($db, "candidates", "default_resume_file_name")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN default_resume_file_name VARCHAR(255) NULL AFTER education");
    }
    if (!table_column_exists($db, "candidates", "default_resume_path")) {
        exec_stmt($db, "ALTER TABLE candidates ADD COLUMN default_resume_path VARCHAR(500) NULL AFTER default_resume_file_name");
    }

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS candidate_accounts (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          candidate_id INT UNSIGNED NOT NULL,
          email VARCHAR(180) NOT NULL UNIQUE,
          password_hash VARCHAR(255) NOT NULL,
          status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
          last_login_at DATETIME NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_candidate_accounts_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
          UNIQUE KEY uq_candidate_accounts_candidate (candidate_id)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS candidate_sessions (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          candidate_account_id INT UNSIGNED NOT NULL,
          token_hash CHAR(64) NOT NULL UNIQUE,
          expires_at DATETIME NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_candidate_sessions_account FOREIGN KEY (candidate_account_id) REFERENCES candidate_accounts(id) ON DELETE CASCADE,
          INDEX idx_candidate_sessions_account (candidate_account_id),
          INDEX idx_candidate_sessions_expires (expires_at)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS candidate_password_resets (
          id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          candidate_account_id INT UNSIGNED NOT NULL,
          token_hash CHAR(64) NOT NULL UNIQUE,
          expires_at DATETIME NOT NULL,
          used_at DATETIME NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_candidate_password_resets_account FOREIGN KEY (candidate_account_id) REFERENCES candidate_accounts(id) ON DELETE CASCADE,
          INDEX idx_candidate_password_resets_account (candidate_account_id),
          INDEX idx_candidate_password_resets_expiry (expires_at)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS application_documents (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          application_id INT UNSIGNED NOT NULL,
          original_file_name VARCHAR(255) NOT NULL,
          stored_file_path VARCHAR(500) NOT NULL,
          file_mime_type VARCHAR(120) NOT NULL DEFAULT 'application/pdf',
          file_size_bytes INT UNSIGNED NOT NULL,
          uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_application_documents_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
          INDEX idx_application_documents_application (application_id)
        ) ENGINE=InnoDB"
    );
    if (!table_column_exists($db, "resumes", "parsed_profile_json")) {
        exec_stmt($db, "ALTER TABLE resumes ADD COLUMN parsed_profile_json LONGTEXT NULL AFTER parsed_text");
    }
    if (!table_column_exists($db, "resumes", "parse_metadata_json")) {
        exec_stmt($db, "ALTER TABLE resumes ADD COLUMN parse_metadata_json TEXT NULL AFTER parsed_profile_json");
    }
    if (!table_column_exists($db, "resumes", "parser_version")) {
        exec_stmt($db, "ALTER TABLE resumes ADD COLUMN parser_version VARCHAR(80) NULL AFTER parse_metadata_json");
    }
    if (!table_column_exists($db, "resumes", "parsed_at")) {
        exec_stmt($db, "ALTER TABLE resumes ADD COLUMN parsed_at DATETIME NULL AFTER parser_version");
    }
    if (!table_column_exists($db, "applications", "analysis_status")) {
        exec_stmt($db, "ALTER TABLE applications ADD COLUMN analysis_status VARCHAR(32) NULL AFTER scoring_version");
    }
    exec_stmt($db, "ALTER TABLE applications MODIFY application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL DEFAULT 'new'");
    if (!table_column_exists($db, "applications", "hired_start_date")) {
        exec_stmt($db, "ALTER TABLE applications ADD COLUMN hired_start_date DATE NULL AFTER interview_sent_at");
    }
    exec_stmt($db, "ALTER TABLE application_submission_history MODIFY previous_application_status ENUM('new', 'reviewed', 'shortlisted', 'interview', 'interviewed', 'hired', 'rejected', 'filtered_out', 'withdrawn') NOT NULL");
}

function candidate_public_status(string $status): string
{
    return match ($status) {
        "new" => "Submitted",
        "reviewed" => "Under Review",
        "shortlisted" => "Shortlisted",
        "interview", "interviewed" => "Interview",
        "hired" => "Hired",
        "withdrawn" => "Withdrawn",
        "rejected", "filtered_out" => "Rejected",
        default => "Submitted",
    };
}

function normalize_candidate_languages_json(string $value): string
{
    if ($value === "") {
        return "[]";
    }

    $decoded = json_decode($value, true);
    if (!is_array($decoded)) {
        return "[]";
    }

    $languages = [];
    foreach ($decoded as $item) {
        if (!is_array($item)) {
            continue;
        }

        $language = trim((string) ($item["language"] ?? ""));
        $level = trim((string) ($item["level"] ?? ""));
        if ($language === "" && $level === "") {
            continue;
        }

        $languages[] = [
            "language" => $language,
            "level" => $level,
        ];
    }

    return json_encode($languages);
}

function is_valid_malaysian_phone(string $phone): bool
{
    $normalized = preg_replace('/[\s()-]/', '', $phone);

    return is_string($normalized)
        && preg_match('/^(?:\+?60|0)(?:1\d{8,9}|[3-9]\d{7,8})$/', $normalized) === 1;
}

// Candidate account and career portal actions.
function candidate_register(mysqli $db): void
{
    ensure_candidate_portal_schema($db);
    $data = input_json();
    $fullName = trim((string) ($data["fullName"] ?? ""));
    $email = strtolower(trim((string) ($data["email"] ?? "")));
    $password = (string) ($data["password"] ?? "");
    $phone = trim((string) ($data["phone"] ?? ""));

    if ($fullName === "" || $email === "" || $password === "") {
        respond(["error" => "Full name, email, and password are required"], 422);
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Please enter a valid email"], 422);
    }
    if ($phone !== "" && !is_valid_malaysian_phone($phone)) {
        respond(["error" => "Please enter a valid Malaysian phone number"], 422);
    }
    if (strlen($password) < 8) {
        respond(["error" => "Password must be at least 8 characters"], 422);
    }
    if (row($db, "SELECT id FROM candidate_accounts WHERE email = ? LIMIT 1", "s", [$email])) {
        respond(["error" => "This email is already registered"], 409);
    }

    $candidate = row($db, "SELECT id FROM candidates WHERE email = ? LIMIT 1", "s", [$email]);
    if (!$candidate) {
        exec_stmt(
            $db,
            "INSERT INTO candidates (full_name, email, phone) VALUES (?, ?, ?)",
            "sss",
            [$fullName, $email, $phone]
        );
        $candidateId = $db->insert_id;
    } else {
        $candidateId = (int) $candidate["id"];
        if (row($db, "SELECT id FROM candidate_accounts WHERE candidate_id = ? LIMIT 1", "i", [$candidateId])) {
            respond(["error" => "This candidate already has an account"], 409);
        }
        exec_stmt($db, "UPDATE candidates SET full_name = ?, phone = IF(? = '', phone, ?) WHERE id = ?", "sssi", [$fullName, $phone, $phone, $candidateId]);
    }

    exec_stmt(
        $db,
        "INSERT INTO candidate_accounts (candidate_id, email, password_hash)
         VALUES (?, ?, ?)",
        "iss",
        [$candidateId, $email, password_hash($password, PASSWORD_DEFAULT)]
    );
    $accountId = $db->insert_id;
    $token = create_candidate_session($db, $accountId);
    exec_stmt($db, "UPDATE candidate_accounts SET last_login_at = NOW() WHERE id = ?", "i", [$accountId]);

    $session = candidate_session_from_account($db, $accountId);
    respond(["candidate" => candidate_account_payload($session, $token)], 201);
}

function candidate_login(mysqli $db): void
{
    $data = input_json();
    $email = strtolower(trim((string) ($data["email"] ?? "")));
    $password = (string) ($data["password"] ?? "");

    $account = row($db, "SELECT id, password_hash AS passwordHash FROM candidate_accounts WHERE email = ? AND status = 'active' LIMIT 1", "s", [$email]);
    if (!$account || !password_verify($password, (string) $account["passwordHash"])) {
        respond(["error" => "Invalid email or password"], 401);
    }

    $accountId = (int) $account["id"];
    $token = create_candidate_session($db, $accountId);
    exec_stmt($db, "UPDATE candidate_accounts SET last_login_at = NOW() WHERE id = ?", "i", [$accountId]);
    respond(["candidate" => candidate_account_payload(candidate_session_from_account($db, $accountId), $token)]);
}

function candidate_password_reset_request(mysqli $db): void
{
    ensure_candidate_portal_schema($db);
    $data = input_json();
    $email = strtolower(trim((string) ($data["email"] ?? "")));
    $genericResponse = [
        "ok" => true,
        "message" => "If an account exists for this email, a password reset link has been sent.",
    ];

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Please enter a valid email address"], 422);
    }

    $account = row(
        $db,
        "SELECT ca.id AS accountId, ca.email, c.full_name AS fullName
         FROM candidate_accounts ca
         JOIN candidates c ON c.id = ca.candidate_id
         WHERE ca.email = ? AND ca.status = 'active'
         LIMIT 1",
        "s",
        [$email]
    );

    // Keep account existence private while still giving real accounts a reset email.
    if (!$account) {
        respond($genericResponse);
    }

    $token = bin2hex(random_bytes(32));
    exec_stmt(
        $db,
        "DELETE FROM candidate_password_resets WHERE candidate_account_id = ? OR expires_at <= NOW()",
        "i",
        [(int) $account["accountId"]]
    );
    exec_stmt(
        $db,
        "INSERT INTO candidate_password_resets (candidate_account_id, token_hash, expires_at)
         VALUES (?, ?, DATE_ADD(NOW(), INTERVAL 30 MINUTE))",
        "is",
        [(int) $account["accountId"], hash("sha256", $token)]
    );

    $resetUrl = candidate_password_reset_url($token);
    $toName = (string) ($account["fullName"] ?? "Candidate");
    $subject = "Reset your UWC Careers password";
    $body = "Dear {$toName},\n\n"
        . "We received a request to reset your UWC Careers password. Use the link below within 30 minutes to choose a new password:\n\n"
        . "{$resetUrl}\n\n"
        . "If you did not request this, you can ignore this email.\n\n"
        . "Regards,\nUWC Recruitment";

    try {
        $config = mail_config();
        $fromEmail = (string) (
            $config["sendgrid_from_email"]
            ?? $config["resend_from_email"]
            ?? $config["from_email"]
            ?? $config["username"]
            ?? ""
        );
        $fromName = (string) (
            $config["sendgrid_from_name"]
            ?? $config["resend_from_name"]
            ?? $config["from_name"]
            ?? "UWC Recruitment"
        );
        send_recruitment_email($email, $toName, $subject, $body, $fromEmail, $fromName);
    } catch (Throwable $error) {
        error_log("Candidate password reset email failed: " . $error->getMessage());
        respond(["error" => "Unable to send the password reset email"], 500);
    }

    respond($genericResponse);
}

function candidate_password_reset_confirm(mysqli $db): void
{
    ensure_candidate_portal_schema($db);
    $data = input_json();
    $token = trim((string) ($data["token"] ?? ""));
    $newPassword = (string) ($data["newPassword"] ?? "");

    if ($token === "") {
        respond(["error" => "This password reset link is invalid or expired"], 422);
    }
    if (strlen($newPassword) < 8) {
        respond(["error" => "Password must be at least 8 characters"], 422);
    }

    $reset = row(
        $db,
        "SELECT id, candidate_account_id AS accountId
         FROM candidate_password_resets
         WHERE token_hash = ? AND used_at IS NULL AND expires_at > NOW()
         LIMIT 1",
        "s",
        [hash("sha256", $token)]
    );
    if (!$reset) {
        respond(["error" => "This password reset link is invalid or expired"], 422);
    }

    $accountId = (int) $reset["accountId"];
    exec_stmt(
        $db,
        "UPDATE candidate_accounts SET password_hash = ? WHERE id = ? AND status = 'active'",
        "si",
        [password_hash($newPassword, PASSWORD_DEFAULT), $accountId]
    );
    exec_stmt($db, "UPDATE candidate_password_resets SET used_at = NOW() WHERE id = ?", "i", [(int) $reset["id"]]);
    exec_stmt($db, "DELETE FROM candidate_sessions WHERE candidate_account_id = ?", "i", [$accountId]);
    respond(["ok" => true]);
}

function candidate_password_reset_url(string $token): string
{
    $baseUrl = environment_value("CANDIDATE_WEB_URL")
        ?? environment_value("PUBLIC_CANDIDATE_WEB_URL")
        ?? trim((string) ($_SERVER["HTTP_ORIGIN"] ?? ""));
    if ($baseUrl === "") {
        $baseUrl = "http://localhost:5173";
    }

    return rtrim($baseUrl, "/")
        . "/candidate/login?reset=1&token="
        . rawurlencode($token);
}

function candidate_logout(mysqli $db): void
{
    $token = get_bearer_token();
    if ($token !== "") {
        exec_stmt($db, "DELETE FROM candidate_sessions WHERE token_hash = ?", "s", [hash("sha256", $token)]);
    }
    respond(["ok" => true]);
}

function candidate_me(mysqli $db): void
{
    respond(["candidate" => candidate_account_payload(candidate_session($db))]);
}

function candidate_update_profile(mysqli $db): void
{
    $session = candidate_session($db);
    $data = input_data();
    $fullName = trim((string) ($data["fullName"] ?? ""));
    $email = strtolower(trim((string) ($data["email"] ?? "")));
    $phone = trim((string) ($data["phone"] ?? ""));
    $address = trim((string) ($data["address"] ?? ""));
    $education = trim((string) ($data["education"] ?? ""));

    if ($fullName === "" || $email === "") {
        respond(["error" => "Full name and email are required"], 422);
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Please enter a valid email"], 422);
    }
    if ($phone !== "" && !is_valid_malaysian_phone($phone)) {
        respond(["error" => "Please enter a valid Malaysian phone number"], 422);
    }
    $duplicate = row($db, "SELECT id FROM candidate_accounts WHERE email = ? AND id <> ? LIMIT 1", "si", [$email, (int) $session["accountId"]]);
    if ($duplicate) {
        respond(["error" => "This email is already used by another candidate"], 409);
    }

    [$resumeName, $resumePath] = save_candidate_default_resume($session);

    exec_stmt(
        $db,
        "UPDATE candidates
         SET full_name = ?, email = ?, phone = ?, address = ?, education = ?,
             default_resume_file_name = COALESCE(?, default_resume_file_name),
             default_resume_path = COALESCE(?, default_resume_path)
         WHERE id = ?",
        "sssssssi",
        [$fullName, $email, $phone, $address, $education, $resumeName, $resumePath, (int) $session["candidateId"]]
    );
    exec_stmt($db, "UPDATE candidate_accounts SET email = ? WHERE id = ?", "si", [$email, (int) $session["accountId"]]);
    respond(["candidate" => candidate_account_payload(candidate_session_from_account($db, (int) $session["accountId"]))]);
}

function save_candidate_default_resume(array $session): array
{
    if (!isset($_FILES["defaultResume"]) || !is_array($_FILES["defaultResume"]) || (int) ($_FILES["defaultResume"]["error"] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) {
        return [null, null];
    }

    $file = $_FILES["defaultResume"];
    if ((int) $file["error"] !== UPLOAD_ERR_OK) {
        respond(["error" => "Default resume upload failed"], 422);
    }
    $originalName = basename((string) $file["name"]);
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ["pdf", "jpg", "jpeg", "png"], true)) {
        respond(["error" => "Default resume must be PDF, JPG, JPEG, or PNG"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "candidate-defaults";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare candidate upload folder"], 500);
    }
    $storedName = sprintf("candidate-%d-%s.%s", (int) $session["candidateId"], bin2hex(random_bytes(6)), $extension === "jpeg" ? "jpg" : $extension);
    if (!move_uploaded_file((string) $file["tmp_name"], $uploadDir . DIRECTORY_SEPARATOR . $storedName)) {
        respond(["error" => "Unable to save default resume"], 500);
    }

    return [$originalName, public_file_url("/uploads/candidate-defaults/{$storedName}")];
}

function candidate_update_password(mysqli $db): void
{
    $session = candidate_session($db);
    $data = input_json();
    $currentPassword = (string) ($data["currentPassword"] ?? "");
    $newPassword = (string) ($data["newPassword"] ?? "");
    if (strlen($newPassword) < 8) {
        respond(["error" => "New password must be at least 8 characters"], 422);
    }

    $account = row($db, "SELECT password_hash AS passwordHash FROM candidate_accounts WHERE id = ? LIMIT 1", "i", [(int) $session["accountId"]]);
    if (!$account || !password_verify($currentPassword, (string) $account["passwordHash"])) {
        respond(["error" => "Current password is incorrect"], 422);
    }

    exec_stmt($db, "UPDATE candidate_accounts SET password_hash = ? WHERE id = ?", "si", [password_hash($newPassword, PASSWORD_DEFAULT), (int) $session["accountId"]]);
    respond(["ok" => true]);
}

function candidate_public_job_type_sql(string $jobAlias = "j"): string
{
    // An explicit job type is authoritative. The internship eligibility flag
    // remains a fallback for older jobs created before job type was exposed.
    return "CASE
        WHEN NULLIF(TRIM({$jobAlias}.employment_type), '') IS NOT NULL
            THEN TRIM({$jobAlias}.employment_type)
        WHEN EXISTS (
            SELECT 1
            FROM eligibility_filters internship_filter
            WHERE internship_filter.job_id = {$jobAlias}.id
              AND internship_filter.internship_accepted = 1
        ) OR EXISTS (
            SELECT 1
            FROM job_eligibility_filter_values internship_value
            WHERE internship_value.job_id = {$jobAlias}.id
              AND internship_value.filter_key = 'internshipAccepted'
              AND LOWER(TRIM(COALESCE(internship_value.filter_value, ''))) = 'yes'
        ) THEN 'Internship'
        ELSE 'Full-time'
    END";
}

function ensure_job_employment_type_schema(mysqli $db): void
{
    if (!table_exists($db, "jobs")) {
        return;
    }

    if (!table_column_exists($db, "jobs", "employment_type")) {
        exec_stmt(
            $db,
            "ALTER TABLE jobs ADD COLUMN employment_type VARCHAR(80) NULL"
        );
    }

    $internshipConditions = [];
    if (
        table_exists($db, "eligibility_filters") &&
        table_column_exists($db, "eligibility_filters", "internship_accepted")
    ) {
        $internshipConditions[] = "EXISTS (
            SELECT 1
            FROM eligibility_filters ef
            WHERE ef.job_id = j.id
              AND ef.internship_accepted = 1
        )";
    }
    if (
        table_exists($db, "job_eligibility_filter_values") &&
        table_column_exists($db, "job_eligibility_filter_values", "filter_key") &&
        table_column_exists($db, "job_eligibility_filter_values", "filter_value")
    ) {
        $internshipConditions[] = "EXISTS (
            SELECT 1
            FROM job_eligibility_filter_values jv
            WHERE jv.job_id = j.id
              AND jv.filter_key = 'internshipAccepted'
              AND LOWER(TRIM(COALESCE(jv.filter_value, ''))) = 'yes'
        )";
    }

    $internshipCheck = $internshipConditions
        ? implode(" OR ", $internshipConditions)
        : "0 = 1";

    exec_stmt(
        $db,
        "UPDATE jobs j
         SET j.employment_type = CASE
           WHEN {$internshipCheck} THEN 'Internship'
           ELSE 'Full-time'
         END
         WHERE j.employment_type IS NULL OR TRIM(j.employment_type) = ''"
    );
}

function career_jobs(mysqli $db): void
{
    $candidateSession = optional_candidate_session($db);
    $jobs = rows(
        $db,
        "SELECT
           j.id,
           j.job_code AS jobCode,
           j.title,
           j.department,
           j.location,
           j.salary_range AS salaryRange,
           " . candidate_public_job_type_sql() . " AS employmentType,
           j.description,
           j.published_at AS publishedAt,
           j.closed_at AS closingDate,
           j.created_at AS createdAt
         FROM jobs j
         WHERE j.status = 'active'
         ORDER BY COALESCE(j.published_at, j.created_at) DESC, j.id DESC"
    );

    $appliedJobIds = [];
    if ($candidateSession) {
        $appliedRows = rows(
            $db,
            "SELECT DISTINCT job_id AS jobId FROM applications WHERE candidate_id = ?",
            "i",
            [(int) $candidateSession["candidateId"]]
        );
        $appliedJobIds = array_fill_keys(
            array_map(fn (array $row): int => (int) $row["jobId"], $appliedRows),
            true
        );
    }

    $jobs = array_map(function (array $job) use ($appliedJobIds): array {
        $job["hasApplied"] = isset($appliedJobIds[(int) $job["id"]]);
        return $job;
    }, $jobs);

    respond(["jobs" => $jobs]);
}

function career_job_details(mysqli $db, string $jobCode): void
{
    $job = row(
        $db,
        "SELECT
           j.id,
           j.job_code AS jobCode,
           j.title,
           j.department,
           j.location,
           j.salary_range AS salaryRange,
           " . candidate_public_job_type_sql() . " AS employmentType,
           j.description,
           j.published_at AS publishedAt,
           j.closed_at AS closingDate,
           j.created_at AS createdAt
         FROM jobs j
         WHERE j.job_code = ?
           AND j.status = 'active'
         LIMIT 1",
        "s",
        [$jobCode]
    );
    if (!$job) {
        respond(["error" => "Job opening not found"], 404);
    }
    $jobId = (int) $job["id"];
    [
        $responsibilities,
        $qualifications,
        $skills,
        $applicationQuestions,
        $questionOptions,
    ] = row_sets($db, [
        "SELECT responsibility
         FROM job_responsibilities
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT qualification
         FROM job_qualifications
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT skill_name AS skillName, skill_type AS skillType, importance
         FROM job_required_skills
         WHERE job_id = {$jobId}
         ORDER BY FIELD(importance, 'required', 'preferred'), skill_name",
        "SELECT
           id,
           question_text AS question,
           field_type AS fieldType,
           is_required AS required,
           sort_order AS sortOrder
         FROM job_application_questions
         WHERE job_id = {$jobId}
           AND is_active = 1
         ORDER BY sort_order, id",
        "SELECT
           question_option.question_id AS questionId,
           question_option.option_label AS optionLabel
         FROM job_application_question_options question_option
         JOIN job_application_questions question ON question.id = question_option.question_id
         WHERE question.job_id = {$jobId}
           AND question.is_active = 1
         ORDER BY question_option.question_id, question_option.sort_order, question_option.id",
    ]);
    $job["responsibilities"] = $responsibilities;
    $job["qualifications"] = $qualifications;
    $job["skills"] = $skills;
    $job["applicationQuestions"] = hydrate_application_questions(
        $applicationQuestions,
        $questionOptions
    );
    respond(["job" => $job]);
}

function candidate_applications(mysqli $db): void
{
    $session = candidate_session($db);
    $status = trim((string) ($_GET["status"] ?? "all"));
    $applications = rows(
        $db,
        "SELECT
           a.id,
           a.job_id AS jobId,
           j.job_code AS jobCode,
           j.title AS jobTitle,
           j.department,
           a.application_status AS internalStatus,
           a.submitted_at AS submittedDate,
           a.updated_at AS updatedDate
         FROM applications a
         JOIN jobs j ON j.id = a.job_id
         WHERE a.candidate_id = ?
         ORDER BY a.submitted_at DESC, a.id DESC",
        "i",
        [(int) $session["candidateId"]]
    );
    $items = array_map(function (array $application): array {
        $application["status"] = candidate_public_status((string) $application["internalStatus"]);
        unset($application["internalStatus"]);
        return $application;
    }, $applications);
    if ($status !== "all") {
        $items = array_values(array_filter($items, fn (array $item): bool => strtolower((string) $item["status"]) === strtolower($status)));
    }
    respond(["applications" => $items]);
}

function candidate_application_details(mysqli $db, int $applicationId): void
{
    $session = candidate_session($db);
    $application = row(
        $db,
        "SELECT
           a.id,
           a.application_status AS internalStatus,
           a.analysis_status AS analysisStatus,
           a.submitted_at AS submittedDate,
           a.updated_at AS updatedDate,
           a.interview_sent_at AS interviewSentAt,
           c.full_name AS fullName,
           c.email,
           c.phone,
           c.gender,
           c.country,
           c.current_location AS currentLocation,
           c.languages_json AS languagesJson,
           c.current_cgpa AS currentCgpa,
           c.notice_period_days AS noticePeriodDays,
           c.address,
           c.education,
           j.title AS jobTitle,
           j.department,
           j.location,
           " . candidate_public_job_type_sql() . " AS employmentType
         FROM applications a
         JOIN candidates c ON c.id = a.candidate_id
         JOIN jobs j ON j.id = a.job_id
         WHERE a.id = ?
           AND a.candidate_id = ?
         LIMIT 1",
        "ii",
        [$applicationId, (int) $session["candidateId"]]
    );
    if (!$application) {
        respond(["error" => "Application not found"], 404);
    }
    $application["status"] = candidate_public_status((string) $application["internalStatus"]);
    unset($application["internalStatus"]);
    $application["documents"] = rows(
        $db,
        "SELECT id, original_file_name AS fileName, stored_file_path AS fileUrl, file_mime_type AS mimeType, file_size_bytes AS fileSize, uploaded_at AS uploadedAt
         FROM application_documents
         WHERE application_id = ?
         ORDER BY uploaded_at DESC, id DESC",
        "i",
        [$applicationId]
    );
    if (count($application["documents"]) === 0) {
        $application["documents"] = rows(
            $db,
            "SELECT id, original_file_name AS fileName, stored_file_path AS fileUrl, file_mime_type AS mimeType, file_size_bytes AS fileSize, uploaded_at AS uploadedAt
             FROM resumes
             WHERE application_id = ?
             ORDER BY uploaded_at DESC, id DESC",
            "i",
            [$applicationId]
        );
    }
    $application["interview"] = row(
        $db,
        "SELECT scheduled_interview_at AS scheduledAt, sent_at AS sentAt, subject
         FROM email_logs
         WHERE application_id = ?
           AND email_type = 'interview'
           AND status = 'sent'
         ORDER BY sent_at DESC, id DESC
         LIMIT 1",
        "i",
        [$applicationId]
    );
    respond(["application" => $application]);
}

function candidate_withdraw_application(mysqli $db, int $applicationId): void
{
    $session = candidate_session($db);
    $application = row(
        $db,
        "SELECT application_status AS status
         FROM applications
         WHERE id = ?
           AND candidate_id = ?
         LIMIT 1",
        "ii",
        [$applicationId, (int) $session["candidateId"]]
    );
    if (!$application) {
        respond(["error" => "Application not found"], 404);
    }
    if (in_array((string) $application["status"], ["interview", "interviewed", "hired", "rejected", "withdrawn"], true)) {
        respond(["error" => "This application can no longer be withdrawn"], 422);
    }
    exec_stmt($db, "UPDATE applications SET application_status = 'withdrawn', is_shortlisted = 0, updated_at = NOW() WHERE id = ?", "i", [$applicationId]);
    respond(["ok" => true]);
}

// Candidate and HR employment form actions.
function ensure_employment_form_submission_schema(mysqli $db): void
{
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS employment_form_submissions (
          id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          job_id INT UNSIGNED NOT NULL,
          candidate_id INT UNSIGNED NULL,
          candidate_email VARCHAR(180) NOT NULL,
          candidate_form_data LONGTEXT NOT NULL,
          hr_form_data LONGTEXT NULL,
          candidate_submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          hr_updated_at DATETIME NULL,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_employment_form_submissions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE RESTRICT,
          CONSTRAINT fk_employment_form_submissions_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
          INDEX idx_employment_form_submissions_job (job_id, candidate_submitted_at),
          INDEX idx_employment_form_submissions_candidate (candidate_id, candidate_submitted_at),
          INDEX idx_employment_form_submissions_email (candidate_email, candidate_submitted_at)
        ) ENGINE=InnoDB"
    );

    if (!table_column_exists($db, "employment_form_submissions", "hr_form_data")) {
        exec_stmt($db, "ALTER TABLE employment_form_submissions ADD COLUMN hr_form_data LONGTEXT NULL AFTER candidate_form_data");
    }

    if (table_column_exists($db, "employment_form_submissions", "status")) {
        exec_stmt($db, "ALTER TABLE employment_form_submissions DROP COLUMN status");
    }

    if (table_column_exists($db, "employment_form_submissions", "hiring_department_data")) {
        exec_stmt(
            $db,
            "UPDATE employment_form_submissions
             SET hr_form_data = hiring_department_data
             WHERE hr_form_data IS NULL
               AND hiring_department_data IS NOT NULL"
        );
    }

    if (table_column_exists($db, "employment_form_submissions", "hr_data")) {
        exec_stmt(
            $db,
            "UPDATE employment_form_submissions
             SET hr_form_data = hr_data
             WHERE hr_form_data IS NULL
               AND hr_data IS NOT NULL"
        );
    }
}

function submit_employment_form(mysqli $db): void
{
    ensure_employment_form_submission_schema($db);
    $data = input_json();
    $jobId = (int) ($data["jobId"] ?? 0);
    $candidateEmail = strtolower(trim((string) ($data["candidateEmail"] ?? "")));
    $candidateData = $data["candidateData"] ?? null;

    if ($jobId <= 0 || !filter_var($candidateEmail, FILTER_VALIDATE_EMAIL) || !is_array($candidateData)) {
        respond(["error" => "A position, candidate email, and form details are required"], 422);
    }

    $job = row(
        $db,
        "SELECT id FROM jobs WHERE id = ? AND status IN ('active', 'closed') LIMIT 1",
        "i",
        [$jobId]
    );
    if (!$job) {
        respond(["error" => "The selected position is not available"], 422);
    }

    $candidateValues = is_array($candidateData["values"] ?? null) ? $candidateData["values"] : [];
    foreach ([
        "employeeNo", "dateJoined", "hiringPosition", "startingSalary", "jobLevel", "dailyTransportClaim",
        "hiringDepartment", "maximumTransportClaim", "shiftGroup", "fuelClaim", "supervisor", "monthlyOtClaim",
        "mentor", "firstApprover", "secondApprover", "seniorHrManagerName", "seniorHrManagerSignature",
        "seniorHrManagerDate", "suitableDepartment", "interviewerComments", "hrJoiningDate", "hrOfferDate",
        "loaIssuedDate", "hrEmployeeNo", "badgeNo", "interviewerName", "interviewerSignature", "interviewerDate",
        "departmentManagerName", "departmentManagerSignature", "departmentManagerDate", "headApprovalName",
        "headApprovalSignature", "headApprovalDate",
    ] as $internalKey) {
        unset($candidateValues[$internalKey]);
    }

    $mobile = trim((string) ($candidateValues["mobile"] ?? ""));
    $residentialPhone = trim((string) ($candidateValues["residentialPhone"] ?? ""));
    $formEmail = strtolower(trim((string) ($candidateValues["email"] ?? "")));
    if ($formEmail === "" || !filter_var($formEmail, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Please enter a valid employment form email"], 422);
    }
    if ($mobile === "" || !is_valid_malaysian_phone($mobile)) {
        respond(["error" => "Please enter a valid Malaysian mobile number"], 422);
    }
    if ($residentialPhone !== "" && !is_valid_malaysian_phone($residentialPhone)) {
        respond(["error" => "Please enter a valid Malaysian residential phone number"], 422);
    }

    $candidateData["values"] = $candidateValues;

    $candidateChecks = is_array($candidateData["checks"] ?? null) ? $candidateData["checks"] : [];
    unset($candidateChecks["interviewStatus"]);
    $candidateData["checks"] = $candidateChecks;

    $formData = json_encode($candidateData, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
    if ($formData === false) {
        respond(["error" => "The form details could not be saved"], 422);
    }

    $candidate = row($db, "SELECT id FROM candidates WHERE email = ? LIMIT 1", "s", [$candidateEmail]);
    $candidateId = $candidate ? (int) $candidate["id"] : null;
    if ($candidateId !== null) {
        exec_stmt(
            $db,
            "INSERT INTO employment_form_submissions (job_id, candidate_id, candidate_email, candidate_form_data)
             VALUES (?, ?, ?, ?)",
            "iiss",
            [$jobId, $candidateId, $candidateEmail, $formData]
        );
    } else {
        exec_stmt(
            $db,
            "INSERT INTO employment_form_submissions (job_id, candidate_email, candidate_form_data)
             VALUES (?, ?, ?)",
            "iss",
            [$jobId, $candidateEmail, $formData]
        );
    }

    respond([
        "ok" => true,
        "submissionId" => $db->insert_id,
        "candidateId" => $candidateId,
    ], 201);
}

function employment_form_submission(mysqli $db, int $submissionId): void
{
    if ($submissionId <= 0) {
        respond(["error" => "Submission not found"], 404);
    }

    $submission = row(
        $db,
        "SELECT
           efs.id,
           efs.job_id AS jobId,
           efs.candidate_id AS candidateId,
           efs.candidate_email AS candidateEmail,
           efs.candidate_form_data AS candidateFormData,
           efs.hr_form_data AS hrFormData,
           efs.candidate_submitted_at AS candidateSubmittedAt,
           j.title AS jobTitle,
           j.department AS jobDepartment
         FROM employment_form_submissions efs
         JOIN jobs j ON j.id = efs.job_id
         WHERE efs.id = ?
         LIMIT 1",
        "i",
        [$submissionId]
    );

    if (!$submission) {
        respond(["error" => "Submission not found"], 404);
    }

    $decodeJson = static function (?string $value): array {
        if (!$value) {
            return [];
        }
        $decoded = json_decode($value, true);
        return is_array($decoded) ? $decoded : [];
    };

    respond([
        "submission" => [
            "id" => (int) $submission["id"],
            "jobId" => (int) $submission["jobId"],
            "candidateId" => $submission["candidateId"] === null ? null : (int) $submission["candidateId"],
            "candidateEmail" => (string) $submission["candidateEmail"],
            "candidateData" => $decodeJson($submission["candidateFormData"] ?? null),
            "hrFormData" => $decodeJson($submission["hrFormData"] ?? null),
            "candidateSubmittedAt" => (string) $submission["candidateSubmittedAt"],
            "jobTitle" => (string) $submission["jobTitle"],
            "jobDepartment" => (string) $submission["jobDepartment"],
        ],
    ]);
}

function employment_form_submissions(mysqli $db): void
{
    $submissions = rows(
        $db,
        "SELECT
           efs.id AS submissionId,
           efs.job_id AS jobId,
           efs.candidate_id AS candidateId,
           COALESCE(NULLIF(c.full_name, ''), NULLIF(JSON_UNQUOTE(JSON_EXTRACT(efs.candidate_form_data, '$.values.fullName')), ''), efs.candidate_email) AS candidateName,
           efs.candidate_email AS candidateEmail,
           j.title AS jobTitle,
           j.department AS jobDepartment,
           efs.candidate_submitted_at AS formSubmittedAt,
           efs.candidate_submitted_at AS submittedDate
         FROM employment_form_submissions efs
         JOIN jobs j ON j.id = efs.job_id
         LEFT JOIN candidates c ON c.id = efs.candidate_id
         ORDER BY efs.candidate_submitted_at DESC, efs.id DESC"
    );

    respond(["submissions" => $submissions]);
}

function update_employment_form_internal(mysqli $db, int $submissionId): void
{
    ensure_employment_form_submission_schema($db);
    if ($submissionId <= 0) {
        respond(["error" => "Submission not found"], 404);
    }

    $exists = row($db, "SELECT id FROM employment_form_submissions WHERE id = ? LIMIT 1", "i", [$submissionId]);
    if (!$exists) {
        respond(["error" => "Submission not found"], 404);
    }

    $data = input_json();
    $hrFormData = is_array($data["hrFormData"] ?? null) ? $data["hrFormData"] : [];
    $hrJson = $hrFormData === []
        ? "{}"
        : json_encode($hrFormData, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);

    if ($hrJson === false) {
        respond(["error" => "The HR section details could not be saved"], 422);
    }

    exec_stmt(
        $db,
        "UPDATE employment_form_submissions
         SET hr_form_data = ?,
             hr_updated_at = NOW()
         WHERE id = ?",
        "si",
        [$hrJson, $submissionId]
    );

    respond(["ok" => true]);
}

// Job dashboard and Create Job actions.
function application_analysis_status_is_processing(?string $status): bool
{
    $normalized = strtolower(trim((string) ($status ?? "")));
    return $normalized === "" || in_array($normalized, ["pending", "parsing", "scoring"], true);
}

function application_analysis_processing_sql(string $alias = "a"): string
{
    return "({$alias}.analysis_status IS NULL OR {$alias}.analysis_status IN ('pending', 'parsing', 'scoring'))";
}

function jobs_query(): string
{
    $processingSql = application_analysis_processing_sql("a");
    return "SELECT
        j.id,
        j.job_code AS jobCode,
        j.title,
        j.department,
        j.location,
        j.salary_range AS salaryRange,
        " . candidate_public_job_type_sql() . " AS employmentType,
        j.status,
        j.description,
        j.jd_file_name AS jdFileName,
        j.jd_file_path AS jdFilePath,
        j.published_at AS publishedAt,
        j.created_at AS createdAt,
        al.public_path AS link,
        COUNT(a.id) AS applicants,
        SUM(CASE WHEN a.submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY) THEN 1 ELSE 0 END) AS newApplicants,
        ROUND(COALESCE(AVG(CASE WHEN {$processingSql} THEN NULL ELSE a.total_score END), 0), 2) AS avgScore,
        SUM(CASE WHEN a.application_status = 'shortlisted' THEN 1 ELSE 0 END) AS shortlistedCount,
        SUM(CASE WHEN a.application_status = 'new' THEN 1 ELSE 0 END) AS pendingCount,
        SUM(CASE WHEN a.application_status IN ('interview', 'interviewed') THEN 1 ELSE 0 END) AS interviewCount,
        SUM(CASE WHEN a.application_status = 'rejected' THEN 1 ELSE 0 END) AS rejectedCount,
        SUM(CASE WHEN a.application_status = 'filtered_out' OR a.eligibility_status = 'filtered_out' THEN 1 ELSE 0 END) AS filteredOutCount
      FROM jobs j
      LEFT JOIN application_links al ON al.job_id = j.id
      LEFT JOIN applications a ON a.job_id = j.id
      GROUP BY j.id, al.public_path";
}

function job_document_absolute_path(string $path): string
{
    if ($path === "" || strpos($path, "\0") !== false) {
        return "";
    }

    return __DIR__ . str_replace("/", DIRECTORY_SEPARATOR, $path);
}

function job_document_candidate(array $document): ?array
{
    $path = trim((string) ($document["filePath"] ?? ""));
    $absolutePath = job_document_absolute_path($path);
    if ($path === "" || $absolutePath === "" || !is_file($absolutePath)) {
        return null;
    }

    $fileName = basename((string) ($document["fileName"] ?? ""));
    if ($fileName === "") {
        $fileName = basename($path);
    }

    return [
        "fileName" => $fileName,
        "filePath" => $path,
        "absolutePath" => $absolutePath,
    ];
}

function resolve_job_description_document(mysqli $db, int $jobId, array $job): ?array
{
    // A job's own file always wins when it is still available on disk.
    $ownDocument = job_document_candidate([
        "fileName" => $job["jdFileName"] ?? $job["jd_file_name"] ?? "",
        "filePath" => $job["jdFilePath"] ?? $job["jd_file_path"] ?? "",
    ]);
    if ($ownDocument) {
        return $ownDocument;
    }

    // Demo/older records may point at a file that is no longer bundled with the
    // deployment. Reuse another real job-description file before using the
    // bundled workbook, so the link still resolves to an actual document.
    $otherJobs = rows(
        $db,
        "SELECT id, jd_file_name AS fileName, jd_file_path AS filePath
         FROM jobs
         WHERE id <> ?
           AND jd_file_path IS NOT NULL
           AND TRIM(jd_file_path) <> ''
         ORDER BY id",
        "i",
        [$jobId]
    );
    foreach ($otherJobs as $otherJob) {
        $fallbackDocument = job_document_candidate($otherJob);
        if ($fallbackDocument) {
            return $fallbackDocument;
        }
    }

    $mockDocument = job_document_candidate([
        "fileName" => "job-description.xlsx",
        "filePath" => "/mock-files/job-description.xlsx",
    ]);

    return $mockDocument;
}

function normalize_job_document_metadata(mysqli $db, array $job): array
{
    $jobId = (int) ($job["id"] ?? 0);
    $document = resolve_job_description_document($db, $jobId, $job);
    if (!$document) {
        $job["jdFileName"] = null;
        $job["jdFilePath"] = null;
        return $job;
    }

    $job["jdFileName"] = $document["fileName"];
    $job["jdFilePath"] = $document["filePath"];
    return $job;
}

function dashboard(mysqli $db): void
{
    $jobs = array_map(
        static fn(array $job): array => normalize_job_document_metadata($db, $job),
        rows($db, jobs_query() . " ORDER BY j.created_at DESC")
    );
    $summary = row(
        $db,
        "SELECT
          (SELECT COUNT(*) FROM jobs) AS totalJobs,
          (SELECT COUNT(*) FROM jobs WHERE status = 'active') AS activeJobs,
          (SELECT COUNT(*) FROM applications) AS totalCandidates,
          (SELECT COUNT(*) FROM applications WHERE application_status = 'new') AS pendingReview,
          (SELECT COUNT(*) FROM applications WHERE application_status = 'shortlisted') AS shortlisted,
          (SELECT COUNT(*) FROM applications WHERE submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)) AS recentApplications"
    );
    respond(["summary" => $summary, "jobs" => $jobs]);
}

function jobs(mysqli $db): void
{
    respond([
        "jobs" => array_map(
            static fn(array $job): array => normalize_job_document_metadata($db, $job),
            rows($db, jobs_query() . " ORDER BY j.department, j.created_at DESC")
        ),
    ]);
}

function ensure_job_creation_schema(mysqli $db): void
{
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS job_qualifications (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          job_id INT UNSIGNED NOT NULL,
          qualification TEXT NOT NULL,
          sort_order INT UNSIGNED NOT NULL DEFAULT 1,
          CONSTRAINT fk_job_qualifications_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
          UNIQUE KEY uq_job_qualifications_order (job_id, sort_order)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS job_eligibility_filter_values (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          job_id INT UNSIGNED NOT NULL,
          filter_key VARCHAR(100) NOT NULL,
          filter_label VARCHAR(160) NOT NULL,
          filter_value VARCHAR(500) NULL,
          sort_order INT UNSIGNED NOT NULL DEFAULT 0,
          CONSTRAINT fk_job_eligibility_values_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
          UNIQUE KEY uq_job_eligibility_value (job_id, filter_key),
          INDEX idx_job_eligibility_values_job (job_id)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS job_application_questions (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          job_id INT UNSIGNED NOT NULL,
          question_text VARCHAR(500) NOT NULL,
          field_type ENUM('text', 'textarea', 'number', 'dropdown') NOT NULL DEFAULT 'text',
          is_required TINYINT(1) NOT NULL DEFAULT 0,
          is_active TINYINT(1) NOT NULL DEFAULT 1,
          sort_order INT UNSIGNED NOT NULL DEFAULT 0,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_job_application_questions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
          INDEX idx_job_application_questions_job (job_id, is_active, sort_order)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS job_application_question_options (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          question_id INT UNSIGNED NOT NULL,
          option_label VARCHAR(255) NOT NULL,
          sort_order INT UNSIGNED NOT NULL DEFAULT 0,
          CONSTRAINT fk_job_application_question_options_question FOREIGN KEY (question_id) REFERENCES job_application_questions(id) ON DELETE CASCADE,
          UNIQUE KEY uq_job_application_question_option (question_id, option_label),
          INDEX idx_job_application_question_options_question (question_id, sort_order)
        ) ENGINE=InnoDB"
    );
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS application_question_answers (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          application_id INT UNSIGNED NOT NULL,
          question_id INT UNSIGNED NOT NULL,
          answer_text TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_application_question_answers_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
          CONSTRAINT fk_application_question_answers_question FOREIGN KEY (question_id) REFERENCES job_application_questions(id) ON DELETE RESTRICT,
          UNIQUE KEY uq_application_question_answer (application_id, question_id),
          INDEX idx_application_question_answers_application (application_id)
        ) ENGINE=InnoDB"
    );
    if (!table_column_exists($db, "job_criteria", "criterion_type")) {
        exec_stmt(
            $db,
            "ALTER TABLE job_criteria
             ADD COLUMN criterion_type ENUM(
               'relevant_skill',
               'relevant_experience',
               'education_relevance',
               'domain_knowledge',
               'preferred_certification',
               'job_related_language'
             ) NOT NULL DEFAULT 'relevant_skill' AFTER criteria_name"
        );
    }
    if (!table_column_exists($db, "job_criteria", "source_text")) {
        exec_stmt(
            $db,
            "ALTER TABLE job_criteria ADD COLUMN source_text TEXT NULL AFTER description"
        );
    }
    if (!table_column_exists($db, "job_criteria", "evidence_rule")) {
        exec_stmt(
            $db,
            "ALTER TABLE job_criteria ADD COLUMN evidence_rule TEXT NULL AFTER source_text"
        );
    }
}

function job_request_data(): array
{
    $data = input_data();
    if (isset($data["payload"]) && is_string($data["payload"])) {
        $payload = json_decode($data["payload"], true);
        return is_array($payload) ? $payload : [];
    }
    return $data;
}

function generate_job_code(mysqli $db): string
{
    do {
        $code = "JOB-" . date("ymd") . "-" . strtoupper(bin2hex(random_bytes(2)));
    } while (row($db, "SELECT id FROM jobs WHERE job_code = ? LIMIT 1", "s", [$code]));
    return $code;
}

function store_job_description_file(): ?array
{
    $file = $_FILES["jdFile"] ?? null;
    if (!$file || (int) ($file["error"] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) {
        return null;
    }
    if ((int) ($file["error"] ?? UPLOAD_ERR_OK) !== UPLOAD_ERR_OK) {
        respond(["error" => "The job description file could not be uploaded"], 422);
    }

    $originalName = basename((string) ($file["name"] ?? "job-description.xlsx"));
    if (strtolower(pathinfo($originalName, PATHINFO_EXTENSION)) !== "xlsx") {
        respond(["error" => "Only XLSX job description files are accepted"], 422);
    }
    if ((int) ($file["size"] ?? 0) > 5 * 1024 * 1024) {
        respond(["error" => "Job description file size must be less than 5MB"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "job-descriptions";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true) && !is_dir($uploadDir)) {
        throw new RuntimeException("Unable to create the job description upload directory");
    }

    $storedName = date("YmdHis") . "-" . bin2hex(random_bytes(5)) . ".xlsx";
    $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
    if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
        throw new RuntimeException("Unable to store the uploaded job description file");
    }

    return [$originalName, "/uploads/job-descriptions/{$storedName}", $destination];
}

function delete_replaced_job_file(?string $path): void
{
    if (!$path || strpos($path, "/uploads/job-descriptions/") !== 0) {
        return;
    }
    $absolutePath = __DIR__ . str_replace("/", DIRECTORY_SEPARATOR, $path);
    if (is_file($absolutePath)) {
        @unlink($absolutePath);
    }
}

function create_job(mysqli $db): void
{
    persist_job($db, null);
}

function job_description_file(mysqli $db, int $jobId): void
{
    $job = row($db, "SELECT jd_file_name, jd_file_path FROM jobs WHERE id = ? LIMIT 1", "i", [$jobId]);
    if (!$job) {
        respond(["error" => "Job description file not found"], 404);
    }

    $document = resolve_job_description_document($db, $jobId, $job);
    if (!$document) {
        respond(["error" => "Job description file not found"], 404);
    }

    $absolutePath = $document["absolutePath"];
    $fileName = $document["fileName"];
    $extension = strtolower(pathinfo($fileName, PATHINFO_EXTENSION));
    $contentType = match ($extension) {
        "pdf" => "application/pdf",
        "xls" => "application/vnd.ms-excel",
        "xlsx" => "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        default => "application/octet-stream",
    };

    header("Content-Type: {$contentType}");
    header("Content-Length: " . filesize($absolutePath));
    header("Content-Disposition: inline; filename=\"{$fileName}\"");
    readfile($absolutePath);
    exit;
}

function save_job(mysqli $db, int $jobId): void
{
    persist_job($db, $jobId);
}

function persist_job(mysqli $db, ?int $jobId): void
{
    // This is the shared create/edit boundary: it persists job details first,
    // then replaces HR-owned qualifications, criteria, eligibility, questions,
    // and the optional JD document as one logical workflow.
    ensure_job_creation_schema($db);
    $data = job_request_data();
    $title = trim((string) ($data["title"] ?? ""));
    $department = trim((string) ($data["department"] ?? ""));
    $status = (string) ($data["status"] ?? "draft");
    if ($title === "" || $department === "") {
        respond(["error" => "Job title and department are required"], 422);
    }
    if (!in_array($status, ["draft", "active"], true)) {
        respond(["error" => "Job status must be draft or active"], 422);
    }

    $existingJob = null;
    if ($jobId !== null) {
        $existingJob = row($db, "SELECT * FROM jobs WHERE id = ? LIMIT 1", "i", [$jobId]);
        if (!$existingJob) {
            respond(["error" => "Job not found"], 404);
        }
    }

    $createdByUserId = $existingJob
        ? (int) $existingJob["created_by_user_id"]
        : (int) ($data["createdByUserId"] ?? 0);
    $actionUserId = (int) ($data["actionUserId"] ?? 0);
    if ($actionUserId <= 0) {
        $actionUserId = $createdByUserId;
    }
    if (!$existingJob && !$createdByUserId) {
        respond(["error" => "The logged-in HR user is required"], 422);
    }
    if (!$existingJob && !row($db, "SELECT id FROM users WHERE id = ? AND status = 'active' LIMIT 1", "i", [$createdByUserId])) {
        respond(["error" => "The logged-in HR user was not found"], 422);
    }

    $responsibilities = array_values(array_filter(array_map(
        static fn($value): string => trim((string) $value),
        is_array($data["responsibilities"] ?? null) ? $data["responsibilities"] : []
    ), static fn(string $value): bool => $value !== ""));
    $qualifications = array_values(array_filter(array_map(
        static fn($value): string => trim((string) $value),
        is_array($data["qualifications"] ?? null) ? $data["qualifications"] : []
    ), static fn(string $value): bool => $value !== ""));
    $criteria = is_array($data["criteria"] ?? null) ? $data["criteria"] : [];

    if ($status === "active") {
        $activeCriteria = array_values(array_filter(
            $criteria,
            static fn($item): bool => is_array($item) && ($item["status"] ?? "active") === "active" && trim((string) ($item["name"] ?? "")) !== ""
        ));
        $totalWeight = array_reduce(
            $activeCriteria,
            static fn(float $sum, array $item): float => $sum + (float) ($item["weight"] ?? 0),
            0.0
        );
        if (!$activeCriteria || abs($totalWeight - 100.0) > 0.01) {
            respond(["error" => "Active jobs require criteria totalling 100%"], 422);
        }
    }

    $uploadedFile = store_job_description_file();
    if (!$existingJob && !$uploadedFile) {
        respond(["error" => "An XLSX job description file is required"], 422);
    }
    $removeJdFile = $existingJob && !$uploadedFile && filter_var(
        $data["removeJdFile"] ?? false,
        FILTER_VALIDATE_BOOLEAN
    );
    $fileName = $removeJdFile
        ? null
        : ($uploadedFile[0] ?? ($existingJob["jd_file_name"] ?? null));
    $filePath = $removeJdFile
        ? null
        : ($uploadedFile[1] ?? ($existingJob["jd_file_path"] ?? null));
    $newFileAbsolutePath = $uploadedFile[2] ?? null;
    $oldFilePath = $existingJob["jd_file_path"] ?? null;

    $location = trim((string) ($data["location"] ?? ""));
    $salaryRange = trim((string) ($data["salaryRange"] ?? ""));
    $description = trim((string) ($data["description"] ?? implode("\n", $responsibilities)));
    $eligibilityFilters = is_array($data["eligibilityFilters"] ?? null)
        ? $data["eligibilityFilters"]
        : [];
    $enabledEligibilityFilters = is_array($eligibilityFilters["enabledFilters"] ?? null)
        ? array_map("strval", $eligibilityFilters["enabledFilters"])
        : [];
    $requestedEmploymentType = trim((string) ($data["employmentType"] ?? ""));
    $allowedEmploymentTypes = ["Full-time", "Part-time", "Internship"];
    $employmentType = in_array($requestedEmploymentType, $allowedEmploymentTypes, true)
        ? $requestedEmploymentType
        : (
            in_array("internshipAccepted", $enabledEligibilityFilters, true)
                && strtolower(trim((string) ($eligibilityFilters["internshipAccepted"] ?? ""))) === "yes"
                ? "Internship"
                : "Full-time"
        );
    $jobCode = $existingJob["job_code"] ?? generate_job_code($db);

    $db->begin_transaction();
    try {
        if ($existingJob) {
            $params = [
                $title, $department, $location, $salaryRange, $description,
                $employmentType, $status, $fileName, $filePath, $status, $jobId,
            ];
            exec_stmt(
                $db,
                "UPDATE jobs SET
                  title = ?, department = ?, location = ?, salary_range = ?, description = ?,
                  employment_type = ?, status = ?, jd_file_name = ?, jd_file_path = ?,
                  published_at = CASE WHEN ? = 'active' THEN COALESCE(published_at, NOW()) ELSE published_at END
                 WHERE id = ?",
                str_repeat("s", 10) . "i",
                $params
            );
        } else {
            $params = [
                $jobCode, $createdByUserId, $title, $department, $location,
                $salaryRange, $employmentType, $description, $status,
                $fileName, $filePath, $status,
            ];
            exec_stmt(
                $db,
                "INSERT INTO jobs (
                  job_code, created_by_user_id, title, department, location,
                  salary_range, employment_type, description, status,
                  jd_file_name, jd_file_path, published_at
                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, IF(? = 'active', NOW(), NULL))",
                "si" . str_repeat("s", 10),
                $params
            );
            $jobId = (int) $db->insert_id;
        }

        replace_job_detail_rows($db, $jobId, $responsibilities, $qualifications, $criteria);
        replace_job_eligibility($db, $jobId, $eligibilityFilters);
        replace_job_application_questions(
            $db,
            $jobId,
            is_array($data["applicationQuestions"] ?? null) ? $data["applicationQuestions"] : []
        );

        if ($status === "active") {
            $link = row($db, "SELECT id FROM application_links WHERE job_id = ? LIMIT 1", "i", [$jobId]);
            if ($link) {
                exec_stmt($db, "UPDATE application_links SET status = 'active' WHERE job_id = ?", "i", [$jobId]);
            } else {
                $token = bin2hex(random_bytes(20));
                $publicPath = "/apply/{$jobCode}";
                exec_stmt(
                    $db,
                    "INSERT INTO application_links (job_id, token, public_path, status) VALUES (?, ?, ?, 'active')",
                    "iss",
                    [$jobId, $token, $publicPath]
                );
            }
    } else {
        exec_stmt($db, "UPDATE application_links SET status = 'disabled' WHERE job_id = ?", "i", [$jobId]);
    }

        $db->commit();
    } catch (Throwable $error) {
        $db->rollback();
        if ($newFileAbsolutePath && is_file($newFileAbsolutePath)) {
            @unlink($newFileAbsolutePath);
        }
        throw $error;
    }

    if (($uploadedFile || $removeJdFile) && $oldFilePath && $oldFilePath !== $filePath) {
        delete_replaced_job_file((string) $oldFilePath);
    }
    log_job_action(
        $db,
        $actionUserId,
        (int) $jobId,
        $title,
        $existingJob ? "edit_job" : "create_job",
        $existingJob ? "Edited Job" : "Created Job"
    );
    job_details($db, $jobId);
}

function replace_job_detail_rows(mysqli $db, int $jobId, array $responsibilities, array $qualifications, array $criteria): void
{
    exec_stmt($db, "DELETE FROM job_responsibilities WHERE job_id = ?", "i", [$jobId]);
    foreach ($responsibilities as $index => $responsibility) {
        exec_stmt(
            $db,
            "INSERT INTO job_responsibilities (job_id, responsibility, sort_order) VALUES (?, ?, ?)",
            "isi",
            [$jobId, $responsibility, $index + 1]
        );
    }
    exec_stmt($db, "DELETE FROM job_qualifications WHERE job_id = ?", "i", [$jobId]);
    foreach ($qualifications as $index => $qualification) {
        exec_stmt(
            $db,
            "INSERT INTO job_qualifications (job_id, qualification, sort_order) VALUES (?, ?, ?)",
            "isi",
            [$jobId, $qualification, $index + 1]
        );
    }

    $existingCriteriaRows = rows(
        $db,
        "SELECT id FROM job_criteria WHERE job_id = ? ORDER BY sort_order, id",
        "i",
        [$jobId]
    );
    $existingCriteriaIds = [];
    foreach ($existingCriteriaRows as $existingCriteriaRow) {
        $existingCriteriaIds[(int) $existingCriteriaRow["id"]] = true;
    }
    $savedCriteriaIds = [];
    $allowedCriterionTypes = [
        "relevant_skill",
        "relevant_experience",
        "education_relevance",
        "domain_knowledge",
        "preferred_certification",
        "job_related_language",
    ];
    foreach ($criteria as $index => $criterion) {
        if (!is_array($criterion)) {
            continue;
        }
        $name = trim((string) ($criterion["name"] ?? ""));
        if ($name === "") {
            continue;
        }
        $weight = max(0, min(100, (float) ($criterion["weight"] ?? 0)));
        $criterionType = trim((string) ($criterion["type"] ?? "relevant_skill"));
        if (!in_array($criterionType, $allowedCriterionTypes, true)) {
            $criterionType = "relevant_skill";
        }
        $description = trim((string) ($criterion["explanation"] ?? ""));
        $sourceText = trim((string) ($criterion["sourceText"] ?? ""));
        $evidenceRule = trim((string) ($criterion["evidenceRule"] ?? ""));
        $isActive = ($criterion["status"] ?? "active") === "active" ? 1 : 0;
        $criterionId = is_numeric($criterion["id"] ?? null)
            ? (int) $criterion["id"]
            : 0;

        if ($criterionId > 0 && isset($existingCriteriaIds[$criterionId])) {
            exec_stmt(
                $db,
                "UPDATE job_criteria
                 SET criteria_name = ?, criterion_type = ?, weight = ?, description = ?,
                     source_text = ?, evidence_rule = ?, is_active = ?, sort_order = ?
                 WHERE id = ? AND job_id = ?",
                "ssdsssiiii",
                [
                    $name,
                    $criterionType,
                    $weight,
                    $description,
                    $sourceText,
                    $evidenceRule,
                    $isActive,
                    $index + 1,
                    $criterionId,
                    $jobId,
                ]
            );
            $savedCriteriaIds[$criterionId] = true;
            continue;
        }

        exec_stmt(
            $db,
            "INSERT INTO job_criteria (job_id, criteria_name, criterion_type, weight, description, source_text, evidence_rule, is_active, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "issdsssii",
            [$jobId, $name, $criterionType, $weight, $description, $sourceText, $evidenceRule, $isActive, $index + 1]
        );
        $savedCriteriaIds[(int) $db->insert_id] = true;
    }

    // Keep removed criteria as inactive records so historical score breakdowns
    // retain their foreign-key target instead of being deleted by cascade.
    foreach ($existingCriteriaIds as $existingCriteriaId => $_present) {
        if (isset($savedCriteriaIds[$existingCriteriaId])) {
            continue;
        }
        exec_stmt(
            $db,
            "UPDATE job_criteria SET is_active = 0, sort_order = ? WHERE id = ? AND job_id = ?",
            "iii",
            [100000 + $existingCriteriaId, $existingCriteriaId, $jobId]
        );
    }
}

function replace_job_eligibility(mysqli $db, int $jobId, array $filters): void
{
    exec_stmt($db, "DELETE FROM job_eligibility_filter_values WHERE job_id = ?", "i", [$jobId]);
    exec_stmt($db, "DELETE FROM eligibility_filters WHERE job_id = ?", "i", [$jobId]);

    $enabled = is_array($filters["enabledFilters"] ?? null) ? $filters["enabledFilters"] : [];
    $customFilters = is_array($filters["customFilters"] ?? null) ? $filters["customFilters"] : [];
    $labels = [
        "minCGPA" => "Minimum CGPA",
        "minExperience" => "Minimum Experience",
        "educationLevel" => "Education Level",
        "maxNoticePeriod" => "Maximum Notice Period",
        "requiredLanguage" => "Required Language",
        "requiredLocation" => "Required Location",
        "internshipAccepted" => "Internship Accepted",
    ];

    foreach (array_values(array_unique(array_map("strval", $enabled))) as $index => $key) {
        $label = $labels[$key] ?? $key;
        $value = $filters[$key] ?? "";
        foreach ($customFilters as $customFilter) {
            if (is_array($customFilter) && (string) ($customFilter["id"] ?? "") === $key) {
                $label = (string) ($customFilter["label"] ?? $key);
                $value = $customFilter["value"] ?? "";
                break;
            }
        }
        exec_stmt(
            $db,
            "INSERT INTO job_eligibility_filter_values (job_id, filter_key, filter_label, filter_value, sort_order) VALUES (?, ?, ?, ?, ?)",
            "isssi",
            [$jobId, $key, $label, (string) $value, $index + 1]
        );
    }

    if (!$enabled) {
        return;
    }
    $minCgpa = in_array("minCGPA", $enabled, true) ? (float) ($filters["minCGPA"] ?? 0) : null;
    preg_match('/[0-9]+(?:\.[0-9]+)?/', (string) ($filters["minExperience"] ?? ""), $experienceMatch);
    $minExperience = in_array("minExperience", $enabled, true) && $experienceMatch ? (float) $experienceMatch[0] : null;
    $internshipAccepted = in_array("internshipAccepted", $enabled, true) && strtolower((string) ($filters["internshipAccepted"] ?? "")) === "yes" ? 1 : 0;
    $qualification = in_array("educationLevel", $enabled, true) ? (string) ($filters["educationLevel"] ?? "") : null;
    $language = in_array("requiredLanguage", $enabled, true) ? (string) ($filters["requiredLanguage"] ?? "") : null;
    $location = in_array("requiredLocation", $enabled, true) ? (string) ($filters["requiredLocation"] ?? "") : null;
    preg_match('/[0-9]+/', (string) ($filters["maxNoticePeriod"] ?? ""), $noticeMatch);
    $noticeDays = in_array("maxNoticePeriod", $enabled, true) && $noticeMatch ? (int) $noticeMatch[0] : null;
    exec_stmt(
        $db,
        "INSERT INTO eligibility_filters (
          job_id, min_cgpa, min_years_experience, internship_accepted,
          required_qualification, required_language, required_location, max_notice_period_days
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        "iddisssi",
        [$jobId, $minCgpa, $minExperience, $internshipAccepted, $qualification, $language, $location, $noticeDays]
    );
}

function sanitize_application_question_type(mixed $value): string
{
    $type = strtolower(trim((string) $value));
    return in_array($type, ["text", "textarea", "number", "dropdown"], true)
        ? $type
        : "text";
}

function replace_job_application_questions(mysqli $db, int $jobId, array $questions): void
{
    exec_stmt($db, "UPDATE job_application_questions SET is_active = 0 WHERE job_id = ?", "i", [$jobId]);

    foreach ($questions as $index => $question) {
        if (!is_array($question)) {
            continue;
        }
        $text = trim((string) ($question["question"] ?? ""));
        if ($text === "") {
            continue;
        }
        $type = sanitize_application_question_type($question["fieldType"] ?? "text");
        $required = filter_var($question["required"] ?? false, FILTER_VALIDATE_BOOLEAN) ? 1 : 0;
        $questionId = (int) ($question["id"] ?? 0);
        $existing = $questionId > 0
            ? row($db, "SELECT id FROM job_application_questions WHERE id = ? AND job_id = ?", "ii", [$questionId, $jobId])
            : null;

        if ($existing) {
            exec_stmt(
                $db,
                "UPDATE job_application_questions
                 SET question_text = ?, field_type = ?, is_required = ?, is_active = 1, sort_order = ?
                 WHERE id = ? AND job_id = ?",
                "ssiiii",
                [$text, $type, $required, $index + 1, $questionId, $jobId]
            );
        } else {
            exec_stmt(
                $db,
                "INSERT INTO job_application_questions
                   (job_id, question_text, field_type, is_required, is_active, sort_order)
                 VALUES (?, ?, ?, ?, 1, ?)",
                "issii",
                [$jobId, $text, $type, $required, $index + 1]
            );
            $questionId = (int) $db->insert_id;
        }

        exec_stmt($db, "DELETE FROM job_application_question_options WHERE question_id = ?", "i", [$questionId]);
        if ($type !== "dropdown") {
            continue;
        }
        $options = array_values(array_unique(array_filter(array_map(
            static fn($option): string => trim((string) $option),
            is_array($question["options"] ?? null) ? $question["options"] : []
        ), static fn(string $option): bool => $option !== "")));
        foreach ($options as $optionIndex => $option) {
            exec_stmt(
                $db,
                "INSERT INTO job_application_question_options (question_id, option_label, sort_order) VALUES (?, ?, ?)",
                "isi",
                [$questionId, $option, $optionIndex + 1]
            );
        }
    }
}

function application_questions_payload(mysqli $db, int $jobId): array
{
    $questions = rows(
        $db,
        "SELECT id, question_text AS question, field_type AS fieldType,
                is_required AS required, sort_order AS sortOrder
         FROM job_application_questions
         WHERE job_id = ? AND is_active = 1
         ORDER BY sort_order, id",
        "i",
        [$jobId]
    );

    $options = rows(
        $db,
        "SELECT
           question_option.question_id AS questionId,
           question_option.option_label AS optionLabel
         FROM job_application_question_options question_option
         JOIN job_application_questions question ON question.id = question_option.question_id
         WHERE question.job_id = ?
           AND question.is_active = 1
         ORDER BY question_option.question_id, question_option.sort_order, question_option.id",
        "i",
        [$jobId]
    );

    return hydrate_application_questions($questions, $options);
}

function hydrate_application_questions(array $questions, array $options): array
{
    $optionsByQuestion = rows_grouped_by_int_key($options, "questionId");
    foreach ($questions as &$question) {
        $questionId = (int) $question["id"];
        $question["id"] = (int) $question["id"];
        $question["required"] = (int) $question["required"] === 1;
        $question["sortOrder"] = (int) $question["sortOrder"];
        $question["options"] = array_map(
            static fn(array $option): string => (string) $option["optionLabel"],
            $optionsByQuestion[$questionId] ?? []
        );
    }
    unset($question);
    return $questions;
}

function application_question_answers_payload(mysqli $db, int $applicationId): array
{
    return rows(
        $db,
        "SELECT q.id AS questionId, q.question_text AS question,
                q.field_type AS fieldType, a.answer_text AS answer
         FROM application_question_answers a
         JOIN job_application_questions q ON q.id = a.question_id
         WHERE a.application_id = ?
         ORDER BY q.sort_order, q.id",
        "i",
        [$applicationId]
    );
}

// Candidate review, ranking, and status actions.
function applications(mysqli $db): void
{
    $filter = (string) ($_GET["filter"] ?? "all");
    $where = "";

    if ($filter === "last24") {
        $where = "WHERE a.submitted_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)";
    } elseif ($filter === "pending") {
        $where = "WHERE a.application_status = 'new'";
    }

    $processingSql = application_analysis_processing_sql("a");
    $applications = rows(
        $db,
        "SELECT
           a.id AS applicationId,
           c.id AS candidateId,
           c.full_name AS candidateName,
           c.email AS candidateEmail,
           j.id AS jobId,
           j.title AS jobTitle,
           j.department AS jobDepartment,
           a.submitted_at AS submittedDate,
           CASE
             WHEN a.analysis_status = 'failed' THEN 'filtered_out'
             ELSE a.eligibility_status
           END AS eligibilityStatus,
           a.analysis_status AS analysisStatus,
           CASE WHEN {$processingSql} THEN NULL ELSE a.rank_no END AS `rank`,
           CASE
             WHEN {$processingSql} THEN NULL
             WHEN a.analysis_status = 'failed' THEN 0
             ELSE a.total_score
           END AS score,
           a.application_status AS status,
           CASE
             WHEN a.analysis_status = 'failed'
               OR a.eligibility_status = 'filtered_out'
               OR a.application_status = 'filtered_out'
             THEN 1
             ELSE 0
           END AS filteredOut,
           (
             SELECT efs.id
             FROM employment_form_submissions efs
             WHERE efs.job_id = a.job_id
               AND (efs.candidate_id = c.id OR LOWER(efs.candidate_email) = LOWER(c.email))
             ORDER BY efs.candidate_submitted_at DESC, efs.id DESC
             LIMIT 1
           ) AS employmentFormSubmissionId,
           CASE
             WHEN {$processingSql} THEN 'Pending Score'
             WHEN a.analysis_status = 'failed' THEN 'Scored'
             WHEN a.total_score IS NULL THEN 'Pending Score'
             ELSE 'Scored'
           END AS scoreStatus
         FROM applications a
         JOIN candidates c ON c.id = a.candidate_id
         JOIN jobs j ON j.id = a.job_id
         {$where}
         ORDER BY a.submitted_at DESC, a.id DESC"
    );

    $documentsByApplication = application_documents_by_application(
        $db,
        array_map(
            static fn(array $application): int => (int) $application["applicationId"],
            $applications
        )
    );
    foreach ($applications as &$application) {
        $applicationId = (int) $application["applicationId"];
        $application["documents"] = $documentsByApplication[$applicationId] ?? [];
    }
    unset($application);

    respond(["applications" => $applications]);
}

function job_details(mysqli $db, int $jobId): void
{
    [
        $jobRows,
        $responsibilities,
        $qualifications,
        $skills,
        $criteria,
        $eligibilityRows,
        $eligibilityValues,
        $applicationQuestions,
        $questionOptions,
    ] = row_sets($db, [
        jobs_query() . " HAVING j.id = {$jobId} LIMIT 1",
        "SELECT responsibility
         FROM job_responsibilities
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT qualification
         FROM job_qualifications
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT skill_name AS name, skill_type AS type, importance
         FROM job_required_skills
         WHERE job_id = {$jobId}
         ORDER BY importance, skill_name",
        "SELECT
           id,
           criteria_name AS name,
           criterion_type AS type,
           weight,
           description,
           source_text AS sourceText,
           evidence_rule AS evidenceRule,
           is_active AS isActive
         FROM job_criteria
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT
           min_cgpa AS minCgpa,
           min_years_experience AS minYearsExperience,
           internship_accepted AS internshipAccepted,
           required_qualification AS requiredQualification,
           required_language AS requiredLanguage,
           required_location AS requiredLocation,
           max_notice_period_days AS maxNoticePeriodDays
         FROM eligibility_filters
         WHERE job_id = {$jobId}
         LIMIT 1",
        "SELECT
           filter_key AS filterKey,
           filter_label AS filterLabel,
           filter_value AS filterValue
         FROM job_eligibility_filter_values
         WHERE job_id = {$jobId}
         ORDER BY sort_order",
        "SELECT
           id,
           question_text AS question,
           field_type AS fieldType,
           is_required AS required,
           sort_order AS sortOrder
         FROM job_application_questions
         WHERE job_id = {$jobId}
           AND is_active = 1
         ORDER BY sort_order, id",
        "SELECT
           question_option.question_id AS questionId,
           question_option.option_label AS optionLabel
         FROM job_application_question_options question_option
         JOIN job_application_questions job_question ON job_question.id = question_option.question_id
         WHERE job_question.job_id = {$jobId}
           AND job_question.is_active = 1
         ORDER BY question_option.question_id, question_option.sort_order, question_option.id",
    ]);

    $job = isset($jobRows[0])
        ? normalize_job_document_metadata($db, $jobRows[0])
        : null;
    if (!$job) {
        respond(["error" => "Job not found"], 404);
    }

    $applicationQuestions = hydrate_application_questions(
        $applicationQuestions,
        $questionOptions
    );

    $job["responsibilities"] = $responsibilities;
    $job["qualifications"] = $qualifications;
    $job["skills"] = $skills;
    $job["criteria"] = $criteria;
    $job["eligibility"] = $eligibilityRows[0] ?? null;
    $job["eligibilityValues"] = $eligibilityValues;
    $job["applicationQuestions"] = $applicationQuestions;

    respond(["job" => $job]);
}

function update_job(mysqli $db, int $jobId): void
{
    $data = input_json();
    $job = row(
        $db,
        "SELECT id, title, created_by_user_id AS createdByUserId
         FROM jobs
         WHERE id = ?
         LIMIT 1",
        "i",
        [$jobId]
    );
    if (!$job) {
        respond(["error" => "Job not found"], 404);
    }

    $status = (string) ($data["status"] ?? "");
    $allowed = ["draft", "active", "closed", "archived"];
    if (!in_array($status, $allowed, true)) {
        respond(["error" => "Invalid job status"], 422);
    }

    exec_stmt($db, "UPDATE jobs SET status = ?, closed_at = IF(? = 'closed', NOW(), closed_at) WHERE id = ?", "ssi", [$status, $status, $jobId]);
    log_job_action(
        $db,
        (int) ($data["actionUserId"] ?? $job["createdByUserId"] ?? 0),
        $jobId,
        (string) $job["title"],
        "edit_job",
        "Edited Job"
    );
    job_details($db, $jobId);
}

function delete_job(mysqli $db, int $jobId): void
{
    $job = row($db, "SELECT id, title, created_by_user_id AS createdByUserId, jd_file_path AS jdFilePath FROM jobs WHERE id = ? LIMIT 1", "i", [$jobId]);
    if (!$job) {
        respond(["error" => "Job not found"], 404);
    }

    $submissionCount = row(
        $db,
        "SELECT COUNT(*) AS total FROM employment_form_submissions WHERE job_id = ?",
        "i",
        [$jobId]
    );
    if ((int) ($submissionCount["total"] ?? 0) > 0) {
        respond([
            "error" => "This job cannot be deleted because it has employment form submissions.",
        ], 409);
    }

    $actionData = input_json();
    $actionUserId = (int) ($actionData["actionUserId"] ?? $job["createdByUserId"] ?? 0);
    exec_stmt($db, "DELETE FROM jobs WHERE id = ?", "i", [$jobId]);
    delete_replaced_job_file((string) ($job["jdFilePath"] ?? ""));
    log_job_action(
        $db,
        $actionUserId,
        null,
        (string) $job["title"],
        "delete_job",
        "Deleted Job"
    );
    respond(["ok" => true, "jobId" => $jobId]);
}

function update_department(mysqli $db): void
{
    $data = input_json();
    $currentDepartment = trim((string) ($data["department"] ?? ""));
    $newDepartment = trim((string) ($data["newDepartment"] ?? ""));

    if ($currentDepartment === "" || $newDepartment === "") {
        respond(["error" => "Both the current and new department names are required"], 422);
    }

    if (strlen($newDepartment) > 120) {
        respond(["error" => "Department name must be 120 characters or fewer"], 422);
    }

    $departmentJobs = rows(
        $db,
        "SELECT id, title, created_by_user_id AS createdByUserId
         FROM jobs
         WHERE department = ?
         ORDER BY title, id",
        "s",
        [$currentDepartment]
    );
    if (!$departmentJobs) {
        respond(["error" => "Department not found"], 404);
    }

    if ($currentDepartment === $newDepartment) {
        respond([
            "ok" => true,
            "department" => $newDepartment,
            "updatedJobCount" => 0,
        ]);
    }

    $actionUserId = (int) ($data["actionUserId"] ?? 0);
    if ($actionUserId <= 0) {
        $actionUserId = (int) ($departmentJobs[0]["createdByUserId"] ?? 0);
    }

    $db->begin_transaction();
    try {
        exec_stmt(
            $db,
            "UPDATE jobs SET department = ? WHERE department = ?",
            "ss",
            [$newDepartment, $currentDepartment]
        );
        $db->commit();
    } catch (Throwable $error) {
        $db->rollback();
        throw $error;
    }

    foreach ($departmentJobs as $job) {
        log_job_action(
            $db,
            $actionUserId,
            (int) $job["id"],
            (string) $job["title"],
            "edit_job_department",
            "Edited Department"
        );
    }

    respond([
        "ok" => true,
        "department" => $newDepartment,
        "updatedJobCount" => count($departmentJobs),
        "jobs" => array_map(
            static fn(array $job): array => [
                "id" => (int) $job["id"],
                "title" => (string) $job["title"],
            ],
            $departmentJobs
        ),
    ]);
}

function delete_department(mysqli $db): void
{
    $data = input_json();
    $department = trim((string) ($data["department"] ?? ""));
    if ($department === "") {
        respond(["error" => "Department is required"], 422);
    }

    $departmentJobs = rows(
        $db,
        "SELECT id, title, created_by_user_id AS createdByUserId, jd_file_path AS jdFilePath
         FROM jobs
         WHERE department = ?
         ORDER BY title, id",
        "s",
        [$department]
    );
    if (!$departmentJobs) {
        respond(["error" => "Department not found"], 404);
    }

    $blockedJobs = rows(
        $db,
        "SELECT j.title, COUNT(efs.id) AS submissionCount
         FROM jobs j
         JOIN employment_form_submissions efs ON efs.job_id = j.id
         WHERE j.department = ?
         GROUP BY j.id, j.title
         ORDER BY j.title",
        "s",
        [$department]
    );
    if ($blockedJobs) {
        respond([
            "error" => "This department cannot be deleted because some jobs have employment form submissions.",
            "blockedJobs" => array_map(
                static fn(array $job): array => [
                    "title" => (string) $job["title"],
                    "submissionCount" => (int) $job["submissionCount"],
                ],
                $blockedJobs
            ),
        ], 409);
    }

    $actionUserId = (int) ($data["actionUserId"] ?? 0);
    if ($actionUserId <= 0) {
        $actionUserId = (int) ($departmentJobs[0]["createdByUserId"] ?? 0);
    }

    $db->begin_transaction();
    try {
        exec_stmt($db, "DELETE FROM jobs WHERE department = ?", "s", [$department]);
        $db->commit();
    } catch (Throwable $error) {
        $db->rollback();
        throw $error;
    }

    foreach ($departmentJobs as $job) {
        delete_replaced_job_file((string) ($job["jdFilePath"] ?? ""));
        log_job_action(
            $db,
            $actionUserId,
            null,
            (string) $job["title"],
            "delete_job_department",
            "Deleted Job via Department"
        );
    }

    respond([
        "ok" => true,
        "department" => $department,
        "deletedJobCount" => count($departmentJobs),
        "deletedJobs" => array_map(
            static fn(array $job): array => [
                "id" => (int) $job["id"],
                "title" => (string) $job["title"],
            ],
            $departmentJobs
        ),
    ]);
}

function log_job_action(
    mysqli $db,
    int $userId,
    ?int $jobId,
    string $jobTitle,
    string $actionType,
    string $actionLabel
): void {
    if ($userId <= 0 || trim($jobTitle) === "") {
        return;
    }

    $activeUser = row(
        $db,
        "SELECT id FROM users WHERE id = ? AND status = 'active' LIMIT 1",
        "i",
        [$userId]
    );
    if (!$activeUser) {
        return;
    }

    ensure_hr_action_log_reason_columns($db);
    if ($jobId === null) {
        exec_stmt(
            $db,
            "INSERT INTO hr_action_logs (user_id, application_id, job_id, candidate_id, action_type, action_label, job_title)
             VALUES (?, NULL, NULL, NULL, ?, ?, ?)",
            "isss",
            [$userId, $actionType, $actionLabel, $jobTitle]
        );
        return;
    }

    exec_stmt(
        $db,
        "INSERT INTO hr_action_logs (user_id, application_id, job_id, candidate_id, action_type, action_label, job_title)
         VALUES (?, NULL, ?, NULL, ?, ?, ?)",
        "iisss",
        [$userId, $jobId, $actionType, $actionLabel, $jobTitle]
    );
}

function job_candidates(mysqli $db, int $jobId): void
{
    /**
     * Build the HR candidate review read model. Scores/ranks stay hidden while
     * parsing or scoring is active, so the UI cannot present stale results as
     * completed analysis.
     */
    $job = row($db, "SELECT id, job_code AS jobCode, title, department FROM jobs WHERE id = ?", "i", [$jobId]);
    if (!$job) {
        respond(["error" => "Job not found"], 404);
    }

    $processingSql = application_analysis_processing_sql("a");
    $candidates = rows(
        $db,
        "SELECT
          a.id AS applicationId,
          c.id,
          c.full_name AS name,
          c.email,
          c.phone,
          c.current_cgpa AS cgpa,
          c.years_experience AS yearsExperience,
          c.notice_period_days AS noticePeriodDays,
          c.gender,
          c.country,
          c.current_location AS currentLocation,
          c.languages_json AS languagesJson,
          a.submitted_at AS appliedDate,
          CASE WHEN {$processingSql} THEN NULL ELSE a.rank_no END AS `rank`,
          a.application_status AS status,
          a.is_shortlisted AS isShortlisted,
          a.interview_sent_at AS interviewSentAt,
          a.hired_start_date AS hiredStartDate,
          EXISTS (
            SELECT 1
            FROM hr_action_logs hired_log
            WHERE hired_log.application_id = a.id
              AND hired_log.action_type = 'hire_candidate'
          ) AS wasHired,
          a.assigned_hr_user_id AS assignedHrUserId,
          assigned_user.full_name AS assignedHrName,
          latest_email.email_type AS lastEmailType,
          latest_email.sent_at AS lastEmailSentAt,
          email_sender.full_name AS lastEmailSentBy,
          latest_reject.action_type AS latestRejectActionType,
          reject_actor.full_name AS latestRejectActionBy,
          latest_reason.action_log_id AS latestEmailActionLogId,
          latest_reason.reason_type AS latestEmailReasonType,
          latest_reason.reason_details AS latestEmailReasonDetails,
           CASE
             WHEN a.analysis_status = 'failed' THEN 'filtered_out'
             ELSE a.eligibility_status
           END AS eligibilityStatus,
           a.analysis_status AS analysisStatus,
           a.eligibility_reasons_json AS eligibilityReasonsJson,
           CASE
             WHEN {$processingSql} THEN NULL
             WHEN a.analysis_status = 'failed' THEN 0
             ELSE a.total_score
           END AS score,
          a.ai_summary AS summary,
          (
            SELECT r1.stored_file_path
            FROM resumes r1
            WHERE r1.application_id = a.id
            ORDER BY r1.uploaded_at DESC, r1.id DESC
            LIMIT 1
          ) AS resumeUrl,
          (
            SELECT r1.original_file_name
            FROM resumes r1
            WHERE r1.application_id = a.id
            ORDER BY r1.uploaded_at DESC, r1.id DESC
            LIMIT 1
          ) AS resumeFileName,
          (
            SELECT COUNT(*) + 1
            FROM application_submission_history ash
            WHERE ash.application_id = a.id
          ) AS currentSubmissionNo,
          (
            SELECT efs.id
            FROM employment_form_submissions efs
            WHERE efs.job_id = a.job_id
              AND (
                efs.candidate_id = c.id
                OR LOWER(efs.candidate_email) = LOWER(c.email)
              )
            ORDER BY efs.candidate_submitted_at DESC, efs.id DESC
            LIMIT 1
          ) AS employmentFormSubmissionId
        FROM applications a
        JOIN candidates c ON c.id = a.candidate_id
        LEFT JOIN users assigned_user ON assigned_user.id = a.assigned_hr_user_id
        LEFT JOIN (
          SELECT el.*
          FROM email_logs el
          JOIN (
            SELECT application_id, MAX(id) AS latest_email_id
            FROM email_logs
            WHERE status = 'sent'
            GROUP BY application_id
          ) latest ON latest.latest_email_id = el.id
        ) latest_email ON latest_email.application_id = a.id
        LEFT JOIN users email_sender ON email_sender.id = latest_email.sent_by_user_id
        LEFT JOIN (
          SELECT hal.application_id, hal.user_id, hal.action_type
          FROM hr_action_logs hal
          JOIN (
            SELECT application_id, MAX(id) AS latest_action_id
            FROM hr_action_logs
            WHERE action_type IN ('reject_candidate', 'send_rejection_email')
            GROUP BY application_id
          ) latest_action ON latest_action.latest_action_id = hal.id
        ) latest_reject ON latest_reject.application_id = a.id
        LEFT JOIN users reject_actor ON reject_actor.id = latest_reject.user_id
        LEFT JOIN (
          SELECT hal.application_id, hal.id AS action_log_id, hal.reason_type, hal.reason_details
          FROM hr_action_logs hal
          JOIN (
            SELECT application_id, MAX(id) AS latest_action_id
            FROM hr_action_logs
            WHERE action_type = 'rejection_reason'
            GROUP BY application_id
          ) latest_action ON latest_action.latest_action_id = hal.id
        ) latest_reason ON latest_reason.application_id = a.id
        WHERE a.job_id = ?
        ORDER BY
          CASE WHEN {$processingSql} OR a.rank_no IS NULL THEN 999999 ELSE a.rank_no END,
          CASE WHEN {$processingSql} THEN NULL ELSE a.total_score END DESC",
        "i",
        [$jobId]
    );

    [
        $skillRows,
        $documentRows,
        $breakdownRows,
        $breakdownItemRows,
        $answerRows,
        $submissionHistoryRows,
        $jobHistoryRows,
        $resumeProfileRows,
    ] = row_sets($db, [
        "SELECT DISTINCT
           sb.application_id AS applicationId,
           sbi.requirement_text AS name
         FROM score_breakdowns sb
         JOIN score_breakdown_items sbi ON sbi.score_breakdown_id = sb.id
         JOIN applications current_application ON current_application.id = sb.application_id
         WHERE current_application.job_id = {$jobId}
           AND sbi.match_status IN ('matched', 'partial')
         ORDER BY sb.application_id, sbi.requirement_text",
        "SELECT
           resume.application_id AS applicationId,
           resume.id,
           resume.original_file_name AS fileName,
           resume.stored_file_path AS fileUrl,
           resume.file_mime_type AS mimeType,
           resume.file_size_bytes AS fileSize,
           resume.uploaded_at AS uploadedAt
         FROM resumes resume
         JOIN applications current_application ON current_application.id = resume.application_id
         WHERE current_application.job_id = {$jobId}
         ORDER BY resume.application_id, resume.uploaded_at DESC, resume.id DESC",
        "SELECT
           sb.application_id AS applicationId,
           sb.id,
           jc.criteria_name AS title,
           sb.raw_score AS criteriaScore,
           sb.semantic_score AS semanticScore,
           sb.weight,
           sb.weighted_score AS weightedScore,
           sb.explanation AS justification,
           sb.criterion_type AS criterionType,
           sb.matched_resume_evidence_json AS matchedResumeEvidenceJson,
           sb.evidence_ids_json AS evidenceIdsJson,
           sb.grounded,
           sb.qwen_status AS qwenStatus
         FROM score_breakdowns sb
         JOIN job_criteria jc ON jc.id = sb.criteria_id
         JOIN applications current_application ON current_application.id = sb.application_id
         WHERE current_application.job_id = {$jobId}
         ORDER BY sb.application_id, jc.sort_order",
        "SELECT
           item.score_breakdown_id AS scoreBreakdownId,
           item.requirement_text AS requirement,
           item.match_status AS matchStatus,
           item.evidence_text AS evidence,
           item.item_score AS itemScore
         FROM score_breakdown_items item
         JOIN score_breakdowns sb ON sb.id = item.score_breakdown_id
         JOIN applications current_application ON current_application.id = sb.application_id
         WHERE current_application.job_id = {$jobId}
         ORDER BY item.score_breakdown_id, item.id",
        "SELECT
           answer.application_id AS applicationId,
           question.id AS questionId,
           question.question_text AS question,
           question.field_type AS fieldType,
           answer.answer_text AS answer
         FROM application_question_answers answer
         JOIN job_application_questions question ON question.id = answer.question_id
         JOIN applications current_application ON current_application.id = answer.application_id
         WHERE current_application.job_id = {$jobId}
         ORDER BY answer.application_id, question.sort_order, question.id",
        "SELECT
           history.application_id AS applicationId,
           CONCAT('submission-', history.id) AS historyKey,
           history.job_id AS jobId,
           history_job.title AS jobTitle,
           history_job.department,
           history.original_submitted_at AS submittedDate,
           history.previous_score AS score,
           NULL AS `rank`,
           CONCAT(
             history.submission_no,
             CASE
               WHEN history.submission_no % 100 BETWEEN 11 AND 13 THEN 'th'
               WHEN history.submission_no % 10 = 1 THEN 'st'
               WHEN history.submission_no % 10 = 2 THEN 'nd'
               WHEN history.submission_no % 10 = 3 THEN 'rd'
               ELSE 'th'
             END,
             ' Submission'
           ) AS status
         FROM application_submission_history history
         JOIN jobs history_job ON history_job.id = history.job_id
         JOIN applications current_application ON current_application.id = history.application_id
         WHERE current_application.job_id = {$jobId}
         ORDER BY history.application_id, history.submission_no DESC, history.recorded_at DESC",
        "SELECT
            history_application.candidate_id AS candidateId,
           history_application.id AS applicationId,
           CONCAT('job-', history_application.id) AS historyKey,
           history_job.id AS jobId,
           history_job.title AS jobTitle,
           history_job.department,
           history_application.submitted_at AS submittedDate,
           history_application.total_score AS score,
           CASE
             WHEN history_application.application_status IN ('filtered_out', 'rejected') THEN NULL
             ELSE COALESCE(
               history_application.rank_no,
               (
                 SELECT COUNT(*) + 1
                 FROM applications ranked
                 WHERE ranked.job_id = history_application.job_id
                   AND ranked.application_status IN ('new', 'reviewed', 'shortlisted', 'interview')
                   AND COALESCE(ranked.total_score, 0) > COALESCE(history_application.total_score, 0)
               )
             )
           END AS `rank`,
           CASE
             WHEN history_application.is_shortlisted = 1
               AND history_application.application_status NOT IN ('interview', 'interviewed', 'hired')
             THEN 'shortlisted'
             ELSE history_application.application_status
           END AS status
         FROM applications history_application
         JOIN jobs history_job ON history_job.id = history_application.job_id
         WHERE history_application.candidate_id IN (
           SELECT candidate_id
           FROM applications
           WHERE job_id = {$jobId}
         )
            AND history_application.job_id <> {$jobId}
          ORDER BY history_application.candidate_id, history_application.submitted_at DESC",
        "SELECT
            resume.application_id AS applicationId,
            resume.id AS resumeId,
            resume.parsed_profile_json AS profileJson,
            resume.parsing_status AS parsingStatus,
            resume.parser_version AS parserVersion,
            resume.parsed_at AS parsedAt
          FROM resumes resume
          JOIN applications current_application ON current_application.id = resume.application_id
          WHERE current_application.job_id = {$jobId}
          ORDER BY resume.application_id, resume.uploaded_at DESC, resume.id DESC",
    ]);

    $decodeJson = static function (?string $value): array {
        if (!$value) {
            return [];
        }
        $decoded = json_decode($value, true);
        return is_array($decoded) ? $decoded : [];
    };

    // Editing a job used to cascade-delete score breakdown rows through the
    // criteria foreign key. Keep the persisted scoring run as a read fallback
    // so older applications can still show the score details they received.
    $scoringRunRows = [];
    if (table_exists($db, "candidate_scoring_runs")) {
        $scoringRunRows = rows(
            $db,
            "SELECT run.application_id AS applicationId, run.response_json AS responseJson
             FROM candidate_scoring_runs run
             JOIN (
               SELECT application_id, MAX(id) AS latestId
               FROM candidate_scoring_runs
               WHERE job_id = ?
               GROUP BY application_id
             ) latest ON latest.latestId = run.id
             JOIN applications current_application ON current_application.id = run.application_id
             WHERE current_application.job_id = ?",
            "ii",
            [$jobId, $jobId]
        );
    }

    $scoringRunBreakdownsByApplication = [];
    foreach ($scoringRunRows as $scoringRunRow) {
        $applicationId = (int) ($scoringRunRow["applicationId"] ?? 0);
        $response = $decodeJson($scoringRunRow["responseJson"] ?? null);
        $scoreBreakdown = $response["scoreBreakdown"] ?? [];
        if ($applicationId <= 0 || !is_array($scoreBreakdown)) {
            continue;
        }

        foreach ($scoreBreakdown as $index => $item) {
            if (!is_array($item)) {
                continue;
            }
            $rawScore = is_numeric($item["rawScore"] ?? null)
                ? max(0.0, min(10.0, (float) $item["rawScore"]))
                : 0.0;
            $evidenceIds = is_array($item["evidenceIds"] ?? null)
                ? array_values(array_filter(array_map("strval", $item["evidenceIds"]), static fn(string $value): bool => $value !== ""))
                : [];
            $criterionId = is_numeric($item["criterionId"] ?? null)
                ? (int) $item["criterionId"]
                : 0;

            $scoringRunBreakdownsByApplication[$applicationId][] = [
                "applicationId" => $applicationId,
                "id" => $criterionId > 0 ? $criterionId : "run-{$applicationId}-{$index}",
                "title" => (string) ($item["criterionName"] ?? "Criterion"),
                "criteriaScore" => $rawScore,
                "scoreOutOf10" => $rawScore,
                "weight" => (float) ($item["weight"] ?? 0),
                "weightedScore" => (float) ($item["weightedContribution"] ?? 0),
                "weightedContribution" => (float) ($item["weightedContribution"] ?? 0),
                "justification" => (string) ($item["explanation"] ?? ""),
                "criterionType" => $item["criterionType"] ?? null,
                "usedEvidenceIds" => $evidenceIds,
                "matchedResumeEvidence" => is_array($item["matchedResumeEvidence"] ?? null)
                    ? $item["matchedResumeEvidence"]
                    : [],
                "grounded" => in_array($item["grounded"] ?? false, [true, 1, "1", "true"], true),
                "matchLevel" => (string) ($item["matchLevel"] ?? candidate_match_level($rawScore, $evidenceIds !== [])),
            ];
        }
    }

    $resumeProfilesByApplication = [];
    foreach ($resumeProfileRows as $profileRow) {
        $applicationId = (int) ($profileRow["applicationId"] ?? 0);
        if ($applicationId <= 0 || isset($resumeProfilesByApplication[$applicationId])) {
            continue;
        }

        $resumeProfilesByApplication[$applicationId] = [
            "resumeId" => (int) ($profileRow["resumeId"] ?? 0),
            "parsingStatus" => (string) ($profileRow["parsingStatus"] ?? "pending"),
            "parserVersion" => $profileRow["parserVersion"] === null
                ? null
                : (string) $profileRow["parserVersion"],
            "parsedAt" => $profileRow["parsedAt"] === null
                ? null
                : (string) $profileRow["parsedAt"],
            "profile" => $decodeJson($profileRow["profileJson"] ?? null),
        ];
    }

    foreach ($documentRows as &$document) {
        $document["fileUrl"] = public_file_url((string) $document["fileUrl"]);
    }
    unset($document);
    $itemsByBreakdown = rows_grouped_by_int_key($breakdownItemRows, "scoreBreakdownId");
    foreach ($breakdownRows as &$breakdown) {
        $breakdown["items"] = $itemsByBreakdown[(int) $breakdown["id"]] ?? [];
        $usedEvidenceIds = array_values(array_filter(
            array_map(
                static fn(mixed $value): string => trim((string) $value),
                $decodeJson($breakdown["evidenceIdsJson"] ?? null)
            ),
            static fn(string $value): bool => $value !== ""
        ));
        $legacyScore = (float) ($breakdown["criteriaScore"] ?? 0);
        $semanticScore = $breakdown["semanticScore"] ?? null;
        $scoreOutOf10 = is_numeric($semanticScore)
            ? (float) $semanticScore
            : ($legacyScore > 10 ? $legacyScore / 10 : $legacyScore);
        $scoreOutOf10 = max(0.0, min(10.0, $scoreOutOf10));
        $breakdown["scoreOutOf10"] = round($scoreOutOf10, 2);
        $breakdown["weightedContribution"] = (float) ($breakdown["weightedScore"] ?? 0);
        $breakdown["usedEvidenceIds"] = $usedEvidenceIds;
        $breakdown["matchedResumeEvidence"] = $decodeJson($breakdown["matchedResumeEvidenceJson"] ?? null);
        $breakdown["grounded"] = (bool) ((int) ($breakdown["grounded"] ?? 0));
        $breakdown["matchLevel"] = candidate_match_level($scoreOutOf10, $usedEvidenceIds !== []);
        unset($breakdown["evidenceIdsJson"], $breakdown["matchedResumeEvidenceJson"], $breakdown["semanticScore"]);
    }
    unset($breakdown);

    $skillsByApplication = rows_grouped_by_int_key($skillRows, "applicationId");
    $documentsByApplication = rows_grouped_by_int_key($documentRows, "applicationId");
    $breakdownsByApplication = rows_grouped_by_int_key($breakdownRows, "applicationId");
    $answersByApplication = rows_grouped_by_int_key($answerRows, "applicationId");
    $submissionHistoryByApplication = rows_grouped_by_int_key($submissionHistoryRows, "applicationId");
    $jobHistoryByCandidate = rows_grouped_by_int_key($jobHistoryRows, "candidateId");

    foreach ($candidates as &$candidate) {
        $applicationId = (int) $candidate["applicationId"];
        $candidateId = (int) $candidate["id"];
        $isAnalysisProcessing = application_analysis_status_is_processing($candidate["analysisStatus"] ?? null);
        if (isset($candidate["resumeUrl"])) {
            $candidate["resumeUrl"] = public_file_url((string) $candidate["resumeUrl"]);
        }
        $candidate["skills"] = $skillsByApplication[$applicationId] ?? [];
        $candidate["currentSubmissionLabel"] = ordinal_submission_label((int) $candidate["currentSubmissionNo"]);
        $candidate["documents"] = $documentsByApplication[$applicationId] ?? [];
        $candidate["scoreBreakdown"] = $isAnalysisProcessing
            ? []
            : ($breakdownsByApplication[$applicationId]
                ?? ($scoringRunBreakdownsByApplication[$applicationId] ?? []));
        $candidate["questionAnswers"] = $answersByApplication[$applicationId] ?? [];
        $candidate["eligibilityReasons"] = $decodeJson($candidate["eligibilityReasonsJson"] ?? null);
        $candidate["totalScore"] = $candidate["score"] === null ? null : (float) $candidate["score"];
        $candidate["filteredOut"] = $candidate["eligibilityStatus"] === "filtered_out"
            || $candidate["status"] === "filtered_out";
        $resumeProfile = $resumeProfilesByApplication[$applicationId] ?? null;
        $candidate["parsedProfile"] = $resumeProfile !== null
            && $resumeProfile["parsingStatus"] === "parsed"
            && $resumeProfile["profile"] !== []
            ? $resumeProfile["profile"]
            : null;
        $candidate["resumeParsingStatus"] = $resumeProfile["parsingStatus"] ?? null;
        $candidate["parserVersion"] = $resumeProfile["parserVersion"] ?? null;
        $candidate["parsedAt"] = $resumeProfile["parsedAt"] ?? null;
        unset($candidate["eligibilityReasonsJson"]);
        $submissionHistory = $submissionHistoryByApplication[$applicationId] ?? [];
        $otherJobHistory = array_values(array_filter(
            $jobHistoryByCandidate[$candidateId] ?? [],
            static fn(array $history): bool => (int) $history["applicationId"] !== $applicationId
        ));
        foreach ($otherJobHistory as &$history) {
            unset($history["applicationId"]);
        }
        unset($history);
        $candidate["jobHistory"] = array_merge($submissionHistory, $otherJobHistory);
    }
    unset($candidate);

    respond(["job" => $job, "candidates" => $candidates]);
}

function candidate_breakdown(mysqli $db, int $applicationId): array
{
    $breakdowns = rows(
        $db,
        "SELECT sb.id, jc.criteria_name AS title, sb.raw_score AS criteriaScore, sb.semantic_score AS semanticScore, sb.weight, sb.weighted_score AS weightedScore, sb.explanation AS justification
         FROM score_breakdowns sb
         JOIN job_criteria jc ON jc.id = sb.criteria_id
         WHERE sb.application_id = ?
         ORDER BY jc.sort_order",
        "i",
        [$applicationId]
    );

    foreach ($breakdowns as &$breakdown) {
        $legacyScore = (float) ($breakdown["criteriaScore"] ?? 0);
        $semanticScore = $breakdown["semanticScore"] ?? null;
        $scoreOutOf10 = is_numeric($semanticScore)
            ? (float) $semanticScore
            : ($legacyScore > 10 ? $legacyScore / 10 : $legacyScore);
        $scoreOutOf10 = max(0.0, min(10.0, $scoreOutOf10));
        $breakdown["scoreOutOf10"] = round($scoreOutOf10, 2);
        $breakdown["items"] = rows(
            $db,
            "SELECT requirement_text AS requirement, match_status AS matchStatus, evidence_text AS evidence, item_score AS itemScore
             FROM score_breakdown_items
             WHERE score_breakdown_id = ?
             ORDER BY id",
            "i",
            [(int) $breakdown["id"]]
        );
        $breakdown["matchLevel"] = candidate_match_level($scoreOutOf10, $breakdown["items"] !== []);
        unset($breakdown["semanticScore"]);
    }

    return $breakdowns;
}

function normalized_positive_int_ids(array $ids): array
{
    return array_values(array_unique(array_filter(
        array_map("intval", $ids),
        static fn(int $id): bool => $id > 0
    )));
}

function rows_grouped_by_int_key(array $items, string $key, bool $removeKey = true): array
{
    $grouped = [];
    foreach ($items as $item) {
        $id = (int) ($item[$key] ?? 0);
        if ($id <= 0) {
            continue;
        }
        if ($removeKey) {
            unset($item[$key]);
        }
        $grouped[$id][] = $item;
    }
    return $grouped;
}

function application_documents(mysqli $db, int $applicationId): array
{
    $groupedDocuments = application_documents_by_application($db, [$applicationId]);
    return $groupedDocuments[$applicationId] ?? [];
}

function application_documents_by_application(mysqli $db, array $applicationIds): array
{
    $applicationIds = normalized_positive_int_ids($applicationIds);
    if ($applicationIds === []) {
        return [];
    }

    // Load all documents in one query to avoid one remote query per application.
    $placeholders = implode(",", array_fill(0, count($applicationIds), "?"));
    $documents = rows(
        $db,
        "SELECT
           application_id AS applicationId,
           id,
           original_file_name AS fileName,
           stored_file_path AS fileUrl,
           file_mime_type AS mimeType,
           file_size_bytes AS fileSize,
           uploaded_at AS uploadedAt
         FROM resumes
         WHERE application_id IN ({$placeholders})
         ORDER BY application_id, uploaded_at DESC, id DESC",
        str_repeat("i", count($applicationIds)),
        $applicationIds
    );

    $groupedDocuments = [];
    foreach ($documents as $document) {
        $applicationId = (int) $document["applicationId"];
        unset($document["applicationId"]);
        $document["fileUrl"] = public_file_url((string) $document["fileUrl"]);
        $groupedDocuments[$applicationId][] = $document;
    }

    return $groupedDocuments;
}

function update_application(mysqli $db, int $applicationId): void
{
    /**
     * Apply one HR workflow transition and write its audit/notification side
     effects while keeping final hiring decisions under human control.
     */
    ensure_candidate_portal_schema($db);
    $data = input_json();
    $status = (string) ($data["status"] ?? "");
    $actionUserId = (int) ($data["actionUserId"] ?? 0);
    $interviewDateTime = trim((string) ($data["interviewDateTime"] ?? ""));
    $emailAction = filter_var($data["emailAction"] ?? false, FILTER_VALIDATE_BOOLEAN);
    $reasonType = trim((string) ($data["reasonType"] ?? ""));
    $reasonDetails = trim((string) ($data["reasonDetails"] ?? ""));
    $hiredStartDate = isset($data["hiredStartDate"]) ? trim((string) $data["hiredStartDate"]) : null;
    if ($hiredStartDate === "") {
        $hiredStartDate = null;
    }
    $allowed = ["new", "reviewed", "shortlisted", "interview", "interviewed", "hired", "rejected", "filtered_out", "withdrawn"];

    if (!in_array($status, $allowed, true)) {
        respond(["error" => "Invalid application status"], 422);
    }

    $before = row(
        $db,
        "SELECT application_status, is_shortlisted, interview_sent_at, hired_start_date FROM applications WHERE id = ?",
        "i",
        [$applicationId]
    );

    if ($status === "shortlisted") {
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), is_shortlisted = 1, application_status = IF(application_status IN ('interview', 'interviewed', 'hired'), application_status, 'shortlisted'), reviewed_at = NOW() WHERE id = ?", "ii", [$actionUserId, $applicationId]);
    } elseif ($status === "reviewed") {
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), is_shortlisted = 0, application_status = IF(application_status IN ('interview', 'interviewed', 'hired'), application_status, 'reviewed'), reviewed_at = NOW() WHERE id = ?", "ii", [$actionUserId, $applicationId]);
    } elseif ($status === "interview") {
        if ($emailAction) {
            try {
                create_email_sent_notification($db, $applicationId, $actionUserId, "interview", $interviewDateTime);
            } catch (Throwable $error) {
                respond([
                    "error" => "Unable to send interview email",
                    "detail" => $error->getMessage(),
                ], 502);
            }
        }
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), is_shortlisted = 1, interview_sent_at = COALESCE(interview_sent_at, NOW()), application_status = 'interview', reviewed_at = NOW() WHERE id = ?", "ii", [$actionUserId, $applicationId]);
    } elseif ($status === "interviewed") {
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), application_status = 'interviewed', reviewed_at = NOW() WHERE id = ?", "ii", [$actionUserId, $applicationId]);
    } elseif ($status === "hired") {
        if ($hiredStartDate !== null && !preg_match('/^\d{4}-\d{2}-\d{2}$/', $hiredStartDate)) {
            respond(["error" => "Invalid start date"], 422);
        }
        if ($hiredStartDate !== null && $hiredStartDate < date("Y-m-d")) {
            respond(["error" => "Start date cannot be in the past"], 422);
        }
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), is_shortlisted = 1, application_status = 'hired', hired_start_date = ?, reviewed_at = NOW() WHERE id = ?", "isi", [$actionUserId, $hiredStartDate, $applicationId]);
    } elseif ($status === "rejected") {
        if ($emailAction) {
            try {
                create_email_sent_notification($db, $applicationId, $actionUserId, "reject", "");
            } catch (Throwable $error) {
                respond([
                    "error" => "Unable to send rejection email",
                    "detail" => $error->getMessage(),
                ], 502);
            }
        }
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), application_status = 'rejected', is_shortlisted = 0, reviewed_at = NOW() WHERE id = ?", "ii", [$actionUserId, $applicationId]);
    } else {
        exec_stmt($db, "UPDATE applications SET assigned_hr_user_id = COALESCE(assigned_hr_user_id, (SELECT id FROM users WHERE id = NULLIF(?, 0) LIMIT 1)), application_status = ?, reviewed_at = NOW() WHERE id = ?", "isi", [$actionUserId, $status, $applicationId]);
    }

    $updated = row($db, "SELECT application_status, is_shortlisted, interview_sent_at, hired_start_date, assigned_hr_user_id FROM applications WHERE id = ?", "i", [$applicationId]);
    $isHiredDateOnlyUpdate =
        $status === "hired" &&
        (string) ($before["application_status"] ?? "") === "hired";
    if ($isHiredDateOnlyUpdate) {
        $beforeStartDate = $before["hired_start_date"] ?? null;
        $afterStartDate = $updated["hired_start_date"] ?? null;
        if ((string) $beforeStartDate !== (string) $afterStartDate) {
            log_hired_start_date_action($db, $applicationId, $actionUserId, $before ?: [], $updated ?: []);
        }
    } else {
        log_application_action($db, $applicationId, $actionUserId, $status, $emailAction, $interviewDateTime, $before ?: [], $updated ?: []);
    }
    if ($status === "rejected" && ($reasonType !== "" || $reasonDetails !== "")) {
        log_rejection_reason_action($db, $applicationId, $actionUserId, $reasonType, $reasonDetails, false);
    }
    respond(["ok" => true, "application" => $updated ?: []]);
}

function log_hired_start_date_action(
    mysqli $db,
    int $applicationId,
    int $userId,
    array $before,
    array $after
): void {
    if ($userId <= 0) {
        return;
    }

    $application = row(
        $db,
        "SELECT a.job_id AS jobId, a.candidate_id AS candidateId
         FROM applications a
         WHERE a.id = ?",
        "i",
        [$applicationId]
    );

    if (!$application) {
        return;
    }

    ensure_hr_action_log_reason_columns($db);
    exec_stmt(
        $db,
        "INSERT INTO hr_action_logs (user_id, application_id, job_id, candidate_id, action_type, action_label, reason_type, reason_details)
         VALUES (?, ?, ?, ?, 'update_hired_start_date', 'Updated Start Date', ?, ?)",
        "iiiiss",
        [
            $userId,
            $applicationId,
            (int) $application["jobId"],
            (int) $application["candidateId"],
            null,
            json_encode(["before" => $before, "after" => $after]),
        ]
    );
}

function log_application_action(
    mysqli $db,
    int $applicationId,
    int $userId,
    string $status,
    bool $emailAction,
    string $interviewDateTime,
    array $before,
    array $after
): void {
    if ($userId <= 0) {
        return;
    }

    $application = row(
        $db,
        "SELECT a.job_id AS jobId, a.candidate_id AS candidateId, j.title AS jobTitle, c.full_name AS candidateName
         FROM applications a
         JOIN jobs j ON j.id = a.job_id
         JOIN candidates c ON c.id = a.candidate_id
         WHERE a.id = ?",
        "i",
        [$applicationId]
    );

    if (!$application) {
        return;
    }

    $actionType = "status_update";
    $actionLabel = "Updated Application Status";

    if ($status === "reviewed") {
        $actionType = "review_candidate";
        $actionLabel = "Reviewed Candidate";
    } elseif ($status === "shortlisted") {
        $actionType = "shortlist_candidate";
        $actionLabel = "Shortlisted Candidate";
    } elseif ($status === "interview") {
        $actionType = "send_interview_email";
        $actionLabel = "Sent Interview Email";
    } elseif ($status === "interviewed") {
        $actionType = "mark_interviewed";
        $actionLabel = "Marked Interview Completed";
    } elseif ($status === "hired") {
        $actionType = "hire_candidate";
        $actionLabel = "Hired Candidate";
    } elseif ($status === "rejected") {
        $actionType = $emailAction ? "send_rejection_email" : "reject_candidate";
        $actionLabel = $emailAction ? "Rejection Email Sent" : "Rejected";
    } elseif ($status === "filtered_out") {
        $actionType = "filter_out_candidate";
        $actionLabel = "Filtered Out Candidate";
    }

    ensure_hr_action_log_reason_columns($db);
    exec_stmt(
        $db,
        "INSERT INTO hr_action_logs (user_id, application_id, job_id, candidate_id, action_type, action_label, reason_type, reason_details)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        "iiiissss",
        [
            $userId,
            $applicationId,
            (int) $application["jobId"],
            (int) $application["candidateId"],
            $actionType,
            $actionLabel,
            null,
            null,
        ]
    );
}

function log_rejection_reason_action(
    mysqli $db,
    int $applicationId,
    int $userId,
    string $reasonType,
    string $reasonDetails,
    bool $isUpdate
): void {
    if ($userId <= 0) {
        return;
    }

    $application = row(
        $db,
        "SELECT job_id AS jobId, candidate_id AS candidateId
         FROM applications
         WHERE id = ?
         LIMIT 1",
        "i",
        [$applicationId]
    );

    if (!$application) {
        return;
    }

    ensure_hr_action_log_reason_columns($db);
    exec_stmt(
        $db,
        "INSERT INTO hr_action_logs (user_id, application_id, job_id, candidate_id, action_type, action_label, reason_type, reason_details)
         VALUES (?, ?, ?, ?, 'rejection_reason', ?, NULLIF(?, ''), NULLIF(?, ''))",
        "iiiisss",
        [
            $userId,
            $applicationId,
            (int) $application["jobId"],
            (int) $application["candidateId"],
            $isUpdate ? "Updated Rejection Reason" : "Added Rejection Reason",
            $reasonType,
            $reasonDetails,
        ]
    );
}

function update_application_action_reason(mysqli $db, int $applicationId): void
{
    $data = input_json();
    $actionUserId = (int) ($data["actionUserId"] ?? 0);
    $reasonType = trim((string) ($data["reasonType"] ?? ""));
    $reasonDetails = trim((string) ($data["reasonDetails"] ?? ""));

    if ($actionUserId <= 0) {
        respond(["error" => "Action user is required"], 422);
    }

    ensure_hr_action_log_reason_columns($db);
    $existingReason = row(
        $db,
        "SELECT id
         FROM hr_action_logs
         WHERE application_id = ?
           AND action_type = 'rejection_reason'
         ORDER BY created_at DESC, id DESC
         LIMIT 1",
        "i",
        [$applicationId]
    );

    log_rejection_reason_action($db, $applicationId, $actionUserId, $reasonType, $reasonDetails, $existingReason !== null);

    respond(["ok" => true]);
}

// Public application form and submission actions.
function apply_job(mysqli $db, string $jobCode): void
{
    $job = row(
        $db,
        "SELECT j.id, j.job_code AS jobCode, j.title, j.department, j.location, j.salary_range AS salaryRange, " . candidate_public_job_type_sql() . " AS employmentType
         FROM jobs j
         JOIN application_links al ON al.job_id = j.id
         WHERE j.job_code = ? AND j.status = 'active' AND al.status = 'active'
         LIMIT 1",
        "s",
        [$jobCode]
    );

    if (!$job) {
        respond(["error" => "Application link not found or inactive"], 404);
    }

    $job["applicationQuestions"] = application_questions_payload($db, (int) $job["id"]);
    respond(["job" => $job]);
}

function submit_application(mysqli $db, string $jobCode): void
{
    /**
     * Persist candidate, application, answers, resume, and notifications before
     * queueing any parser/scorer call. AI failure therefore cannot erase a
     * submitted application and retries can reuse its stable identifiers.
     */
    ensure_candidate_portal_schema($db);
    ensure_job_creation_schema($db);
    $data = input_data();
    $job = row($db, "SELECT id, title FROM jobs WHERE job_code = ? AND status = 'active'", "s", [$jobCode]);
    if (!$job) {
        respond(["error" => "Job is not open"], 404);
    }
    $questionAnswers = validate_application_question_answers(
        $db,
        (int) $job["id"],
        $data["questionAnswers"] ?? "[]"
    );

    $fullName = trim((string) ($data["fullName"] ?? ""));
    $email = trim((string) ($data["email"] ?? ""));
    $phone = trim((string) ($data["phone"] ?? ""));
    $gender = trim((string) ($data["gender"] ?? ""));
    $country = trim((string) ($data["country"] ?? ""));
    $currentLocation = trim((string) ($data["currentLocation"] ?? ""));
    $languagesJson = normalize_candidate_languages_json(trim((string) ($data["languages"] ?? "")));
    $cgpa = (float) ($data["cgpa"] ?? 0);
    $hasNoticePeriod = array_key_exists("noticePeriodDays", $data)
        && trim((string) $data["noticePeriodDays"]) !== "";
    $noticePeriodDays = notice_period_days_from_input($data["noticePeriodDays"] ?? 0);
    $applicationLanguages = json_decode($languagesJson, true);
    $applicationData = [
        "name" => $fullName,
        "email" => $email,
        "phone" => $phone,
        "location" => $currentLocation,
        "cgpa" => $cgpa > 0 ? $cgpa : null,
        "noticePeriod" => !$hasNoticePeriod
            ? null
            : ($noticePeriodDays === 0 ? "Immediate" : "{$noticePeriodDays} days"),
        "languages" => is_array($applicationLanguages) ? $applicationLanguages : [],
    ];

    if ($fullName === "" || $email === "" || $phone === "") {
        respond(["error" => "Full name, email, and phone are required"], 422);
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Please enter a valid email"], 422);
    }
    if (!is_valid_malaysian_phone($phone)) {
        respond(["error" => "Please enter a valid Malaysian phone number"], 422);
    }

    if (!isset($_FILES["resume"])) {
        respond(["error" => "A PDF resume file is required"], 422);
    }

    $candidateSession = optional_candidate_session($db);
    if ($candidateSession && strtolower($email) !== strtolower((string) $candidateSession["email"])) {
        respond(["error" => "Logged-in candidates can only apply using their own account email"], 403);
    }

    $candidate = row($db, "SELECT id, education FROM candidates WHERE email = ?", "s", [$email]);
    $existing = $candidate
        ? row($db, "SELECT id FROM applications WHERE job_id = ? AND candidate_id = ?", "ii", [(int) $job["id"], (int) $candidate["id"]])
        : null;

    if ($existing) {
        $replaceExisting = filter_var($data["replaceExisting"] ?? false, FILTER_VALIDATE_BOOLEAN);
        if (!$replaceExisting) {
            respond([
                "error" => "This email has already applied for this job.",
                "duplicate" => true,
                "applicationId" => (int) $existing["id"],
            ], 409);
        }

        exec_stmt(
            $db,
            "INSERT INTO candidates (full_name, email, phone, gender, country, current_location, languages_json, current_cgpa, years_experience, notice_period_days)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
             ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), phone = VALUES(phone), gender = VALUES(gender), country = VALUES(country), current_location = VALUES(current_location), languages_json = VALUES(languages_json), current_cgpa = VALUES(current_cgpa), notice_period_days = VALUES(notice_period_days)",
            "sssssssdi",
            [$fullName, $email, $phone, $gender, $country, $currentLocation, $languagesJson, $cgpa, $noticePeriodDays]
        );

        $replacement = replace_existing_application(
            $db,
            (int) $existing["id"],
            (int) $candidate["id"],
            (int) $job["id"],
            $fullName,
            (string) ($data["resumeFileName"] ?? "resume.pdf"),
            $questionAnswers,
            $applicationData
        );
        try {
            send_application_confirmation_email(
                $db,
                $email,
                $fullName,
                (string) ($job["title"] ?? "the selected position")
            );
        } catch (Throwable $error) {
            // The replacement is already persisted. Do not turn a successful
            // application update into a failure when SMTP is temporarily unavailable.
            error_log("Application confirmation email failed for application {$existing["id"]}: " . $error->getMessage());
        }
        respond(array_merge(
            ["ok" => true, "applicationId" => (int) $existing["id"], "replaced" => true],
            application_analysis_response($replacement["analysis"])
        ), 200);
    }

    exec_stmt(
        $db,
        "INSERT INTO candidates (full_name, email, phone, gender, country, current_location, languages_json, current_cgpa, years_experience, notice_period_days)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
         ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), phone = VALUES(phone), gender = VALUES(gender), country = VALUES(country), current_location = VALUES(current_location), languages_json = VALUES(languages_json), current_cgpa = VALUES(current_cgpa), notice_period_days = VALUES(notice_period_days)",
        "sssssssdi",
        [$fullName, $email, $phone, $gender, $country, $currentLocation, $languagesJson, $cgpa, $noticePeriodDays]
    );

    $candidate = row($db, "SELECT id FROM candidates WHERE email = ?", "s", [$email]);
    if ($candidateSession && (int) $candidate["id"] !== (int) $candidateSession["candidateId"]) {
        respond(["error" => "Application email does not match the signed-in candidate"], 403);
    }

    exec_stmt(
        $db,
        "INSERT INTO applications (
           job_id, candidate_id, application_link_id, application_status,
           eligibility_status, analysis_status, total_score, ai_summary, scoring_diagnostics_json
         ) VALUES (?, ?, (SELECT id FROM application_links WHERE job_id = ?), 'new', 'pending', 'pending', NULL, NULL, ?)",
        "iiis",
        [
            (int) $job["id"],
            (int) $candidate["id"],
            (int) $job["id"],
            application_analysis_initial_diagnostics_json(),
        ]
    );

    $applicationId = $db->insert_id;
    save_application_question_answers($db, (int) $applicationId, $questionAnswers);
    $storedResumes = save_uploaded_documents(
        $db,
        $applicationId,
        (string) ($data["resumeFileName"] ?? "resume.pdf"),
        (int) $candidate["id"],
        $applicationData
    );
    create_application_notifications($db, $applicationId, $fullName, (int) $job["id"], false);
    try {
        send_application_confirmation_email(
            $db,
            $email,
            $fullName,
            (string) ($job["title"] ?? "the selected position")
        );
    } catch (Throwable $error) {
        // Application persistence has succeeded even if the confirmation email fails.
        error_log("Application confirmation email failed for application {$applicationId}: " . $error->getMessage());
    }
    try {
        queue_application_analysis($db, $applicationId, "all", "submission");
    } catch (Throwable $error) {
        // The persistence boundary has already succeeded. Leave the durable
        // pending marker for the worker's recovery scan and do not fail the
        // candidate submission because the queue marker could not be updated.
        error_log("Application analysis queue marker failed for application {$applicationId}: " . $error->getMessage());
    }
    $analysis = application_analysis_pending_result(
        array_values(array_map(
            static fn(array $resume): int => (int) ($resume["resumeId"] ?? 0),
            $storedResumes
        )),
        (int) $candidate["id"]
    );
    respond(array_merge(
        ["ok" => true, "applicationId" => $applicationId],
        application_analysis_response($analysis)
    ), 201);
}

function send_application_confirmation_email(mysqli $db, string $toEmail, string $toName, string $jobTitle): void
{
    ensure_email_template_schema($db);
    $config = mail_config();
    $fromEmail = (string) (
        $config["sendgrid_from_email"]
        ?? $config["resend_from_email"]
        ?? $config["from_email"]
        ?? $config["username"]
        ?? ""
    );
    $fromName = (string) (
        $config["sendgrid_from_name"]
        ?? $config["resend_from_name"]
        ?? $config["from_name"]
        ?? "UWC Recruitment"
    );
    $template = row(
        $db,
        "SELECT id, subject, body, is_active AS isActive,
                attachment_path AS attachmentPath,
                attachment_file_name AS attachmentFileName,
                logo_attachment_path AS logoAttachmentPath,
                logo_attachment_file_name AS logoAttachmentFileName
         FROM email_templates
         WHERE template_key = 'application_confirmation'
         LIMIT 1"
    );

    if ($template && !filter_var($template["isActive"] ?? true, FILTER_VALIDATE_BOOLEAN)) {
        return;
    }

    $subject = (string) ($template["subject"] ?? "Application received for {jobTitle}");
    $body = (string) ($template["body"] ?? (
        "Dear {candidateName},\n\n"
        . "Thank you for applying for the {jobTitle} position at {companyName}.\n\n"
        . "We have received your application successfully. Our HR team will review your application and contact you if you are shortlisted.\n\n"
        . "Please keep this email for your records.\n\n"
        . "Regards,\n"
        . "{companyName}"
    ));
    $replacements = [
        "{{candidate_name}}" => $toName,
        "{{job_title}}" => $jobTitle,
        "{candidateName}" => $toName,
        "{jobTitle}" => $jobTitle,
        "{companyName}" => $fromName,
    ];
    $subject = strtr($subject, $replacements);
    $body = str_replace("\\n", "\n", strtr($body, $replacements));

    send_recruitment_email(
        $toEmail,
        $toName,
        $subject,
        $body,
        $fromEmail,
        $fromName,
        resolve_attachment_path((string) ($template["attachmentPath"] ?? "")),
        (string) ($template["attachmentFileName"] ?? ""),
        resolve_attachment_path((string) ($template["logoAttachmentPath"] ?? "")),
        (string) ($template["logoAttachmentFileName"] ?? "")
    );
}

function candidate_match_level(float $score, bool $hasEvidence): string
{
    if (!$hasEvidence || $score <= 0) {
        return "none";
    }
    if ($score < 5) {
        return "weak";
    }
    if ($score < 7) {
        return "partial";
    }
    if ($score < 9) {
        return "matched";
    }
    return "strong_match";
}

function replace_existing_application(
    mysqli $db,
    int $applicationId,
    int $candidateId,
    int $jobId,
    string $fullName,
    string $fallbackResumeName,
    array $questionAnswers,
    array $applicationData = []
): array {
    /**
     * Record the previous submission, replace its derived files/data in a
     * transaction, and queue analysis against the same application ID.
     */
    $existing = row(
        $db,
        "SELECT
           a.application_status,
           a.eligibility_status,
           a.total_score,
           a.rank_no,
           a.assigned_hr_user_id,
           a.ai_summary,
           a.submitted_at,
           r.original_file_name AS resumeFileName,
           r.stored_file_path AS resumeUrl
         FROM applications a
         LEFT JOIN resumes r ON r.application_id = a.id
         WHERE a.id = ?",
        "i",
        [$applicationId]
    );
    if (!$existing) {
        respond(["error" => "Existing application not found"], 404);
    }

    $historyCount = row($db, "SELECT COUNT(*) AS total FROM application_submission_history WHERE application_id = ?", "i", [$applicationId]);
    $submissionNo = (int) ($historyCount["total"] ?? 0) + 1;
    $initialAnalysisDiagnostics = application_analysis_initial_diagnostics_json();

    $db->begin_transaction();
    try {
        exec_stmt(
            $db,
            "INSERT INTO application_submission_history (
               candidate_id, application_id, job_id, submission_no,
               previous_application_status, previous_eligibility_status,
               previous_score, previous_rank_no, previous_assigned_hr_user_id, previous_resume_file_name,
               previous_resume_url, previous_ai_summary, original_submitted_at
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "iiiissdiissss",
            [
                $candidateId,
                $applicationId,
                $jobId,
                $submissionNo,
                (string) $existing["application_status"],
                (string) $existing["eligibility_status"],
                $existing["total_score"] === null ? null : (float) $existing["total_score"],
                $existing["rank_no"] === null ? null : (int) $existing["rank_no"],
                $existing["assigned_hr_user_id"] === null ? null : (int) $existing["assigned_hr_user_id"],
                (string) ($existing["resumeFileName"] ?? ""),
                (string) ($existing["resumeUrl"] ?? ""),
                (string) ($existing["ai_summary"] ?? ""),
                (string) ($existing["submitted_at"] ?? ""),
            ]
        );

        exec_stmt(
            $db,
            "UPDATE applications
             SET application_status = 'new', is_shortlisted = 0, interview_sent_at = NULL,
                 assigned_hr_user_id = NULL, eligibility_status = 'pending',
                 analysis_status = 'pending', total_score = NULL, rank_no = NULL,
                 ai_summary = NULL, scoring_diagnostics_json = ?,
                 eligibility_reasons_json = NULL, criteria_snapshot_json = NULL,
                 scored_at = NULL, submitted_at = NOW(), reviewed_at = NULL
             WHERE id = ?",
            "si",
            [$initialAnalysisDiagnostics, $applicationId]
        );

        exec_stmt(
            $db,
            "DELETE FROM resumes WHERE application_id = ?",
            "i",
            [$applicationId]
        );
        exec_stmt(
            $db,
            "DELETE FROM application_documents WHERE application_id = ?",
            "i",
            [$applicationId]
        );
        $storedResumes = save_uploaded_documents(
            $db,
            $applicationId,
            $fallbackResumeName,
            $candidateId,
            $applicationData
        );
        save_application_question_answers($db, $applicationId, $questionAnswers);

        exec_stmt(
            $db,
            "DELETE FROM score_breakdowns WHERE application_id = ?",
            "i",
            [$applicationId]
        );
        create_application_notifications($db, $applicationId, $fullName, $jobId, true);

        $db->commit();
    } catch (Throwable $error) {
        $db->rollback();
        throw $error;
    }

    try {
        queue_application_analysis($db, $applicationId, "all", "replacement");
    } catch (Throwable $error) {
        error_log("Application analysis replacement queue marker failed for application {$applicationId}: " . $error->getMessage());
    }
    $analysis = application_analysis_pending_result(
        array_values(array_map(
            static fn(array $resume): int => (int) ($resume["resumeId"] ?? 0),
            $storedResumes
        )),
        $candidateId
    );
    return [
        "analysis" => $analysis,
        "storedResumes" => $storedResumes,
    ];
}

function validate_application_question_answers(mysqli $db, int $jobId, mixed $rawAnswers): array
{
    $answers = is_string($rawAnswers) ? json_decode($rawAnswers, true) : $rawAnswers;
    $answers = is_array($answers) ? $answers : [];
    $submitted = [];
    foreach ($answers as $answer) {
        if (!is_array($answer)) {
            continue;
        }
        $questionId = (int) ($answer["questionId"] ?? 0);
        if ($questionId > 0) {
            $submitted[$questionId] = trim((string) ($answer["answer"] ?? ""));
        }
    }

    $questions = application_questions_payload($db, $jobId);
    $validated = [];
    foreach ($questions as $question) {
        $questionId = (int) $question["id"];
        $value = $submitted[$questionId] ?? "";
        if ((bool) $question["required"] && $value === "") {
            respond(["error" => (string) $question["question"] . " is required"], 422);
        }
        if ($value === "") {
            continue;
        }
        if ($question["fieldType"] === "number" && !is_numeric($value)) {
            respond(["error" => (string) $question["question"] . " must be a number"], 422);
        }
        if ($question["fieldType"] === "dropdown" && !in_array($value, $question["options"], true)) {
            respond(["error" => "Invalid answer for " . (string) $question["question"]], 422);
        }
        $validated[$questionId] = $value;
    }
    return $validated;
}

function save_application_question_answers(mysqli $db, int $applicationId, array $answers): void
{
    exec_stmt($db, "DELETE FROM application_question_answers WHERE application_id = ?", "i", [$applicationId]);
    foreach ($answers as $questionId => $answer) {
        exec_stmt(
            $db,
            "INSERT INTO application_question_answers (application_id, question_id, answer_text) VALUES (?, ?, ?)",
            "iis",
            [$applicationId, (int) $questionId, (string) $answer]
        );
    }
}

function create_score_breakdown(mysqli $db, int $applicationId, int $jobId, float $score): void
{
    $criteria = rows(
        $db,
        "SELECT id, criteria_name, weight, sort_order FROM job_criteria WHERE job_id = ? AND is_active = 1 ORDER BY sort_order",
        "i",
        [$jobId]
    );

    foreach ($criteria as $criterion) {
        $rawScore = max(0, min(10, $score));
        $weight = (float) $criterion["weight"];
        $weightedScore = round(($rawScore / 10) * $weight, 2);
        $criteriaName = (string) $criterion["criteria_name"];

        exec_stmt(
            $db,
            "INSERT INTO score_breakdowns (application_id, criteria_id, raw_score, weight, weighted_score, explanation)
             VALUES (?, ?, ?, ?, ?, ?)
             ON DUPLICATE KEY UPDATE
               raw_score = VALUES(raw_score),
               weight = VALUES(weight),
               weighted_score = VALUES(weighted_score),
               explanation = VALUES(explanation)",
            "iiddds",
            [
                $applicationId,
                (int) $criterion["id"],
                $rawScore,
                $weight,
                $weightedScore,
                "$criteriaName evaluated from submitted resume information and job requirements.",
            ]
        );

        $breakdown = row(
            $db,
            "SELECT id FROM score_breakdowns WHERE application_id = ? AND criteria_id = ?",
            "ii",
            [$applicationId, (int) $criterion["id"]]
        );
        if ($breakdown) {
            exec_stmt(
                $db,
                "INSERT INTO score_breakdown_items (score_breakdown_id, requirement_text, match_status, evidence_text, item_score)
                 VALUES (?, ?, ?, ?, ?)
                 ON DUPLICATE KEY UPDATE
                   match_status = VALUES(match_status),
                   evidence_text = VALUES(evidence_text),
                   item_score = VALUES(item_score)",
                "isssd",
                [
                    (int) $breakdown["id"],
                    $criteriaName,
                    $rawScore >= 7 ? "matched" : ($rawScore >= 5 ? "partial" : "missing"),
                    "The resume was submitted through the application form and is ready for HR review.",
                    $rawScore,
                ]
            );
        }
    }
}

function table_column_exists(mysqli $db, string $table, string $column): bool
{
    $existing = row(
        $db,
        "SELECT COLUMN_NAME
         FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = ?
           AND COLUMN_NAME = ?
         LIMIT 1",
        "ss",
        [$table, $column]
    );

    return $existing !== null;
}

function table_exists(mysqli $db, string $table): bool
{
    $existing = row(
        $db,
        "SELECT TABLE_NAME
         FROM INFORMATION_SCHEMA.TABLES
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = ?
         LIMIT 1",
        "s",
        [$table]
    );

    return $existing !== null;
}

function ensure_hr_action_log_reason_columns(mysqli $db): void
{
    if (!table_column_exists($db, "hr_action_logs", "job_title")) {
        exec_stmt($db, "ALTER TABLE hr_action_logs ADD COLUMN job_title VARCHAR(255) NULL AFTER action_label");
    }

    if (!table_column_exists($db, "hr_action_logs", "reason_type")) {
        exec_stmt($db, "ALTER TABLE hr_action_logs ADD COLUMN reason_type VARCHAR(120) NULL AFTER action_label");
    }

    if (!table_column_exists($db, "hr_action_logs", "reason_details")) {
        exec_stmt($db, "ALTER TABLE hr_action_logs ADD COLUMN reason_details TEXT NULL AFTER reason_type");
    }

    if (table_column_exists($db, "hr_action_logs", "details")) {
        exec_stmt($db, "ALTER TABLE hr_action_logs DROP COLUMN details");
    }
}

// Notification records created by application actions.
function cleanup_old_notifications(mysqli $db): void
{
    exec_stmt($db, "DELETE FROM notifications WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)");
}

function create_application_notifications(mysqli $db, int $applicationId, string $candidateName, int $jobId, bool $isResubmission): void
{
    cleanup_old_notifications($db);

    $job = row($db, "SELECT title FROM jobs WHERE id = ?", "i", [$jobId]);
    $jobTitle = (string) ($job["title"] ?? "Job");
    $title = "New Application for $jobTitle";
    $message = $isResubmission
        ? "A candidate has resubmitted an application."
        : "A new candidate has submitted an application.";

    $recipients = rows($db, "SELECT id FROM users WHERE status = 'active'");
    foreach ($recipients as $user) {
        exec_stmt(
            $db,
            "INSERT INTO notifications (user_id, related_application_id, notification_type, title, message)
             VALUES (?, ?, 'new_application', ?, ?)",
            "iiss",
            [(int) $user["id"], $applicationId, $title, $message]
        );
    }
}

function create_email_sent_notification(mysqli $db, int $applicationId, int $userId, string $emailType, string $interviewDateTime): void
{
    ensure_email_template_schema($db);
    if ($userId <= 0 || !in_array($emailType, ["interview", "reject"], true)) {
        throw new RuntimeException("Valid HR user is required to send email");
    }

    cleanup_old_notifications($db);

    $application = row(
        $db,
        "SELECT c.full_name AS candidateName, c.email AS candidateEmail, j.title AS jobTitle, u.full_name AS senderName, u.email AS senderEmail
         FROM applications a
         JOIN candidates c ON c.id = a.candidate_id
         JOIN jobs j ON j.id = a.job_id
         JOIN users u ON u.id = ?
         WHERE a.id = ?",
        "ii",
        [$userId, $applicationId]
    );
    if (!$application) {
        throw new RuntimeException("Application or sender not found");
    }

    $templateKey = $emailType === "interview" ? "interview_invitation" : "reject_application";
    $template = row($db, "SELECT id, subject, body, attachment_path AS attachmentPath, attachment_file_name AS attachmentFileName, logo_attachment_path AS logoAttachmentPath, logo_attachment_file_name AS logoAttachmentFileName FROM email_templates WHERE template_key = ? AND is_active = 1 LIMIT 1", "s", [$templateKey]);
    $title = $emailType === "interview" ? "Interview Email Sent" : "Rejection Email Sent";
    $message = $emailType === "interview"
        ? "The interview email has been sent successfully."
        : "The rejection email has been sent successfully.";
    $subject = (string) ($template["subject"] ?? $title);
    $body = (string) ($template["body"] ?? $message);
    $scheduledAt = $emailType === "interview"
        ? normalize_interview_scheduled_at($interviewDateTime)
        : null;
    $replacements = [
        "{{candidate_name}}" => (string) $application["candidateName"],
        "{{job_title}}" => (string) $application["jobTitle"],
        "{{interview_datetime}}" => $interviewDateTime !== "" ? $interviewDateTime : "a scheduled time to be confirmed",
        "{candidateName}" => (string) $application["candidateName"],
        "{jobTitle}" => (string) $application["jobTitle"],
        "{companyName}" => "UWC Berhad",
        "{interviewDate}" => $interviewDateTime !== "" ? $interviewDateTime : "{interviewDateOptions}",
        "{interviewDateOptions}" => $interviewDateTime !== "" ? $interviewDateTime : "{interviewDateOptions}",
    ];
    $subject = strtr($subject, $replacements);
    $body = str_replace("\\n", "\n", strtr($body, $replacements));

    send_recruitment_email(
        (string) $application["candidateEmail"],
        (string) $application["candidateName"],
        $subject,
        $body,
        (string) $application["senderEmail"],
        (string) $application["senderName"],
        resolve_attachment_path((string) ($template["attachmentPath"] ?? "")),
        (string) ($template["attachmentFileName"] ?? ""),
        resolve_attachment_path((string) ($template["logoAttachmentPath"] ?? "")),
        (string) ($template["logoAttachmentFileName"] ?? "")
    );

    exec_stmt(
        $db,
        "INSERT INTO email_logs (
           application_id, sent_by_user_id, template_id, email_type,
           recipient_email, subject, body, scheduled_interview_at, status
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sent')",
        "iiisssss",
        [
            $applicationId,
            $userId,
            $template["id"] ?? null,
            $emailType,
            (string) $application["candidateEmail"],
            $subject,
            $body,
            $scheduledAt,
        ]
    );

    exec_stmt(
        $db,
        "INSERT INTO notifications (user_id, related_application_id, notification_type, title, message)
         VALUES (?, ?, 'email_sent', ?, ?)",
        "iiss",
        [$userId, $applicationId, $title, $message]
    );
}

function normalize_interview_scheduled_at(string $value): ?string
{
    $value = trim($value);
    if ($value === "") {
        return null;
    }

    // The email can offer multiple choices; the log stores the first scheduled option.
    $firstOption = trim(explode(" / ", $value, 2)[0]);
    $formats = [
        "d/m/Y, g:i A",
        "d/m/Y, h:i A",
        "Y-m-d H:i:s",
        "Y-m-d H:i",
        "Y-m-d\TH:i:s",
        "Y-m-d\TH:i",
    ];

    foreach ($formats as $format) {
        $date = DateTime::createFromFormat("!" . $format, $firstOption);
        $errors = DateTime::getLastErrors();
        $isValid = $errors === false ||
            ($errors["warning_count"] === 0 && $errors["error_count"] === 0);

        if ($date instanceof DateTime && $isValid) {
            return $date->format("Y-m-d H:i:s");
        }
    }

    return null;
}

function upload_interview_attachment(mysqli $db): void
{
    ensure_email_template_schema($db);
    if (!isset($_FILES["attachment"]) || !is_array($_FILES["attachment"])) {
        respond(["error" => "Attachment file is required"], 422);
    }

    $file = $_FILES["attachment"];
    if ((int) $file["error"] !== UPLOAD_ERR_OK) {
        respond(["error" => "Attachment upload failed"], 422);
    }

    $originalName = basename((string) $file["name"]);
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ["pdf", "doc", "docx"], true)) {
        respond(["error" => "Attachment must be PDF, DOC, or DOCX"], 422);
    }

    $size = (int) $file["size"];
    if ($size <= 0 || $size > 10 * 1024 * 1024) {
        respond(["error" => "Attachment size must be between 1 byte and 10 MB"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "email-attachments";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare attachment upload folder"], 500);
    }

    $storedName = sprintf("interview-attachment-%s.%s", bin2hex(random_bytes(6)), $extension);
    $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
    if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
        respond(["error" => "Unable to save uploaded attachment"], 500);
    }

    $relativePath = "/uploads/email-attachments/{$storedName}";
    exec_stmt(
        $db,
        "UPDATE email_templates SET attachment_path = ?, attachment_file_name = ?, updated_at = CURRENT_TIMESTAMP WHERE template_key = 'interview_invitation'",
        "ss",
        [$relativePath, $originalName]
    );

    respond([
        "ok" => true,
        "fileName" => $originalName,
        "attachmentPath" => $relativePath,
    ]);
}

function upload_interview_logo_attachment(mysqli $db): void
{
    ensure_email_template_schema($db);
    if (!isset($_FILES["attachment"]) || !is_array($_FILES["attachment"])) {
        respond(["error" => "Logo attachment file is required"], 422);
    }

    $file = $_FILES["attachment"];
    if ((int) $file["error"] !== UPLOAD_ERR_OK) {
        respond(["error" => "Logo attachment upload failed"], 422);
    }

    $originalName = basename((string) $file["name"]);
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ["jpg", "jpeg", "png", "gif", "webp"], true)) {
        respond(["error" => "Logo attachment must be JPG, PNG, GIF, or WEBP"], 422);
    }

    $size = (int) $file["size"];
    if ($size <= 0 || $size > 5 * 1024 * 1024) {
        respond(["error" => "Logo attachment size must be between 1 byte and 5 MB"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "email-attachments";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare attachment upload folder"], 500);
    }

    $storedName = sprintf("interview-logo-%s.%s", bin2hex(random_bytes(6)), $extension);
    $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
    if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
        respond(["error" => "Unable to save uploaded logo attachment"], 500);
    }

    $relativePath = "/uploads/email-attachments/{$storedName}";
    exec_stmt(
        $db,
        "UPDATE email_templates SET logo_attachment_path = ?, logo_attachment_file_name = ?, updated_at = CURRENT_TIMESTAMP WHERE template_key = 'interview_invitation'",
        "ss",
        [$relativePath, $originalName]
    );

    respond([
        "ok" => true,
        "fileName" => $originalName,
        "attachmentPath" => $relativePath,
    ]);
}

function remove_interview_email_asset(mysqli $db, bool $isLogo): void
{
    ensure_email_template_schema($db);
    $pathColumn = $isLogo ? "logo_attachment_path" : "attachment_path";
    $nameColumn = $isLogo ? "logo_attachment_file_name" : "attachment_file_name";
    $template = row(
        $db,
        "SELECT {$pathColumn} AS storedPath
         FROM email_templates
         WHERE template_key = 'interview_invitation'
         LIMIT 1"
    );
    $storedPath = (string) ($template["storedPath"] ?? "");

    exec_stmt(
        $db,
        "UPDATE email_templates
         SET {$pathColumn} = NULL, {$nameColumn} = NULL, updated_at = CURRENT_TIMESTAMP
         WHERE template_key = 'interview_invitation'"
    );

    $absolutePath = resolve_attachment_path($storedPath);
    $attachmentDirectory = realpath(
        __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "email-attachments"
    );
    if ($absolutePath !== null && $attachmentDirectory !== false) {
        $resolvedPath = realpath($absolutePath);
        if (
            $resolvedPath !== false &&
            str_starts_with($resolvedPath, $attachmentDirectory . DIRECTORY_SEPARATOR)
        ) {
            @unlink($resolvedPath);
        }
    }

    respond(["ok" => true]);
}

function normalize_email_template_key(string $templateKey): ?string
{
    $allowedKeys = [
        "interview_invitation",
        "reject_application",
        "application_confirmation",
    ];

    return in_array($templateKey, $allowedKeys, true) ? $templateKey : null;
}

function upload_email_template_asset(mysqli $db, string $templateKey, bool $isLogo): void
{
    ensure_email_template_schema($db);
    $templateKey = normalize_email_template_key($templateKey);
    if ($templateKey === null) {
        respond(["error" => "Unsupported email template"], 422);
    }

    if (!isset($_FILES["attachment"]) || !is_array($_FILES["attachment"])) {
        respond(["error" => $isLogo ? "Logo attachment file is required" : "Attachment file is required"], 422);
    }

    $file = $_FILES["attachment"];
    if ((int) ($file["error"] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
        respond(["error" => $isLogo ? "Logo attachment upload failed" : "Attachment upload failed"], 422);
    }

    $originalName = basename((string) ($file["name"] ?? ""));
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    $allowedExtensions = $isLogo
        ? ["jpg", "jpeg", "png", "gif", "webp"]
        : ["pdf", "doc", "docx"];
    if (!in_array($extension, $allowedExtensions, true)) {
        respond([
            "error" => $isLogo
                ? "Logo attachment must be JPG, PNG, GIF, or WEBP"
                : "Attachment must be PDF, DOC, or DOCX",
        ], 422);
    }

    $maxSize = $isLogo ? 5 * 1024 * 1024 : 10 * 1024 * 1024;
    $size = (int) ($file["size"] ?? 0);
    if ($size <= 0 || $size > $maxSize) {
        respond([
            "error" => $isLogo
                ? "Logo attachment size must be between 1 byte and 5 MB"
                : "Attachment size must be between 1 byte and 10 MB",
        ], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "email-attachments";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare attachment upload folder"], 500);
    }

    $assetName = $isLogo ? "logo" : "attachment";
    $storedName = sprintf(
        "%s-%s-%s.%s",
        $templateKey,
        $assetName,
        bin2hex(random_bytes(6)),
        $extension
    );
    $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
    if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
        respond(["error" => $isLogo ? "Unable to save uploaded logo attachment" : "Unable to save uploaded attachment"], 500);
    }

    $pathColumn = $isLogo ? "logo_attachment_path" : "attachment_path";
    $nameColumn = $isLogo ? "logo_attachment_file_name" : "attachment_file_name";
    $relativePath = "/uploads/email-attachments/{$storedName}";
    exec_stmt(
        $db,
        "UPDATE email_templates
         SET {$pathColumn} = ?, {$nameColumn} = ?, updated_at = CURRENT_TIMESTAMP
         WHERE template_key = ?",
        "sss",
        [$relativePath, $originalName, $templateKey]
    );

    respond([
        "ok" => true,
        "templateKey" => $templateKey,
        "fileName" => $originalName,
        "attachmentPath" => $relativePath,
    ]);
}

function remove_email_template_asset(mysqli $db, string $templateKey, bool $isLogo): void
{
    ensure_email_template_schema($db);
    $templateKey = normalize_email_template_key($templateKey);
    if ($templateKey === null) {
        respond(["error" => "Unsupported email template"], 422);
    }

    $pathColumn = $isLogo ? "logo_attachment_path" : "attachment_path";
    $nameColumn = $isLogo ? "logo_attachment_file_name" : "attachment_file_name";
    $template = row(
        $db,
        "SELECT {$pathColumn} AS storedPath
         FROM email_templates
         WHERE template_key = ?
         LIMIT 1",
        "s",
        [$templateKey]
    );
    $storedPath = (string) ($template["storedPath"] ?? "");

    exec_stmt(
        $db,
        "UPDATE email_templates
         SET {$pathColumn} = NULL, {$nameColumn} = NULL, updated_at = CURRENT_TIMESTAMP
         WHERE template_key = ?",
        "s",
        [$templateKey]
    );

    $absolutePath = resolve_attachment_path($storedPath);
    $attachmentDirectory = realpath(
        __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "email-attachments"
    );
    if ($absolutePath !== null && $attachmentDirectory !== false) {
        $resolvedPath = realpath($absolutePath);
        if (
            $resolvedPath !== false &&
            str_starts_with($resolvedPath, $attachmentDirectory . DIRECTORY_SEPARATOR)
        ) {
            @unlink($resolvedPath);
        }
    }

    respond(["ok" => true]);
}

// HR-managed email templates.
function ensure_email_template_schema(mysqli $db): void
{
    if (!table_column_exists($db, "email_templates", "logo_attachment_path")) {
        exec_stmt($db, "ALTER TABLE email_templates ADD COLUMN logo_attachment_path VARCHAR(500) NULL AFTER attachment_file_name");
    }
    if (!table_column_exists($db, "email_templates", "logo_attachment_file_name")) {
        exec_stmt($db, "ALTER TABLE email_templates ADD COLUMN logo_attachment_file_name VARCHAR(255) NULL AFTER logo_attachment_path");
    }
}

function email_templates(mysqli $db): void
{
    $templates = rows(
        $db,
        "SELECT
           template_key AS templateKey,
           subject,
           body,
           is_active AS isActive,
           attachment_path AS attachmentPath,
           attachment_file_name AS attachmentFileName,
           logo_attachment_path AS logoAttachmentPath,
           logo_attachment_file_name AS logoAttachmentFileName
         FROM email_templates
           WHERE template_key IN ('interview_invitation', 'reject_application', 'application_confirmation')"
    );

    $mapped = [];
    foreach ($templates as $template) {
        $mapped[(string) $template["templateKey"]] = $template;
    }

    respond(["templates" => $mapped]);
}

function update_email_templates(mysqli $db): void
{
    ensure_email_template_schema($db);
    $data = input_json();
    $interview = is_array($data["interview"] ?? null) ? $data["interview"] : [];
    $reject = is_array($data["reject"] ?? null) ? $data["reject"] : [];
    $application = is_array($data["application"] ?? null) ? $data["application"] : [];

    update_email_template_row(
        $db,
        "interview_invitation",
        "Interview Invitation",
        (string) ($interview["subject"] ?? ""),
        (string) ($interview["body"] ?? ""),
        filter_var($interview["enabled"] ?? true, FILTER_VALIDATE_BOOLEAN)
    );
    update_email_template_row(
        $db,
        "reject_application",
        "Reject Application",
        (string) ($reject["subject"] ?? ""),
        (string) ($reject["body"] ?? ""),
        filter_var($reject["enabled"] ?? true, FILTER_VALIDATE_BOOLEAN)
    );
    update_email_template_row(
        $db,
        "application_confirmation",
        "Application Confirmation",
        (string) ($application["subject"] ?? "Application received for {jobTitle}"),
        (string) ($application["body"] ?? (
            "Dear {candidateName},\n\n"
            . "Thank you for applying for the {jobTitle} position at {companyName}.\n\n"
            . "We have received your application successfully. Our HR team will review your application and contact you if you are shortlisted.\n\n"
            . "Please keep this email for your records.\n\n"
            . "Regards,\n{companyName}"
        )),
        filter_var($application["enabled"] ?? true, FILTER_VALIDATE_BOOLEAN)
    );

    respond(["ok" => true]);
}

function update_email_template_row(mysqli $db, string $key, string $name, string $subject, string $body, bool $enabled): void
{
    if ($subject === "" || $body === "") {
        respond(["error" => "Email template subject and message are required"], 422);
    }

    exec_stmt(
        $db,
        "INSERT INTO email_templates (template_key, template_name, subject, body, is_active, created_by_user_id)
         VALUES (?, ?, ?, ?, ?, 2)
         ON DUPLICATE KEY UPDATE
           template_name = VALUES(template_name),
           subject = VALUES(subject),
           body = VALUES(body),
           is_active = VALUES(is_active),
           updated_at = CURRENT_TIMESTAMP",
        "ssssi",
        [$key, $name, $subject, $body, $enabled ? 1 : 0]
    );
}

// HR-managed eligibility filter definitions.
function ensure_eligibility_filter_definition_schema(mysqli $db): void
{
    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS eligibility_filter_definitions (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          filter_key VARCHAR(100) NOT NULL UNIQUE,
          filter_name VARCHAR(160) NOT NULL,
          filter_type ENUM('dropdown', 'text', 'number') NOT NULL DEFAULT 'dropdown',
          is_system TINYINT(1) NOT NULL DEFAULT 0,
          sort_order INT UNSIGNED NOT NULL DEFAULT 0,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB"
    );

    if (!table_column_exists($db, "eligibility_filter_definitions", "filter_type")) {
        exec_stmt(
            $db,
            "ALTER TABLE eligibility_filter_definitions
             ADD COLUMN filter_type ENUM('dropdown', 'text', 'number') NOT NULL DEFAULT 'dropdown' AFTER filter_name"
        );
    }

    exec_stmt($db, "UPDATE eligibility_filter_definitions SET filter_type = 'number' WHERE filter_key = 'minCGPA'");
    exec_stmt($db, "UPDATE eligibility_filter_definitions SET filter_type = 'dropdown' WHERE filter_key IN ('minExperience', 'educationLevel', 'maxNoticePeriod', 'requiredLanguage', 'requiredLocation')");

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS eligibility_filter_options (
          id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          filter_id INT UNSIGNED NOT NULL,
          option_label VARCHAR(160) NOT NULL,
          sort_order INT UNSIGNED NOT NULL DEFAULT 0,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_eligibility_filter_options_definition
            FOREIGN KEY (filter_id) REFERENCES eligibility_filter_definitions(id) ON DELETE CASCADE,
          UNIQUE KEY uq_eligibility_filter_option (filter_id, option_label),
          INDEX idx_eligibility_filter_options_filter (filter_id)
        ) ENGINE=InnoDB"
    );

    // Job type now owns internship classification. Keep legacy job data
    // readable, but do not expose the old eligibility filter anymore.
    exec_stmt(
        $db,
        "DELETE FROM eligibility_filter_definitions
         WHERE filter_key = 'internshipAccepted'"
    );

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS eligibility_filter_seed_state (
          id TINYINT UNSIGNED PRIMARY KEY,
          seeded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB"
    );

    if (!row($db, "SELECT id FROM eligibility_filter_seed_state WHERE id = 1 LIMIT 1")) {
        seed_eligibility_filter_definitions($db);
        exec_stmt($db, "INSERT INTO eligibility_filter_seed_state (id) VALUES (1)");
    }
}

function seed_eligibility_filter_definitions(mysqli $db): void
{
    $filters = [
        ["minCGPA", "Minimum CGPA", "number", [], 10],
        ["minExperience", "Minimum Experience", "dropdown", ["Internship", "0 year", "1 year", "2 years", "3 years", "4 years", "5+ years", "8+ years", "10+ years"], 20],
        ["educationLevel", "Education Level", "dropdown", ["SPM", "STPM / Foundation / Matriculation", "Diploma", "Bachelor Degree", "Master Degree", "PhD"], 30],
        ["maxNoticePeriod", "Max Notice Period", "dropdown", ["Any", "Immediate", "14 days", "30 days", "60 days", "90 days"], 40],
        ["requiredLanguage", "Required Language", "dropdown", ["Any", "English", "Bahasa Malaysia", "Mandarin", "Tamil", "Japanese", "Korean"], 50],
        ["requiredLocation", "Candidate Location", "dropdown", ["Any", "Penang", "Kuala Lumpur", "Selangor", "Johor", "Perak", "Malaysia only", "Open to relocation"], 60],
    ];

    foreach ($filters as [$key, $name, $type, $options, $sortOrder]) {
        exec_stmt(
            $db,
            "INSERT INTO eligibility_filter_definitions (filter_key, filter_name, filter_type, is_system, sort_order)
             VALUES (?, ?, ?, 1, ?)
             ON DUPLICATE KEY UPDATE
               filter_name = VALUES(filter_name),
               filter_type = VALUES(filter_type),
               is_system = VALUES(is_system),
               sort_order = VALUES(sort_order)",
            "sssi",
            [$key, $name, $type, $sortOrder]
        );

        $filter = row($db, "SELECT id FROM eligibility_filter_definitions WHERE filter_key = ? LIMIT 1", "s", [$key]);
        if ($filter) {
            replace_eligibility_filter_options($db, (int) $filter["id"], $options);
        }
    }
}

function eligibility_filter_definition_payload(mysqli $db): array
{
    $filters = rows(
        $db,
        "SELECT
           id,
           filter_key AS filterKey,
           filter_name AS filterName,
           filter_type AS filterType,
           is_system AS isSystem,
           sort_order AS sortOrder
         FROM eligibility_filter_definitions
         ORDER BY sort_order ASC, filter_name ASC"
    );

    $options = rows(
        $db,
        "SELECT
           filter_id AS filterId,
           option_label AS optionLabel
         FROM eligibility_filter_options
         ORDER BY filter_id ASC, sort_order ASC, id ASC"
    );

    $optionsByFilter = [];
    foreach ($options as $option) {
        $filterId = (int) $option["filterId"];
        $optionsByFilter[$filterId] ??= [];
        $optionsByFilter[$filterId][] = (string) $option["optionLabel"];
    }

    return array_map(function (array $filter) use ($optionsByFilter): array {
        $id = (int) $filter["id"];
        return [
            "id" => $id,
            "filterKey" => (string) $filter["filterKey"],
            "filterName" => (string) $filter["filterName"],
            "filterType" => (string) ($filter["filterType"] ?? "dropdown"),
            "options" => $optionsByFilter[$id] ?? [],
            "isSystem" => (int) $filter["isSystem"] === 1,
            "sortOrder" => (int) $filter["sortOrder"],
        ];
    }, $filters);
}

function eligibility_filter_definitions(mysqli $db): void
{
    ensure_eligibility_filter_definition_schema($db);
    respond(["filters" => eligibility_filter_definition_payload($db)]);
}

function create_eligibility_filter_definition(mysqli $db): void
{
    ensure_eligibility_filter_definition_schema($db);
    $data = input_json();
    $filterName = trim((string) ($data["filterName"] ?? ""));
    $filterType = sanitize_eligibility_filter_type($data["filterType"] ?? "dropdown");
    $options = sanitize_eligibility_filter_options($data["options"] ?? []);

    if ($filterName === "") {
        respond(["error" => "Filter name is required"], 422);
    }

    $filterKey = unique_eligibility_filter_key($db, $filterName);
    $maxSort = row($db, "SELECT COALESCE(MAX(sort_order), 0) AS maxSort FROM eligibility_filter_definitions");
    $sortOrder = ((int) ($maxSort["maxSort"] ?? 0)) + 10;

    exec_stmt(
        $db,
        "INSERT INTO eligibility_filter_definitions (filter_key, filter_name, filter_type, is_system, sort_order)
         VALUES (?, ?, ?, 0, ?)",
        "sssi",
        [$filterKey, $filterName, $filterType, $sortOrder]
    );

    $filterId = (int) $db->insert_id;
    replace_eligibility_filter_options($db, $filterId, $filterType === "dropdown" ? $options : []);
    respond(["filters" => eligibility_filter_definition_payload($db)]);
}

function update_eligibility_filter_definition(mysqli $db, int $filterId): void
{
    ensure_eligibility_filter_definition_schema($db);
    $data = input_json();
    $filterName = trim((string) ($data["filterName"] ?? ""));
    $filterType = sanitize_eligibility_filter_type($data["filterType"] ?? "dropdown");
    $options = sanitize_eligibility_filter_options($data["options"] ?? []);

    if ($filterName === "") {
        respond(["error" => "Filter name is required"], 422);
    }

    if (!row($db, "SELECT id FROM eligibility_filter_definitions WHERE id = ? LIMIT 1", "i", [$filterId])) {
        respond(["error" => "Filter not found"], 404);
    }

    exec_stmt(
        $db,
        "UPDATE eligibility_filter_definitions SET filter_name = ?, filter_type = ? WHERE id = ?",
        "ssi",
        [$filterName, $filterType, $filterId]
    );
    replace_eligibility_filter_options($db, $filterId, $filterType === "dropdown" ? $options : []);
    respond(["filters" => eligibility_filter_definition_payload($db)]);
}

function delete_eligibility_filter_definition(mysqli $db, int $filterId): void
{
    ensure_eligibility_filter_definition_schema($db);

    if (!row($db, "SELECT id FROM eligibility_filter_definitions WHERE id = ? LIMIT 1", "i", [$filterId])) {
        respond(["error" => "Filter not found"], 404);
    }

    exec_stmt($db, "DELETE FROM eligibility_filter_definitions WHERE id = ?", "i", [$filterId]);
    respond(["filters" => eligibility_filter_definition_payload($db)]);
}

function sanitize_eligibility_filter_options(mixed $rawOptions): array
{
    if (!is_array($rawOptions)) {
        return [];
    }

    $options = [];
    foreach ($rawOptions as $option) {
        $value = trim((string) $option);
        if ($value !== "" && !in_array($value, $options, true)) {
            $options[] = $value;
        }
    }

    return $options;
}

function sanitize_eligibility_filter_type(mixed $rawType): string
{
    $type = (string) $rawType;
    return in_array($type, ["dropdown", "text", "number"], true) ? $type : "dropdown";
}

function replace_eligibility_filter_options(mysqli $db, int $filterId, array $options): void
{
    exec_stmt($db, "DELETE FROM eligibility_filter_options WHERE filter_id = ?", "i", [$filterId]);

    foreach (array_values($options) as $index => $option) {
        exec_stmt(
            $db,
            "INSERT INTO eligibility_filter_options (filter_id, option_label, sort_order)
             VALUES (?, ?, ?)",
            "isi",
            [$filterId, $option, ($index + 1) * 10]
        );
    }
}

function unique_eligibility_filter_key(mysqli $db, string $filterName): string
{
    $base = strtolower(trim(preg_replace("/[^a-zA-Z0-9]+/", "_", $filterName), "_"));
    if ($base === "") {
        $base = "custom_filter";
    }

    $base = "custom_" . substr($base, 0, 80);
    $key = $base;
    $counter = 2;

    while (row($db, "SELECT id FROM eligibility_filter_definitions WHERE filter_key = ? LIMIT 1", "s", [$key])) {
        $key = $base . "_" . $counter;
        $counter++;
    }

    return $key;
}

// SMTP transport and email formatting.
function mail_config(): array
{
    $configPath = __DIR__ . DIRECTORY_SEPARATOR . "mail-config.local.php";
    $config = [];
    if (is_file($configPath)) {
        $loadedConfig = require $configPath;
        $config = is_array($loadedConfig) ? $loadedConfig : [];
    }

    // Hosted services do not include the ignored local mail config file.
    // Allow Railway and other deployments to provide the same settings through
    // environment variables while keeping the local file as the default.
    $environmentConfig = [
        "provider" => environment_value("MAIL_PROVIDER", environment_value("EMAIL_PROVIDER")),
        "enabled" => environment_value("SMTP_ENABLED", environment_value("MAIL_ENABLED")),
        "host" => environment_value("SMTP_HOST", environment_value("MAIL_HOST")),
        "port" => environment_value("SMTP_PORT", environment_value("MAIL_PORT")),
        "username" => environment_value("SMTP_USERNAME", environment_value("MAIL_USERNAME")),
        "password" => environment_value("SMTP_PASSWORD", environment_value("MAIL_PASSWORD")),
        "encryption" => environment_value("SMTP_ENCRYPTION", environment_value("MAIL_ENCRYPTION")),
        "from_email" => environment_value("SMTP_FROM_EMAIL", environment_value("MAIL_FROM_EMAIL")),
        "from_name" => environment_value("SMTP_FROM_NAME", environment_value("MAIL_FROM_NAME")),
        "verify_peer" => environment_value("SMTP_VERIFY_PEER", environment_value("MAIL_VERIFY_PEER")),
        "resend_api_key" => environment_value("RESEND_API_KEY"),
        "resend_api_url" => environment_value("RESEND_API_URL"),
        "resend_from_email" => environment_value("RESEND_FROM_EMAIL"),
        "resend_from_name" => environment_value("RESEND_FROM_NAME"),
        "sendgrid_api_key" => environment_value("SENDGRID_API_KEY"),
        "sendgrid_api_url" => environment_value("SENDGRID_API_URL"),
        "sendgrid_from_email" => environment_value("SENDGRID_FROM_EMAIL"),
        "sendgrid_from_name" => environment_value("SENDGRID_FROM_NAME"),
    ];
    foreach ($environmentConfig as $key => $value) {
        if ($value !== null) {
            $config[$key] = $value;
        }
    }

    foreach (["enabled", "verify_peer"] as $booleanKey) {
        if (isset($config[$booleanKey]) && is_string($config[$booleanKey])) {
            $config[$booleanKey] = filter_var($config[$booleanKey], FILTER_VALIDATE_BOOLEAN);
        }
    }
    if (isset($config["port"])) {
        $config["port"] = (int) $config["port"];
    }

    $config["provider"] = strtolower(trim((string) ($config["provider"] ?? "smtp")));
    if ($config["provider"] === "") {
        $config["provider"] = "smtp";
    }

    if ($config["provider"] === "resend") {
        if (trim((string) ($config["resend_api_key"] ?? "")) === "") {
            throw new RuntimeException("Resend mail config is incomplete");
        }

        return $config;
    }

    if ($config["provider"] === "sendgrid") {
        if (trim((string) ($config["sendgrid_api_key"] ?? "")) === "") {
            throw new RuntimeException("SendGrid mail config is incomplete");
        }

        return $config;
    }

    if (!is_array($config) || empty($config["enabled"])) {
        throw new RuntimeException("Mail sending is not configured");
    }

    // Gmail displays app passwords in groups of four characters, but SMTP
    // authentication expects the continuous value. Keep other SMTP providers'
    // passwords unchanged because spaces may be meaningful there.
    $host = strtolower(trim((string) ($config["host"] ?? "")));
    if (str_contains($host, "gmail.com")) {
        $password = preg_replace('/\s+/', "", (string) ($config["password"] ?? ""));
        if (is_string($password)) {
            $config["password"] = $password;
        }
    }

    return $config;
}

function send_recruitment_email(string $toEmail, string $toName, string $subject, string $body, string $replyToEmail, string $replyToName, ?string $attachmentPath = null, string $attachmentFileName = "", ?string $logoAttachmentPath = null, string $logoAttachmentFileName = ""): void
{
    $config = mail_config();

    if (($config["provider"] ?? "smtp") === "resend") {
        resend_send_mail(
            $config,
            $toEmail,
            $toName,
            $subject,
            $body,
            $replyToEmail,
            $replyToName,
            $attachmentPath,
            $attachmentFileName,
            $logoAttachmentPath,
            $logoAttachmentFileName
        );
        return;
    }

    if (($config["provider"] ?? "smtp") === "sendgrid") {
        sendgrid_send_mail(
            $config,
            $toEmail,
            $toName,
            $subject,
            $body,
            $replyToEmail,
            $replyToName,
            $attachmentPath,
            $attachmentFileName,
            $logoAttachmentPath,
            $logoAttachmentFileName
        );
        return;
    }

    smtp_send_mail(
        $config,
        $toEmail,
        $toName,
        $subject,
        $body,
        $replyToEmail,
        $replyToName,
        $attachmentPath,
        $attachmentFileName,
        $logoAttachmentPath,
        $logoAttachmentFileName
    );
}

function resend_send_mail(array $config, string $toEmail, string $toName, string $subject, string $body, string $replyToEmail, string $replyToName, ?string $attachmentPath = null, string $attachmentFileName = "", ?string $logoAttachmentPath = null, string $logoAttachmentFileName = ""): void
{
    $apiKey = trim((string) ($config["resend_api_key"] ?? ""));
    $apiUrl = trim((string) ($config["resend_api_url"] ?? "https://api.resend.com/emails"));
    $fromEmail = trim((string) ($config["resend_from_email"] ?? $config["from_email"] ?? $config["username"] ?? ""));
    $fromName = trim((string) ($config["resend_from_name"] ?? $config["from_name"] ?? "UWC Recruitment"));

    if ($apiKey === "" || $apiUrl === "" || $fromEmail === "") {
        throw new RuntimeException("Resend mail config is incomplete");
    }

    $payload = [
        "from" => format_mailbox_address($fromName, $fromEmail),
        "to" => [$toEmail],
        "subject" => $subject,
        "text" => $body,
        "html" => build_resend_html_email_body($body, $logoAttachmentPath),
    ];

    if ($replyToEmail !== "") {
        $payload["reply_to"] = [$replyToEmail];
    }

    $attachments = [];
    if ($attachmentPath !== null && is_file($attachmentPath)) {
        $attachments[] = resend_attachment_payload($attachmentPath, $attachmentFileName);
    }
    if ($logoAttachmentPath !== null && is_file($logoAttachmentPath)) {
        // The logo is embedded in the HTML body so it remains visible in the email.
        // It is not sent a second time as a separate attachment.
    }
    if ($attachments !== []) {
        $payload["attachments"] = $attachments;
    }

    try {
        $jsonPayload = json_encode(
            $payload,
            JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
        );
    } catch (JsonException $error) {
        throw new RuntimeException("Unable to prepare Resend request: " . $error->getMessage(), 0, $error);
    }

    $context = stream_context_create([
        "http" => [
            "method" => "POST",
            "header" => implode("\r\n", [
                "Authorization: Bearer {$apiKey}",
                "Content-Type: application/json",
                "Accept: application/json",
            ]),
            "content" => $jsonPayload,
            "timeout" => 20,
            "ignore_errors" => true,
        ],
        "ssl" => [
            "verify_peer" => true,
            "verify_peer_name" => true,
        ],
    ]);

    $responseBody = @file_get_contents($apiUrl, false, $context);
    $responseHeaders = $http_response_header ?? [];
    $statusCode = 0;
    if (isset($responseHeaders[0]) && preg_match('/\s(\d{3})\s/', $responseHeaders[0], $matches)) {
        $statusCode = (int) $matches[1];
    }

    if ($responseBody === false) {
        throw new RuntimeException("Unable to connect to Resend API");
    }

    if ($statusCode < 200 || $statusCode >= 300) {
        $decoded = json_decode($responseBody, true);
        $message = is_array($decoded)
            ? (string) ($decoded["message"] ?? $decoded["name"] ?? "Resend rejected the email")
            : "Resend rejected the email";
        throw new RuntimeException("Resend API error ({$statusCode}): {$message}");
    }
}

function resend_attachment_payload(string $path, string $fileName): array
{
    $contents = file_get_contents($path);
    if ($contents === false) {
        throw new RuntimeException("Unable to read email attachment");
    }

    return [
        "filename" => $fileName !== "" ? $fileName : basename($path),
        "content" => base64_encode($contents),
    ];
}

function build_resend_html_email_body(string $body, ?string $logoPath = null): string
{
    $logoMarkup = "";
    if ($logoPath !== null && is_file($logoPath)) {
        $logoContents = file_get_contents($logoPath);
        if ($logoContents !== false) {
            $logoMimeType = attachment_mime_type($logoPath);
            $logoMarkup = "<div style=\"margin-bottom:20px;\"><img src=\"data:{$logoMimeType};base64," . base64_encode($logoContents) . "\" alt=\"UWC Logo\" style=\"max-width:140px;height:auto;display:block;\"></div>";
        }
    }

    $escapedBody = nl2br(htmlspecialchars($body, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8"));
    return "<!doctype html><html><body style=\"font-family:Arial,sans-serif;color:#111827;line-height:1.5;\">"
        . $logoMarkup
        . "<div>{$escapedBody}</div>"
        . "</body></html>";
}

function format_mailbox_address(string $name, string $email): string
{
    return $name !== "" ? "{$name} <{$email}>" : $email;
}

function sendgrid_send_mail(array $config, string $toEmail, string $toName, string $subject, string $body, string $replyToEmail, string $replyToName, ?string $attachmentPath = null, string $attachmentFileName = "", ?string $logoAttachmentPath = null, string $logoAttachmentFileName = ""): void
{
    $apiKey = trim((string) ($config["sendgrid_api_key"] ?? ""));
    $apiUrl = trim((string) ($config["sendgrid_api_url"] ?? "https://api.sendgrid.com/v3/mail/send"));
    $fromEmail = trim((string) ($config["sendgrid_from_email"] ?? $config["from_email"] ?? $config["username"] ?? ""));
    $fromName = trim((string) ($config["sendgrid_from_name"] ?? $config["from_name"] ?? "UWC Recruitment"));

    if ($apiKey === "" || $apiUrl === "" || $fromEmail === "") {
        throw new RuntimeException("SendGrid mail config is incomplete");
    }

    $logoCid = "uwc-logo";
    $payload = [
        "personalizations" => [[
            "to" => [[
                "email" => $toEmail,
                "name" => $toName,
            ]],
        ]],
        "from" => [
            "email" => $fromEmail,
            "name" => $fromName,
        ],
        "subject" => $subject,
        "content" => [
            ["type" => "text/plain", "value" => $body],
            [
                "type" => "text/html",
                "value" => $logoAttachmentPath !== null && is_file($logoAttachmentPath)
                    ? build_html_email_body($body, $logoCid)
                    : build_resend_html_email_body($body),
            ],
        ],
    ];

    if ($replyToEmail !== "") {
        $payload["reply_to"] = [
            "email" => $replyToEmail,
            "name" => $replyToName,
        ];
    }

    $attachments = [];
    if ($attachmentPath !== null && is_file($attachmentPath)) {
        $attachments[] = sendgrid_attachment_payload(
            $attachmentPath,
            $attachmentFileName,
            "attachment"
        );
    }
    if ($logoAttachmentPath !== null && is_file($logoAttachmentPath)) {
        $attachments[] = sendgrid_attachment_payload(
            $logoAttachmentPath,
            $logoAttachmentFileName,
            "inline",
            $logoCid
        );
    }
    if ($attachments !== []) {
        $payload["attachments"] = $attachments;
    }

    try {
        $jsonPayload = json_encode(
            $payload,
            JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
        );
    } catch (JsonException $error) {
        throw new RuntimeException("Unable to prepare SendGrid request: " . $error->getMessage(), 0, $error);
    }

    $context = stream_context_create([
        "http" => [
            "method" => "POST",
            "header" => implode("\r\n", [
                "Authorization: Bearer {$apiKey}",
                "Content-Type: application/json",
                "Accept: application/json",
            ]),
            "content" => $jsonPayload,
            "timeout" => 20,
            "ignore_errors" => true,
        ],
        "ssl" => [
            "verify_peer" => true,
            "verify_peer_name" => true,
        ],
    ]);

    $responseBody = @file_get_contents($apiUrl, false, $context);
    $responseHeaders = $http_response_header ?? [];
    $statusCode = 0;
    if (isset($responseHeaders[0]) && preg_match('/\s(\d{3})\s/', $responseHeaders[0], $matches)) {
        $statusCode = (int) $matches[1];
    }

    if ($responseBody === false) {
        throw new RuntimeException("Unable to connect to SendGrid API");
    }

    if ($statusCode !== 202) {
        $decoded = json_decode($responseBody, true);
        $message = "SendGrid rejected the email";
        if (is_array($decoded) && isset($decoded["errors"][0]["message"])) {
            $message = (string) $decoded["errors"][0]["message"];
        }
        throw new RuntimeException("SendGrid API error ({$statusCode}): {$message}");
    }
}

function sendgrid_attachment_payload(string $path, string $fileName, string $disposition, string $contentId = ""): array
{
    $contents = file_get_contents($path);
    if ($contents === false) {
        throw new RuntimeException("Unable to read email attachment");
    }

    $payload = [
        "content" => base64_encode($contents),
        "type" => attachment_mime_type($path),
        "filename" => $fileName !== "" ? $fileName : basename($path),
        "disposition" => $disposition,
    ];
    if ($contentId !== "") {
        $payload["content_id"] = $contentId;
    }

    return $payload;
}

function smtp_send_mail(array $config, string $toEmail, string $toName, string $subject, string $body, string $replyToEmail, string $replyToName, ?string $attachmentPath = null, string $attachmentFileName = "", ?string $logoAttachmentPath = null, string $logoAttachmentFileName = ""): void
{
    $host = (string) ($config["host"] ?? "");
    $port = (int) ($config["port"] ?? 587);
    $username = (string) ($config["username"] ?? "");
    $password = (string) ($config["password"] ?? "");
    $fromEmail = (string) ($config["from_email"] ?? $username);
    $fromName = (string) ($config["from_name"] ?? "UWC Recruitment");

    if ($host === "" || $username === "" || $password === "" || $fromEmail === "") {
        throw new RuntimeException("Mail config is incomplete");
    }

    $context = stream_context_create([
        "ssl" => [
            "verify_peer" => (bool) ($config["verify_peer"] ?? true),
            "verify_peer_name" => (bool) ($config["verify_peer"] ?? true),
            "allow_self_signed" => !(bool) ($config["verify_peer"] ?? true),
        ],
    ]);
    $socket = @stream_socket_client("tcp://{$host}:{$port}", $errno, $errstr, 20, STREAM_CLIENT_CONNECT, $context);
    if (!$socket) {
        throw new RuntimeException("Unable to connect to SMTP server: {$errstr}");
    }

    stream_set_timeout($socket, 20);

    try {
        smtp_expect($socket, [220]);
        smtp_command($socket, "EHLO localhost", [250]);

        if (($config["encryption"] ?? "tls") === "tls") {
            smtp_command($socket, "STARTTLS", [220]);
            if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
                throw new RuntimeException("Unable to start SMTP TLS encryption");
            }
            smtp_command($socket, "EHLO localhost", [250]);
        }

        smtp_command($socket, "AUTH LOGIN", [334]);
        smtp_command($socket, base64_encode($username), [334]);
        smtp_command($socket, base64_encode($password), [235]);
        smtp_command($socket, "MAIL FROM:<{$fromEmail}>", [250]);
        smtp_command($socket, "RCPT TO:<{$toEmail}>", [250, 251]);
        smtp_command($socket, "DATA", [354]);

        $headers = [
            "From: " . mime_header_name($fromName) . " <{$fromEmail}>",
            "To: " . mime_header_name($toName) . " <{$toEmail}>",
            "Reply-To: " . mime_header_name($replyToName) . " <{$replyToEmail}>",
            "Subject: " . mime_header_text($subject),
            "MIME-Version: 1.0",
        ];
        $messageBody = build_email_message_body(
            $body,
            $headers,
            [
                ["path" => $attachmentPath, "fileName" => $attachmentFileName],
            ],
            ["path" => $logoAttachmentPath, "fileName" => $logoAttachmentFileName]
        );
        $message = implode("\r\n", $headers) . "\r\n\r\n" . $messageBody . "\r\n.";
        smtp_command($socket, $message, [250]);
        smtp_command($socket, "QUIT", [221]);
    } finally {
        fclose($socket);
    }
}

function build_email_message_body(string $body, array &$headers, array $attachments = [], ?array $inlineLogo = null): string
{
    $validAttachments = [];
    foreach ($attachments as $attachment) {
        $path = (string) ($attachment["path"] ?? "");
        if ($path !== "" && is_file($path)) {
            $validAttachments[] = [
                "path" => $path,
                "fileName" => (string) ($attachment["fileName"] ?? ""),
            ];
        }
    }

    $logoPath = (string) ($inlineLogo["path"] ?? "");
    $hasInlineLogo = $logoPath !== "" && is_file($logoPath);

    if (count($validAttachments) === 0 && !$hasInlineLogo) {
        $headers[] = "Content-Type: text/plain; charset=UTF-8";
        $headers[] = "Content-Transfer-Encoding: 8bit";
        return normalize_smtp_body($body);
    }

    $boundary = "uwc_boundary_" . bin2hex(random_bytes(8));
    $headers[] = "Content-Type: multipart/mixed; boundary=\"{$boundary}\"";

    if ($hasInlineLogo) {
        $relatedBoundary = "uwc_related_" . bin2hex(random_bytes(8));
        $logoCid = "uwc-logo-" . bin2hex(random_bytes(6));
        $logoFileName = (string) ($inlineLogo["fileName"] ?? "");
        $logoFileName = $logoFileName !== "" ? $logoFileName : basename($logoPath);
        $escapedLogoFileName = addcslashes($logoFileName, "\"\\");
        $logoMimeType = attachment_mime_type($logoPath);
        $encodedLogo = chunk_split(base64_encode((string) file_get_contents($logoPath)));

        $message = "--{$boundary}\r\n"
            . "Content-Type: multipart/related; boundary=\"{$relatedBoundary}\"\r\n\r\n"
            . "--{$relatedBoundary}\r\n"
            . "Content-Type: text/html; charset=UTF-8\r\n"
            . "Content-Transfer-Encoding: 8bit\r\n\r\n"
            . build_html_email_body($body, $logoCid) . "\r\n"
            . "--{$relatedBoundary}\r\n"
            . "Content-Type: {$logoMimeType}; name=\"{$escapedLogoFileName}\"\r\n"
            . "Content-Transfer-Encoding: base64\r\n"
            . "Content-ID: <{$logoCid}>\r\n"
            . "Content-Disposition: inline; filename=\"{$escapedLogoFileName}\"\r\n\r\n"
            . $encodedLogo . "\r\n"
            . "--{$relatedBoundary}--\r\n";
    } else {
        $message = "--{$boundary}\r\n"
            . "Content-Type: text/plain; charset=UTF-8\r\n"
            . "Content-Transfer-Encoding: 8bit\r\n\r\n"
            . normalize_smtp_body($body) . "\r\n";
    }

    foreach ($validAttachments as $attachment) {
        $path = (string) $attachment["path"];
        $fileName = $attachment["fileName"] !== "" ? (string) $attachment["fileName"] : basename($path);
        $mimeType = attachment_mime_type($path);
        $encodedFile = chunk_split(base64_encode((string) file_get_contents($path)));
        $escapedFileName = addcslashes($fileName, "\"\\");

        $message .= "--{$boundary}\r\n"
            . "Content-Type: {$mimeType}; name=\"{$escapedFileName}\"\r\n"
            . "Content-Transfer-Encoding: base64\r\n"
            . "Content-Disposition: attachment; filename=\"{$escapedFileName}\"\r\n\r\n"
            . $encodedFile . "\r\n";
    }

    return $message . "--{$boundary}--";
}

function build_html_email_body(string $body, string $logoCid): string
{
    $escapedBody = nl2br(htmlspecialchars(normalize_smtp_body($body), ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8"));
    return "<!doctype html><html><body style=\"font-family:Arial,sans-serif;color:#111827;line-height:1.5;\">"
        . "<div style=\"margin-bottom:20px;\"><img src=\"cid:{$logoCid}\" alt=\"UWC Logo\" style=\"max-width:140px;height:auto;display:block;\"></div>"
        . "<div>{$escapedBody}</div>"
        . "</body></html>";
}

function resolve_attachment_path(string $path): ?string
{
    if ($path === "") {
        return null;
    }

    if (preg_match("#^https?://#i", $path)) {
        return null;
    }

    $normalized = str_replace(["/", "\\"], DIRECTORY_SEPARATOR, ltrim($path, "/\\"));
    $fullPath = __DIR__ . DIRECTORY_SEPARATOR . $normalized;
    return is_file($fullPath) ? $fullPath : null;
}

function attachment_mime_type(string $path): string
{
    if (function_exists("finfo_open")) {
        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        if ($finfo) {
            $detectedType = finfo_file($finfo, $path);
            finfo_close($finfo);
            if (is_string($detectedType) && $detectedType !== "") {
                return $detectedType;
            }
        }
    }

    return "application/octet-stream";
}

function smtp_command($socket, string $command, array $expectedCodes): string
{
    fwrite($socket, $command . "\r\n");
    return smtp_expect($socket, $expectedCodes);
}

function smtp_expect($socket, array $expectedCodes): string
{
    $response = "";
    do {
        $line = fgets($socket, 515);
        if ($line === false) {
            throw new RuntimeException("SMTP server did not respond");
        }
        $response .= $line;
    } while (isset($line[3]) && $line[3] === "-");

    $code = (int) substr($response, 0, 3);
    if (!in_array($code, $expectedCodes, true)) {
        throw new RuntimeException("SMTP error: " . trim($response));
    }

    return $response;
}

function normalize_smtp_body(string $body): string
{
    $body = preg_replace("/\r\n|\r|\n/", "\r\n", $body) ?? $body;
    return preg_replace("/^\./m", "..", $body) ?? $body;
}

function mime_header_text(string $value): string
{
    if (!function_exists("mb_encode_mimeheader")) {
        return $value;
    }

    return mb_encode_mimeheader($value, "UTF-8", "B", "\r\n");
}

function mime_header_name(string $value): string
{
    if ($value === "") {
        return "";
    }

    return mime_header_text($value);
}

// Notification list and read state.
function notifications(mysqli $db): void
{
    cleanup_old_notifications($db);

    $userId = (int) ($_GET["userId"] ?? 0);
    if ($userId <= 0) {
        respond(["error" => "userId is required"], 422);
    }

    $items = rows(
        $db,
        "SELECT
           n.id,
           n.related_application_id AS applicationId,
           a.job_id AS jobId,
           n.notification_type AS notificationType,
           n.title,
           n.message,
           n.is_read AS isRead,
           n.created_at AS createdAt
         FROM notifications n
         LEFT JOIN applications a ON a.id = n.related_application_id
         WHERE n.user_id = ?
         ORDER BY n.created_at DESC
         LIMIT 100",
        "i",
        [$userId]
    );
    $summary = row($db, "SELECT COUNT(*) AS unreadCount FROM notifications WHERE user_id = ? AND is_read = 0", "i", [$userId]);

    respond([
        "items" => $items,
        "preview" => array_slice($items, 0, 3),
        "unreadCount" => (int) ($summary["unreadCount"] ?? 0),
    ]);
}

function mark_notifications_read(mysqli $db): void
{
    cleanup_old_notifications($db);

    $data = input_json();
    $userId = (int) ($data["userId"] ?? 0);
    if ($userId <= 0) {
        respond(["error" => "userId is required"], 422);
    }

    exec_stmt($db, "UPDATE notifications SET is_read = 1 WHERE user_id = ?", "i", [$userId]);
    respond(["ok" => true]);
}

function ordinal_submission_label(int $submissionNo): string
{
    $suffix = "th";
    if ($submissionNo % 100 < 11 || $submissionNo % 100 > 13) {
        $lastDigit = $submissionNo % 10;
        if ($lastDigit === 1) {
            $suffix = "st";
        } elseif ($lastDigit === 2) {
            $suffix = "nd";
        } elseif ($lastDigit === 3) {
            $suffix = "rd";
        }
    }

    return $submissionNo . $suffix . " Submission";
}

function save_uploaded_documents(
    mysqli $db,
    int $applicationId,
    string $fallbackName,
    ?int $candidateId = null,
    array $applicationData = []
): array
{
    $fallbackName = basename($fallbackName) ?: "resume.pdf";
    $storedResumes = [];

    if (!isset($_FILES["resume"])) {
        exec_stmt(
            $db,
            "INSERT INTO resumes (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes, parsing_status)
             VALUES (?, ?, '/uploads/resumes/pending.pdf', 'application/pdf', 0, 'pending')",
            "is",
            [$applicationId, $fallbackName]
        );
        $resumeId = (int) $db->insert_id;
        exec_stmt(
            $db,
            "INSERT INTO application_documents (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes)
             VALUES (?, ?, '/uploads/resumes/pending.pdf', 'application/pdf', 0)",
            "is",
            [$applicationId, $fallbackName]
        );
        return [[
            "resumeId" => $resumeId,
            "originalName" => $fallbackName,
            "localPath" => null,
        ]];
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "resumes";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare resume upload folder"], 500);
    }

    $allowedExtensions = ["pdf"];
    $allowedMimeTypes = ["application/pdf"];

    foreach (normalize_uploaded_files($_FILES["resume"]) as $file) {
        if ((int) $file["error"] !== UPLOAD_ERR_OK) {
            respond(["error" => "Application document upload failed"], 422);
        }

        $originalName = basename((string) $file["name"]);
        $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
        if (!in_array($extension, $allowedExtensions, true)) {
            respond(["error" => "Application documents must be PDF files"], 422);
        }

        $size = (int) $file["size"];
        if ($size <= 0 || $size > 10 * 1024 * 1024) {
            respond(["error" => "Application document file size must be between 1 byte and 10 MB"], 422);
        }

        $mimeType = (string) ($file["type"] ?? "application/octet-stream");
        if (function_exists("finfo_open")) {
            $finfo = finfo_open(FILEINFO_MIME_TYPE);
            if ($finfo) {
                $detectedType = finfo_file($finfo, (string) $file["tmp_name"]);
                finfo_close($finfo);
                if (is_string($detectedType) && $detectedType !== "") {
                    $mimeType = $detectedType;
                }
            }
        }

        if (!in_array($mimeType, $allowedMimeTypes, true)) {
            respond(["error" => "Application documents must be PDF files"], 422);
        }

        $storedName = sprintf("application-%d-%s.%s", $applicationId, bin2hex(random_bytes(6)), $extension === "jpeg" ? "jpg" : $extension);
        $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
        if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
            respond(["error" => "Unable to save uploaded application document"], 500);
        }

        exec_stmt(
            $db,
            "INSERT INTO resumes (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes, parsing_status)
             VALUES (?, ?, ?, ?, ?, 'pending')",
            "isssi",
            [$applicationId, $originalName, public_file_url("/uploads/resumes/{$storedName}"), $mimeType, $size]
        );
        $resumeId = (int) $db->insert_id;
        exec_stmt(
            $db,
            "INSERT INTO application_documents (application_id, original_file_name, stored_file_path, file_mime_type, file_size_bytes)
             VALUES (?, ?, ?, ?, ?)",
            "isssi",
            [$applicationId, $originalName, public_file_url("/uploads/resumes/{$storedName}"), $mimeType, $size]
        );
        $storedResumes[] = [
            "resumeId" => $resumeId,
            "originalName" => $originalName,
            "localPath" => $destination,
        ];
    }

    return $storedResumes;
}

// HR user accounts, profiles, and audit history.
function users(mysqli $db): void
{
    ensure_user_profile_schema($db);
    respond([
        "users" => rows(
            $db,
            "SELECT
               u.id,
               u.full_name AS name,
               u.email,
               u.department,
               u.phone,
               u.avatar_path AS avatarPath,
               u.status,
               u.role_id AS roleId,
               CASE WHEN u.role_id = 2 THEN 'hiring_manager' ELSE 'hr_staff' END AS roleKey,
               r.role_name AS roleName,
               u.last_login_at AS lastLoginAt,
               u.created_at AS createdAt
             FROM users u
             JOIN roles r ON r.id = u.role_id
             ORDER BY u.role_id, u.full_name"
        )
    ]);
}

function save_user_avatar(): string
{
    if (!isset($_FILES["avatar"]) || !is_array($_FILES["avatar"]) || (int) ($_FILES["avatar"]["error"] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) {
        return "";
    }

    $file = $_FILES["avatar"];
    if ((int) $file["error"] !== UPLOAD_ERR_OK) {
        respond(["error" => "Avatar upload failed"], 422);
    }

    $originalName = basename((string) $file["name"]);
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ["jpg", "jpeg", "png", "gif", "webp"], true)) {
        respond(["error" => "Avatar must be JPG, PNG, GIF, or WEBP"], 422);
    }

    $size = (int) $file["size"];
    if ($size <= 0 || $size > 5 * 1024 * 1024) {
        respond(["error" => "Avatar size must be between 1 byte and 5 MB"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "user-avatars";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare avatar upload folder"], 500);
    }

    $storedName = sprintf("user-avatar-%s.%s", bin2hex(random_bytes(6)), $extension);
    if (!move_uploaded_file((string) $file["tmp_name"], $uploadDir . DIRECTORY_SEPARATOR . $storedName)) {
        respond(["error" => "Unable to save uploaded avatar"], 500);
    }

    return public_file_url("/uploads/user-avatars/{$storedName}");
}

function update_auth_profile(mysqli $db): void
{
    ensure_user_profile_schema($db);
    $data = input_data();
    $userId = (int) ($data["userId"] ?? 0);
    $fullName = trim((string) ($data["fullName"] ?? ""));
    $department = trim((string) ($data["department"] ?? ""));
    $phone = trim((string) ($data["phone"] ?? ""));
    $avatarPath = save_user_avatar();

    if ($userId <= 0) {
        respond(["error" => "Invalid user"], 422);
    }

    if ($fullName === "" || $department === "") {
        respond(["error" => "Full name and department are required"], 422);
    }

    $existing = row($db, "SELECT id FROM users WHERE id = ? AND status = 'active' LIMIT 1", "i", [$userId]);
    if (!$existing) {
        respond(["error" => "Active user not found"], 404);
    }

    if ($avatarPath !== "") {
        exec_stmt(
            $db,
            "UPDATE users SET full_name = ?, department = ?, phone = ?, avatar_path = ?, updated_at = NOW() WHERE id = ?",
            "ssssi",
            [$fullName, $department, $phone, $avatarPath, $userId]
        );
    } else {
        exec_stmt(
            $db,
            "UPDATE users SET full_name = ?, department = ?, phone = ?, updated_at = NOW() WHERE id = ?",
            "sssi",
            [$fullName, $department, $phone, $userId]
        );
    }

    $user = row(
        $db,
        "SELECT
           u.id,
           u.full_name AS name,
           u.email,
           u.department,
           u.phone,
           u.avatar_path AS avatarPath,
           u.status,
           u.role_id AS roleId,
           CASE WHEN u.role_id = 2 THEN 'hiring_manager' ELSE 'hr_staff' END AS roleKey,
           r.role_name AS roleName,
           u.last_login_at AS lastLoginAt,
           u.created_at AS createdAt
         FROM users u
         JOIN roles r ON r.id = u.role_id
         WHERE u.id = ?
         LIMIT 1",
        "i",
        [$userId]
    );

    respond(["user" => $user]);
}

function user_action_logs(mysqli $db, int $userId): void
{
    if ($userId <= 0) {
        respond(["error" => "Invalid user"], 422);
    }

    ensure_hr_action_log_reason_columns($db);

    respond([
        "actions" => rows(
            $db,
            "SELECT
               hal.id,
               hal.action_type AS actionType,
               hal.action_label AS actionLabel,
               hal.reason_type AS reasonType,
               hal.reason_details AS reasonDetails,
               hal.created_at AS createdAt,
               hal.application_id AS applicationId,
               j.id AS jobId,
               COALESCE(hal.job_title, j.title) AS jobTitle,
               j.department AS jobDepartment,
               c.id AS candidateId,
               c.full_name AS candidateName,
               c.email AS candidateEmail,
               a.application_status AS applicationStatus
             FROM hr_action_logs hal
             LEFT JOIN applications a ON a.id = hal.application_id
             LEFT JOIN jobs j ON j.id = hal.job_id
             LEFT JOIN candidates c ON c.id = hal.candidate_id
             WHERE hal.user_id = ?
             ORDER BY hal.created_at DESC, hal.id DESC
             LIMIT 200",
            "i",
            [$userId]
        )
    ]);
}

function create_user(mysqli $db): void
{
    ensure_user_profile_schema($db);
    $data = input_json();
    $fullName = trim((string) ($data["fullName"] ?? ""));
    $email = trim((string) ($data["email"] ?? ""));
    $roleId = (int) ($data["roleId"] ?? 0);
    $status = (string) ($data["status"] ?? "active");
    $temporaryPassword = (string) ($data["temporaryPassword"] ?? "");

    if ($fullName === "" || $email === "") {
        respond(["error" => "Full name and email are required"], 422);
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond(["error" => "Valid email is required"], 422);
    }

    if (!in_array($roleId, [1, 2], true)) {
        respond(["error" => "Role must be HR Staff or Hiring Manager"], 422);
    }

    if (!in_array($status, ["active", "inactive"], true)) {
        respond(["error" => "Invalid user status"], 422);
    }

    if (strlen($temporaryPassword) < 8) {
        respond(["error" => "Temporary password must be at least 8 characters"], 422);
    }

    $existing = row($db, "SELECT id FROM users WHERE email = ? LIMIT 1", "s", [$email]);
    if ($existing) {
        respond(["error" => "Email is already used by another user"], 409);
    }

    $passwordHash = password_hash($temporaryPassword, PASSWORD_DEFAULT);

    exec_stmt(
        $db,
        "INSERT INTO users (role_id, full_name, email, password_hash, department, phone, status)
         VALUES (?, ?, ?, ?, ?, ?, ?)",
        "issssss",
        [
            $roleId,
            $fullName,
            $email,
            $passwordHash,
            (string) ($data["department"] ?? "Human Resources"),
            (string) ($data["phone"] ?? ""),
            $status,
        ]
    );

    $userId = $db->insert_id;
    $user = row(
        $db,
        "SELECT
           u.id,
           u.full_name AS name,
           u.email,
           u.department,
           u.phone,
           u.avatar_path AS avatarPath,
           u.status,
           u.role_id AS roleId,
           CASE WHEN u.role_id = 2 THEN 'hiring_manager' ELSE 'hr_staff' END AS roleKey,
           r.role_name AS roleName,
           u.last_login_at AS lastLoginAt,
           u.created_at AS createdAt
         FROM users u
         JOIN roles r ON r.id = u.role_id
         WHERE u.id = ?
         LIMIT 1",
        "i",
        [$userId]
    );

    respond(["user" => $user], 201);
}

function update_user_password(mysqli $db, int $userId): void
{
    ensure_user_profile_schema($db);
    $data = input_json();
    $temporaryPassword = (string) ($data["temporaryPassword"] ?? "");
    $requirePasswordChange = (bool) ($data["requirePasswordChange"] ?? false);

    if ($userId <= 0) {
        respond(["error" => "Invalid user"], 422);
    }

    if (strlen($temporaryPassword) < 8) {
        respond(["error" => "Temporary password must be at least 8 characters"], 422);
    }

    $user = row($db, "SELECT id, full_name FROM users WHERE id = ? LIMIT 1", "i", [$userId]);
    if (!$user) {
        respond(["error" => "User not found"], 404);
    }

    exec_stmt(
        $db,
        "UPDATE users SET password_hash = ?, must_change_password = ?, updated_at = NOW() WHERE id = ?",
        "sii",
        [password_hash($temporaryPassword, PASSWORD_DEFAULT), $requirePasswordChange ? 1 : 0, $userId]
    );

    respond([
        "ok" => true,
        "userId" => $userId,
        "mustChangePassword" => $requirePasswordChange,
    ]);
}

function hr_efficiency(mysqli $db): void
{
    $summary = rows(
        $db,
        "SELECT
          u.full_name AS hrName,
          COUNT(latest_email.application_id) AS totalCandidates,
          ROUND(AVG(GREATEST(0, TIMESTAMPDIFF(MINUTE, a.submitted_at, latest_email.sent_at))) / 60, 1) AS avgProcessingHours,
          SUM(CASE WHEN a.application_status IN ('shortlisted', 'interview', 'interviewed') THEN 1 ELSE 0 END) AS shortlisted,
          SUM(CASE WHEN a.application_status = 'rejected' THEN 1 ELSE 0 END) AS rejected
         FROM users u
         LEFT JOIN applications a ON a.assigned_hr_user_id = u.id
         LEFT JOIN (
           SELECT el.application_id, el.sent_at
           FROM email_logs el
           JOIN (
             SELECT email_log.application_id, MAX(email_log.id) AS latest_email_id
             FROM email_logs email_log
             JOIN applications current_application ON current_application.id = email_log.application_id
             WHERE email_log.status = 'sent'
               AND email_log.email_type IN ('interview', 'reject')
               AND email_log.sent_at >= current_application.submitted_at
             GROUP BY email_log.application_id
           ) latest ON latest.latest_email_id = el.id
         ) latest_email ON latest_email.application_id = a.id
         WHERE u.role_id IN (1, 2)
           AND a.application_status <> 'new'
         GROUP BY u.id
         ORDER BY totalCandidates DESC"
    );
    $details = rows(
        $db,
        "SELECT
          c.full_name AS candidateName,
          c.email AS candidateEmail,
          j.id AS jobId,
          j.title AS jobTitle,
          j.department AS jobDepartment,
          a.application_status AS currentStatus,
          a.submitted_at AS applicationDate,
          CASE
            WHEN first_direct_reject.rejected_at IS NOT NULL THEN first_direct_reject.rejected_at
            WHEN first_hire.hired_at IS NOT NULL THEN first_hire.hired_at
            ELSE COALESCE(
              first_interviewed.interviewed_at,
              first_email.sent_at,
              a.reviewed_at
            )
          END AS lastActionDate,
          CASE
            WHEN first_direct_reject.rejected_at IS NOT NULL
              THEN GREATEST(0, TIMESTAMPDIFF(MINUTE, a.submitted_at, first_direct_reject.rejected_at))
            WHEN first_hire.hired_at IS NOT NULL
              THEN GREATEST(0, TIMESTAMPDIFF(MINUTE, a.submitted_at, first_hire.hired_at))
            ELSE NULL
          END AS processingMinutes,
          CASE
            WHEN first_direct_reject.rejected_at IS NOT NULL
              THEN 'reject'
            WHEN first_hire.hired_at IS NOT NULL
              THEN NULL
            WHEN first_email.sent_at IS NOT NULL
              THEN first_email.email_type
            ELSE NULL
          END AS emailOutcome,
          CASE
            WHEN first_direct_reject.rejected_at IS NOT NULL
              THEN 'rejected'
            WHEN first_hire.hired_at IS NOT NULL
              THEN 'hired'
            WHEN first_email.sent_at IS NOT NULL
              AND first_email.email_type = 'interview'
              THEN 'interview_email_sent'
            WHEN first_email.sent_at IS NOT NULL
              AND first_email.email_type = 'reject'
              THEN 'rejection_email_sent'
            ELSE a.application_status
          END AS processingStatus,
          CASE
            WHEN first_email.sent_at IS NOT NULL
              AND first_email.email_type = 'interview'
              AND a.application_status = 'rejected'
              AND latest_reject_action.action_type = 'send_rejection_email'
              THEN 'rejection_email_sent'
            WHEN first_email.sent_at IS NOT NULL
              AND first_email.email_type = 'interview'
              AND a.application_status = 'rejected'
              THEN 'rejected'
            WHEN first_email.sent_at IS NOT NULL
              AND first_email.email_type = 'interview'
              AND a.application_status = 'interviewed'
              THEN 'interviewed'
            ELSE NULL
          END AS followUpStatus,
          COALESCE(u.full_name, 'Unassigned') AS hrAssigned
         FROM applications a
         JOIN candidates c ON c.id = a.candidate_id
         JOIN jobs j ON j.id = a.job_id
         LEFT JOIN users u ON u.id = a.assigned_hr_user_id
         LEFT JOIN (
           SELECT el.application_id, el.email_type, el.sent_at
           FROM email_logs el
           JOIN (
             SELECT email_log.application_id, MIN(email_log.id) AS first_email_id
             FROM email_logs email_log
             JOIN (
               SELECT earliest_email.application_id, MIN(earliest_email.sent_at) AS first_sent_at
               FROM email_logs earliest_email
               JOIN applications current_application ON current_application.id = earliest_email.application_id
               WHERE earliest_email.status = 'sent'
                 AND earliest_email.email_type IN ('interview', 'reject')
                 AND earliest_email.sent_at >= current_application.submitted_at
               GROUP BY earliest_email.application_id
             ) first_sent ON first_sent.application_id = email_log.application_id
               AND first_sent.first_sent_at = email_log.sent_at
             JOIN applications current_application ON current_application.id = email_log.application_id
             WHERE email_log.status = 'sent'
               AND email_log.email_type IN ('interview', 'reject')
               AND email_log.sent_at >= current_application.submitted_at
             GROUP BY email_log.application_id
           ) first_email_id ON first_email_id.first_email_id = el.id
         ) first_email ON first_email.application_id = a.id
         LEFT JOIN (
           SELECT action_log.application_id, MIN(action_log.created_at) AS rejected_at
           FROM hr_action_logs action_log
           JOIN applications current_application ON current_application.id = action_log.application_id
           WHERE action_log.action_type IN ('reject_candidate', 'send_rejection_email')
             AND action_log.created_at >= current_application.submitted_at
           GROUP BY action_log.application_id
         ) first_direct_reject ON first_direct_reject.application_id = a.id
         LEFT JOIN (
           SELECT action_log.application_id, MIN(action_log.created_at) AS hired_at
           FROM hr_action_logs action_log
           JOIN applications current_application ON current_application.id = action_log.application_id
           WHERE action_log.action_type = 'hire_candidate'
             AND action_log.created_at >= current_application.submitted_at
           GROUP BY action_log.application_id
         ) first_hire ON first_hire.application_id = a.id
         LEFT JOIN (
           SELECT action_log.application_id, MIN(action_log.created_at) AS interviewed_at
           FROM hr_action_logs action_log
           JOIN applications current_application ON current_application.id = action_log.application_id
           WHERE action_log.action_type = 'mark_interviewed'
             AND action_log.created_at >= current_application.submitted_at
           GROUP BY action_log.application_id
         ) first_interviewed ON first_interviewed.application_id = a.id
         LEFT JOIN (
           SELECT action_log.application_id, action_log.action_type
           FROM hr_action_logs action_log
           JOIN (
             SELECT reject_log.application_id, MAX(reject_log.id) AS latest_reject_action_id
             FROM hr_action_logs reject_log
             JOIN applications current_application ON current_application.id = reject_log.application_id
             WHERE reject_log.action_type IN ('reject_candidate', 'send_rejection_email')
               AND reject_log.created_at >= current_application.submitted_at
             GROUP BY reject_log.application_id
           ) latest_reject ON latest_reject.latest_reject_action_id = action_log.id
         ) latest_reject_action ON latest_reject_action.application_id = a.id
         WHERE a.application_status <> 'new'
         ORDER BY lastActionDate DESC, a.id DESC"
    );

    respond(["data" => $summary, "details" => $details]);
}

// Attendance settings, imports, and analytics.
function attendance_analytics(mysqli $db): void
{
    [$settingsRows, $uploadRows] = row_sets($db, [
        "SELECT
           TIME_FORMAT(work_start_time, '%H:%i') AS workStartTime,
           TIME_FORMAT(work_end_time, '%H:%i') AS workEndTime,
           updated_by AS updatedBy,
           updated_at AS updatedAt
         FROM attendance_settings
         WHERE setting_id = 1
         LIMIT 1",
        "SELECT
           upload_id AS uploadId,
           file_name AS fileName,
           file_path AS filePath,
           uploaded_by AS uploadedBy,
           uploaded_at AS uploadedAt,
           total_rows AS totalRows
         FROM attendance_uploads
         ORDER BY uploaded_at DESC, upload_id DESC
         LIMIT 1",
    ]);

    $settings = $settingsRows[0] ?? [
        "workStartTime" => "08:00",
        "workEndTime" => "17:00",
        "updatedBy" => null,
        "updatedAt" => null,
    ];
    $latestUpload = $uploadRows[0] ?? null;
    $cachePath = attendance_cache_path($latestUpload, $settings);
    if (is_file($cachePath)) {
        read_json_cache($cachePath);
    }

    $cacheLock = fopen($cachePath . ".lock", "c");
    if ($cacheLock !== false) {
        flock($cacheLock, LOCK_EX);
        if (is_file($cachePath)) {
            read_json_cache($cachePath);
        }
    }

    $records = [];
    if ($latestUpload) {
        $records = rows(
            $db,
            "SELECT
               record_id AS recordId,
               upload_id AS uploadId,
               employee_id AS employeeId,
               name,
               department,
               job_title AS jobTitle,
               attendance_date AS attendanceDate,
               attendance_time AS attendanceTime,
               clock_in_time AS clockInTime,
               clock_out_time AS clockOutTime,
               status
             FROM attendance_records
             WHERE upload_id = ?
             ORDER BY attendance_date DESC, COALESCE(clock_in_time, attendance_time) DESC, record_id DESC",
            "i",
            [(int) $latestUpload["uploadId"]]
        );
    }

    $payload = ["latestUpload" => $latestUpload, "records" => $records, "settings" => $settings];
    write_json_cache($cachePath, $payload);
    if ($cacheLock !== false) {
        flock($cacheLock, LOCK_UN);
        fclose($cacheLock);
    }
    respond($payload);
}

function attendance_cache_path(?array $latestUpload, array $settings): string
{
    $cacheDirectory = rtrim(sys_get_temp_dir(), "\\/")
        . DIRECTORY_SEPARATOR
        . "uwc-hr-api-cache";
    if (!is_dir($cacheDirectory) && !mkdir($cacheDirectory, 0775, true) && !is_dir($cacheDirectory)) {
        throw new RuntimeException("Unable to prepare attendance cache");
    }

    $cacheKey = hash("sha256", json_encode([
        "uploadId" => $latestUpload["uploadId"] ?? 0,
        "uploadedAt" => $latestUpload["uploadedAt"] ?? "",
        "settingsUpdatedAt" => $settings["updatedAt"] ?? "",
    ]));
    return $cacheDirectory . DIRECTORY_SEPARATOR . "attendance-{$cacheKey}.json";
}

function read_json_cache(string $cachePath): void
{
    $cache = file_get_contents($cachePath);
    if ($cache === false || $cache === "") {
        return;
    }

    echo $cache;
    exit;
}

function write_json_cache(string $cachePath, array $payload): void
{
    $json = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if ($json === false) {
        return;
    }

    $temporaryPath = $cachePath . "." . bin2hex(random_bytes(4)) . ".tmp";
    if (file_put_contents($temporaryPath, $json, LOCK_EX) === false) {
        return;
    }
    if (!rename($temporaryPath, $cachePath)) {
        if (is_file($temporaryPath)) {
            unlink($temporaryPath);
        }
        return;
    }

    foreach (glob(dirname($cachePath) . DIRECTORY_SEPARATOR . "attendance-*.json") ?: [] as $oldCachePath) {
        if ($oldCachePath !== $cachePath && is_file($oldCachePath)) {
            unlink($oldCachePath);
        }
    }
}

function ensure_attendance_schema(mysqli $db): void
{
    if (table_exists($db, "attendance_records") && !table_column_exists($db, "attendance_records", "record_id")) {
        $legacyName = "attendance_records_legacy_" . date("YmdHis");
        exec_stmt($db, "RENAME TABLE attendance_records TO {$legacyName}");
    }

    if (table_exists($db, "attendance_uploads") && !table_column_exists($db, "attendance_uploads", "upload_id")) {
        $legacyName = "attendance_uploads_legacy_" . date("YmdHis");
        exec_stmt($db, "RENAME TABLE attendance_uploads TO {$legacyName}");
    }

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS attendance_uploads (
          upload_id INT AUTO_INCREMENT PRIMARY KEY,
          file_name VARCHAR(255) NOT NULL,
          file_path VARCHAR(500) NOT NULL,
          uploaded_by INT NULL,
          uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          total_rows INT UNSIGNED NOT NULL DEFAULT 0,
          INDEX idx_attendance_uploads_uploaded_at (uploaded_at),
          INDEX idx_attendance_uploads_uploaded_by (uploaded_by)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS attendance_records (
          record_id INT AUTO_INCREMENT PRIMARY KEY,
          upload_id INT NOT NULL,
          employee_id VARCHAR(80) NOT NULL,
          name VARCHAR(255) NOT NULL,
          department VARCHAR(160) NOT NULL DEFAULT '',
          job_title VARCHAR(160) NOT NULL DEFAULT '',
          attendance_date DATE NOT NULL,
          attendance_time TIME NULL,
          clock_in_time TIME NULL,
          clock_out_time TIME NULL,
          status ENUM('Attend','Late','Absent','MC','Leave') NOT NULL,
          CONSTRAINT fk_attendance_records_upload FOREIGN KEY (upload_id) REFERENCES attendance_uploads(upload_id) ON DELETE CASCADE,
          INDEX idx_attendance_records_upload (upload_id),
          INDEX idx_attendance_records_date (attendance_date),
          INDEX idx_attendance_records_employee (employee_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );

    if (!table_column_exists($db, "attendance_records", "clock_in_time")) {
        exec_stmt($db, "ALTER TABLE attendance_records ADD COLUMN clock_in_time TIME NULL AFTER attendance_time");
    }

    if (!table_column_exists($db, "attendance_records", "clock_out_time")) {
        exec_stmt($db, "ALTER TABLE attendance_records ADD COLUMN clock_out_time TIME NULL AFTER clock_in_time");
    }

    if (!table_column_exists($db, "attendance_records", "department")) {
        exec_stmt($db, "ALTER TABLE attendance_records ADD COLUMN department VARCHAR(160) NOT NULL DEFAULT '' AFTER name");
    }

    if (!table_column_exists($db, "attendance_records", "job_title")) {
        exec_stmt($db, "ALTER TABLE attendance_records ADD COLUMN job_title VARCHAR(160) NOT NULL DEFAULT '' AFTER department");
    }

    exec_stmt(
        $db,
        "CREATE TABLE IF NOT EXISTS attendance_settings (
          setting_id TINYINT UNSIGNED PRIMARY KEY,
          work_start_time TIME NOT NULL DEFAULT '08:00:00',
          work_end_time TIME NOT NULL DEFAULT '17:00:00',
          updated_by INT NULL,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_attendance_settings_updated_by (updated_by)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );

    exec_stmt(
        $db,
        "INSERT IGNORE INTO attendance_settings (setting_id, work_start_time, work_end_time)
         VALUES (1, '08:00:00', '17:00:00')"
    );
}

function attendance_settings(mysqli $db): array
{
    $settings = row(
        $db,
        "SELECT
           TIME_FORMAT(work_start_time, '%H:%i') AS workStartTime,
           TIME_FORMAT(work_end_time, '%H:%i') AS workEndTime,
           updated_by AS updatedBy,
           updated_at AS updatedAt
         FROM attendance_settings
         WHERE setting_id = 1
         LIMIT 1"
    );

    return $settings ?: [
        "workStartTime" => "08:00",
        "workEndTime" => "17:00",
        "updatedBy" => null,
        "updatedAt" => null,
    ];
}

function update_attendance_settings(mysqli $db): void
{
    ensure_attendance_schema($db);
    $data = input_json();
    $workStartTime = normalize_attendance_time((string) ($data["workStartTime"] ?? ""));
    $workEndTime = normalize_attendance_time((string) ($data["workEndTime"] ?? ""));
    $updatedBy = (int) ($data["updatedBy"] ?? 0);

    if (!$workStartTime || !$workEndTime) {
        respond(["error" => "Start time and end time are required"], 422);
    }

    if ($workStartTime >= $workEndTime) {
        respond(["error" => "End time must be later than start time"], 422);
    }

    $manager = row(
        $db,
        "SELECT id FROM users WHERE id = ? AND role_id = 2 AND status = 'active' LIMIT 1",
        "i",
        [$updatedBy]
    );

    if (!$manager) {
        respond(["error" => "Only hiring managers can update attendance settings"], 403);
    }

    exec_stmt(
        $db,
        "INSERT INTO attendance_settings (setting_id, work_start_time, work_end_time, updated_by)
         VALUES (1, ?, ?, ?)
         ON DUPLICATE KEY UPDATE
           work_start_time = VALUES(work_start_time),
           work_end_time = VALUES(work_end_time),
           updated_by = VALUES(updated_by),
           updated_at = CURRENT_TIMESTAMP",
        "ssi",
        [$workStartTime, $workEndTime, $updatedBy]
    );

    respond(["settings" => attendance_settings($db)]);
}

function upload_attendance_file(mysqli $db): void
{
    ensure_attendance_schema($db);

    if (!isset($_FILES["attendanceFile"]) || !is_array($_FILES["attendanceFile"])) {
        respond(["error" => "Attendance Excel file is required"], 422);
    }

    $file = $_FILES["attendanceFile"];
    if ((int) $file["error"] !== UPLOAD_ERR_OK) {
        respond(["error" => "Attendance file upload failed"], 422);
    }

    $originalName = basename((string) $file["name"]);
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ["xlsx", "xls"], true)) {
        respond(["error" => "Attendance file must be .xlsx or .xls"], 422);
    }

    $recordsJson = (string) ($_POST["records"] ?? "");
    $records = json_decode($recordsJson, true);
    if (!is_array($records) || count($records) === 0) {
        respond(["error" => "Attendance records are required"], 422);
    }

    $uploadedBy = isset($_POST["uploadedBy"]) && $_POST["uploadedBy"] !== "" ? (int) $_POST["uploadedBy"] : null;
    $size = (int) ($file["size"] ?? 0);
    if ($size <= 0) {
        respond(["error" => "Attendance file is empty"], 422);
    }

    $uploadDir = __DIR__ . DIRECTORY_SEPARATOR . "uploads" . DIRECTORY_SEPARATOR . "attendance";
    if (!is_dir($uploadDir) && !mkdir($uploadDir, 0775, true)) {
        respond(["error" => "Unable to prepare attendance upload folder"], 500);
    }

    $storedName = sprintf("attendance-%s-%s.%s", date("YmdHis"), bin2hex(random_bytes(5)), $extension);
    $destination = $uploadDir . DIRECTORY_SEPARATOR . $storedName;
    if (!move_uploaded_file((string) $file["tmp_name"], $destination)) {
        respond(["error" => "Unable to save attendance file"], 500);
    }

    $relativePath = "/uploads/attendance/{$storedName}";
    $mimeType = (string) ($file["type"] ?? "application/octet-stream");

    $db->begin_transaction();
    try {
        exec_stmt(
            $db,
            "INSERT INTO attendance_uploads (file_name, file_path, uploaded_by, total_rows)
             VALUES (?, ?, ?, ?)",
            "ssii",
            [$originalName, $relativePath, $uploadedBy, count($records)]
        );
        $uploadId = (int) $db->insert_id;

        $insertSql =
            "INSERT INTO attendance_records
              (upload_id, employee_id, name, department, job_title, attendance_date, attendance_time, clock_in_time, clock_out_time, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        foreach ($records as $record) {
            if (!is_array($record)) {
                throw new RuntimeException("Invalid attendance record format");
            }

            $employeeId = trim((string) ($record["employeeId"] ?? ""));
            $name = trim((string) ($record["name"] ?? ""));
            $department = trim((string) ($record["department"] ?? ""));
            $jobTitle = trim((string) ($record["jobTitle"] ?? ""));
            $date = normalize_attendance_date((string) ($record["date"] ?? ""));
            $clockIn = normalize_attendance_time((string) ($record["clockIn"] ?? $record["time"] ?? ""));
            $clockOut = normalize_attendance_time((string) ($record["clockOut"] ?? ""));
            $status = normalize_attendance_status((string) ($record["status"] ?? ""));

            if ($employeeId === "" || $name === "" || $department === "" || $jobTitle === "" || $date === "" || $status === "") {
                throw new RuntimeException("Attendance records must include employee ID, name, department, job title, date, and status");
            }

            exec_stmt(
                $db,
                $insertSql,
                "isssssssss",
                [$uploadId, $employeeId, $name, $department, $jobTitle, $date, $clockIn, $clockIn, $clockOut, $status]
            );
        }

        exec_stmt(
            $db,
            "DELETE FROM attendance_uploads WHERE upload_id <> ?",
            "i",
            [$uploadId]
        );

        $db->commit();
    } catch (Throwable $error) {
        $db->rollback();
        if (is_file($destination)) {
            unlink($destination);
        }
        respond(["error" => $error->getMessage()], 422);
    }

    $insertedRecords = rows(
        $db,
        "SELECT
           record_id AS recordId,
           upload_id AS uploadId,
           employee_id AS employeeId,
           name,
           department,
           job_title AS jobTitle,
           attendance_date AS attendanceDate,
           attendance_time AS attendanceTime,
           clock_in_time AS clockInTime,
           clock_out_time AS clockOutTime,
           status
         FROM attendance_records
         WHERE upload_id = ?
         ORDER BY record_id ASC",
        "i",
        [$uploadId]
    );

    respond([
        "upload" => [
            "uploadId" => $uploadId,
            "fileName" => $originalName,
            "filePath" => $relativePath,
            "uploadedBy" => $uploadedBy,
            "totalRows" => count($insertedRecords),
            "mimeType" => $mimeType,
        ],
        "records" => $insertedRecords,
    ], 201);
}

function normalize_attendance_date(string $value): string
{
    $value = trim($value);
    if ($value === "") {
        return "";
    }

    $formats = ["Y-m-d", "d/m/Y", "d-m-Y", "m/d/Y", "m-d-Y", "d M Y", "d F Y"];
    foreach ($formats as $format) {
        $date = DateTime::createFromFormat("!" . $format, $value);
        if ($date instanceof DateTime) {
            return $date->format("Y-m-d");
        }
    }

    $timestamp = strtotime($value);
    return $timestamp ? date("Y-m-d", $timestamp) : "";
}

function normalize_attendance_time(string $value): ?string
{
    $value = trim($value);
    if ($value === "" || $value === "-") {
        return null;
    }

    $formats = ["H:i:s", "H:i", "h:i A", "h:i a", "g:i A", "g:i a"];
    foreach ($formats as $format) {
        $time = DateTime::createFromFormat("!" . $format, $value);
        if ($time instanceof DateTime) {
            return $time->format("H:i:s");
        }
    }

    $timestamp = strtotime($value);
    return $timestamp ? date("H:i:s", $timestamp) : null;
}

function normalize_attendance_status(string $value): string
{
    $status = trim($value);
    $allowed = ["Attend", "Late", "Absent", "MC", "Leave"];
    foreach ($allowed as $item) {
        if (strcasecmp($status, $item) === 0) {
            return $item;
        }
    }
    return "";
}
