export type QualificationRank = 0 | 1 | 2 | 3 | 4 | 5;

type QualificationRule = {
  rank: Exclude<QualificationRank, 0>;
  patterns: RegExp[];
  aliases: string[];
};

// The rank is an eligibility threshold, so alternatives in one requirement
// use the lowest explicitly accepted qualification level.
const QUALIFICATION_RULES: QualificationRule[] = [
  {
    rank: 5,
    patterns: [/\bphd\b/i, /\bdoctorate\b/i],
    aliases: ["phd", "doctorate"],
  },
  {
    rank: 4,
    patterns: [/\bmaster(?:'s)?\s+degree\b/i, /\bmaster(?:'s)?\b/i],
    aliases: ["master degree", "master's degree", "master"],
  },
  {
    rank: 3,
    patterns: [
      /\bbachelor(?:'s)?\s+degree\b/i,
      /\bbachelor(?:'s)?\b/i,
      /\bdegree\b/i,
    ],
    aliases: ["bachelor degree", "bachelor's degree", "bachelor", "degree"],
  },
  {
    rank: 2,
    patterns: [
      /\bstpm\b/i,
      /\bfoundation\b/i,
      /\bmatriculation\b/i,
      /\ba[\s-]?level\b/i,
      /\bdiploma\b/i,
    ],
    aliases: ["stpm", "foundation", "matriculation", "a-level", "a level", "diploma"],
  },
  {
    rank: 1,
    patterns: [/\bspm\b/i, /\bo[\s-]?level\b/i],
    aliases: ["spm", "o-level", "o level"],
  },
];

const normalizedOption = (value: string) =>
  value
    .toLowerCase()
    .replace(/['\u2019]/g, "'")
    .replace(/[\u2010-\u2015]/g, "-")
    .replace(/\s+/g, " ")
    .trim();

const containsAlias = (value: string, alias: string) => {
  const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "[\\s-]+");
  return new RegExp(`\\b${escaped}\\b`, "i").test(value);
};

const matchedRanks = (value: string): number[] => {
  let remaining = normalizedOption(value);
  const matches: number[] = [];

  // Remove more specific phrases before checking generic "degree", so
  // "Master Degree" is not also interpreted as a Bachelor-level degree.
  QUALIFICATION_RULES.forEach((rule) => {
    rule.patterns.forEach((pattern) => {
      while (pattern.test(remaining)) {
        matches.push(rule.rank);
        remaining = remaining.replace(pattern, " ");
      }
    });
  });

  return matches;
};

export function qualificationRankFromText(value: string): QualificationRank {
  const ranks = matchedRanks(value);
  return (ranks.length ? Math.min(...ranks) : 0) as QualificationRank;
}

export function qualificationOptionForText(
  value: string,
  options: string[],
): string {
  const rank = qualificationRankFromText(value);
  if (!rank) return "";

  const source = normalizedOption(value);
  const sameRank = options.filter((option) => qualificationRankFromText(option) === rank);

  // Prefer an option that preserves an explicitly named equivalent from the JD.
  for (const rule of QUALIFICATION_RULES) {
    if (rule.rank !== rank) continue;
    const sourceAlias = rule.aliases.find((alias) => containsAlias(source, alias));
    if (!sourceAlias) continue;
    const matchingOption = sameRank.find((option) =>
      containsAlias(normalizedOption(option), sourceAlias),
    );
    if (matchingOption) return matchingOption;
  }

  return sameRank[0] || "";
}
