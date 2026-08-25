<?php
// Calls the internal FastAPI candidate scoring route after a parsed profile is persisted.

declare(strict_types=1);

function candidate_scoring_endpoint(): ?string
{
    $configured = trim((string) (environment_value("CANDIDATE_SCORING_API_URL") ?? ""));
    if ($configured !== "") {
        return $configured;
    }

    // Keep local/hosted setup small when both routes live in the same FastAPI
    // service. An explicit CANDIDATE_SCORING_API_URL still wins.
    $parserEndpoint = trim((string) (environment_value("RESUME_PARSING_API_URL") ?? ""));
    if ($parserEndpoint === "") {
        return null;
    }

    $derived = preg_replace(
        "#/api/resume/parse/?$#",
        "/api/scoring/candidate",
        $parserEndpoint
    );
    return is_string($derived) && $derived !== $parserEndpoint ? $derived : null;
}

function candidate_scoring_timeout_seconds(): int
{
    $value = (int) (environment_value("CANDIDATE_SCORING_TIMEOUT_SECONDS", "240") ?? "240");
    return max(10, min($value, 300));
}

/**
 * Trigger scoring using only server-owned identifiers. The response is kept
 * as a safe status object; the scoring service remains authoritative for all
 * score, eligibility and breakdown persistence.
 */
function request_candidate_scoring(int $jobId, int $applicationId): array
{
    $endpoint = candidate_scoring_endpoint();
    if ($endpoint === null) {
        return [
            "ok" => false,
            "status" => "pending",
            "code" => "SCORING_NOT_CONFIGURED",
            "message" => "Candidate scoring service is not configured",
        ];
    }

    if (!function_exists("curl_init")) {
        return [
            "ok" => false,
            "status" => "failed",
            "code" => "SCORING_REQUEST_UNAVAILABLE",
            "message" => "The candidate scoring request could not be started",
        ];
    }

    $requestBody = json_encode(
        [
            "jobId" => $jobId,
            "applicationId" => $applicationId,
            "forceRescore" => false,
        ],
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    );
    if ($requestBody === false) {
        return [
            "ok" => false,
            "status" => "failed",
            "code" => "SCORING_REQUEST_INVALID",
            "message" => "Candidate scoring request could not be encoded",
        ];
    }

    $headers = [
        "Accept: application/json",
        "Content-Type: application/json",
    ];
    $apiKey = trim((string) (environment_value("CANDIDATE_SCORING_API_KEY") ?? ""));
    if ($apiKey !== "") {
        $headers[] = "Authorization: Bearer {$apiKey}";
    }

    $curl = curl_init($endpoint);
    if ($curl === false) {
        return [
            "ok" => false,
            "status" => "failed",
            "code" => "SCORING_REQUEST_UNAVAILABLE",
            "message" => "The candidate scoring request could not be initialized",
        ];
    }

    curl_setopt_array($curl, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $requestBody,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_TIMEOUT => candidate_scoring_timeout_seconds(),
    ]);
    $body = curl_exec($curl);
    $httpCode = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $curlError = curl_error($curl);
    curl_close($curl);

    if (!is_string($body) || $body === "" || $httpCode < 200 || $httpCode >= 300) {
        return [
            "ok" => false,
            "status" => "failed",
            "code" => "SCORING_REQUEST_FAILED",
            "httpStatus" => $httpCode,
            "message" => $curlError !== ""
                ? "Candidate scoring request failed"
                : "Candidate scoring returned an error",
        ];
    }

    $decoded = json_decode($body, true);
    $data = is_array($decoded) ? ($decoded["data"] ?? null) : null;
    if (
        !is_array($decoded)
        || ($decoded["success"] ?? false) !== true
        || !is_array($data)
        || (int) ($data["runId"] ?? 0) <= 0
    ) {
        return [
            "ok" => false,
            "status" => "failed",
            "code" => "SCORING_INVALID_RESPONSE",
            "message" => "Candidate scoring response did not contain a scoring run",
        ];
    }

    $diagnostics = is_array($data["diagnostics"] ?? null) ? $data["diagnostics"] : [];
    return [
        "ok" => true,
        "status" => "completed",
        "runId" => (int) $data["runId"],
        "overallScore" => is_numeric($data["overallScore"] ?? null)
            ? (float) $data["overallScore"]
            : null,
        "rankingReady" => ($data["rankingReady"] ?? false) === true,
        "eligibility" => is_array($data["eligibility"] ?? null) ? $data["eligibility"] : [],
        "diagnostics" => [
            "qwenStatus" => is_string($diagnostics["qwenStatus"] ?? null)
                ? $diagnostics["qwenStatus"]
                : null,
            "qwenUsed" => ($diagnostics["qwenUsed"] ?? false) === true,
            "fallbackUsed" => ($diagnostics["fallbackUsed"] ?? false) === true,
            "runtimeTask" => is_string($diagnostics["runtimeTask"] ?? null)
                ? $diagnostics["runtimeTask"]
                : null,
            "model" => is_string($diagnostics["model"] ?? null)
                ? $diagnostics["model"]
                : null,
        ],
    ];
}
