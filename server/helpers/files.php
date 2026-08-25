<?php
// Builds public file links and normalises uploads.

declare(strict_types=1);

function request_scheme(): string
{
    // Hosted proxies pass the original scheme in this header.
    $forwardedProto = strtolower(trim(explode(
        ",",
        (string) ($_SERVER["HTTP_X_FORWARDED_PROTO"] ?? "")
    )[0]));
    if (in_array($forwardedProto, ["http", "https"], true)) {
        return $forwardedProto;
    }

    return (!empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off") ? "https" : "http";
}

function public_api_base_url(): string
{
    // A fixed public URL avoids local Apache paths in online file links.
    $configuredBaseUrl = function_exists("environment_value")
        ? environment_value("PUBLIC_API_BASE_URL")
        : null;
    if ($configuredBaseUrl) {
        return rtrim($configuredBaseUrl, "/");
    }

    $host = (string) ($_SERVER["HTTP_HOST"] ?? "localhost");
    $basePath = rtrim(str_replace(
        "\\",
        "/",
        dirname((string) ($_SERVER["SCRIPT_NAME"] ?? "/uwc-hr-api/api.php"))
    ), "/");

    return request_scheme() . "://{$host}{$basePath}";
}

function public_file_url(string $path): string
{
    if ($path === "" || preg_match("#^https?://#i", $path)) {
        return $path;
    }

    return public_api_base_url() . (substr($path, 0, 1) === "/" ? $path : "/{$path}");
}

function normalize_uploaded_files(array $fileInput): array
{
    // PHP uses a different shape when one field uploads many files.
    if (!isset($fileInput["name"]) || !is_array($fileInput["name"])) {
        return [$fileInput];
    }

    $files = [];
    foreach ($fileInput["name"] as $index => $name) {
        $files[] = [
            "name" => $name,
            "type" => $fileInput["type"][$index] ?? "",
            "tmp_name" => $fileInput["tmp_name"][$index] ?? "",
            "error" => $fileInput["error"][$index] ?? UPLOAD_ERR_NO_FILE,
            "size" => $fileInput["size"][$index] ?? 0,
        ];
    }

    return $files;
}
