// Provides application status helpers.
export type InternalApplicationStatus =
  | "new"
  | "reviewed"
  | "shortlisted"
  | "interview"
  | "interviewed"
  | "hired"
  | "rejected"
  | "withdrawn"
  | "filtered_out";

export type CandidateFacingStatus =
  | "Submitted"
  | "Under Review"
  | "Shortlisted"
  | "Interview"
  | "Hired"
  | "Rejected"
  | "Withdrawn";

export const APPLICATION_STATUS_LABELS: Record<InternalApplicationStatus, string> = {
  new: "New",
  reviewed: "Reviewed",
  shortlisted: "Shortlisted",
  interview: "Interview",
  interviewed: "Interviewed",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  filtered_out: "Filtered Out",
};

export const APPLICATION_STATUS_BADGE_CLASSES: Record<InternalApplicationStatus, string> = {
  new: "bg-yellow-600 text-white",
  reviewed: "bg-green-600 text-white",
  shortlisted: "bg-amber-500 text-white",
  interview: "bg-blue-600 text-white",
  interviewed: "bg-sky-700 text-white",
  hired: "bg-emerald-600 text-white",
  rejected: "bg-red-600 text-white",
  withdrawn: "bg-slate-500 text-white",
  filtered_out: "bg-slate-500 text-white",
};

export const SOFT_APPLICATION_STATUS_BADGE_CLASSES: Record<InternalApplicationStatus, string> = {
  new: "bg-yellow-50 text-yellow-700",
  reviewed: "bg-green-50 text-green-700",
  shortlisted: "bg-amber-50 text-amber-700",
  interview: "bg-blue-50 text-blue-700",
  interviewed: "bg-sky-50 text-sky-700",
  hired: "bg-emerald-50 text-emerald-700",
  rejected: "bg-red-50 text-red-700",
  withdrawn: "bg-slate-100 text-slate-600",
  filtered_out: "bg-slate-100 text-slate-600",
};

export const CANDIDATE_STATUS_BADGE_CLASSES: Record<CandidateFacingStatus, string> = {
  Submitted: "bg-amber-50 text-amber-700",
  "Under Review": "bg-green-50 text-green-700",
  Shortlisted: "bg-blue-50 text-blue-700",
  Interview: "bg-sky-50 text-sky-700",
  Hired: "bg-emerald-50 text-emerald-700",
  Rejected: "bg-red-50 text-red-700",
  Withdrawn: "bg-slate-100 text-slate-600",
};

export const CANDIDATE_STATUS_OPTIONS: CandidateFacingStatus[] = [
  "Submitted",
  "Under Review",
  "Shortlisted",
  "Interview",
  "Hired",
  "Rejected",
  "Withdrawn",
];

export const PENDING_REVIEW_STATUSES: InternalApplicationStatus[] = ["new"];
export const COMPLETED_EMAIL_ACTION_STATUSES = ["interview_email_sent", "rejection_email_sent"] as const;

const isInternalApplicationStatus = (status: string): status is InternalApplicationStatus =>
  status in APPLICATION_STATUS_LABELS;

const isCandidateFacingStatus = (status: string): status is CandidateFacingStatus =>
  status in CANDIDATE_STATUS_BADGE_CLASSES;

export const getApplicationStatusLabel = (status: string) =>
  isInternalApplicationStatus(status)
    ? APPLICATION_STATUS_LABELS[status]
    : status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export const getApplicationStatusBadgeClass = (status: string) =>
  isInternalApplicationStatus(status)
    ? APPLICATION_STATUS_BADGE_CLASSES[status]
    : "bg-slate-500 text-white";

export const getSoftApplicationStatusBadgeClass = (status: string) =>
  isInternalApplicationStatus(status)
    ? SOFT_APPLICATION_STATUS_BADGE_CLASSES[status]
    : "bg-slate-100 text-slate-600";

export const getCandidateStatusBadgeClass = (status: string) =>
  isCandidateFacingStatus(status)
    ? CANDIDATE_STATUS_BADGE_CLASSES[status]
    : "bg-slate-100 text-slate-600";
