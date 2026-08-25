<?php

declare(strict_types=1);

require_once dirname(__DIR__) . "/helpers/response.php";
require_once dirname(__DIR__) . "/helpers/environment.php";
require_once dirname(__DIR__) . "/helpers/resume_parser.php";
require_once dirname(__DIR__) . "/helpers/candidate_scoring.php";
require_once dirname(__DIR__) . "/helpers/application_analysis.php";

function assert_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

foreach (["pending", "parsing", "scoring", "completed", "failed"] as $status) {
    assert_true(
        application_analysis_status_is_valid($status),
        "{$status} must be a valid application analysis status"
    );
}
assert_true(
    !application_analysis_status_is_valid("eligible"),
    "Eligibility values must not be reused as analysis statuses"
);

$initialDiagnostics = application_analysis_decode_diagnostics(application_analysis_initial_diagnostics_json());
$initialWorker = $initialDiagnostics["analysisWorker"] ?? [];
assert_true(($initialWorker["automaticRetryCount"] ?? null) === 0, "New analysis must start with no automatic retry used");
assert_true(($initialWorker["automaticRetryLimit"] ?? null) === 1, "New analysis must persist the one-retry limit");
assert_true(($initialWorker["automaticRetryScheduled"] ?? null) === false, "New analysis must not start as an automatic retry");

foreach ([0, 408, 425, 429, 499, 500, 502, 599] as $httpStatus) {
    assert_true(
        application_analysis_transient_http_status($httpStatus),
        "HTTP {$httpStatus} must be treated as a transient analysis transport status"
    );
}
foreach ([400, 401, 404, 409, 422, 600] as $httpStatus) {
    assert_true(
        !application_analysis_transient_http_status($httpStatus),
        "HTTP {$httpStatus} must remain a permanent analysis failure"
    );
}
assert_true(
    !application_analysis_transient_http_status(null),
    "A missing HTTP status must not be retried automatically"
);

$parserRetry = [
    "status" => "failed",
    "stage" => "parsing",
    "code" => "PARSER_REQUEST_FAILED",
    "httpStatus" => 502,
];
$scoringRetry = [
    "status" => "failed",
    "stage" => "scoring",
    "code" => "SCORING_REQUEST_FAILED",
    "httpStatus" => 0,
];
assert_true(
    application_analysis_automatic_retry_stage($parserRetry, 0) === "all",
    "A transient parser failure must retry the full analysis flow"
);
assert_true(
    application_analysis_automatic_retry_stage($scoringRetry, 0) === "score",
    "A transient scoring failure must retry scoring without reparsing"
);
assert_true(
    application_analysis_automatic_retry_stage($parserRetry, 1) === null,
    "The automatic retry budget must stop a second retry"
);
assert_true(
    application_analysis_automatic_retry_stage(array_merge($parserRetry, ["status" => "pending"]), 0) === null,
    "Pending configuration work must not be treated as a failed transient attempt"
);
assert_true(
    application_analysis_automatic_retry_stage(array_merge($parserRetry, ["httpStatus" => 422]), 0) === null,
    "A permanent parser response must not be retried"
);
assert_true(
    application_analysis_automatic_retry_stage([
        "status" => "failed",
        "stage" => "parsing",
        "code" => "PARSER_INVALID_RESPONSE",
        "httpStatus" => 502,
    ], 0) === null,
    "Only the explicit parser transport failure code may be retried"
);
assert_true(
    application_analysis_automatic_retry_stage([
        "status" => "failed",
        "stage" => "scoring",
        "code" => "SCORING_REQUEST_UNAVAILABLE",
    ], 0) === null,
    "Local scoring runtime/configuration failures must not be retried"
);

$workerRetryState = ["automaticRetryCount" => 0];
assert_true(
    application_analysis_automatic_retry_count_for_queue($workerRetryState, "automatic-retry") === 1,
    "Scheduling the automatic retry must consume its one-attempt budget"
);
assert_true(
    application_analysis_automatic_retry_count_for_queue(["automaticRetryCount" => 1], "automatic-retry") === 1,
    "The persisted automatic retry counter must be capped at one"
);
assert_true(
    application_analysis_automatic_retry_count_for_queue(["automaticRetryCount" => 1], "retry") === 0,
    "An explicit manual retry must start with a fresh automatic retry budget"
);
assert_true(
    application_analysis_automatic_retry_count_for_queue(["automaticRetryCount" => 1], "stale-recovery") === 1,
    "Crash recovery must preserve the automatic retry budget"
);

$response = application_analysis_response([
    "status" => "completed",
    "resumeIds" => [41, "42"],
    "runId" => 77,
    "diagnostics" => [
        "qwenUsed" => true,
        "fallbackUsed" => false,
    ],
]);
assert_true($response["analysisStatus"] === "completed", "Analysis response must expose the final status");
assert_true($response["resumeIds"] === [41, 42], "Analysis response must normalize resume IDs");
assert_true($response["scoringRunId"] === 77, "Analysis response must expose the scoring run ID");
assert_true($response["analysisDiagnostics"]["qwenUsed"] === true, "Analysis diagnostics must be preserved");

putenv("RESUME_PARSING_API_URL=https://parser.example/api/resume/parse");
putenv("CANDIDATE_SCORING_API_URL");
assert_true(
    candidate_scoring_endpoint() === "https://parser.example/api/scoring/candidate",
    "Candidate scoring must derive its route from the shared parser service"
);

putenv("CANDIDATE_SCORING_API_URL=https://scoring.example/api/scoring/candidate");
assert_true(
    candidate_scoring_endpoint() === "https://scoring.example/api/scoring/candidate",
    "An explicit scoring URL must take precedence"
);

$apiSource = file_get_contents(dirname(__DIR__) . "/api.php");
$analysisSource = file_get_contents(dirname(__DIR__) . "/helpers/application_analysis.php");
$migrationSource = file_get_contents(dirname(__DIR__, 2) . "/database/migrations/2026-08-10-application-analysis-status.sql");
assert_true(is_string($apiSource), "The API source must be readable");
assert_true(is_string($analysisSource), "The analysis coordinator must be readable");
assert_true(is_string($migrationSource), "The analysis migration must be readable");

$submitStart = strpos($apiSource, "function submit_application");
$replaceStart = strpos($apiSource, "function replace_existing_application");
assert_true($submitStart !== false && $replaceStart !== false && $replaceStart > $submitStart, "Submission handler boundaries must be present");
$submitSource = substr($apiSource, $submitStart, $replaceStart - $submitStart);
$storageCall = strpos($submitSource, "save_uploaded_documents(");
$queueCall = strpos($submitSource, "queue_application_analysis(");
assert_true($storageCall !== false && $queueCall !== false && $storageCall < $queueCall, "Resume storage must precede background queueing");
assert_true(!str_contains($submitSource, "process_candidate_application_analysis("), "Submission must not execute external analysis synchronously");
assert_true(str_contains($submitSource, "analysis_status, total_score, ai_summary"), "New applications must begin in pending analysis state");
assert_true(!str_contains($submitSource, "create_score_breakdown("), "Submission must not create a placeholder score breakdown");
assert_true(str_contains($submitSource, "eligibility_status, analysis_status, total_score, ai_summary"), "Submission must persist pending eligibility before analysis");
assert_true(str_contains($submitSource, "application_analysis_pending_result"), "Submission must return a pending analysis response");

$parseCall = strpos($analysisSource, "parse_saved_resume_document(");
$scoreCall = strpos($analysisSource, "return score_persisted_application(");
assert_true($parseCall !== false && $scoreCall !== false && $parseCall < $scoreCall, "Scoring must follow persisted resume parsing");
assert_true(str_contains($analysisSource, 'if ($stage === "score")'), "Retry must support score-only retries");
assert_true(str_contains($analysisSource, '["all", "parse", "score"]'), "Retry must support full retries");
assert_true(str_contains($analysisSource, "resumeIds"), "Retry responses must identify the reused resume");
$retryStart = strpos($analysisSource, "function retry_application_analysis");
$scoreBranch = strpos($analysisSource, 'if ($stage === "score")', $retryStart === false ? 0 : $retryStart);
assert_true($scoreBranch !== false, "Retry must validate score-only prerequisites before queueing");
assert_true(str_contains(substr($analysisSource, $retryStart), "queue_application_analysis"), "Retry must queue work instead of blocking on analysis");

$workerSource = file_get_contents(dirname(__DIR__) . "/application_analysis_worker.php");
assert_true(is_string($workerSource), "The application analysis worker must be readable");
$workerParseCall = strpos($workerSource, "process_candidate_application_analysis(");
$workerScoreCall = strpos($workerSource, "score_persisted_application(");
assert_true($workerParseCall !== false && $workerScoreCall !== false, "The worker must reuse parsing and scoring orchestration");
assert_true(str_contains($workerSource, "claim_application_analysis"), "The worker must claim applications atomically");
assert_true(str_contains($workerSource, "analysis_worker_recover_stale"), "The worker must recover stale processing records");
assert_true(str_contains($workerSource, "application_analysis_automatic_retry_stage"), "The worker must classify failed attempts before automatic retry");
assert_true(str_contains($workerSource, '"automatic-retry"'), "The worker must use the dedicated automatic retry trigger");
assert_true(str_contains($analysisSource, '$persistFailureStatus'), "Worker orchestration must be able to defer the final failed state until retry policy is evaluated");

assert_true(!preg_match("/\\b(DROP|TRUNCATE|RENAME)\\b/i", $migrationSource), "Analysis migration must not contain destructive DDL");
assert_true(str_contains($migrationSource, "ADD COLUMN analysis_status"), "Analysis migration must add only the analysis status field");
assert_true(str_contains($migrationSource, "ADD INDEX idx_applications_analysis_status"), "Analysis migration must index analysis status");

$jobCandidatesStart = strpos($apiSource, "function job_candidates");
assert_true($jobCandidatesStart !== false, "The job candidates route must remain present");
$jobCandidatesSource = substr($apiSource, $jobCandidatesStart);
assert_true(str_contains($jobCandidatesSource, "a.eligibility_reasons_json AS eligibilityReasonsJson"), "Candidate responses must expose persisted eligibility reasons");
assert_true(str_contains($jobCandidatesSource, "resume.parsed_profile_json AS profileJson"), "Candidate responses must read the persisted parsed profile");
assert_true(str_contains($jobCandidatesSource, '$candidate["scoreBreakdown"]'), "Candidate responses must expose persisted score breakdowns");
assert_true(str_contains($jobCandidatesSource, '$candidate["parsedProfile"]'), "Candidate responses must expose parsed profile data");
assert_true(str_contains($jobCandidatesSource, '$candidate["filteredOut"]'), "Candidate responses must expose filtered-out state");

fwrite(STDOUT, "Application analysis contract tests passed.\n");
