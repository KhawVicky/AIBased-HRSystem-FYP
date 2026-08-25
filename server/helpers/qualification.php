<?php

declare(strict_types=1);

/**
 * Returns the lowest qualification rank explicitly accepted by a requirement.
 * Equivalent qualifications share a rank. For example, "STPM, Diploma or
 * Degree" is rank 2 because Diploma is the lowest accepted alternative.
 */
function qualification_rank_from_text(string $value): int
{
    $remaining = strtolower(str_replace("\u{2019}", "'", $value));
    $groups = [
        5 => ["~\bphd\b~", "~\bdoctorate\b~"],
        4 => ["~\bmaster(?:'s)?\s+degree\b~", "~\bmaster(?:'s)?\b~"],
        3 => ["~\bbachelor(?:'s)?\s+degree\b~", "~\bbachelor(?:'s)?\b~", "~\bdegree\b~"],
        2 => ["~\bstpm\b~", "~\bfoundation\b~", "~\bmatriculation\b~", "~\ba[\s-]?level\b~", "~\bdiploma\b~"],
        1 => ["~\bspm\b~", "~\bo[\s-]?level\b~"],
    ];

    $matchedRanks = [];
    foreach ($groups as $rank => $patterns) {
        foreach ($patterns as $pattern) {
            while (preg_match($pattern, $remaining, $match, PREG_OFFSET_CAPTURE) === 1) {
                $matchedRanks[] = $rank;
                $offset = (int) $match[0][1];
                $length = strlen((string) $match[0][0]);
                $remaining = substr_replace($remaining, str_repeat(" ", $length), $offset, $length);
            }
        }
    }

    return $matchedRanks ? min($matchedRanks) : 0;
}

function qualification_meets_requirement(string $candidateQualification, string $requiredQualification): bool
{
    $requiredRank = qualification_rank_from_text($requiredQualification);
    if ($requiredRank === 0) {
        return true;
    }

    $candidateRank = qualification_rank_from_text($candidateQualification);
    return $candidateRank >= $requiredRank;
}
