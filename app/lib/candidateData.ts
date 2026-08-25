// Normalizes persisted HR candidate data for the Candidates UI.

export type CandidateStatus =
  | "new"
  | "reviewed"
  | "shortlisted"
  | "interview"
  | "interviewed"
  | "hired"
  | "filtered_out"
  | "rejected"
  | "withdrawn";

export interface ProfileEvidenceReference {
  sourceId: string;
  text: string;
  sourceSection?: string | null;
}

export interface EducationEntry {
  id: string;
  level?: string | null;
  rawQualification?: string | null;
  qualification?: string | null;
  field?: string | null;
  institution?: string | null;
  graduationYear?: number | null;
  cgpa?: number | null;
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface ExperienceEntry {
  id: string;
  jobTitle?: string | null;
  company?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  isCurrent?: boolean;
  durationMonths?: number | null;
  responsibilities?: string[];
  achievements?: string[];
  skillsEvidence?: ProfileEvidenceReference[];
  workDomain?: string | null;
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface SkillEntry {
  id: string;
  name: string;
  normalizedName?: string | null;
  evidence?: ProfileEvidenceReference[];
}

export interface CertificationEntry {
  id: string;
  name: string;
  issuer?: string | null;
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface LanguageEntry {
  id: string;
  language: string;
  proficiency?: string | null;
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface ProjectEntry {
  id: string;
  title?: string | null;
  description?: string | null;
  technologies?: string[];
  responsibilities?: string[];
  achievements?: string[];
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface AchievementEntry {
  id: string;
  text: string;
  sourceId?: string | null;
  sourceText?: string | null;
  sourceSection?: string | null;
}

export interface CandidateProfile {
  candidateId?: number | string | null;
  personalInfo?: {
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    location?: string | null;
  };
  profileSummary?: string | null;
  primaryDomain?: string | null;
  keyStrengths?: string[];
  education?: EducationEntry[];
  experience?: ExperienceEntry[];
  skills?: SkillEntry[];
  certifications?: CertificationEntry[];
  languages?: LanguageEntry[];
  projects?: ProjectEntry[];
  achievements?: AchievementEntry[];
  cgpa?: number | null;
  noticePeriod?: string | null;
  totalExperienceYears?: number | null;
  totalExperienceMonths?: number | null;
  highestEducationLevel?: string | null;
  candidateSummary?: string | null;
  evidenceIndex?: MatchedEvidence[];
}

export interface MatchedEvidence {
  sourceId: string;
  sourceSection?: string | null;
  sourceText: string;
  sourceType?: string | null;
}

export interface EligibilityReason {
  key?: string;
  label?: string;
  passed?: boolean;
  actual?: unknown;
  required?: unknown;
  reason?: string;
  [key: string]: unknown;
}

export interface ScoreBreakdownItem {
  id: string;
  title: string;
  justification: string;
  criteriaScore: number;
  weight: number;
  weightedScore?: number;
  maxWeightedScore?: number;
  color: string;
  badgeColor: string;
  criterionType?: string | null;
  matchLevel?: string | null;
  grounded?: boolean;
  usedEvidenceIds: string[];
  matchedEvidence: MatchedEvidence[];
}

export interface CandidateDocument {
  id: string;
  fileName: string;
  fileUrl: string;
  mimeType: string;
  fileSize: number;
  uploadedAt?: string;
}

export interface AppliedJobHistoryItem {
  historyKey: string;
  jobId: string;
  jobTitle: string;
  department: string;
  submittedDate: string;
  score: number;
  rank: number | null;
  status: string;
}

export interface Candidate {
  id: string;
  applicationId?: string;
  name: string;
  email: string;
  phone: string;
  appliedDate: string;
  appliedAt?: string | null;
  rank: number | null;
  status: CandidateStatus;
  isShortlisted: boolean;
  interviewSentAt?: string | null;
  assignedHrUserId?: number | null;
  assignedHrName?: string | null;
  lastEmailType?: string | null;
  lastEmailSentAt?: string | null;
  lastEmailSentBy?: string | null;
  latestRejectActionType?: string | null;
  latestRejectActionBy?: string | null;
  latestEmailActionLogId?: number | null;
  latestEmailReasonType?: string | null;
  latestEmailReasonDetails?: string | null;
  employmentFormSubmissionId?: number | null;
  currentSubmissionNo: number;
  currentSubmissionLabel: string;
  experience: string;
  education: string;
  cgpa?: string;
  noticePeriod?: string;
  gender?: string;
  country?: string;
  currentLocation?: string;
  languages?: { language: string; level: string }[];
  questionAnswers?: {
    questionId: number;
    question: string;
    fieldType: string;
    answer: string;
  }[];
  hiredStartDate?: string | null;
  wasHired?: boolean;
  skills: string[];
  resumeUrl: string;
  documents: CandidateDocument[];
  summary: string | null;
  scoreBreakdown: ScoreBreakdownItem[];
  score: number | null;
  appliedJobHistory?: AppliedJobHistoryItem[];
  analysisStatus?: string | null;
  eligibilityStatus?: string | null;
  eligibilityReasons: EligibilityReason[];
  filteredOut: boolean;
  parsedProfile: CandidateProfile | null;
  resumeParsingStatus?: string | null;
  parsedAt?: string | null;
  parserVersion?: string | null;
}

export interface ApiScoreBreakdownItem {
  id: number | string;
  title: string;
  criterionType?: string | null;
  justification?: string | null;
  criteriaScore?: number | string | null;
  scoreOutOf10?: number | string | null;
  weight?: number | string | null;
  weightedScore?: number | string | null;
  weightedContribution?: number | string | null;
  matchLevel?: string | null;
  grounded?: boolean | number | string;
  usedEvidenceIds?: string[];
  matchedResumeEvidence?: MatchedEvidence[];
  items?: {
    requirement?: string | null;
    matchStatus?: string | null;
    evidence?: string | null;
    itemScore?: number | string | null;
  }[];
}

export interface ApiCandidate {
  applicationId: number;
  id: number;
  name: string;
  email: string;
  phone: string;
  cgpa: string | number | null;
  yearsExperience: string | number | null;
  noticePeriodDays: string | number | null;
  gender?: string | null;
  country?: string | null;
  currentLocation?: string | null;
  languagesJson?: string | null;
  hiredStartDate?: string | null;
  wasHired?: boolean | number | string;
  appliedDate: string;
  rank: string | number | null;
  status: CandidateStatus;
  isShortlisted: boolean | number | string;
  interviewSentAt: string | null;
  assignedHrUserId: string | number | null;
  assignedHrName: string | null;
  lastEmailType: string | null;
  lastEmailSentAt: string | null;
  lastEmailSentBy: string | null;
  latestRejectActionType: string | null;
  latestRejectActionBy: string | null;
  latestEmailActionLogId: string | number | null;
  latestEmailReasonType: string | null;
  latestEmailReasonDetails: string | null;
  employmentFormSubmissionId: string | number | null;
  currentSubmissionNo: string | number;
  currentSubmissionLabel: string;
  eligibilityStatus?: string | null;
  eligibilityReasons?: EligibilityReason[];
  filteredOut?: boolean | number | string;
  analysisStatus?: string | null;
  score?: string | number | null;
  totalScore?: string | number | null;
  summary: string | null;
  resumeUrl: string | null;
  resumeFileName?: string | null;
  resumeParsingStatus?: string | null;
  parsedAt?: string | null;
  parserVersion?: string | null;
  parsedProfile?: CandidateProfile | null;
  documents?: {
    id: number | string;
    fileName: string;
    fileUrl: string;
    mimeType: string;
    fileSize: string | number;
    uploadedAt: string;
  }[];
  questionAnswers?: {
    questionId: number;
    question: string;
    fieldType: string;
    answer: string;
  }[];
  skills: { name: string }[];
  scoreBreakdown: ApiScoreBreakdownItem[];
  jobHistory: {
    historyKey: string;
    jobId: number;
    jobTitle: string;
    department: string;
    submittedDate: string;
    score: string | number;
    rank: string | number | null;
    status: string;
  }[];
}

// A missing analysis status is a legacy pending state. Processing applications
// must not expose persisted score or rank values until analysis is completed.
export const isAnalysisProcessing = (status?: string | null) => {
  const normalized = String(status ?? "").trim().toLowerCase();
  return normalized === "" || ["pending", "parsing", "scoring"].includes(normalized);
};

const scoreColors = [
  { color: "bg-violet-500", badgeColor: "text-violet-700 bg-violet-100" },
  { color: "bg-sky-500", badgeColor: "text-sky-700 bg-sky-100" },
  { color: "bg-orange-500", badgeColor: "text-orange-700 bg-orange-100" },
  { color: "bg-green-500", badgeColor: "text-green-700 bg-green-100" },
];

const toNullableNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const toBoolean = (value: unknown) =>
  value === true || value === 1 || value === "1" || value === "true";

const formatDateOnly = (value: string | null | undefined) =>
  value ? value.slice(0, 10) : "";

const dateMonthIndex = (
  value: string | null | undefined,
  boundary: "start" | "end",
) => {
  const match = String(value ?? "").match(/^(\d{4})(?:-(\d{1,2}))?/);
  if (!match) return null;

  const year = Number(match[1]);
  const month = match[2]
    ? Number(match[2])
    : boundary === "start"
      ? 1
      : 12;
  if (!Number.isInteger(year) || month < 1 || month > 12) return null;

  return year * 12 + month - 1;
};

const getProfileExperienceMonths = (profile: CandidateProfile | null) => {
  const storedMonths = toNullableNumber(profile?.totalExperienceMonths);
  const entries = profile?.experience ?? [];
  const today = new Date();
  const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const intervals = entries.map((entry) => {
    const start = dateMonthIndex(entry.startDate, "start");
    const end = dateMonthIndex(
      entry.isCurrent ? currentMonth : entry.endDate,
      "end",
    );
    return start !== null && end !== null && end >= start
      ? ([start, end] as const)
      : null;
  });

  // Recalculate from dates when every parsed role has usable boundaries. This
  // keeps older profiles correct when their persisted month total used to be
  // calculated as an exclusive end-month difference.
  if (intervals.length > 0 && intervals.every(Boolean)) {
    const sorted = intervals
      .filter((interval): interval is readonly [number, number] => interval !== null)
      .sort(([firstStart], [secondStart]) => firstStart - secondStart);
    let total = 0;
    let [currentStart, currentEnd] = sorted[0];

    for (const [start, end] of sorted.slice(1)) {
      if (start <= currentEnd + 1) {
        currentEnd = Math.max(currentEnd, end);
      } else {
        total += currentEnd - currentStart + 1;
        currentStart = start;
        currentEnd = end;
      }
    }

    return total + currentEnd - currentStart + 1;
  }

  return storedMonths;
};

export const formatExperience = (
  value: string | number | null | undefined,
  monthsValue?: string | number | null,
) => {
  const years = toNullableNumber(value);
  const months = toNullableNumber(monthsValue) ??
    (years !== null && years > 0 ? Math.round(years * 12) : null);
  if ((months === null || months <= 0) && (years === null || years <= 0)) return "";
  if (months !== null && months > 0 && months < 12) {
    return `${Math.round(months)} month${Math.round(months) === 1 ? "" : "s"}`;
  }

  const displayYears = months !== null && months >= 12 ? months / 12 : years ?? 0;
  const label = displayYears === 1 ? "year" : "years";
  return `${Number.isInteger(displayYears) ? displayYears : displayYears.toFixed(1)} ${label}`;
};

const parseCandidateLanguages = (value?: string | null) => {
  if (!value) return [];

  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .map((item) => ({
        language: String(
          (item as { language?: unknown } | null)?.language ?? "",
        ).trim(),
        level: String(
          (item as { level?: unknown } | null)?.level ?? "",
        ).trim(),
      }))
      .filter((item) => item.language || item.level);
  } catch {
    return [];
  }
};

const formatEducation = (profile: CandidateProfile | null) =>
  (profile?.education ?? [])
    .map((item) =>
      [item.level || item.qualification, item.field, item.institution]
        .filter(Boolean)
        .join(" · "),
    )
    .filter(Boolean)
    .join("; ");

const profileLanguages = (profile: CandidateProfile | null) =>
  (profile?.languages ?? [])
    .map((item) => ({
      language: item.language,
      level: item.proficiency || "",
    }))
    .filter((item) => item.language || item.level);

const normalizeStatus = (value: string): CandidateStatus => {
  const validStatuses: CandidateStatus[] = [
    "new",
    "reviewed",
    "shortlisted",
    "interview",
    "interviewed",
    "hired",
    "filtered_out",
    "rejected",
    "withdrawn",
  ];
  return validStatuses.includes(value as CandidateStatus)
    ? (value as CandidateStatus)
    : "new";
};

const normalizeEvidence = (items: unknown): MatchedEvidence[] => {
  if (!Array.isArray(items)) return [];
  return items.reduce<MatchedEvidence[]>((result, item) => {
      const evidence = item as Partial<MatchedEvidence> | null;
      const sourceText = String(evidence?.sourceText ?? "").trim();
      const sourceId = String(evidence?.sourceId ?? "").trim();
      if (!sourceId || !sourceText) return result;
      result.push({
        sourceId,
        sourceText,
        sourceSection: evidence?.sourceSection ?? null,
        sourceType: evidence?.sourceType ?? null,
      });
      return result;
    }, []);
};

const mapScoreBreakdown = (
  items: ApiScoreBreakdownItem[] | undefined,
): ScoreBreakdownItem[] =>
  (items ?? []).map((item, index) => {
    const persistedScore = toNullableNumber(item.scoreOutOf10);
    const legacyScore = toNullableNumber(item.criteriaScore);
    const criteriaScore =
      persistedScore ??
      (legacyScore === null ? 0 : legacyScore > 10 ? legacyScore / 10 : legacyScore);
    const weightedScore =
      toNullableNumber(item.weightedContribution) ??
      toNullableNumber(item.weightedScore) ??
      0;
    const usedEvidenceIds = Array.isArray(item.usedEvidenceIds)
      ? item.usedEvidenceIds.map(String).filter(Boolean)
      : [];
    const matchedEvidence = normalizeEvidence(item.matchedResumeEvidence);

    return {
      id: String(item.id),
      title: item.title,
      justification: item.justification || "",
      criteriaScore,
      weight: toNullableNumber(item.weight) ?? 0,
      weightedScore,
      maxWeightedScore: toNullableNumber(item.weight) ?? 0,
      color: scoreColors[index % scoreColors.length].color,
      badgeColor: scoreColors[index % scoreColors.length].badgeColor,
      criterionType: item.criterionType || null,
      matchLevel: item.matchLevel || "none",
      grounded: toBoolean(item.grounded),
      usedEvidenceIds,
      matchedEvidence,
    };
  });

// Converts one HR API candidate into the UI model.
export const mapApiCandidate = (candidate: ApiCandidate): Candidate => {
  const profile = candidate.parsedProfile ?? null;
  const processing = isAnalysisProcessing(candidate.analysisStatus);
  const analysisFailed =
    candidate.analysisStatus?.toLowerCase() === "failed" ||
    candidate.resumeParsingStatus?.toLowerCase() === "failed";
  const parsedScore = processing
    ? null
    : toNullableNumber(candidate.totalScore ?? candidate.score) ??
      (analysisFailed ? 0 : null);
  const profileSkills = (profile?.skills ?? [])
    .map((skill) => skill.name.trim())
    .filter(Boolean);
  const profileLanguagesValue = profileLanguages(profile);
  const profileExperienceMonths = getProfileExperienceMonths(profile);
  const noticePeriodDays =
    candidate.noticePeriodDays === null ||
    candidate.noticePeriodDays === undefined ||
    candidate.noticePeriodDays === ""
      ? null
      : Number(candidate.noticePeriodDays);

  return {
    id: String(candidate.id),
    applicationId: String(candidate.applicationId),
    name: candidate.name,
    email: candidate.email,
    phone: candidate.phone,
    appliedDate: formatDateOnly(candidate.appliedDate),
    appliedAt: candidate.appliedDate || null,
    rank: processing ? null : toNullableNumber(candidate.rank),
    status: normalizeStatus(candidate.status),
    isShortlisted:
      candidate.status === "shortlisted" ||
      candidate.status === "interview" ||
      toBoolean(candidate.isShortlisted),
    interviewSentAt: candidate.interviewSentAt || null,
    assignedHrUserId: toNullableNumber(candidate.assignedHrUserId),
    assignedHrName: candidate.assignedHrName,
    lastEmailType: candidate.lastEmailType,
    lastEmailSentAt: candidate.lastEmailSentAt,
    lastEmailSentBy: candidate.lastEmailSentBy,
    latestRejectActionType: candidate.latestRejectActionType,
    latestRejectActionBy: candidate.latestRejectActionBy,
    latestEmailActionLogId: toNullableNumber(candidate.latestEmailActionLogId),
    latestEmailReasonType: candidate.latestEmailReasonType,
    latestEmailReasonDetails: candidate.latestEmailReasonDetails,
    employmentFormSubmissionId: toNullableNumber(candidate.employmentFormSubmissionId),
    currentSubmissionNo: Number(candidate.currentSubmissionNo ?? 1),
    currentSubmissionLabel: candidate.currentSubmissionLabel || "1st Submission",
    experience: formatExperience(
      profile?.totalExperienceYears ?? candidate.yearsExperience,
      profileExperienceMonths,
    ),
    education: formatEducation(profile),
    cgpa: String(profile?.cgpa ?? candidate.cgpa ?? "-") || "-",
    noticePeriod: profile?.noticePeriod ||
      (noticePeriodDays === 0
        ? "Immediate"
        : noticePeriodDays !== null && Number.isFinite(noticePeriodDays)
          ? `${noticePeriodDays} days`
          : "-"),
    gender: candidate.gender || "-",
    country: candidate.country || "-",
    currentLocation: candidate.currentLocation || profile?.personalInfo?.location || "-",
    languages: profileLanguagesValue.length
      ? profileLanguagesValue
      : parseCandidateLanguages(candidate.languagesJson),
    questionAnswers: candidate.questionAnswers ?? [],
    hiredStartDate: candidate.hiredStartDate
      ? formatDateOnly(candidate.hiredStartDate)
      : null,
    wasHired: candidate.status === "hired" || toBoolean(candidate.wasHired),
    skills: profileSkills.length
      ? profileSkills
      : (candidate.skills ?? []).map((skill) => skill.name),
    resumeUrl: candidate.resumeUrl || "",
    documents: (candidate.documents ?? []).map((document): CandidateDocument => ({
      id: String(document.id),
      fileName: document.fileName,
      fileUrl: document.fileUrl,
      mimeType: document.mimeType,
      fileSize: Number(document.fileSize ?? 0),
      uploadedAt: document.uploadedAt,
    })),
    summary: candidate.summary?.trim() || profile?.candidateSummary?.trim() || null,
    scoreBreakdown: processing ? [] : mapScoreBreakdown(candidate.scoreBreakdown),
    score: parsedScore,
    appliedJobHistory: (candidate.jobHistory ?? []).map((history) => ({
      historyKey: history.historyKey,
      jobId: String(history.jobId),
      jobTitle: history.jobTitle,
      department: history.department,
      submittedDate: formatDateOnly(history.submittedDate),
      score: toNullableNumber(history.score) ?? 0,
      rank: toNullableNumber(history.rank),
      status: history.status,
    })),
    analysisStatus: candidate.analysisStatus || null,
    eligibilityStatus: analysisFailed
      ? "filtered_out"
      : candidate.eligibilityStatus || "pending",
    eligibilityReasons: candidate.eligibilityReasons ?? [],
    filteredOut:
      analysisFailed ||
      (candidate.filteredOut !== undefined
        ? toBoolean(candidate.filteredOut)
        : candidate.eligibilityStatus === "filtered_out" ||
          candidate.status === "filtered_out"),
    parsedProfile: profile,
    resumeParsingStatus: candidate.resumeParsingStatus || null,
    parsedAt: candidate.parsedAt || null,
    parserVersion: candidate.parserVersion || null,
  };
};

export const getAnalysisStatusLabel = (status?: string | null) => {
  switch (status) {
    case "completed":
      return "Analysis Completed";
    case "parsing":
      return "Parsing Resume";
    case "scoring":
      return "Scoring Candidate";
    case "failed":
      return "Analysis Failed";
    case "pending":
      return "Pending Analysis";
    default:
      return status ? status.replace(/_/g, " ") : "Analysis Pending";
  }
};

export const getAnalysisStatusClass = (status?: string | null) => {
  switch (status) {
    case "completed":
      return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100";
    case "failed":
      return "bg-red-50 text-red-700 ring-1 ring-red-100";
    case "parsing":
    case "scoring":
      return "bg-blue-50 text-blue-700 ring-1 ring-blue-100";
    default:
      return "bg-slate-100 text-slate-600 ring-1 ring-slate-200";
  }
};

export const getEligibilityStatusLabel = (status?: string | null) => {
  switch (status) {
    case "eligible":
      return "Eligible";
    case "filtered_out":
      return "Filtered Out";
    default:
      return "Eligibility Pending";
  }
};

export const getEligibilityStatusClass = (status?: string | null) => {
  switch (status) {
    case "eligible":
      return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100";
    case "filtered_out":
      return "bg-slate-100 text-slate-600 ring-1 ring-slate-200";
    default:
      return "bg-amber-50 text-amber-700 ring-1 ring-amber-100";
  }
};
