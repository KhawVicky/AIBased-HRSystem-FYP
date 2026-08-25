<?php
// Proxies JD criteria requests to RunPod without exposing the API key to the browser.

declare(strict_types=1);

function runpod_criteria_configuration(): array
{
    $endpoint = environment_value("RUNPOD_CRITERIA_ENDPOINT_URL");
    $apiKey = environment_value("RUNPOD_API_KEY");
    $missing = [];

    if (!$endpoint) {
        $missing[] = "RUNPOD_CRITERIA_ENDPOINT_URL";
    }
    if (!$apiKey) {
        $missing[] = "RUNPOD_API_KEY";
    }

    return [
        "endpoint" => $endpoint,
        "apiKey" => $apiKey,
        "timeout" => max(30, (int) (environment_value("RUNPOD_CRITERIA_TIMEOUT_SECONDS", "240") ?? "240")),
        "missing" => $missing,
    ];
}

/**
 * Build the complete, frontend-compatible JD input sent to RunPod.
 */
function runpod_criteria_input(array $input): array
{
    $stringList = static function (mixed $values): array {
        if (!is_array($values)) {
            return [];
        }

        $result = [];
        foreach ($values as $value) {
            if (!is_string($value) || trim($value) === "") {
                continue;
            }
            $result[] = trim($value);
        }
        return array_values($result);
    };

    return [
        "jobTitle" => trim((string) ($input["jobTitle"] ?? "")),
        "department" => trim((string) ($input["department"] ?? "")),
        "responsibilities" => $stringList($input["responsibilities"] ?? null),
        "requirements" => $stringList($input["requirements"] ?? null),
        "qualifications" => $stringList($input["qualifications"] ?? null),
    ];
}

/**
 * Return a validated string array without inventing or coercing metadata.
 * Invalid optional arrays are omitted by the response mapper.
 */
function runpod_optional_string_array(array $criterion, string $key): ?array
{
    if (!array_key_exists($key, $criterion)) {
        return null;
    }

    if (!is_array($criterion[$key])) {
        return null;
    }

    $values = [];
    foreach ($criterion[$key] as $value) {
        if (!is_string($value) || trim($value) === "") {
            return null;
        }
        $values[] = trim($value);
    }

    return $values;
}

/**
 * Return a validated numeric array without converting invalid values.
 */
function runpod_optional_score_array(array $criterion, string $key): ?array
{
    if (!array_key_exists($key, $criterion)) {
        return null;
    }

    if (!is_array($criterion[$key])) {
        return null;
    }

    $values = [];
    foreach ($criterion[$key] as $value) {
        if ((!is_int($value) && !is_float($value)) || !is_finite((float) $value)) {
            return null;
        }
        $values[] = $value;
    }

    return $values;
}

/**
 * Keep per-source metadata aligned with jdEvidence. Extra trailing values are
 * safe to remove; missing values are omitted rather than fabricated.
 */
function runpod_aligned_optional_array(
    array $criterion,
    string $key,
    int $evidenceCount,
    bool $scores = false
): ?array {
    $values = $scores
        ? runpod_optional_score_array($criterion, $key)
        : runpod_optional_string_array($criterion, $key);

    if ($values === null) {
        return null;
    }

    if (count($values) > $evidenceCount) {
        $values = array_slice($values, 0, $evidenceCount);
    }

    return count($values) === $evidenceCount ? $values : null;
}

function runpod_map_criterion(array $criterion, int $index): array
{
    $sourceText = trim((string) ($criterion["sourceText"] ?? ""));
    $evidence = $sourceText === ""
        ? []
        : array_values(array_filter(array_map("trim", explode("|", $sourceText))));
    $type = trim((string) ($criterion["type"] ?? "relevant_skill"));
    $name = trim((string) ($criterion["name"] ?? ""));

    $mapped = [
        "id" => (string) ($criterion["criterionId"] ?? "criterion-" . ($index + 1)),
        "category" => $type,
        "type" => $type,
        "name" => $name,
        "weight" => (int) ($criterion["suggestedWeight"] ?? 0),
        "status" => "active",
        "jdEvidence" => $evidence,
        "explanation" => (string) ($criterion["description"] ?? ""),
        "resumeEvidenceToCheck" => (string) ($criterion["evidenceRule"] ?? ""),
        "isAutoDetected" => true,
    ];

    $importance = $criterion["importance"] ?? null;
    if (is_string($importance) && in_array($importance, ["high", "medium", "low"], true)) {
        $mapped["importance"] = $importance;
    }

    foreach (["sourceCriterionIds", "mergedFromIds"] as $key) {
        $values = runpod_optional_string_array($criterion, $key);
        if ($values !== null) {
            $mapped[$key] = $values;
        }
    }

    foreach (["sourceIds", "groundingScores"] as $key) {
        $values = runpod_aligned_optional_array(
            $criterion,
            $key,
            count($evidence),
            $key === "groundingScores"
        );
        if ($values !== null) {
            $mapped[$key] = $values;
        }
    }

    return $mapped;
}

function runpod_safe_deployment(mixed $deployment): array
{
    if (!is_array($deployment)) {
        return [];
    }

    return [
        "imageTag" => is_string($deployment["imageTag"] ?? null)
            ? trim($deployment["imageTag"])
            : "",
        "pipelineVersion" => is_string($deployment["pipelineVersion"] ?? null)
            ? trim($deployment["pipelineVersion"])
            : "",
        "gitCommitHash" => is_string($deployment["gitCommitHash"] ?? null)
            ? trim($deployment["gitCommitHash"])
            : "",
        "roleContextEnabled" => ($deployment["roleContextEnabled"] ?? false) === true,
        "finalEvidenceSafetyEnabled" => ($deployment["finalEvidenceSafetyEnabled"] ?? false) === true,
    ];
}

function runpod_safe_audit_value(mixed $value, ?string $key = null): mixed
{
    $blockedKeys = [
        "apikey",
        "hf_token",
        "hftoken",
        "rawmodeloutput",
        "originalrawmodeloutput",
        "finalrawmodeloutput",
        "retryrawmodeloutput",
        "originalretryrawmodeloutput",
        "rawoutput",
        "rawtext",
        "sourcetext",
        "keptsourcetext",
        "removedsourcetext",
        "responsibilities",
        "requirements",
        "jobdescription",
    ];
    if ($key !== null && in_array(strtolower($key), $blockedKeys, true)) {
        return null;
    }

    if (!is_array($value)) {
        return $value;
    }

    $cleaned = [];
    foreach ($value as $childKey => $childValue) {
        $childKeyString = is_string($childKey) ? $childKey : (string) $childKey;
        if (in_array(strtolower($childKeyString), $blockedKeys, true)) {
            continue;
        }
        $cleaned[$childKey] = runpod_safe_audit_value($childValue, $childKeyString);
    }

    return $cleaned;
}

function runpod_safe_hard_requirements(mixed $value): array
{
    if (!is_array($value)) {
        return ["requirements" => [], "exactValues" => []];
    }
    $allowedKinds = [
        "minimum_experience",
        "education_level",
        "minimum_cgpa",
        "required_language",
        "mandatory_certification",
    ];
    $requirements = [];
    foreach (is_array($value["requirements"] ?? null) ? $value["requirements"] : [] as $item) {
        if (!is_array($item) || !in_array($item["kind"] ?? null, $allowedKinds, true)) {
            continue;
        }
        $itemValue = $item["value"] ?? null;
        if (!is_scalar($itemValue) && $itemValue !== null) {
            continue;
        }
        $requirements[] = [
            "kind" => (string) $item["kind"],
            "value" => $itemValue,
            "sourceRef" => is_string($item["sourceRef"] ?? null) ? trim($item["sourceRef"]) : "",
            "sourceId" => is_string($item["sourceId"] ?? null) ? trim($item["sourceId"]) : "",
            "sourceHash" => is_string($item["sourceHash"] ?? null) ? trim($item["sourceHash"]) : "",
        ];
    }
    $exactInput = is_array($value["exactValues"] ?? null) ? $value["exactValues"] : [];
    $exactValues = [];
    foreach (["minExperience", "minCGPA", "requiredLanguages"] as $key) {
        if (!array_key_exists($key, $exactInput)) {
            continue;
        }
        $cleaned = runpod_safe_audit_value($exactInput[$key], $key);
        if ($cleaned !== null) {
            $exactValues[$key] = $cleaned;
        }
    }
    return ["requirements" => $requirements, "exactValues" => $exactValues];
}

function runpod_safe_source_accounting(mixed $value): array
{
    if (!is_array($value)) {
        return ["valid" => false, "sources" => []];
    }
    $sources = [];
    foreach (is_array($value["sources"] ?? null) ? $value["sources"] : [] as $item) {
        if (!is_array($item)) {
            continue;
        }
        $criterionIds = [];
        foreach (is_array($item["generatedCriterionIds"] ?? null) ? $item["generatedCriterionIds"] : [] as $criterionId) {
            if (is_string($criterionId) && trim($criterionId) !== "") {
                $criterionIds[] = trim($criterionId);
            }
        }
        $sources[] = [
            "sourceRef" => is_string($item["sourceRef"] ?? null) ? trim($item["sourceRef"]) : "",
            "sourceId" => is_string($item["sourceId"] ?? null) ? trim($item["sourceId"]) : "",
            "sourceHash" => is_string($item["sourceHash"] ?? null) ? trim($item["sourceHash"]) : "",
            "section" => is_string($item["section"] ?? null) ? trim($item["section"]) : "",
            "processingOutcome" => is_string($item["processingOutcome"] ?? null) ? trim($item["processingOutcome"]) : "",
            "mapped" => ($item["mapped"] ?? false) === true,
            "hardRequirementKinds" => is_array($item["hardRequirementKinds"] ?? null)
                ? array_values(array_filter(
                    $item["hardRequirementKinds"],
                    static fn ($kind): bool => is_string($kind) && trim($kind) !== ""
                ))
                : [],
            "reason" => is_string($item["reason"] ?? null) ? substr(trim($item["reason"]), 0, 240) : "",
            "generatedCriterionIds" => array_values(array_unique($criterionIds)),
        ];
    }
    return [
        "valid" => ($value["valid"] ?? false) === true,
        "sources" => $sources,
        "unknownSourceRefs" => runpod_safe_audit_value($value["unknownSourceRefs"] ?? []),
        "duplicateSourceRefs" => runpod_safe_audit_value($value["duplicateSourceRefs"] ?? []),
        "unmappedSourceRefs" => runpod_safe_audit_value($value["unmappedSourceRefs"] ?? []),
    ];
}

function runpod_safe_eligibility_suggestions(mixed $value): array
{
    $eligibility = is_array($value) ? $value : [];
    return [
        "minCGPA" => is_numeric($eligibility["minCGPA"] ?? null)
            ? (float) $eligibility["minCGPA"]
            : null,
        "minExperience" => is_string($eligibility["minExperience"] ?? null)
            ? trim($eligibility["minExperience"])
            : null,
        "educationLevel" => is_string($eligibility["educationLevel"] ?? null)
            ? trim($eligibility["educationLevel"])
            : null,
        "requiredLanguage" => is_string($eligibility["requiredLanguage"] ?? null)
            ? trim($eligibility["requiredLanguage"])
            : null,
        "requiredLocation" => is_string($eligibility["requiredLocation"] ?? null)
            ? trim($eligibility["requiredLocation"])
            : null,
        "enabledFilters" => is_array($eligibility["enabledFilters"] ?? null)
            ? array_values(array_filter(
                $eligibility["enabledFilters"],
                static fn ($item): bool => is_string($item) && trim($item) !== ""
            ))
            : [],
    ];
}

function runpod_safe_audit(array $audit): array
{
    return [
        "deployment" => runpod_safe_deployment($audit["deployment"] ?? null),
        "debugTrace" => runpod_safe_audit_value($audit["debugTrace"] ?? []),
        "fallbackRecoveries" => runpod_safe_audit_value($audit["fallbackRecoveries"] ?? []),
        "evidenceSafety" => runpod_safe_audit_value($audit["evidenceSafety"] ?? []),
        "hardRequirements" => runpod_safe_hard_requirements($audit["hardRequirements"] ?? null),
        "sourceAccounting" => runpod_safe_source_accounting($audit["sourceAccounting"] ?? null),
    ];
}

function runpod_criteria_proxy(): void
{
    $configuration = runpod_criteria_configuration();

    if ($configuration["missing"] !== []) {
        error_log(
            "RunPod criteria configuration missing: "
            . implode(", ", $configuration["missing"])
        );
        respond([
            "success" => false,
            "error" => "RunPod criteria service is not configured",
        ], 503);
    }

    $endpoint = (string) $configuration["endpoint"];
    $apiKey = (string) $configuration["apiKey"];

    $input = input_json();
    $criteriaInput = runpod_criteria_input($input);
    $responsibilities = $criteriaInput["responsibilities"];
    $requirements = $criteriaInput["requirements"];
    $qualifications = $criteriaInput["qualifications"];

    if (
        $responsibilities === []
        && $requirements === []
        && $qualifications === []
    ) {
        respond([
            "success" => false,
            "error" => "At least one responsibility, requirement or qualification is required",
        ], 400);
    }

    $requestBody = json_encode(
        ["input" => $criteriaInput],
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    );

    if ($requestBody === false) {
        respond([
            "success" => false,
            "error" => "Unable to encode RunPod request",
        ], 400);
    }

    $curl = curl_init($endpoint);
    if ($curl === false) {
        respond([
            "success" => false,
            "error" => "Unable to initialise RunPod request",
        ], 502);
    }

    $timeout = (int) $configuration["timeout"];
    curl_setopt_array($curl, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $requestBody,
        CURLOPT_HTTPHEADER => [
            "Accept: application/json",
            "Authorization: Bearer {$apiKey}",
            "Content-Type: application/json",
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_TIMEOUT => $timeout,
    ]);

    $rawResponse = curl_exec($curl);
    $curlError = curl_error($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);

    if ($rawResponse === false || $curlError !== "") {
        respond([
            "success" => false,
            "error" => "RunPod criteria request failed",
        ], 502);
    }

    $runpodResponse = json_decode((string) $rawResponse, true);
    if (!is_array($runpodResponse)) {
        respond([
            "success" => false,
            "error" => "RunPod returned an invalid response",
        ], 502);
    }

    if ($status < 200 || $status >= 300) {
        respond([
            "success" => false,
            "error" => "RunPod criteria request was rejected",
            "status" => $status,
        ], 502);
    }

    $output = $runpodResponse["output"] ?? $runpodResponse;
    if (is_array($output) && is_array($output["output"] ?? null)) {
        $output = $output["output"];
    }
    if (!is_array($output)) {
        respond([
            "success" => false,
            "error" => "RunPod returned no criteria output",
        ], 502);
    }
    if (!array_key_exists("criteria", $output)) {
        respond([
            "success" => false,
            "error" => "RunPod response did not contain completed criteria output",
        ], 502);
    }

    // Forward only the safe deployment/stage summary. The full RunPod audit
    // can contain raw model diagnostics and must remain server-side.
    $audit = is_array($output["audit"] ?? null) ? $output["audit"] : [];
    $safeAudit = runpod_safe_audit($audit);

    $criteria = [];
    foreach (is_array($output["criteria"] ?? null) ? $output["criteria"] : [] as $index => $criterion) {
        if (!is_array($criterion)) {
            continue;
        }
        $criteria[] = runpod_map_criterion($criterion, (int) $index);
    }

    $eligibility = runpod_safe_eligibility_suggestions(
        $output["eligibilitySuggestions"] ?? null
    );

    respond([
        "success" => true,
        "data" => [
            "criteria" => $criteria,
            "eligibilitySuggestions" => [
                "minCGPA" => $eligibility["minCGPA"],
                "minExperience" => $eligibility["minExperience"],
                "educationLevel" => $eligibility["educationLevel"],
                "requiredLanguage" => $eligibility["requiredLanguage"],
                "requiredLocation" => $eligibility["requiredLocation"],
                "enabledFilters" => $eligibility["enabledFilters"],
            ],
            "audit" => $safeAudit,
        ],
        "warnings" => is_array($output["warnings"] ?? null) ? $output["warnings"] : [],
    ]);
}
