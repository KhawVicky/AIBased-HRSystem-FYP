// Handles requests to the JD services.
import { apiFetch } from "./api";
import { withCriteriaFallback } from "./jdCriteriaFallback";

const JD_PARSING_API_BASE =
  import.meta.env.VITE_JD_PARSING_API_URL || "http://127.0.0.1:8001";
const JD_CRITERIA_API_BASE =
  import.meta.env.VITE_JD_CRITERIA_API_URL || "http://127.0.0.1:8002";

export interface JDSheetSummary {
  sheetName: string;
  jobTitle: string;
  department: string;
}

export interface ParsedJDData {
  sheetName: string;
  jobTitle: string;
  department: string;
  salary: string;
  description: string;
  qualifications: string[];
  responsibilities: string[];
  requirements: string[];
  rawText: string;
}

export type ParsedEmploymentType = "Full-time" | "Part-time" | "Internship";

// Infers the job type from the stable job identity fields. The title and file
// name are preferred over the full JD body so an unrelated mention of an
// internship does not change a regular full-time role.
export function inferEmploymentType(
  jobTitle: string,
  fileName = "",
): ParsedEmploymentType | null {
  const identityText = `${jobTitle} ${fileName}`.toLowerCase();

  if (/\b(?:intern|internship|industrial\s+training|trainee)\b/.test(identityText)) {
    return "Internship";
  }
  if (/\bpart[\s-]?time\b/.test(identityText)) {
    return "Part-time";
  }
  if (/\bfull[\s-]?time\b/.test(identityText)) {
    return "Full-time";
  }

  return null;
}

interface JDSheetsResponse {
  success: true;
  fileName: string;
  totalSheets: number;
  sheets: JDSheetSummary[];
}

interface JDExtractResponse {
  success: true;
  data: ParsedJDData;
  warnings: string[];
}

export interface GeneratedJDCriterion {
  id: string;
  category: string;
  type: JDCriterionType;
  name: string;
  weight: number;
  status: "active";
  jdEvidence: string[];
  explanation: string;
  resumeEvidenceToCheck: string;
  isAutoDetected: true;
}

export interface GeneratedEligibilitySuggestions {
  minCGPA: number | null;
  minExperience: string | null;
  educationLevel: string | null;
  maxNoticePeriod: string | null;
  requiredLanguage: string | null;
  requiredLocation: string | null;
  enabledFilters: string[];
}

const DEFAULT_CRITERION_TYPE_WEIGHTS: Record<JDCriterionType, number> = {
  relevant_skill: 30,
  relevant_experience: 25,
  domain_knowledge: 20,
  education_relevance: 10,
  preferred_certification: 8,
  job_related_language: 7,
};

const ELIGIBILITY_LANGUAGE_NAMES = [
  "Bahasa Malaysia",
  "Bahasa Melayu",
  "English",
  "Mandarin",
  "Tamil",
  "Japanese",
  "Korean",
];

const EDUCATION_LEVEL_PATTERNS: Array<[string, RegExp]> = [
  ["SPM", /\bspm\b/i],
  ["STPM / Foundation / Matriculation", /\b(?:stpm|foundation|matriculation)\b/i],
  ["Diploma", /\bdiploma\b/i],
  ["Bachelor Degree", /\b(?:bachelor(?:'s)?|degree)\b/i],
  ["Master Degree", /\b(?:master(?:'s)?|postgraduate)\b/i],
  ["PhD", /\b(?:phd|doctorate|doctoral)\b/i],
];

const LOCATION_FILTER_VALUES: Array<[string, RegExp]> = [
  ["Penang", /\b(?:penang|batu\s+kawan)\b/i],
  ["Kuala Lumpur", /\bkuala\s+lumpur\b/i],
  ["Selangor", /\bselangor\b/i],
  ["Johor", /\bjohor\b/i],
  ["Perak", /\bperak\b/i],
  ["Malaysia only", /\bmalaysia(?:n)?\s+(?:citizen|only)\b/i],
  ["Open to relocation", /\b(?:relocat(?:e|ion)|willing\s+to\s+move)\b/i],
];

function eligibilitySourceText(jd: ParsedJDData): string {
  return Array.from(
    new Set([
      ...jd.requirements,
      ...jd.qualifications,
      jd.description,
    ].map((item) => item.trim()).filter(Boolean)),
  ).join(" ");
}

function parseExperienceFilter(text: string): string | null {
  const numberWords: Record<string, number> = {
    one: 1,
    two: 2,
    three: 3,
    four: 4,
    five: 5,
    six: 6,
    seven: 7,
    eight: 8,
    nine: 9,
    ten: 10,
  };
  const match = text.match(
    /\b(?:at\s+least|minimum(?:\s+of)?|more\s+than)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*\+?\s*years?\b/i,
  );
  if (!match) return null;

  const years = Number(match[1]) || numberWords[match[1].toLowerCase()];
  if (!years) return null;
  if (years >= 10) return "10+ years";
  if (years >= 8) return "8+ years";
  if (years >= 5) return "5+ years";
  return `${years} year${years === 1 ? "" : "s"}`;
}

function parseCGPAFilter(text: string): number | null {
  const match = text.match(/\b(?:cgpa|gpa)\s*(?:of|:|>=|at\s+least)?\s*(\d(?:\.\d{1,2})?)\b/i);
  return match ? Number(match[1]) : null;
}

function parseNoticePeriodFilter(text: string): string | null {
  if (/\bimmediate(?:ly)?\b/i.test(text) && /\b(?:available|start|join)\b/i.test(text)) {
    return "Immediate";
  }
  const match = text.match(/\b(?:notice\s+period|serve)\D{0,20}(\d+)\s*days?\b/i)
    || text.match(/\b(\d+)\s*days?\s*(?:notice\s+period|notice)\b/i);
  if (!match) return null;
  const days = Number(match[1]);
  if (days <= 14) return "14 days";
  if (days <= 30) return "30 days";
  if (days <= 60) return "60 days";
  return "90 days";
}

/**
 * Maps explicit JD requirements to the filter definitions already owned by
 * the HR system. This is intentionally rule-based and never invents values.
 */
export function inferEligibilitySuggestions(
  jd: ParsedJDData,
): GeneratedEligibilitySuggestions {
  const text = eligibilitySourceText(jd);
  const minCGPA = parseCGPAFilter(text);
  const minExperience = parseExperienceFilter(text);
  const educationLevel = EDUCATION_LEVEL_PATTERNS.find(([, pattern]) =>
    pattern.test(text),
  )?.[0] || null;
  const language = ELIGIBILITY_LANGUAGE_NAMES.find((name) =>
    new RegExp(`\\b${name.replace(/\\s+/g, "\\s+")}\\b`, "i").test(text),
  ) || null;
  const location = LOCATION_FILTER_VALUES.find(([, pattern]) =>
    pattern.test(text),
  )?.[0] || null;
  const maxNoticePeriod = parseNoticePeriodFilter(text);

  const values: Record<string, string | number | null> = {
    minCGPA,
    minExperience,
    educationLevel,
    maxNoticePeriod,
    requiredLanguage: language,
    requiredLocation: location,
  };
  const enabledFilters = Object.entries(values)
    .filter(([, value]) => value !== null && value !== "")
    .map(([key]) => key);

  return {
    minCGPA,
    minExperience,
    educationLevel,
    maxNoticePeriod,
    requiredLanguage: language,
    requiredLocation: location,
    enabledFilters,
  };
}

/**
 * Scores criteria from type priority and the strength of their supplied JD
 * evidence. Threshold-only qualifications are deliberately capped so they do
 * not overpower the core job capabilities.
 */
export function applyCriterionTypeWeights<T extends GeneratedJDCriterion>(
  criteria: T[],
): T[] {
  if (criteria.length === 0) return criteria;

  const typeCounts = criteria.reduce<Record<string, number>>((result, item) => {
    result[item.type] = (result[item.type] || 0) + 1;
    return result;
  }, {});
  const scores = criteria.map((item) => {
    const evidence = [item.name, ...item.jdEvidence]
      .join(" ")
      .toLowerCase();
    const evidenceCount = Math.max(1, item.jdEvidence.length);
    let score = DEFAULT_CRITERION_TYPE_WEIGHTS[item.type] / typeCounts[item.type];

    // Repeated or multi-sentence evidence indicates a broader capability.
    score *= 1 + Math.min(0.35, (evidenceCount - 1) * 0.15);

    const thresholdTerms = /\b(?:minimum|min\.?|at\s+least|required|qualification|diploma|degree|cgpa|\d+\s*\+?\s*years?)\b/i;
    const contextualExperienceTerms = /\b(?:scope|depth|environment|industry|function|process|team|lead|manage|supervis|recruit|payroll|production|project|outcome|result)\w*\b/i;
    if (item.type === "relevant_experience" && thresholdTerms.test(evidence)) {
      // Experience that only states an entry threshold is supporting evidence,
      // while contextual experience remains eligible for a stronger score.
      score *= contextualExperienceTerms.test(evidence) ? 0.65 : 0.4;
    }

    if (item.type === "education_relevance") {
      // A clearly stated education-field requirement is meaningful, but still
      // remains below core work capabilities in the normal case.
      score *= 1.4;
    }
    if (item.type === "preferred_certification" || item.type === "job_related_language") {
      score *= 0.85;
    }

    return Math.max(score, 0.01);
  });
  const scoreTotal = scores.reduce((total, score) => total + score, 0);
  const exact = scores.map((score) => (score / scoreTotal) * 100);
  const weights = exact.map(Math.floor);
  let remainder = 100 - weights.reduce((sum, value) => sum + value, 0);
  const order = exact
    .map((value, index) => ({ index, fraction: value - weights[index] }))
    .sort((left, right) => right.fraction - left.fraction);
  for (const item of order) {
    if (remainder <= 0) break;
    weights[item.index] += 1;
    remainder -= 1;
  }

  return criteria.map((item, index) => ({
    ...item,
    weight: weights[index],
  } as T));
}

interface JDCriteriaGenerationSuccessResponse {
  success: true;
  data: {
    criteria: GeneratedJDCriterion[];
    eligibilitySuggestions: GeneratedEligibilitySuggestions;
    audit?: {
      deployment?: {
        imageTag?: string;
        pipelineVersion?: string;
        gitCommitHash?: string;
        roleContextEnabled?: boolean;
        finalEvidenceSafetyEnabled?: boolean;
      };
      debugTrace?: Array<{
        stage: string;
        criteriaCount: number;
        criteria?: Array<{
          criterionId?: string;
          type?: string;
          name?: string;
          sourceIds?: string[];
          sourceCriterionIds?: string[];
          mergedFromIds?: string[];
          sourceCount?: number;
          sourceTextHashes?: string[];
          groundingScores?: number[];
          suggestedWeight?: number;
        }>;
        [key: string]: unknown;
      }>;
    };
  };
  warnings: string[];
}

interface JDCriteriaGenerationErrorResponse {
  success: false;
  error?: string | { message?: string };
  warnings?: string[];
}

type JDCriteriaGenerationResponse =
  | JDCriteriaGenerationSuccessResponse
  | JDCriteriaGenerationErrorResponse;

export const JD_CRITERION_TYPES = [
  "relevant_skill",
  "relevant_experience",
  "education_relevance",
  "domain_knowledge",
  "preferred_certification",
  "job_related_language",
] as const;

export type JDCriterionType = (typeof JD_CRITERION_TYPES)[number];

export interface SuggestedJDCriterion {
  type: JDCriterionType;
  name: string;
  description: string;
  sourceText: string;
  suggestedWeight: number;
  evidenceRule: string;
}

export interface JDCriteriaExtractionResponse {
  success: boolean;
  criteria: SuggestedJDCriterion[];
  ignoredTexts: string[];
  needsConsolidation: boolean;
  requiresHRReview: true;
  warnings: string[];
  fatalErrors: string[];
  diagnostics: {
    retryAttempted: boolean;
    retrySucceeded: boolean;
    consolidationAttempted: boolean;
    consolidationSucceeded: boolean;
    consolidationMethod: "none" | "llm" | "python_fallback";
    finalCriteriaCountValid: boolean;
    sourceTextGroundingFailureCount: number;
  };
}

interface JDParsingErrorResponse {
  success: false;
  error?: {
    code?: string;
    message?: string;
  };
}

async function postJDForm<T>(path: string, formData: FormData): Promise<T> {
  // Excel endpoints use multipart form data.
  let response: Response;

  try {
    response = await fetch(`${JD_PARSING_API_BASE}${path}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      "Unable to connect to the JD parsing service. Make sure it is running on port 8001.",
    );
  }

  const payload = (await response.json().catch(() => ({}))) as
    | T
    | JDParsingErrorResponse;

  if (!response.ok) {
    const errorPayload = payload as JDParsingErrorResponse;
    throw new Error(
      errorPayload.error?.message || "The Excel file could not be processed.",
    );
  }

  return payload as T;
}

async function postJDJson<T>(path: string, body: unknown): Promise<T> {
  // Rule-based criteria endpoints use JSON.
  let response: Response;

  try {
    response = await fetch(`${JD_PARSING_API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      "Unable to connect to the JD parsing service. Make sure it is running on port 8001.",
    );
  }

  const payload = (await response.json().catch(() => ({}))) as
    | T
    | JDParsingErrorResponse;
  if (!response.ok) {
    const errorPayload = payload as JDParsingErrorResponse;
    throw new Error(
      errorPayload.error?.message || "Criteria could not be generated from the JD.",
    );
  }
  return payload as T;
}

export function listJDSheets(file: File) {
  // Read worksheet names before HR selects one.
  const formData = new FormData();
  formData.append("file", file);
  return postJDForm<JDSheetsResponse>("/api/jd/excel/sheets", formData);
}

export function extractJDSheet(file: File, sheetName: string) {
  // Extract details from the worksheet selected by HR.
  const formData = new FormData();
  formData.append("file", file);
  formData.append("sheet_name", sheetName);
  return postJDForm<JDExtractResponse>("/api/jd/excel/extract", formData);
}

export function generateJDCriteria(
  jd: ParsedJDData,
): Promise<JDCriteriaGenerationSuccessResponse> {
  const requestBody = {
    jobTitle: jd.jobTitle,
    department: jd.department,
    description: jd.description,
    qualifications: jd.qualifications,
    responsibilities: jd.responsibilities,
    requirements: jd.requirements,
  };

  const fallbackWarning =
    "RunPod criteria service was unavailable; local rule-based criteria were used.";
  const debugLog = (message: string, details?: string) => {
    if (import.meta.env.DEV) {
      console.debug("[JD criteria]", message, details || "");
    }
  };

  // RunPod is the primary LLM generator. The existing 8001 rule-based
  // generator remains the local fallback for rejected or unusable responses.
  return withCriteriaFallback<JDCriteriaGenerationSuccessResponse>(
    () =>
      apiFetch<JDCriteriaGenerationResponse>("/jd-criteria-llm", {
        method: "POST",
        body: JSON.stringify(requestBody),
      }),
    () =>
      postJDJson<JDCriteriaGenerationResponse>(
        "/api/jd/criteria/generate",
        requestBody,
      ),
    {
      fallbackWarning,
      logger: debugLog,
    },
  );
}

export async function extractSuggestedJDCriteria(jd: ParsedJDData) {
  // The LLM service returns suggestions only. HR still reviews them.
  let response: Response;

  try {
    response = await fetch(
      `${JD_CRITERIA_API_BASE}/api/jd/criteria/extract`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jobTitle: jd.jobTitle,
          department: jd.department,
          responsibilities: jd.responsibilities,
          requirements: jd.requirements,
        }),
      },
    );
  } catch {
    throw new Error(
      "Unable to connect to the JD criteria service. Make sure it is running on port 8002.",
    );
  }

  const payload = (await response.json().catch(() => null)) as
    | JDCriteriaExtractionResponse
    | null;
  if (!response.ok || !payload) {
    throw new Error(
      payload?.fatalErrors?.[0] ||
        "Suggested criteria could not be generated.",
    );
  }
  if (!payload.success) {
    throw new Error(
      payload.fatalErrors[0] ||
        "The JD criteria result could not be used.",
    );
  }
  return payload;
}
