<?php
// Opens the shared database connection.

declare(strict_types=1);

require_once __DIR__ . "/helpers/environment.php";

$databaseConfig = database_configuration();
$mysqli = mysqli_init();
if (!$mysqli) {
    respond(["error" => "Database connection could not be initialized"], 500);
}

$connectionFlags = 0;
$databaseHost = strtolower(trim((string) $databaseConfig["host"], "[]"));
$isLocalDatabase = in_array($databaseHost, ["localhost", "127.0.0.1", "::1"], true);
// Compress larger result sets when the database is hosted remotely.
if (!$isLocalDatabase) {
    $connectionFlags |= MYSQLI_CLIENT_COMPRESS;
}

// Enable TLS when a hosted database provides a CA file.
if ($databaseConfig["sslCa"]) {
    $mysqli->ssl_set(null, null, $databaseConfig["sslCa"], null, null);
    if ($databaseConfig["sslVerify"] && defined("MYSQLI_CLIENT_SSL_VERIFY_SERVER_CERT")) {
        $connectionFlags |= MYSQLI_CLIENT_SSL_VERIFY_SERVER_CERT;
    } else {
        $connectionFlags |= MYSQLI_CLIENT_SSL;
    }
}

// Use the same connection code for local and hosted databases.
try {
    $connected = $mysqli->real_connect(
        $databaseConfig["host"],
        $databaseConfig["user"],
        $databaseConfig["password"],
        $databaseConfig["database"],
        $databaseConfig["port"],
        null,
        $connectionFlags
    );
} catch (mysqli_sql_exception $error) {
    respond(["error" => "Database connection failed", "detail" => $error->getMessage()], 500);
}

if (!$connected || $mysqli->connect_errno) {
    respond(["error" => "Database connection failed", "detail" => $mysqli->connect_error], 500);
}

$mysqli->set_charset("utf8mb4");
