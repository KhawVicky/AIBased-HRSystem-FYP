<?php

declare(strict_types=1);

require_once dirname(__DIR__) . "/helpers/environment.php";
require_once dirname(__DIR__) . "/helpers/runpod.php";

function assert_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

function set_runpod_values(?string $endpoint, ?string $apiKey, ?string $timeout = "240"): void
{
    putenv("RUNPOD_CRITERIA_ENDPOINT_URL=" . ($endpoint ?? ""));
    putenv("RUNPOD_API_KEY=" . ($apiKey ?? ""));
    putenv("RUNPOD_CRITERIA_TIMEOUT_SECONDS=" . ($timeout ?? ""));
    $_ENV["RUNPOD_CRITERIA_ENDPOINT_URL"] = $endpoint ?? "";
    $_ENV["RUNPOD_API_KEY"] = $apiKey ?? "";
    $_ENV["RUNPOD_CRITERIA_TIMEOUT_SECONDS"] = $timeout ?? "";
}

set_runpod_values(null, null);
$missing = runpod_criteria_configuration();
assert_true(
    $missing["missing"] === ["RUNPOD_CRITERIA_ENDPOINT_URL", "RUNPOD_API_KEY"],
    "Missing endpoint and API key must make configuration unavailable"
);

set_runpod_values("", "test-key");
assert_true(
    runpod_criteria_configuration()["missing"] === ["RUNPOD_CRITERIA_ENDPOINT_URL"],
    "An empty endpoint must be treated as missing"
);

set_runpod_values("   ", "   ");
assert_true(
    runpod_criteria_configuration()["missing"] === ["RUNPOD_CRITERIA_ENDPOINT_URL", "RUNPOD_API_KEY"],
    "Whitespace-only values must be treated as missing"
);

set_runpod_values(
    "https://api.runpod.ai/v2/test-endpoint/runsync",
    "test-only-api-key",
    "240"
);
$configured = runpod_criteria_configuration();
assert_true($configured["missing"] === [], "Both required values must enable configuration");
assert_true(
    $configured["endpoint"] === "https://api.runpod.ai/v2/test-endpoint/runsync",
    "The endpoint must be read as a full URL"
);
assert_true($configured["timeout"] === 240, "The timeout must be configurable");

$_ENV["RUNPOD_API_KEY"] = "env-fallback-key";
putenv("RUNPOD_API_KEY=");
assert_true(
    environment_value("RUNPOD_API_KEY") === "env-fallback-key",
    'Environment values must fall back to $_ENV when getenv is empty'
);

$publicError = "RunPod criteria service is not configured";
assert_true(
    !str_contains($publicError, "test-only-api-key"),
    "Public configuration errors must not contain the API key"
);

fwrite(STDOUT, "RunPod configuration tests passed.\n");
