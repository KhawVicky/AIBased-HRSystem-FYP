<?php

declare(strict_types=1);

require_once dirname(__DIR__) . "/helpers/environment.php";
require_once dirname(__DIR__) . "/helpers/surface.php";
require_once dirname(__DIR__) . "/helpers/files.php";

function assert_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

assert_true(
    candidate_surface_route_allowed("GET", ["career", "jobs"]),
    "Career jobs must be public"
);
assert_true(
    candidate_surface_route_allowed("POST", ["apply", "JOB-001"]),
    "Candidate applications must be public"
);
assert_true(
    candidate_surface_route_allowed("PATCH", ["candidate", "applications", "12", "withdraw"]),
    "Candidates must be able to withdraw their own applications"
);
assert_true(
    candidate_surface_route_allowed("POST", ["employment-form", "submissions"]),
    "Candidate employment form submission must be public"
);
assert_true(
    !candidate_surface_route_allowed("GET", ["jobs"]),
    "Internal job management must not be public"
);
assert_true(
    !candidate_surface_route_allowed("POST", ["users"]),
    "User management must not be public"
);
assert_true(
    !candidate_surface_route_allowed("GET", ["employment-form", "submissions"]),
    "Internal employment form submissions must not be public"
);

putenv("API_SURFACE=candidate");
assert_true(
    !api_surface_route_allowed("GET", ["jobs"]),
    "Candidate API surface must enforce the public route allowlist"
);
putenv("API_SURFACE=full");
assert_true(
    api_surface_route_allowed("GET", ["jobs"]),
    "Local full API surface must preserve internal routes"
);

putenv("DB_HOST=railway.example");
putenv("DB_PORT=20444");
putenv("DB_USER=uwc");
putenv("DB_PASSWORD=test-only");
putenv("DB_NAME=railway");
$config = database_configuration();

assert_true($config["host"] === "railway.example", "DB_HOST must be configurable");
assert_true($config["port"] === 20444, "DB_PORT must be configurable");
assert_true($config["user"] === "uwc", "DB_USER must be configurable");
assert_true($config["database"] === "railway", "DB_NAME must be configurable");

putenv("PUBLIC_API_BASE_URL");
$_SERVER["HTTP_X_FORWARDED_PROTO"] = "https";
$_SERVER["HTTP_HOST"] = "candidate-api.example";
$_SERVER["SCRIPT_NAME"] = "/api.php";
assert_true(
    public_file_url("/uploads/resumes/example.pdf")
        === "https://candidate-api.example/uploads/resumes/example.pdf",
    "Forwarded HTTPS must be preserved in uploaded file URLs"
);

putenv("PUBLIC_API_BASE_URL=https://api.uwc.example");
assert_true(
    public_file_url("/uploads/resumes/example.pdf")
        === "https://api.uwc.example/uploads/resumes/example.pdf",
    "PUBLIC_API_BASE_URL must override proxy-derived URLs"
);

fwrite(STDOUT, "Deployment configuration tests passed.\n");
