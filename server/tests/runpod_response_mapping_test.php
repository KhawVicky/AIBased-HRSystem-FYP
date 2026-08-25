<?php

declare(strict_types=1);

require_once dirname(__DIR__) . "/helpers/runpod.php";

function assert_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "Assertion failed: {$message}\n");
        exit(1);
    }
}

$criteriaInput = runpod_criteria_input([
    "jobTitle" => "  Integration Developer  ",
    "department" => " Technology ",
    "responsibilities" => [" Build integrations. ", 4],
    "requirements" => ["Three years of API experience."],
    "qualifications" => [" Degree in Computer Science. ", ""],
]);
assert_true($criteriaInput["jobTitle"] === "Integration Developer", "job title must be trimmed");
assert_true($criteriaInput["responsibilities"] === ["Build integrations."], "responsibilities must be cleaned");
assert_true($criteriaInput["requirements"] === ["Three years of API experience."], "requirements must be forwarded");
assert_true($criteriaInput["qualifications"] === ["Degree in Computer Science."], "qualifications must be forwarded");

$mapped = runpod_map_criterion([
    "criterionId" => "criterion-1",
    "type" => "relevant_skill",
    "name" => "Recruitment Process",
    "sourceText" => "Source one. | Source two.",
    "sourceIds" => ["responsibilities-1", "responsibilities-2", "stale-id"],
    "groundingScores" => [0.98, 0.91, 0.5],
    "sourceCriterionIds" => ["responsibilities-criterion-1"],
    "mergedFromIds" => ["criterion-1", "criterion-2"],
    "importance" => "high",
    "description" => "Explanation",
    "evidenceRule" => "Resume evidence",
    "suggestedWeight" => 24,
], 0);

assert_true($mapped["id"] === "criterion-1", "criterion ID must be preserved");
assert_true($mapped["sourceIds"] === ["responsibilities-1", "responsibilities-2"], "trailing source IDs must be removed");
assert_true($mapped["groundingScores"] === [0.98, 0.91], "trailing grounding scores must be removed");
assert_true($mapped["sourceCriterionIds"] === ["responsibilities-criterion-1"], "source criterion IDs must be preserved");
assert_true($mapped["mergedFromIds"] === ["criterion-1", "criterion-2"], "merged IDs must be preserved");
assert_true($mapped["importance"] === "high", "importance must be preserved");
assert_true(count($mapped["sourceIds"]) === count($mapped["jdEvidence"]), "source IDs must align with evidence");
assert_true(count($mapped["groundingScores"]) === count($mapped["jdEvidence"]), "scores must align with evidence");

$partial = runpod_map_criterion([
    "criterionId" => "criterion-2",
    "type" => "relevant_skill",
    "name" => "Partial Metadata",
    "sourceText" => "Source one. | Source two.",
    "sourceIds" => ["responsibilities-1"],
    "groundingScores" => [0.9],
], 1);
assert_true(!array_key_exists("sourceIds", $partial), "missing source IDs must not be invented");
assert_true(!array_key_exists("groundingScores", $partial), "missing scores must not be invented");

$missing = runpod_map_criterion([
    "criterionId" => "criterion-3",
    "type" => "domain_knowledge",
    "name" => "Labour Law",
    "sourceText" => "Malaysian labour laws.",
], 2);
assert_true(!array_key_exists("sourceIds", $missing), "absent source IDs must remain absent");
assert_true(!array_key_exists("groundingScores", $missing), "absent scores must remain absent");

$audit = runpod_safe_audit([
    "deployment" => [
        "imageTag" => "v-test",
        "pipelineVersion" => "complete-jd-candidate-extraction-v2",
        "gitCommitHash" => "abc1234",
        "roleContextEnabled" => true,
        "finalEvidenceSafetyEnabled" => true,
        "apiKey" => "must-not-leak",
    ],
    "debugTrace" => [[
        "stage" => "qwen_generation:complete_jd",
        "executed" => true,
        "rawModelOutput" => "secret model response",
        "sourceText" => "complete JD must not leak",
        "sourceTextHashes" => ["hash"],
    ]],
    "fallbackRecoveries" => [[
        "module" => "domain_knowledge_fallback",
        "type" => "domain_knowledge",
        "sourceText" => "full JD evidence must not leak",
        "criterionId" => "criterion-3",
        "groundingScore" => 1.0,
    ]],
    "evidenceSafety" => [
        "removedSourceText" => ["private JD text"],
        "criteria" => [["criterion" => "Labour Law", "sourceText" => "private JD text"]],
    ],
    "hardRequirements" => [
        "requirements" => [[
            "kind" => "minimum_experience",
            "value" => 5,
            "sourceRef" => "Q1",
            "sourceId" => "requirements-1",
            "sourceHash" => "abc123",
            "sourceText" => "hard requirement private text",
        ]],
        "exactValues" => ["minExperience" => 5],
    ],
    "sourceAccounting" => [
        "valid" => true,
        "sources" => [[
            "sourceRef" => "Q1",
            "sourceId" => "requirements-1",
            "sourceHash" => "abc123",
            "reason" => "Central scoped experience.",
            "processingOutcome" => "criterion_contribution",
            "mapped" => true,
            "hardRequirementKinds" => [],
            "generatedCriterionIds" => ["criterion-1"],
            "sourceText" => "disposition private text",
        ]],
    ],
]);

assert_true($audit["deployment"]["imageTag"] === "v-test", "deployment metadata must be preserved");
assert_true($audit["deployment"]["gitCommitHash"] === "abc1234", "commit hash must be preserved");
assert_true($audit["debugTrace"][0]["stage"] === "qwen_generation:complete_jd", "complete JD stage must be preserved");
assert_true($audit["debugTrace"][0]["sourceTextHashes"] === ["hash"], "safe trace hashes must be preserved");
assert_true($audit["hardRequirements"]["requirements"][0]["value"] === 5, "hard requirements must be preserved safely");
assert_true($audit["sourceAccounting"]["sources"][0]["generatedCriterionIds"] === ["criterion-1"], "criterion links must be preserved");

$eligibility = runpod_safe_eligibility_suggestions([
    "minCGPA" => "3.20",
    "minExperience" => "5+ years",
    "educationLevel" => "Bachelor Degree",
    "requiredLanguage" => "English",
    "unexpected" => "drop-me",
]);
assert_true($eligibility["minCGPA"] === 3.2, "CGPA must be normalized");
assert_true($eligibility["minExperience"] === "5+ years", "experience must be preserved");
assert_true(!array_key_exists("unexpected", $eligibility), "unknown eligibility fields must be dropped");

$encodedAudit = json_encode($audit, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
assert_true($encodedAudit !== false, "safe audit must be JSON serializable");
assert_true(!str_contains($encodedAudit, "secret model response"), "raw model output must not be exposed");
assert_true(!str_contains($encodedAudit, "complete JD must not leak"), "raw JD text must not be exposed");
assert_true(!str_contains($encodedAudit, "must-not-leak"), "secrets must not be exposed");
assert_true(!str_contains($encodedAudit, "hard requirement private text"), "hard requirement source text must not leak");
assert_true(!str_contains($encodedAudit, "disposition private text"), "source accounting text must not leak");

fwrite(STDOUT, "RunPod response mapping tests passed.\n");
