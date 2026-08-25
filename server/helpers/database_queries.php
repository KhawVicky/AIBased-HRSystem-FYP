<?php
// Shared prepared-statement helpers used by the HTTP API and CLI workers.

declare(strict_types=1);

function rows(mysqli $db, string $sql, string $types = "", array $params = []): array
{
    $stmt = $db->prepare($sql);
    if (!$stmt) {
        throw new RuntimeException($db->error);
    }

    if ($types !== "") {
        $stmt->bind_param($types, ...$params);
    }

    if (!$stmt->execute()) {
        throw new RuntimeException($stmt->error);
    }

    $result = $stmt->get_result();
    $values = $result ? $result->fetch_all(MYSQLI_ASSOC) : [];
    $stmt->close();
    return $values;
}

function row_sets(mysqli $db, array $queries): array
{
    if ($queries === []) {
        return [];
    }

    if (!$db->multi_query(implode(";\n", $queries))) {
        throw new RuntimeException($db->error ?: "Database query failed");
    }

    $sets = [];
    do {
        $result = $db->store_result();
        $sets[] = $result ? $result->fetch_all(MYSQLI_ASSOC) : [];
        if (!$db->more_results()) {
            break;
        }
        if (!$db->next_result()) {
            throw new RuntimeException($db->error ?: "Database query failed");
        }
    } while (true);

    return $sets;
}

function row(mysqli $db, string $sql, string $types = "", array $params = []): ?array
{
    $all = rows($db, $sql, $types, $params);
    return $all[0] ?? null;
}

function exec_stmt_affected_rows(mysqli $db, string $sql, string $types = "", array $params = []): int
{
    $stmt = $db->prepare($sql);
    if (!$stmt) {
        throw new RuntimeException($db->error);
    }

    if ($types !== "") {
        $stmt->bind_param($types, ...$params);
    }

    if (!$stmt->execute()) {
        throw new RuntimeException($stmt->error);
    }

    $affectedRows = (int) $stmt->affected_rows;
    $stmt->close();
    return $affectedRows;
}

function exec_stmt(mysqli $db, string $sql, string $types = "", array $params = []): void
{
    exec_stmt_affected_rows($db, $sql, $types, $params);
}
