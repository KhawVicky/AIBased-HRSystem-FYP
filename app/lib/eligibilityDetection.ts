// Detects eligibility values from the JD.
import type {
  CustomEligibilityFilter,
  EligibilityFilterDefinition,
  EligibilityFilters,
} from "../components/jobs/CreateJob";
import { qualificationOptionForText } from "./qualificationHierarchy";

type DetectedEligibility = Partial<EligibilityFilters> & {
  enabledFilters: string[];
  customFilters: CustomEligibilityFilter[];
};

const normalize = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9.+]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const findOption = (
  definition: EligibilityFilterDefinition | undefined,
  predicate: (normalizedOption: string) => boolean,
) => definition?.options.find((option) => predicate(normalize(option))) || "";

const findExperienceOption = (
  definition: EligibilityFilterDefinition | undefined,
  years: number,
) => {
  if (!definition) return "";
  const options = definition.options.map((option) => ({
    option,
    years: Number(normalize(option).match(/\d+(?:\.\d+)?/)?.[0]),
    plus: option.includes("+"),
  }));
  const exact = options.find((item) => item.years === years && !item.plus);
  if (exact) return exact.option;

  return (
    options
      .filter((item) => item.plus && item.years <= years)
      .sort((a, b) => b.years - a.years)[0]?.option || ""
  );
};

export function detectEligibilityFromQualifications(
  qualifications: string[],
  definitions: EligibilityFilterDefinition[],
): DetectedEligibility {
  // Use only the filter options that already exist in HR settings.
  const source = normalize(qualifications.join(" "));
  const enabledFilters: string[] = [];
  const customFilters: CustomEligibilityFilter[] = [];
  const detected: DetectedEligibility = { enabledFilters, customFilters };
  const definitionFor = (key: string) =>
    definitions.find((definition) => definition.filterKey === key);
  const enable = (key: string) => {
    if (!enabledFilters.includes(key)) enabledFilters.push(key);
  };

  // Detect common hard requirements from the qualification text.
  const cgpaMatch = source.match(
    /(?:cgpa|gpa)\s*(?:of|at least|minimum|min|[:>=-])*\s*(\d(?:\.\d+)?)/,
  );
  if (cgpaMatch) {
    const cgpa = Number(cgpaMatch[1]);
    if (cgpa > 0 && cgpa <= 4) {
      detected.minCGPA = cgpa;
      enable("minCGPA");
    }
  }

  const experienceMatch = source.match(
    /(?:at least|min(?:imum)?(?: of)?\s*)?(\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)\b|(?:at least|min(?:imum)?(?: of)?\s*)?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b/,
  );
  if (experienceMatch) {
    const years = Number(experienceMatch[1] || experienceMatch[2]);
    const option = findExperienceOption(definitionFor("minExperience"), years);
    if (option) {
      detected.minExperience = option;
      enable("minExperience");
    }
  } else if (/\binternship\b/.test(source)) {
    const option = findOption(
      definitionFor("minExperience"),
      (value) => value === "internship",
    );
    if (option) {
      detected.minExperience = option;
      enable("minExperience");
    }
  }

  const educationDefinition = definitionFor("educationLevel");
  const educationOption = qualificationOptionForText(
    source,
    educationDefinition?.options || [],
  );
  if (educationOption) {
    detected.educationLevel = educationOption;
    enable("educationLevel");
  }

  const languageAliases: Record<string, RegExp> = {
    english: /\benglish\b/,
    "bahasa malaysia": /\b(?:bahasa malaysia|bahasa melayu|malay)\b/,
    mandarin: /\b(?:mandarin|chinese)\b/,
    tamil: /\btamil\b/,
    japanese: /\bjapanese\b/,
    korean: /\bkorean\b/,
  };
  const languageOption = findOption(
    definitionFor("requiredLanguage"),
    (value) => Boolean(languageAliases[value]?.test(source)),
  );
  if (languageOption) {
    detected.requiredLanguage = languageOption;
    enable("requiredLanguage");
  }

  const locationOption = findOption(
    definitionFor("requiredLocation"),
    (value) => value !== "any" && source.includes(value),
  );
  if (locationOption) {
    detected.requiredLocation = locationOption;
    enable("requiredLocation");
  }

  const noticeMatch = source.match(
    /(?:notice period|notice)\s*(?:of|up to|maximum|max|[:<=-])*\s*(immediate|\d+\s*days?)/,
  );
  if (noticeMatch) {
    const notice = normalize(noticeMatch[1]);
    const option = findOption(
      definitionFor("maxNoticePeriod"),
      (value) => value === notice,
    );
    if (option) {
      detected.maxNoticePeriod = option;
      enable("maxNoticePeriod");
    }
  }

  definitions
    .filter(
      (definition) =>
        !definition.isSystem && definition.filterType === "dropdown",
    )
    .forEach((definition) => {
      const option = definition.options.find((item) => {
        const normalizedOption = normalize(item);
        return normalizedOption.length >= 3 && source.includes(normalizedOption);
      });
      if (option) {
        customFilters.push({
          id: definition.filterKey,
          label: definition.filterName,
          value: option,
        });
        enable(definition.filterKey);
      }
    });

  return detected;
}
