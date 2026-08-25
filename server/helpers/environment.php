<?php
// Loads local and hosted environment settings.

declare(strict_types=1);

function load_local_environment(string $path): void
{
    // Local secrets stay outside tracked source files.
    if (!is_file($path) || !is_readable($path)) {
        return;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return;
    }

    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === "" || str_starts_with($line, "#") || !str_contains($line, "=")) {
            continue;
        }

        [$name, $value] = array_map("trim", explode("=", $line, 2));
        if ($name === "" || getenv($name) !== false) {
            continue;
        }

        if (
            strlen($value) >= 2
            && (($value[0] === '"' && $value[strlen($value) - 1] === '"')
                || ($value[0] === "'" && $value[strlen($value) - 1] === "'"))
        ) {
            $value = substr($value, 1, -1);
        }

        putenv("{$name}={$value}");
        $_ENV[$name] = $value;
    }
}

function environment_value(string $name, ?string $default = null): ?string
{
    $value = getenv($name);
    if ($value === false || trim((string) $value) === "") {
        $value = $_ENV[$name] ?? $_SERVER[$name] ?? null;
    }

    if (!is_string($value)) {
        return $default;
    }

    $value = trim($value);
    return $value !== "" ? $value : $default;
}

function configure_api_headers(): void
{
    // Return CORS only for origins listed by the current environment.
    $allowedOrigins = array_values(array_filter(array_map(
        "trim",
        explode(",", environment_value("CORS_ORIGINS", "*") ?? "*")
    )));
    $requestOrigin = trim((string) ($_SERVER["HTTP_ORIGIN"] ?? ""));

    if (in_array("*", $allowedOrigins, true)) {
        header("Access-Control-Allow-Origin: *");
    } elseif ($requestOrigin !== "" && in_array($requestOrigin, $allowedOrigins, true)) {
        header("Access-Control-Allow-Origin: {$requestOrigin}");
        header("Vary: Origin");
    }

    header("Access-Control-Allow-Headers: Content-Type, Authorization");
    header("Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS");
    header("Content-Type: application/json");
}

function database_configuration(): array
{
    // Railway MYSQL values are fallback names for hosted deployment.
    return [
        "host" => environment_value("DB_HOST", environment_value("MYSQLHOST", "127.0.0.1")),
        "port" => (int) (environment_value("DB_PORT", environment_value("MYSQLPORT", "3306")) ?? "3306"),
        "user" => environment_value("DB_USER", environment_value("MYSQLUSER", "root")),
        "password" => environment_value("DB_PASSWORD", environment_value("MYSQLPASSWORD", "")),
        "database" => environment_value(
            "DB_NAME",
            environment_value("MYSQLDATABASE", "uwc_hr_decision_support")
        ),
        "sslCa" => environment_value("DB_SSL_CA"),
        "sslVerify" => strtolower(environment_value("DB_SSL_VERIFY", "false") ?? "false") === "true",
    ];
}

load_local_environment(dirname(__DIR__) . DIRECTORY_SEPARATOR . ".env.local");
