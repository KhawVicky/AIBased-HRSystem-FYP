<?php
// Limits routes exposed by the candidate API.

declare(strict_types=1);

function candidate_surface_route_allowed(string $method, array $segments): bool
{
    // Keep internal HR routes out of the public deployment.
    if ($method === "GET" && $segments === ["health"]) {
        return true;
    }

    if (
        $method === "POST"
        && in_array($segments, [
            ["candidate-auth", "register"],
            ["candidate-auth", "login"],
            ["candidate-auth", "logout"],
            ["candidate-auth", "password-reset", "request"],
            ["candidate-auth", "password-reset", "confirm"],
            ["employment-form", "submissions"],
        ], true)
    ) {
        return true;
    }

    if (
        ($method === "GET" && in_array($segments, [
            ["candidate", "me"],
            ["candidate", "applications"],
            ["career", "jobs"],
        ], true))
        || ($method === "PATCH" && in_array($segments, [
            ["candidate", "profile"],
            ["candidate", "password"],
        ], true))
    ) {
        return true;
    }

    if (
        $method === "GET"
        && count($segments) === 3
        && $segments[0] === "career"
        && $segments[1] === "jobs"
        && $segments[2] !== ""
    ) {
        return true;
    }

    if (
        $method === "GET"
        && count($segments) === 3
        && $segments[0] === "candidate"
        && $segments[1] === "applications"
        && ctype_digit($segments[2])
    ) {
        return true;
    }

    if (
        $method === "PATCH"
        && count($segments) === 4
        && $segments[0] === "candidate"
        && $segments[1] === "applications"
        && ctype_digit($segments[2])
        && $segments[3] === "withdraw"
    ) {
        return true;
    }

    return in_array($method, ["GET", "POST"], true)
        && count($segments) === 2
        && $segments[0] === "apply"
        && $segments[1] !== "";
}

function api_surface_route_allowed(string $method, array $segments): bool
{
    $surface = strtolower(environment_value("API_SURFACE", "full") ?? "full");
    return $surface !== "candidate" || candidate_surface_route_allowed($method, $segments);
}
