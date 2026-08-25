<?php
// Calls the internal FastAPI resume parser and persists its validated result.

declare(strict_types=1);

function resume_parser_endpoint(): ?string
{
    $endpoint = trim((string) (environment_value("RESUME_PARSING_API_URL") ?? ""));
    return $endpoint !== "" ? $endpoint : null;
}

function resume_parser_timeout_seconds(): int
{
    $value = (int) (environment_value("RESUME_PARSING_TIMEOUT_SECONDS", "120") ?? "120");
    return max(5, min($value, 300));
}

function resume_parser_requires_semantic(): bool
{
    $configured = environment_value("RESUME_REQUIRE_SEMANTIC");
    if ($configured === null) {
        return true;
    }

    $parsed = filter_var($configured, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
    return $parsed ?? true;
}

function resume_parser_json(array $value): string
{
    $json = json_encode(
        $value,
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE
    );
    return $json === false ? "{}" : $json;
}

function save_resume_parse_state(
    mysqli $db,
    int $resumeId,
    string $status,
    ?string $parsedText,
    ?string $profileJson,
    array $metadata,
    ?string $parserVersion = null
): void {
    $metadataJson = resume_parser_json($metadata);
    exec_stmt(
        $db,
        "UPDATE resumes
         SET parsed_text = ?,
             parsed_profile_json = ?,
             parse_metadata_json = ?,
             parser_version = ?,
             parsed_at = IF(? = 'parsed', NOW(), parsed_at),
             parsing_status = ?
         WHERE id = ?",
        "ssssssi",
        [
            $parsedText,
            $profileJson,
            $metadataJson,
            $parserVersion,
            $status,
            $status,
            $resumeId,
        ]
    );
}

function parse_saved_resume_document(
    mysqli $db,
    int $resumeId,
    int $applicationId,
    ?int $candidateId,
    string $localPath,
    string $originalName,
    array $applicationData = []
): array {
    /**
     * Send one stored resume to FastAPI and persist the validated profile and
     * diagnostics without changing the candidate/application identity.
     */
    $endpoint = resume_parser_endpoint();
    if ($endpoint === null) {
        save_resume_parse_state(
            $db,
            $resumeId,
            "pending",
            null,
            null,
            [
                "status" => "skipped",
                "reason" => "RESUME_PARSING_API_URL is not configured",
            ]
        );
        return [
            "status" => "pending",
            "code" => "PARSER_NOT_CONFIGURED",
            "message" => "Resume parsing service is not configured",
        ];
    }

    if (!function_exists("curl_init") || !is_file($localPath)) {
        save_resume_parse_state(
            $db,
            $resumeId,
            "failed",
            null,
            null,
            [
                "status" => "failed",
                "code" => "PARSER_REQUEST_UNAVAILABLE",
                "message" => "The internal resume parser request could not be started",
            ],
            "resume-parsing-v1"
        );
        return [
            "status" => "failed",
            "code" => "PARSER_REQUEST_UNAVAILABLE",
            "message" => "The internal resume parser request could not be started",
        ];
    }

    $file = curl_file_create($localPath, "application/pdf", basename($originalName));
    $fields = [
        "file" => $file,
        "candidate_id" => $candidateId === null ? "" : (string) $candidateId,
        "require_semantic" => resume_parser_requires_semantic() ? "1" : "0",
    ];
    if ($applicationData !== []) {
        $fields["application_data"] = resume_parser_json($applicationData);
    }

    $handle = curl_init($endpoint);
    if ($handle === false) {
        save_resume_parse_state(
            $db,
            $resumeId,
            "failed",
            null,
            null,
            [
                "status" => "failed",
                "code" => "PARSER_REQUEST_UNAVAILABLE",
                "message" => "The internal resume parser request could not be initialized",
            ],
            "resume-parsing-v1"
        );
        return [
            "status" => "failed",
            "code" => "PARSER_REQUEST_UNAVAILABLE",
            "message" => "The internal resume parser request could not be initialized",
        ];
    }

    curl_setopt_array($handle, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $fields,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_TIMEOUT => resume_parser_timeout_seconds(),
        CURLOPT_HTTPHEADER => ["Accept: application/json"],
    ]);
    $body = curl_exec($handle);
    $httpCode = (int) curl_getinfo($handle, CURLINFO_HTTP_CODE);
    $curlError = curl_error($handle);
    curl_close($handle);

    if (!is_string($body) || $body === "" || $httpCode < 200 || $httpCode >= 300) {
        save_resume_parse_state(
            $db,
            $resumeId,
            "failed",
            null,
            null,
            [
                "status" => "failed",
                "code" => "PARSER_REQUEST_FAILED",
                "httpStatus" => $httpCode,
                "message" => $curlError !== "" ? "Resume parser request failed" : "Resume parser returned an error",
            ],
            "resume-parsing-v1"
        );
        return [
            "status" => "failed",
            "code" => "PARSER_REQUEST_FAILED",
            "httpStatus" => $httpCode,
            "message" => $curlError !== ""
                ? "Resume parser request failed"
                : "Resume parser returned an error",
        ];
    }

    $decoded = json_decode($body, true);
    $data = is_array($decoded) ? ($decoded["data"] ?? null) : null;
    $profile = is_array($data) ? ($data["profile"] ?? null) : null;
    $rawText = is_array($data) ? (string) ($data["rawText"] ?? "") : "";
    if (!is_array($decoded) || ($decoded["success"] ?? false) !== true || !is_array($profile)) {
        save_resume_parse_state(
            $db,
            $resumeId,
            "failed",
            null,
            null,
            [
                "status" => "failed",
                "code" => "PARSER_INVALID_RESPONSE",
                "message" => "Resume parser response did not contain a candidate profile",
            ],
            "resume-parsing-v1"
        );
        return [
            "status" => "failed",
            "code" => "PARSER_INVALID_RESPONSE",
            "message" => "Resume parser response did not contain a candidate profile",
        ];
    }

    $diagnostics = is_array($data["diagnostics"] ?? null) ? $data["diagnostics"] : [];
    $profileJson = resume_parser_json($profile);
    save_resume_parse_state(
        $db,
        $resumeId,
        "parsed",
        $rawText !== "" ? $rawText : null,
        $profileJson,
        [
            "status" => "parsed",
            "parserVersion" => (string) ($diagnostics["parserVersion"] ?? "resume-parsing-v1"),
            "diagnostics" => $diagnostics,
            "warnings" => is_array($decoded["warnings"] ?? null) ? $decoded["warnings"] : [],
        ],
        (string) ($diagnostics["parserVersion"] ?? "resume-parsing-v1")
    );

    $summary = trim((string) ($profile["candidateSummary"] ?? ""));
    if ($summary !== "") {
        exec_stmt(
            $db,
            "UPDATE applications SET ai_summary = ? WHERE id = ?",
            "si",
            [$summary, $applicationId]
        );
    }

    return [
        "status" => "parsed",
        "qwenStatus" => is_string($diagnostics["qwenStatus"] ?? null)
            ? $diagnostics["qwenStatus"]
            : null,
        "parserVersion" => (string) ($diagnostics["parserVersion"] ?? "resume-parsing-v1"),
    ];
}
