<?php
// Durable, lightweight background processor for candidate application analysis.

declare(strict_types=1);

if (PHP_SAPI !== "cli") {
    fwrite(STDERR, "The application analysis worker must run from the CLI.\n");
    exit(1);
}

set_time_limit(0);

require_once __DIR__ . "/helpers/response.php";
require_once __DIR__ . "/helpers/environment.php";
require_once __DIR__ . "/helpers/database_queries.php";
require_once __DIR__ . "/bootstrap.php";
require_once __DIR__ . "/helpers/resume_parser.php";
require_once __DIR__ . "/helpers/candidate_scoring.php";
require_once __DIR__ . "/helpers/application_analysis.php";

function analysis_worker_recover_stale(mysqli $db): void
{
    // Requeue claims left in parsing/scoring after a process crash or timeout;
    // the status transition keeps the durable queue recoverable without a new row.
    $stale = rows(
        $db,
        "SELECT id, analysis_status AS analysisStatus, scoring_diagnostics_json AS diagnosticsJson
         FROM applications
         WHERE analysis_status IN ('parsing', 'scoring')
           AND updated_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
         ORDER BY updated_at, id
         LIMIT 100"
    );

    foreach ($stale as $application) {
        $currentStatus = (string) ($application["analysisStatus"] ?? "parsing");
        $diagnostics = application_analysis_decode_diagnostics($application["diagnosticsJson"] ?? null);
        $worker = is_array($diagnostics["analysisWorker"] ?? null)
            ? $diagnostics["analysisWorker"]
            : [];
        $diagnostics["analysisWorker"] = array_merge(
            $worker,
            [
                "status" => "pending",
                "workerRunnable" => true,
                "requestedStage" => $currentStatus === "scoring" ? "score" : "all",
                "trigger" => "stale-recovery",
                "recoveredAt" => application_analysis_now(),
            ]
        );

        exec_stmt_affected_rows(
            $db,
            "UPDATE applications
             SET analysis_status = 'pending', scoring_diagnostics_json = ?
             WHERE id = ? AND analysis_status = ?
               AND updated_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE)",
            "sis",
            [
                application_analysis_json($diagnostics),
                (int) $application["id"],
                $currentStatus,
            ]
        );
    }
}

function analysis_worker_recover_unqueued(mysqli $db): void
{
    // Recover submissions whose DB writes completed but whose queue marker was
    // interrupted before the HTTP response returned.
    $pending = rows(
        $db,
        "SELECT a.id, a.scoring_diagnostics_json AS diagnosticsJson
         FROM applications a
         WHERE a.analysis_status = 'pending'
           AND a.updated_at < DATE_SUB(NOW(), INTERVAL 60 SECOND)
           AND EXISTS (SELECT 1 FROM resumes r WHERE r.application_id = a.id)
           AND EXISTS (SELECT 1 FROM application_documents d WHERE d.application_id = a.id)
         ORDER BY a.updated_at, a.id
         LIMIT 100"
    );

    foreach ($pending as $application) {
        $diagnostics = application_analysis_decode_diagnostics($application["diagnosticsJson"] ?? null);
        $worker = $diagnostics["analysisWorker"] ?? null;
        if (!is_array($worker) || ($worker["status"] ?? "") !== "awaiting_persistence") {
            continue;
        }

        try {
            queue_application_analysis($db, (int) $application["id"], "all", "queue-recovery");
        } catch (Throwable $error) {
            error_log("Application analysis queue recovery failed for application " . (int) $application["id"] . ": " . $error->getMessage());
        }
    }
}

function analysis_worker_target_application_id(): ?int
{
    global $argv;
    foreach ($argv as $index => $argument) {
        if ($argument !== "--application-id" || !isset($argv[$index + 1])) {
            continue;
        }
        $applicationId = (int) $argv[$index + 1];
        return $applicationId > 0 ? $applicationId : null;
    }
    return null;
}

function analysis_worker_next(mysqli $db, ?int $targetApplicationId = null): ?array
{
    // Select only persisted applications with both resume and document rows;
    // this prevents the worker from claiming a half-written submission.
    $where = "a.analysis_status = 'pending'
              AND EXISTS (SELECT 1 FROM resumes r WHERE r.application_id = a.id)
              AND EXISTS (SELECT 1 FROM application_documents d WHERE d.application_id = a.id)";
    $params = [];
    $types = "";
    if ($targetApplicationId !== null) {
        $where .= " AND a.id = ?";
        $params[] = $targetApplicationId;
        $types = "i";
    }
    $pending = rows(
        $db,
        "SELECT a.id, a.scoring_diagnostics_json AS diagnosticsJson
         FROM applications a
         WHERE {$where}
         ORDER BY a.submitted_at, a.id
         LIMIT 50",
        $types,
        $params
    );

    foreach ($pending as $application) {
        $diagnostics = application_analysis_decode_diagnostics($application["diagnosticsJson"] ?? null);
        if ($targetApplicationId === null && !analysis_worker_is_runnable($diagnostics)) {
            continue;
        }

        return [
            "applicationId" => (int) $application["id"],
            "stage" => analysis_worker_requested_stage($diagnostics),
        ];
    }

    return null;
}

function analysis_worker_context(mysqli $db, int $applicationId): ?array
{
    $application = row(
        $db,
        "SELECT
           a.job_id AS jobId,
           a.candidate_id AS candidateId,
           c.full_name AS fullName,
           c.email,
           c.phone,
           c.current_location AS currentLocation,
           c.current_cgpa AS currentCgpa,
           c.notice_period_days AS noticePeriodDays,
           c.languages_json AS languagesJson
         FROM applications a
         JOIN candidates c ON c.id = a.candidate_id
         WHERE a.id = ?
         LIMIT 1",
        "i",
        [$applicationId]
    );
    if (!$application) {
        return null;
    }

    $resumeRows = rows(
        $db,
        "SELECT
           id AS resumeId,
           original_file_name AS originalName,
           stored_file_path AS storedPath,
           parsing_status AS parsingStatus,
           parsed_profile_json AS profileJson
         FROM resumes
         WHERE application_id = ?
         ORDER BY uploaded_at, id",
        "i",
        [$applicationId]
    );

    $storedResumes = [];
    $resumeIds = [];
    $profileReady = false;
    foreach ($resumeRows as $resume) {
        $resumeId = (int) ($resume["resumeId"] ?? 0);
        if ($resumeId <= 0) {
            continue;
        }
        $resumeIds[] = $resumeId;
        if (trim((string) ($resume["profileJson"] ?? "")) !== "") {
            $profileReady = true;
        }
        $storedResumes[] = [
            "resumeId" => $resumeId,
            "originalName" => (string) ($resume["originalName"] ?? "resume.pdf"),
            "localPath" => stored_resume_local_path((string) ($resume["storedPath"] ?? "")),
        ];
    }

    $languages = json_decode((string) ($application["languagesJson"] ?? "[]"), true);
    $noticePeriodDays = $application["noticePeriodDays"] === null
        ? null
        : (int) $application["noticePeriodDays"];
    $applicationData = [
        "name" => (string) ($application["fullName"] ?? ""),
        "email" => (string) ($application["email"] ?? ""),
        "phone" => (string) ($application["phone"] ?? ""),
        "location" => (string) ($application["currentLocation"] ?? ""),
        "cgpa" => is_numeric($application["currentCgpa"] ?? null) && (float) $application["currentCgpa"] > 0
            ? (float) $application["currentCgpa"]
            : null,
        "noticePeriod" => $noticePeriodDays === null
            ? null
            : ($noticePeriodDays === 0 ? "Immediate" : $noticePeriodDays . " days"),
        "languages" => is_array($languages) ? $languages : [],
    ];

    return [
        "jobId" => (int) $application["jobId"],
        "candidateId" => (int) $application["candidateId"],
        "resumeIds" => $resumeIds,
        "profileReady" => $profileReady,
        "storedResumes" => $storedResumes,
        "applicationData" => $applicationData,
    ];
}

function analysis_worker_failure(string $stage, string $code, string $message): array
{
    return [
        "status" => "failed",
        "stage" => $stage,
        "code" => $code,
        "message" => $message,
    ];
}

function analysis_worker_run_one(mysqli $db, int $applicationId, string $stage): bool
{
    if (!claim_application_analysis($db, $applicationId, $stage)) {
        return false;
    }

    $claimedDiagnostics = application_analysis_diagnostics($db, $applicationId);
    $claimedWorker = is_array($claimedDiagnostics["analysisWorker"] ?? null)
        ? $claimedDiagnostics["analysisWorker"]
        : [];
    $automaticRetryCount = max(0, (int) ($claimedWorker["automaticRetryCount"] ?? 0));
    $startedAt = microtime(true);
    $context = analysis_worker_context($db, $applicationId);
    try {
        if ($context === null) {
            $result = analysis_worker_failure(
                $stage,
                "APPLICATION_NOT_FOUND",
                "The application disappeared before background analysis started"
            );
            set_application_analysis_status($db, $applicationId, "failed", $result);
        } elseif ($stage === "score" && !$context["profileReady"]) {
            $result = analysis_worker_failure(
                "scoring",
                "PARSED_PROFILE_NOT_AVAILABLE",
                "Score-only analysis requires a persisted parsed profile"
            );
            set_application_analysis_status($db, $applicationId, "failed", $result);
        } elseif ($stage === "score") {
            $result = score_persisted_application(
                $db,
                (int) $context["jobId"],
                $applicationId,
                $context["resumeIds"],
                false
            );
        } else {
            $result = process_candidate_application_analysis(
                $db,
                (int) $context["jobId"],
                $applicationId,
                (int) $context["candidateId"],
                $context["storedResumes"],
                $context["applicationData"],
                false
            );
        }
    } catch (Throwable $error) {
        $result = analysis_worker_failure(
            $stage,
            "BACKGROUND_ANALYSIS_EXCEPTION",
            "Background analysis failed before completion"
        );
        set_application_analysis_status($db, $applicationId, "failed", $result);
        error_log("Background analysis exception for application {$applicationId}: " . $error->getMessage());
    }

    $status = (string) ($result["status"] ?? "failed");
    $durationMs = (int) round((microtime(true) - $startedAt) * 1000);
    $automaticRetryStage = application_analysis_automatic_retry_stage($result, $automaticRetryCount);
    record_analysis_worker_diagnostics($db, $applicationId, [
        "status" => $status,
        "workerRunnable" => false,
        "completedAt" => application_analysis_now(),
        "durationMs" => $durationMs,
        "lastCode" => (string) ($result["code"] ?? ""),
        "lastFailureStage" => $status === "failed" ? (string) ($result["stage"] ?? $stage) : null,
        "lastHttpStatus" => isset($result["httpStatus"]) ? (int) $result["httpStatus"] : null,
        "automaticRetryCount" => $automaticRetryCount,
        "automaticRetryLimit" => application_analysis_automatic_retry_limit(),
        "automaticRetryScheduled" => false,
    ]);

    error_log("Background analysis application={$applicationId} stage={$stage} status={$status} durationMs={$durationMs}");
    if ($automaticRetryStage !== null) {
        try {
            $queued = queue_application_analysis(
                $db,
                $applicationId,
                $automaticRetryStage,
                "automatic-retry"
            );
            if (($queued["queued"] ?? false) === true) {
                error_log(
                    "Background analysis automatic retry scheduled application={$applicationId}"
                    . " stage={$automaticRetryStage} attempt=" . ($automaticRetryCount + 1)
                );
            } else {
                record_analysis_worker_diagnostics($db, $applicationId, [
                    "automaticRetryScheduled" => false,
                    "automaticRetryScheduleFailedAt" => application_analysis_now(),
                ]);
                set_application_analysis_status($db, $applicationId, "failed");
                error_log("Background analysis automatic retry could not be scheduled application={$applicationId}");
            }
        } catch (Throwable $error) {
            record_analysis_worker_diagnostics($db, $applicationId, [
                "automaticRetryScheduled" => false,
                "automaticRetryScheduleFailedAt" => application_analysis_now(),
            ]);
            set_application_analysis_status($db, $applicationId, "failed");
            error_log(
                "Background analysis automatic retry scheduling failed application={$applicationId}: "
                . $error->getMessage()
            );
        }
    } elseif ($status === "failed") {
        set_application_analysis_status($db, $applicationId, "failed");
    }
    return true;
}

try {
    /** @var mysqli $mysqli */
    analysis_worker_recover_stale($mysqli);
    analysis_worker_recover_unqueued($mysqli);
    $next = analysis_worker_next($mysqli, analysis_worker_target_application_id());
    if ($next !== null) {
        analysis_worker_run_one(
            $mysqli,
            (int) $next["applicationId"],
            (string) $next["stage"]
        );
    }
} catch (Throwable $error) {
    error_log("Application analysis worker cycle failed: " . $error->getMessage());
    exit(1);
}
