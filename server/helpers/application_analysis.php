<?php
// Coordinates parser/scoring stages after candidate submission persistence.

declare(strict_types=1);

function application_analysis_status_is_valid(string $status): bool
{
    return in_array($status, ["pending", "parsing", "scoring", "completed", "failed"], true);
}

function application_analysis_json(array $value): string
{
    $json = json_encode(
        $value,
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE
    );
    return $json === false ? "{}" : $json;
}

function application_analysis_now(): string
{
    return gmdate("c");
}

function application_analysis_decode_diagnostics(?string $json): array
{
    if (!is_string($json) || trim($json) === "") {
        return [];
    }

    $decoded = json_decode($json, true);
    return is_array($decoded) ? $decoded : [];
}

function application_analysis_automatic_retry_limit(): int
{
    return 1;
}

function application_analysis_automatic_retry_count_for_queue(array $worker, string $trigger): int
{
    $current = max(0, (int) ($worker["automaticRetryCount"] ?? 0));
    if (in_array($trigger, ["submission", "retry"], true)) {
        return 0;
    }
    if ($trigger === "automatic-retry") {
        return min(application_analysis_automatic_retry_limit(), $current + 1);
    }
    return $current;
}

function application_analysis_transient_http_status(?int $httpStatus): bool
{
    if ($httpStatus === null) {
        return false;
    }
    return $httpStatus === 0
        || in_array($httpStatus, [408, 425, 429, 499], true)
        || ($httpStatus >= 500 && $httpStatus <= 599);
}

function application_analysis_automatic_retry_stage(array $result, int $automaticRetryCount): ?string
{
    if (
        ($result["status"] ?? "") !== "failed"
        || $automaticRetryCount >= application_analysis_automatic_retry_limit()
    ) {
        return null;
    }

    $stage = strtolower(trim((string) ($result["stage"] ?? "")));
    $code = strtoupper(trim((string) ($result["code"] ?? "")));
    $httpStatus = isset($result["httpStatus"]) && is_numeric($result["httpStatus"])
        ? (int) $result["httpStatus"]
        : null;
    if (!application_analysis_transient_http_status($httpStatus)) {
        return null;
    }

    if (in_array($stage, ["parse", "parsing"], true) && $code === "PARSER_REQUEST_FAILED") {
        return "all";
    }
    if (in_array($stage, ["score", "scoring"], true) && $code === "SCORING_REQUEST_FAILED") {
        return "score";
    }
    return null;
}

function application_analysis_initial_diagnostics_json(): string
{
    return application_analysis_json([
        "analysisWorker" => [
            "status" => "awaiting_persistence",
            "workerRunnable" => false,
            "requestedStage" => "all",
            "queuedAt" => application_analysis_now(),
            "retryAttempt" => 0,
            "automaticRetryCount" => 0,
            "automaticRetryLimit" => application_analysis_automatic_retry_limit(),
            "automaticRetryScheduled" => false,
        ],
    ]);
}

function application_analysis_pending_result(array $resumeIds = [], ?int $candidateId = null): array
{
    $result = [
        "status" => "pending",
        "code" => "ANALYSIS_QUEUED",
        "resumeIds" => array_values(array_map("intval", $resumeIds)),
        "diagnostics" => [
            "background" => true,
            "message" => "Application analysis was queued after submission persistence",
        ],
    ];
    if ($candidateId !== null && $candidateId > 0) {
        $result["candidateId"] = $candidateId;
    }
    return $result;
}

function application_analysis_diagnostics(mysqli $db, int $applicationId): array
{
    $record = row(
        $db,
        "SELECT scoring_diagnostics_json AS diagnosticsJson FROM applications WHERE id = ? LIMIT 1",
        "i",
        [$applicationId]
    );
    return application_analysis_decode_diagnostics($record["diagnosticsJson"] ?? null);
}

function queue_application_analysis(
    mysqli $db,
    int $applicationId,
    string $stage = "all",
    string $trigger = "submission"
): array {
    /**
     * Mark durable work only after the application and resume rows exist.
     * The worker later claims this pending marker atomically, so retries reuse
     * the same application/resume identifiers instead of creating duplicates.
     */
    if (!in_array($stage, ["all", "parse", "score"], true)) {
        throw new InvalidArgumentException("Unsupported analysis queue stage");
    }

    $existing = row(
        $db,
        "SELECT analysis_status AS analysisStatus, scoring_diagnostics_json AS diagnosticsJson
         FROM applications WHERE id = ? LIMIT 1",
        "i",
        [$applicationId]
    );
    if (!$existing) {
        throw new RuntimeException("Application not found for analysis queue");
    }

    $currentStatus = (string) ($existing["analysisStatus"] ?? "pending");
    $isAutomaticRetry = $trigger === "automatic-retry";
    if (in_array($currentStatus, ["parsing", "scoring"], true) && !$isAutomaticRetry) {
        return [
            "status" => $currentStatus,
            "queued" => false,
            "active" => true,
        ];
    }

    $diagnostics = application_analysis_decode_diagnostics($existing["diagnosticsJson"] ?? null);
    $worker = is_array($diagnostics["analysisWorker"] ?? null)
        ? $diagnostics["analysisWorker"]
        : [];
    $retryAttempt = (int) ($worker["retryAttempt"] ?? 0);
    if (in_array($trigger, ["retry", "automatic-retry"], true) || $currentStatus === "failed") {
        $retryAttempt++;
    }
    $automaticRetryCount = application_analysis_automatic_retry_count_for_queue($worker, $trigger);
    $automaticRetryScheduled = $trigger === "automatic-retry";
    $diagnostics["analysisWorker"] = array_merge(
        $worker,
        [
            "status" => "pending",
            "workerRunnable" => true,
            "requestedStage" => $stage,
            "trigger" => $trigger,
            "queuedAt" => application_analysis_now(),
            "retryAttempt" => $retryAttempt,
            "automaticRetryCount" => $automaticRetryCount,
            "automaticRetryLimit" => application_analysis_automatic_retry_limit(),
            "automaticRetryScheduled" => $automaticRetryScheduled,
            "automaticRetryStage" => $automaticRetryScheduled ? $stage : null,
            "automaticRetryScheduledAt" => $automaticRetryScheduled ? application_analysis_now() : null,
            "automaticRetryScheduleFailedAt" => null,
        ]
    );

    $statusConstraint = $isAutomaticRetry
        ? "analysis_status IN ('parsing', 'scoring', 'failed')"
        : "(analysis_status IS NULL OR analysis_status NOT IN ('parsing', 'scoring'))";
    $queued = exec_stmt_affected_rows(
        $db,
        "UPDATE applications
         SET analysis_status = 'pending',
             total_score = NULL,
             rank_no = NULL,
             scored_at = NULL,
             scoring_diagnostics_json = ?
         WHERE id = ? AND {$statusConstraint}",
        "si",
        [application_analysis_json($diagnostics), $applicationId]
    );

    if ($queued > 0) {
        // A retry must not expose a previous scoring run while the new run is pending.
        exec_stmt($db, "DELETE FROM score_breakdowns WHERE application_id = ?", "i", [$applicationId]);
    }

    return [
        "status" => "pending",
        "queued" => $queued > 0,
        "active" => false,
    ];
}

function analysis_worker_is_runnable(array $diagnostics): bool
{
    $worker = $diagnostics["analysisWorker"] ?? null;
    if (!is_array($worker) || !array_key_exists("workerRunnable", $worker)) {
        return true;
    }
    return $worker["workerRunnable"] === true;
}

function analysis_worker_requested_stage(array $diagnostics): string
{
    $stage = strtolower(trim((string) ($diagnostics["analysisWorker"]["requestedStage"] ?? "all")));
    return in_array($stage, ["all", "parse", "score"], true) ? $stage : "all";
}

function claim_application_analysis(mysqli $db, int $applicationId, string $stage): bool
{
    // The pending-to-running update is the concurrency boundary: only one
    // candidate-api worker may own a queued application at a time.
    $claimedStatus = $stage === "score" ? "scoring" : "parsing";
    $diagnostics = application_analysis_diagnostics($db, $applicationId);
    $worker = is_array($diagnostics["analysisWorker"] ?? null)
        ? $diagnostics["analysisWorker"]
        : [];
    $diagnostics["analysisWorker"] = array_merge(
        $worker,
        [
            "status" => "running",
            "workerRunnable" => false,
            "stage" => $stage,
            "startedAt" => application_analysis_now(),
        ]
    );

    return exec_stmt_affected_rows(
        $db,
        "UPDATE applications
         SET analysis_status = ?, scoring_diagnostics_json = ?
         WHERE id = ? AND analysis_status = 'pending'",
        "ssi",
        [$claimedStatus, application_analysis_json($diagnostics), $applicationId]
    ) === 1;
}

function record_analysis_worker_diagnostics(mysqli $db, int $applicationId, array $changes): void
{
    $diagnostics = application_analysis_diagnostics($db, $applicationId);
    $worker = is_array($diagnostics["analysisWorker"] ?? null)
        ? $diagnostics["analysisWorker"]
        : [];
    $diagnostics["analysisWorker"] = array_merge($worker, $changes);
    exec_stmt(
        $db,
        "UPDATE applications SET scoring_diagnostics_json = ? WHERE id = ?",
        "si",
        [application_analysis_json($diagnostics), $applicationId]
    );
}

function set_application_analysis_status(
    mysqli $db,
    int $applicationId,
    string $status,
    ?array $diagnostics = null
): void {
    if (!application_analysis_status_is_valid($status)) {
        throw new InvalidArgumentException("Unsupported application analysis status");
    }

    if ($diagnostics === null) {
        if ($status === "failed") {
            exec_stmt(
                $db,
                "UPDATE applications
                 SET analysis_status = ?,
                     total_score = 0,
                     rank_no = NULL,
                     scored_at = NOW()
                 WHERE id = ?",
                "si",
                [$status, $applicationId]
            );
            return;
        }

        exec_stmt(
            $db,
            "UPDATE applications SET analysis_status = ? WHERE id = ?",
            "si",
            [$status, $applicationId]
        );
        return;
    }

    if ($status === "failed") {
        exec_stmt(
            $db,
            "UPDATE applications
             SET analysis_status = ?,
                 total_score = 0,
                 rank_no = NULL,
                 scored_at = NOW(),
                 scoring_diagnostics_json = ?
             WHERE id = ?",
            "ssi",
            [$status, application_analysis_json($diagnostics), $applicationId]
        );
        return;
    }

    exec_stmt(
        $db,
        "UPDATE applications
         SET analysis_status = ?, scoring_diagnostics_json = ?
         WHERE id = ?",
        "ssi",
        [$status, application_analysis_json($diagnostics), $applicationId]
    );
}

function analysis_failure_payload(string $stage, array $result): array
{
    return [
        "status" => "failed",
        "stage" => $stage,
        "code" => (string) ($result["code"] ?? "ANALYSIS_FAILED"),
        "message" => (string) ($result["message"] ?? "Application analysis failed"),
        "httpStatus" => isset($result["httpStatus"]) ? (int) $result["httpStatus"] : null,
    ];
}

function mark_resume_analysis_failure(
    mysqli $db,
    int $resumeId,
    string $code,
    string $message
): void {
    exec_stmt(
        $db,
        "UPDATE resumes
         SET parse_metadata_json = ?, parser_version = ?, parsing_status = 'failed'
         WHERE id = ?",
        "ssi",
        [
            application_analysis_json([
                "status" => "failed",
                "code" => $code,
                "message" => $message,
            ]),
            "resume-parsing-v1",
            $resumeId,
        ]
    );
}

function application_analysis_response(array $result): array
{
    $response = [
        "analysisStatus" => (string) ($result["status"] ?? "pending"),
        "resumeIds" => array_values(array_map("intval", $result["resumeIds"] ?? [])),
        "scoringRunId" => isset($result["runId"]) ? (int) $result["runId"] : null,
    ];

    if (isset($result["candidateId"])) {
        $response["candidateId"] = (int) $result["candidateId"];
    }

    if (isset($result["diagnostics"]) && is_array($result["diagnostics"])) {
        $response["analysisDiagnostics"] = $result["diagnostics"];
    }
    if (isset($result["code"])) {
        $response["analysisCode"] = (string) $result["code"];
    }
    return $response;
}

function score_persisted_application(
    mysqli $db,
    int $jobId,
    int $applicationId,
    array $resumeIds = [],
    bool $persistFailureStatus = true
): array {
    /**
     * Score the parsed profile already stored for the application. This stage
     * deliberately does not reopen or reparse the uploaded PDF.
     */
    set_application_analysis_status($db, $applicationId, "scoring");
    $result = request_candidate_scoring($jobId, $applicationId);
    $result["resumeIds"] = $resumeIds;

    if (($result["ok"] ?? false) !== true) {
        $isPending = ($result["status"] ?? "failed") === "pending";
        $details = $isPending
            ? [
                "status" => "pending",
                "stage" => "scoring",
                "code" => (string) ($result["code"] ?? "SCORING_NOT_CONFIGURED"),
                "message" => (string) ($result["message"] ?? "Candidate scoring is pending"),
            ]
            : analysis_failure_payload("scoring", $result);
        if ($isPending || $persistFailureStatus) {
            set_application_analysis_status($db, $applicationId, $isPending ? "pending" : "failed", $details);
        }
        return array_merge($result, $details, ["status" => $isPending ? "pending" : "failed"]);
    }

    set_application_analysis_status($db, $applicationId, "completed");
    return array_merge($result, ["status" => "completed"]);
}

/**
 * Parse every newly stored resume, then score once against the latest
 * persisted profile. No external call is made until all storage writes have
 * completed and the caller has returned from its DB persistence section.
 */
function process_candidate_application_analysis(
    mysqli $db,
    int $jobId,
    int $applicationId,
    ?int $candidateId,
    array $storedResumes,
    array $applicationData = [],
    bool $persistFailureStatus = true
): array {
    $resumeIds = array_values(array_map(
        static fn (array $resume): int => (int) ($resume["resumeId"] ?? 0),
        $storedResumes
    ));
    $resumeIds = array_values(array_filter($resumeIds, static fn (int $id): bool => $id > 0));

    if ($storedResumes === []) {
        set_application_analysis_status($db, $applicationId, "pending", [
            "status" => "pending",
            "stage" => "parsing",
            "code" => "RESUME_NOT_STORED",
            "message" => "No stored resume is available for parsing",
        ]);
        return ["status" => "pending", "resumeIds" => $resumeIds, "code" => "RESUME_NOT_STORED"];
    }

    set_application_analysis_status($db, $applicationId, "parsing");
    foreach ($storedResumes as $resume) {
        $localPath = (string) ($resume["localPath"] ?? "");
        if ($localPath === "" || !is_file($localPath)) {
            mark_resume_analysis_failure(
                $db,
                (int) ($resume["resumeId"] ?? 0),
                "RESUME_FILE_UNAVAILABLE",
                "The stored resume file is not available to the parser"
            );
            $failure = [
                "status" => "failed",
                "stage" => "parsing",
                "code" => "RESUME_FILE_UNAVAILABLE",
                "message" => "The stored resume file is not available to the parser",
            ];
            if ($persistFailureStatus) {
                set_application_analysis_status($db, $applicationId, "failed", $failure);
            }
            return array_merge($failure, ["resumeIds" => $resumeIds]);
        }

        $parseResult = parse_saved_resume_document(
            $db,
            (int) $resume["resumeId"],
            $applicationId,
            $candidateId,
            $localPath,
            (string) ($resume["originalName"] ?? "resume.pdf"),
            $applicationData
        );
        if (($parseResult["status"] ?? "failed") !== "parsed") {
            $status = ($parseResult["status"] ?? "failed") === "pending" ? "pending" : "failed";
            $details = $status === "pending"
                ? [
                    "status" => "pending",
                    "stage" => "parsing",
                    "code" => (string) ($parseResult["code"] ?? "PARSER_NOT_CONFIGURED"),
                    "message" => (string) ($parseResult["message"] ?? "Resume parsing is pending"),
                ]
                : analysis_failure_payload("parsing", $parseResult);
            if ($status === "pending" || $persistFailureStatus) {
                set_application_analysis_status($db, $applicationId, $status, $details);
            }
            return array_merge($parseResult, ["status" => $status, "resumeIds" => $resumeIds]);
        }
    }

    return score_persisted_application(
        $db,
        $jobId,
        $applicationId,
        $resumeIds,
        $persistFailureStatus
    );
}

function stored_resume_local_path(string $storedPath): ?string
{
    $basename = basename((string) parse_url($storedPath, PHP_URL_PATH));
    if ($basename === "" || $basename === "." || $basename === DIRECTORY_SEPARATOR) {
        return null;
    }

    $path = __DIR__ . DIRECTORY_SEPARATOR . ".." . DIRECTORY_SEPARATOR
        . "uploads" . DIRECTORY_SEPARATOR . "resumes" . DIRECTORY_SEPARATOR . $basename;
    $resolved = realpath($path);
    if ($resolved === false || !is_file($resolved)) {
        return null;
    }
    return $resolved;
}

function retry_application_analysis(mysqli $db, int $applicationId): void
{
    $application = row(
        $db,
        "SELECT job_id AS jobId, candidate_id AS candidateId
         FROM applications WHERE id = ? LIMIT 1",
        "i",
        [$applicationId]
    );
    if (!$application) {
        respond(["error" => "Application not found"], 404);
    }

    $resumes = rows(
        $db,
        "SELECT id AS resumeId, parsed_profile_json AS profileJson
         FROM resumes
         WHERE application_id = ?
         ORDER BY uploaded_at DESC, id DESC",
        "i",
        [$applicationId]
    );
    if ($resumes === []) {
        respond(["error" => "No stored resume is available for retry"], 422);
    }

    $input = input_data();
    $stage = strtolower(trim((string) ($input["stage"] ?? "all")));
    if (!in_array($stage, ["all", "parse", "score"], true)) {
        respond(["error" => "Retry stage must be all, parse, or score"], 422);
    }

    if ($stage === "score") {
        $hasPersistedProfile = false;
        foreach ($resumes as $resume) {
            if (trim((string) ($resume["profileJson"] ?? "")) !== "") {
                $hasPersistedProfile = true;
                break;
            }
        }
        if (!$hasPersistedProfile) {
            respond(["error" => "A persisted parsed profile is required for score-only retry"], 422);
        }
    }

    $queued = queue_application_analysis($db, $applicationId, $stage, "retry");
    if (($queued["active"] ?? false) === true) {
        respond(["error" => "Application analysis is already running"], 409);
    }

    $resumeIds = array_values(array_map(
        static fn(array $resume): int => (int) ($resume["resumeId"] ?? 0),
        $resumes
    ));
    $result = application_analysis_pending_result(
        $resumeIds,
        (int) ($application["candidateId"] ?? 0)
    );
    $result["requestedStage"] = $stage;
    $statusCode = 200;
    respond(array_merge(
        ["ok" => $statusCode === 200, "applicationId" => $applicationId],
        application_analysis_response($result)
    ), $statusCode);
}
