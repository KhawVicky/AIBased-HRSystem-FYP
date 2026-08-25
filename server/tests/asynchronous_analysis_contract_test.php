<?php

declare(strict_types=1);

function assert_async_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

$apiSource = file_get_contents(dirname(__DIR__) . "/api.php");
$workerSource = file_get_contents(dirname(__DIR__) . "/application_analysis_worker.php");
$entrypointSource = file_get_contents(dirname(__DIR__, 2) . "/deploy/railway/candidate-api/entrypoint.sh");
$candidateDockerfile = file_get_contents(dirname(__DIR__, 2) . "/deploy/railway/candidate-api/Dockerfile");
$hrDockerfile = file_get_contents(dirname(__DIR__, 2) . "/deploy/railway/hr-api/Dockerfile");

assert_async_true(is_string($apiSource), "API source must be readable");
assert_async_true(is_string($workerSource), "Worker source must be readable");
assert_async_true(is_string($entrypointSource), "Candidate entrypoint must be readable");
assert_async_true(is_string($candidateDockerfile), "Candidate Dockerfile must be readable");
assert_async_true(is_string($hrDockerfile), "HR Dockerfile must be readable");

$submitStart = strpos($apiSource, "function submit_application");
$replaceStart = strpos($apiSource, "function replace_existing_application");
assert_async_true($submitStart !== false && $replaceStart !== false && $replaceStart > $submitStart, "Submission function boundaries must remain explicit");
$submitSource = substr($apiSource, $submitStart, $replaceStart - $submitStart);

assert_async_true(str_contains($submitSource, "analysis_status, total_score, ai_summary, scoring_diagnostics_json"), "Submission must persist the worker queue marker");
assert_async_true(str_contains($submitSource, "application_analysis_initial_diagnostics_json"), "Submission must mark persistence as incomplete before document writes finish");
assert_async_true(str_contains($submitSource, 'queue_application_analysis($db, $applicationId, "all", "submission")'), "Submission must enqueue after persistence");
assert_async_true(str_contains($submitSource, "application_analysis_pending_result"), "Submission must return before analysis completion");
assert_async_true(!str_contains($submitSource, "parse_saved_resume_document("), "Submission must not call the parser");
assert_async_true(!str_contains($submitSource, "request_candidate_scoring("), "Submission must not call the scorer");

assert_async_true(str_contains($workerSource, "PHP_SAPI !== \"cli\""), "Background analysis must run in a CLI worker");
assert_async_true(str_contains($workerSource, "analysis_worker_next"), "Worker must load queued applications from the database");
assert_async_true(str_contains($workerSource, "--application-id"), "Worker must support targeted CLI diagnostics");
assert_async_true(str_contains($workerSource, "analysis_worker_run_one"), "Worker must execute one claimed application independently");
assert_async_true(str_contains($workerSource, "process_candidate_application_analysis("), "Worker must reuse the existing full analysis flow");
assert_async_true(str_contains($workerSource, "score_persisted_application("), "Worker must reuse the existing score-only flow");
assert_async_true(str_contains($workerSource, "PARSED_PROFILE_NOT_AVAILABLE"), "Worker must reject score-only execution without persisted profile data");
assert_async_true(str_contains($workerSource, "application_analysis_automatic_retry_stage"), "Worker must apply the automatic retry policy after a failed attempt");
assert_async_true(str_contains($workerSource, '"automatic-retry"'), "Worker must persist a distinct automatic retry trigger");
assert_async_true(str_contains($workerSource, '"automaticRetryCount"'), "Worker must restore the persisted retry count after stage diagnostics are replaced");
assert_async_true(str_contains($workerSource, 'set_application_analysis_status($db, $applicationId, "failed")'), "Worker must expose failed only when retry is not scheduled or scheduling fails");

assert_async_true(str_contains($entrypointSource, "application_analysis_worker.php --once"), "Railway entrypoint must start the worker loop");
assert_async_true(str_contains($entrypointSource, "apache2-foreground &"), "Apache must run independently of the worker loop");
assert_async_true(str_contains($entrypointSource, "APPLICATION_ANALYSIS_WORKER_ENABLED"), "Worker startup must be environment-controlled");
assert_async_true(str_contains($candidateDockerfile, "APPLICATION_ANALYSIS_WORKER_ENABLED=true"), "Candidate API must enable the worker");
assert_async_true(str_contains($hrDockerfile, "APPLICATION_ANALYSIS_WORKER_ENABLED=false"), "HR API must not start a duplicate candidate worker");

fwrite(STDOUT, "Asynchronous analysis contract tests passed.\n");
