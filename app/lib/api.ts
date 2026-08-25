// Handles requests to the HR API.
const HR_API_BASE = (
  import.meta.env.VITE_HR_API_BASE_URL ||
  (import.meta.env.VITE_APP_SURFACE === "candidate"
    ? import.meta.env.VITE_API_BASE_URL
    : undefined) ||
  "http://localhost/uwc-hr-api/api.php"
).replace(/\/+$/, "");

const CANDIDATE_API_BASE = (
  import.meta.env.VITE_CANDIDATE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "https://candidate-api-production-6247.up.railway.app/api.php"
).replace(/\/+$/, "");

const candidateRoutePrefixes = [
  "candidate-auth",
  "candidate",
  "career",
  "apply",
];

const isCandidateSurface = import.meta.env.VITE_APP_SURFACE === "candidate";

function getApiBase(path: string) {
  if (isCandidateSurface) return CANDIDATE_API_BASE;

  const route = path.replace(/^\//, "").split("?", 1)[0];
  const isCandidateRoute = candidateRoutePrefixes.some(
    (prefix) => route === prefix || route.startsWith(`${prefix}/`),
  );

  return isCandidateRoute ? CANDIDATE_API_BASE : HR_API_BASE;
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(message: string, status: number, data: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export type UserRole = "hr_staff" | "hiring_manager";

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  phone?: string | null;
  avatarPath?: string | null;
  department: string | null;
  status: string;
  roleId: 1 | 2;
  roleKey: UserRole;
  roleName: string;
  mustChangePassword?: boolean;
}

export interface JobSummary {
  id: number;
  jobCode: string;
  title: string;
  department: string;
  location: string;
  salaryRange: string | null;
  employmentType: string | null;
  status: "draft" | "active" | "closed" | "archived";
  description: string | null;
  jdFileName: string | null;
  jdFilePath?: string | null;
  publishedAt: string | null;
  createdAt: string;
  link: string | null;
  applicants: number;
  newApplicants: number;
  avgScore: number;
  shortlistedCount: number;
  pendingCount: number;
  interviewCount: number;
  rejectedCount: number;
  filteredOutCount: number;
}

export interface NotificationItem {
  id: number;
  applicationId?: number | null;
  jobId?: number | null;
  notificationType: string;
  title: string;
  message: string;
  isRead: 0 | 1 | boolean;
  createdAt: string;
}

export interface NotificationResponse {
  items: NotificationItem[];
  preview: NotificationItem[];
  unreadCount: number;
}

export interface CandidateAccount {
  id: number;
  candidateId: number;
  email: string;
  fullName: string;
  phone: string;
  gender?: string;
  country?: string;
  currentLocation?: string;
  languages?: { language: string; level: string }[];
  address: string;
  education: string;
  defaultResumeFileName?: string | null;
  defaultResumePath?: string | null;
  token?: string;
}

const inFlightGetRequests = new Map<string, Promise<unknown>>();

async function executeApiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // Convert a simple path into the PHP route query.
  const [routePath, queryString] = path.replace(/^\//, "").split("?");
  const route = routePath;
  const query = queryString ? `&${queryString}` : "";
  const isFormData = options.body instanceof FormData;
  const candidateToken = getStoredCandidateToken();
  const response = await fetch(
    `${getApiBase(routePath)}?route=${encodeURIComponent(route)}${query}`,
    {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(candidateToken ? { Authorization: `Bearer ${candidateToken}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
    },
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(
      data.error || "API request failed",
      response.status,
      data,
    );
  }

  return data as T;
}

export function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const canShareRequest =
    method === "GET" &&
    options.body === undefined &&
    options.headers === undefined;

  if (!canShareRequest) {
    return executeApiFetch<T>(path, options);
  }

  // Share matching reads that start at the same time.
  const requestKey = `${getApiBase(path)}:${getStoredCandidateToken() || "hr"}:${path}`;
  const existingRequest = inFlightGetRequests.get(requestKey);
  if (existingRequest) {
    return existingRequest as Promise<T>;
  }

  const request = executeApiFetch<T>(path, options).finally(() => {
    inFlightGetRequests.delete(requestKey);
  });
  inFlightGetRequests.set(requestKey, request);
  return request;
}

export async function fetchJobDescriptionFile(
  jobId: number,
  fileName: string,
): Promise<File> {
  // Rebuild the saved file so the worksheet service can read it.
  const route = encodeURIComponent(`jobs/${jobId}/jd-file`);
  const response = await fetch(`${getApiBase(route)}?route=${route}`);

  if (!response.ok) {
    throw new ApiError(
      "The saved Excel file could not be loaded",
      response.status,
      {},
    );
  }

  const blob = await response.blob();
  return new File([blob], fileName, {
    type:
      blob.type ||
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

export function getJobDescriptionFileUrl(jobId: number): string {
  const route = `jobs/${jobId}/jd-file`;
  return `${getApiBase(route)}?route=${encodeURIComponent(route)}`;
}

export function toPublicApplicationLink(path: string | null) {
  if (!path) return null;
  return `${window.location.origin}${path}`;
}

export function getStoredUser(): AuthUser | null {
  // Keep the HR session available after a page refresh.
  const raw = localStorage.getItem("hr_user_data");
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function canManageUsers(user: AuthUser | null) {
  return user?.roleId === 2 || user?.roleKey === "hiring_manager";
}

export function canViewHrEfficiency(user: AuthUser | null) {
  return canManageUsers(user);
}

export function getStoredCandidate(): CandidateAccount | null {
  const raw = localStorage.getItem("candidate_user_data");
  if (!raw) return null;

  try {
    return JSON.parse(raw) as CandidateAccount;
  } catch {
    return null;
  }
}

export function getStoredCandidateToken() {
  return localStorage.getItem("candidate_session_token") || "";
}

export function storeCandidate(candidate: CandidateAccount) {
  if (candidate.token) {
    localStorage.setItem("candidate_session_token", candidate.token);
  }
  const { token, ...safeCandidate } = candidate;
  localStorage.setItem("candidate_user_data", JSON.stringify(safeCandidate));
}

export function clearStoredCandidate() {
  localStorage.removeItem("candidate_session_token");
  localStorage.removeItem("candidate_user_data");
}
