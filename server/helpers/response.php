<?php
// Reads request data and sends JSON responses.

declare(strict_types=1);

function input_json(): array
{
    $raw = file_get_contents("php://input");
    if (!$raw) {
        return [];
    }

    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

function input_data(): array
{
    // File uploads use form fields while normal requests use JSON.
    $contentType = (string) ($_SERVER["CONTENT_TYPE"] ?? "");
    if (stripos($contentType, "multipart/form-data") !== false) {
        return $_POST;
    }

    return input_json();
}

function respond(array $data, int $status = 200): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}
