<?php

declare(strict_types=1);

require_once dirname(__DIR__) . "/helpers/qualification.php";

function assert_true(bool $condition, string $message): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

assert_true(qualification_rank_from_text("SPM") === 1, "SPM is rank 1");
assert_true(qualification_rank_from_text("O-Level") === 1, "O-Level is rank 1");
assert_true(qualification_rank_from_text("STPM") === 2, "STPM is rank 2");
assert_true(qualification_rank_from_text("Diploma") === 2, "Diploma is rank 2");
assert_true(qualification_rank_from_text("Bachelor's Degree") === 3, "Bachelor's Degree is rank 3");
assert_true(qualification_rank_from_text("Master Degree") === 4, "Master Degree is rank 4");
assert_true(qualification_rank_from_text("PhD") === 5, "PhD is rank 5");
assert_true(qualification_rank_from_text("STPM, Diploma or Degree") === 2, "Mixed STPM/Diploma/Degree requirement uses rank 2");
assert_true(qualification_rank_from_text("Diploma or Degree") === 2, "Diploma/Degree requirement uses rank 2");

assert_true(!qualification_meets_requirement("SPM", "STPM"), "SPM must fail minimum STPM");
assert_true(qualification_meets_requirement("STPM", "STPM"), "STPM must pass minimum STPM");
assert_true(qualification_meets_requirement("Diploma", "STPM"), "Diploma must pass minimum STPM");
assert_true(qualification_meets_requirement("STPM", "Diploma"), "STPM must pass minimum Diploma");
assert_true(qualification_meets_requirement("Diploma", "Diploma"), "Diploma must pass minimum Diploma");
assert_true(qualification_meets_requirement("Bachelor Degree", "Diploma"), "Bachelor Degree must pass minimum Diploma");

fwrite(STDOUT, "Qualification hierarchy tests passed.\n");
