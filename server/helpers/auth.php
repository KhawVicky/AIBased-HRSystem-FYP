<?php
// Handles candidate tokens and sessions.

declare(strict_types=1);

function get_bearer_token(): string
{
    $header = (string) ($_SERVER["HTTP_AUTHORIZATION"] ?? "");
    if ($header === "" && function_exists("getallheaders")) {
        $headers = getallheaders();
        $header = (string) ($headers["Authorization"] ?? $headers["authorization"] ?? "");
    }

    if (preg_match("/Bearer\s+(.+)/i", $header, $matches)) {
        return trim($matches[1]);
    }

    return "";
}

function create_candidate_session(mysqli $db, int $accountId): string
{
    // Store only a hash so a database leak cannot expose active tokens.
    $token = bin2hex(random_bytes(32));
    $tokenHash = hash("sha256", $token);
    exec_stmt(
        $db,
        "INSERT INTO candidate_sessions (candidate_account_id, token_hash, expires_at)
         VALUES (?, ?, DATE_ADD(NOW(), INTERVAL 7 DAY))",
        "is",
        [$accountId, $tokenHash]
    );
    return $token;
}

function candidate_session(mysqli $db): array
{
    ensure_candidate_portal_schema($db);
    $token = get_bearer_token();
    if ($token === "") {
        respond(["error" => "Candidate login is required"], 401);
    }

    // Join the account and candidate profile in one session lookup.
    $session = row(
        $db,
        "SELECT
           ca.id AS accountId,
           ca.email,
           ca.candidate_id AS candidateId,
           c.full_name AS fullName,
           c.phone,
           c.gender,
           c.country,
           c.current_location AS currentLocation,
           c.languages_json AS languagesJson,
           c.address,
           c.education,
           c.default_resume_file_name AS defaultResumeFileName,
           c.default_resume_path AS defaultResumePath
         FROM candidate_sessions cs
         JOIN candidate_accounts ca ON ca.id = cs.candidate_account_id
         JOIN candidates c ON c.id = ca.candidate_id
         WHERE cs.token_hash = ?
           AND cs.expires_at > NOW()
           AND ca.status = 'active'
         LIMIT 1",
        "s",
        [hash("sha256", $token)]
    );

    if (!$session) {
        respond(["error" => "Candidate session expired or invalid"], 401);
    }

    return $session;
}

function optional_candidate_session(mysqli $db): ?array
{
    // Public routes can use candidate context without requiring login.
    $token = get_bearer_token();
    if ($token === "") {
        return null;
    }

    $session = row(
        $db,
        "SELECT
           ca.id AS accountId,
           ca.email,
           ca.candidate_id AS candidateId,
           c.full_name AS fullName,
           c.phone,
           c.gender,
           c.country,
           c.current_location AS currentLocation,
           c.languages_json AS languagesJson,
           c.address,
           c.education,
           c.default_resume_file_name AS defaultResumeFileName,
           c.default_resume_path AS defaultResumePath
         FROM candidate_sessions cs
         JOIN candidate_accounts ca ON ca.id = cs.candidate_account_id
         JOIN candidates c ON c.id = ca.candidate_id
         WHERE cs.token_hash = ?
           AND cs.expires_at > NOW()
           AND ca.status = 'active'
         LIMIT 1",
        "s",
        [hash("sha256", $token)]
    );

    return $session ?: null;
}

function candidate_account_payload(array $session, string $token = ""): array
{
    $payload = [
        "id" => (int) $session["accountId"],
        "candidateId" => (int) $session["candidateId"],
        "email" => (string) $session["email"],
        "fullName" => (string) $session["fullName"],
        "phone" => (string) ($session["phone"] ?? ""),
        "gender" => (string) ($session["gender"] ?? ""),
        "country" => (string) ($session["country"] ?? ""),
        "currentLocation" => (string) ($session["currentLocation"] ?? ""),
        "languages" => json_decode((string) ($session["languagesJson"] ?? "[]"), true) ?: [],
        "address" => (string) ($session["address"] ?? ""),
        "education" => (string) ($session["education"] ?? ""),
        "defaultResumeFileName" => $session["defaultResumeFileName"] ?? null,
        "defaultResumePath" => $session["defaultResumePath"] ?? null,
    ];

    if ($token !== "") {
        $payload["token"] = $token;
    }

    return $payload;
}

function candidate_session_from_account(mysqli $db, int $accountId): array
{
    $session = row(
        $db,
        "SELECT
           ca.id AS accountId,
           ca.email,
           ca.candidate_id AS candidateId,
           c.full_name AS fullName,
           c.phone,
           c.gender,
           c.country,
           c.current_location AS currentLocation,
           c.languages_json AS languagesJson,
           c.address,
           c.education,
           c.default_resume_file_name AS defaultResumeFileName,
           c.default_resume_path AS defaultResumePath
         FROM candidate_accounts ca
         JOIN candidates c ON c.id = ca.candidate_id
         WHERE ca.id = ?
         LIMIT 1",
        "i",
        [$accountId]
    );

    if (!$session) {
        throw new RuntimeException("Candidate account not found");
    }

    return $session;
}
