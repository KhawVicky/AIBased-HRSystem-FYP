// Shows the Candidate Portal view.
import image_a7e321551d78150f830b1e4870452ab5d2dd7d7e from "../../assets/uwc-berhad-logo.png";
import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import {
  Banknote,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Eye,
  EyeOff,
  FileText,
  Lock,
  Mail,
  MapPin,
  Search,
  Shield,
  User,
} from "lucide-react";
import { toast } from "sonner";

import {
  apiFetch,
  clearStoredCandidate,
  getStoredCandidate,
  getStoredCandidateToken,
  storeCandidate,
  type CandidateAccount,
} from "../../lib/api";
import {
  CANDIDATE_STATUS_OPTIONS,
  getCandidateStatusBadgeClass,
  type CandidateFacingStatus,
} from "../../lib/applicationStatus";
import { formatDisplayDate } from "../../lib/date";
import { inferEmploymentType } from "../../lib/jdParsingApi";
import { getCompactPageItems } from "../../lib/pagination";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../ui/pagination";
import { Badge } from "../ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../ui/tabs";
import {
  Dialog,
  DialogContent,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import { LoadingState } from "../shared/LoadingState";
import { PasswordInput } from "../shared/PasswordInput";
import {
  CandidatePortalFooter as SharedCandidatePortalFooter,
  CandidatePortalHeader,
} from "./CandidatePortalLayout";

const CAREERS_JOBS_PER_PAGE = 15;
const CANDIDATE_APPLICATIONS_PER_PAGE = 5;

type CareerJob = {
  id: number;
  jobCode: string;
  title: string;
  department: string;
  location: string | null;
  salaryRange: string | null;
  employmentType: string | null;
  description: string | null;
  publishedAt: string | null;
  closingDate: string | null;
  createdAt: string;
  hasApplied?: boolean;
};

type CareerJobDetails = CareerJob & {
  qualifications: Array<{ qualification: string }>;
  responsibilities: Array<{ responsibility: string }>;
  skills: Array<{ skillName: string; skillType: string; importance: string }>;
};

type CandidateApplication = {
  id: number;
  jobId?: number;
  jobCode?: string;
  jobTitle: string;
  department: string;
  submittedDate: string;
  updatedDate: string;
  status: CandidateFacingStatus;
};

type CandidateApplicationDetails = CandidateApplication & {
  fullName: string;
  email: string;
  phone: string;
  currentCgpa: string | null;
  noticePeriodDays: number | string | null;
  address: string | null;
  education: string | null;
  location: string | null;
  employmentType: string | null;
  documents: Array<{
    id: number;
    fileName: string;
    fileUrl: string;
    mimeType: string;
    fileSize: number;
    uploadedAt: string;
  }>;
  interview: null | {
    scheduledAt: string | null;
    sentAt: string | null;
    subject: string | null;
  };
};

// Keeps older jobs usable while their employment_type column is backfilled.
const getCareerJobEmploymentType = (
  job: Pick<CareerJob, "title" | "employmentType">,
) =>
  job.employmentType?.trim() || inferEmploymentType(job.title) || "Full-time";

const formatNoticePeriod = (days: number | string | null) => {
  if (days === null || days === "") return "-";
  const numericDays = Number(days);
  if (!Number.isFinite(numericDays)) return String(days);
  if (numericDays === 0) return "Immediate";
  return `${numericDays} days`;
};

type CandidateBreadcrumbItem = {
  label: string;
  to?: string;
};

// Provides the applied job text key helper.
const appliedJobTextKey = (title: string, department: string) =>
  `text:${title.trim().toLowerCase()}|${department.trim().toLowerCase()}`;

// Renders the Candidate Breadcrumb component.
function CandidateBreadcrumb({ items }: { items: CandidateBreadcrumbItem[] }) {
  return (
    <nav className="mb-6 flex flex-wrap items-center gap-2 text-sm text-[#496a94]" aria-label="Breadcrumb">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <div key={`${item.label}-${index}`} className="flex items-center gap-2">
            {index > 0 && <ChevronRight className="h-4 w-4 text-[#8aa0bd]" />}
            {item.to && !isLast ? (
              <Link to={item.to} className="transition hover:text-[#003B7A]">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? "font-semibold text-slate-950" : ""}>{item.label}</span>
            )}
          </div>
        );
      })}
    </nav>
  );
}

type CandidateAuthMode = "login" | "register" | "reset-request" | "reset-confirm";

// Renders the Candidate Auth Panel component.
function CandidateAuthPanel({
  mode,
  returnTo,
  resetToken,
  onModeChange,
  onSuccess,
  onResetComplete,
}: {
  mode: CandidateAuthMode;
  returnTo: string;
  resetToken?: string;
  onModeChange: (mode: CandidateAuthMode) => void;
  onSuccess: (candidate: CandidateAccount) => void;
  onResetComplete?: () => void;
}) {
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState<{
    fullName?: string;
    email?: string;
    phone?: string;
    password?: string;
    confirmPassword?: string;
  }>({});
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resetNotice, setResetNotice] = useState("");

  useEffect(() => {
    setErrors({});
    setResetNotice("");
    setShowPassword(false);
  }, [mode]);

  // Validates candidate authentication fields without browser-native popups.
  const validateForm = () => {
    const nextErrors: typeof errors = {};

    if (mode === "register" && !form.fullName.trim()) {
      nextErrors.fullName = "Full name is required";
    }

    if (mode !== "reset-confirm") {
      if (!form.email.trim()) {
        nextErrors.email = "Email is required";
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email.trim())) {
        nextErrors.email = "Please enter a valid email address";
      }
    }

    if (mode === "register" && form.phone.trim()) {
      const normalizedPhone = form.phone.replace(/[\s()-]/g, "");
      if (!/^(?:\+?60|0)(?:1\d{8,9}|[3-9]\d{7,8})$/.test(normalizedPhone)) {
        nextErrors.phone = "Please enter a valid Malaysian phone number";
      }
    }

    if (mode !== "reset-request") {
      if (!form.password) {
        nextErrors.password = "Password is required";
      } else if (form.password.length < 8) {
        nextErrors.password = "Password must be at least 8 characters";
      }
    }

    if (mode === "reset-confirm") {
      if (!form.confirmPassword) {
        nextErrors.confirmPassword = "Please confirm your new password";
      } else if (form.password !== form.confirmPassword) {
        nextErrors.confirmPassword = "Passwords do not match";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    setResetNotice("");
  };

  const showServerValidationError = (message: string) => {
    const normalizedMessage = message.toLowerCase();
    const field = normalizedMessage.includes("phone")
      ? "phone"
      : normalizedMessage.includes("email") || normalizedMessage.includes("registered")
        ? "email"
          : normalizedMessage.includes("password") || normalizedMessage.includes("credential")
            ? "password"
          : normalizedMessage.includes("full name")
            ? "fullName"
            : null;

    if (!field) return false;

    setErrors((prev) => ({ ...prev, [field]: message }));
    return true;
  };

  // Submits the current form.
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    setResetNotice("");
    try {
      if (mode === "reset-request") {
        const response = await apiFetch<{ message: string }>("/candidate-auth/password-reset/request", {
          method: "POST",
          body: JSON.stringify({ email: form.email.trim() }),
        });
        setResetNotice(response.message);
        return;
      }

      if (mode === "reset-confirm") {
        await apiFetch("/candidate-auth/password-reset/confirm", {
          method: "POST",
          body: JSON.stringify({ token: resetToken || "", newPassword: form.password }),
        });
        toast.success("Password reset successfully");
        onResetComplete?.();
        onModeChange("login");
        return;
      }

      const response = await apiFetch<{ candidate: CandidateAccount }>(
        mode === "login" ? "/candidate-auth/login" : "/candidate-auth/register",
        {
          method: "POST",
          body: JSON.stringify(
            mode === "login"
              ? { email: form.email.trim(), password: form.password }
              : {
                  fullName: form.fullName,
                  email: form.email.trim(),
                  phone: form.phone,
                  password: form.password,
                },
          ),
        },
      );
      storeCandidate(response.candidate);
      toast.success(mode === "login" ? "Welcome back" : "Candidate account created");
      onSuccess(response.candidate);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Authentication failed";
      if (!showServerValidationError(message)) {
        toast.error(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full">
      <CardHeader className="space-y-1 px-0 pb-5 pt-0 text-center">
        <img
          src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e}
          alt="UWC Logo"
          className="mx-auto h-16 w-auto"
        />
        <CardTitle className="text-2xl">UWC Careers</CardTitle>
        <CardDescription>
          {mode === "login"
            ? "Sign in to track your applications and manage your profile"
            : mode === "register"
              ? "Create an account to apply for UWC job openings"
              : mode === "reset-request"
                ? "Enter your email to receive a password reset link"
                : "Choose a new password for your account"}
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <form onSubmit={submit} noValidate className="space-y-4">
          {mode === "register" && (
            <>
              <div className="space-y-2">
                <Label>Full Name</Label>
                <Input
                  value={form.fullName}
                  onChange={(event) => updateField("fullName", event.target.value)}
                  aria-invalid={Boolean(errors.fullName)}
                  className={errors.fullName ? "border-red-500" : ""}
                />
                {errors.fullName && <p className="text-sm text-red-500">{errors.fullName}</p>}
              </div>
              <div className="space-y-2">
                <Label>Phone Number</Label>
                <Input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={form.phone}
                  onChange={(event) => updateField("phone", event.target.value)}
                  aria-invalid={Boolean(errors.phone)}
                  className={errors.phone ? "border-red-500" : ""}
                  maxLength={20}
                />
                {errors.phone && <p className="text-sm text-red-500">{errors.phone}</p>}
              </div>
            </>
          )}
          {mode !== "reset-confirm" && (
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="text"
                inputMode="email"
                autoComplete="email"
                value={form.email}
                onChange={(event) => updateField("email", event.target.value)}
                aria-invalid={Boolean(errors.email)}
                className={errors.email ? "border-red-500" : ""}
              />
              {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
            </div>
          )}
          {mode !== "reset-request" && (
            <>
              <div className="space-y-2">
                <Label>{mode === "reset-confirm" ? "New Password" : "Password"}</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    value={form.password}
                    onChange={(event) => updateField("password", event.target.value)}
                    aria-invalid={Boolean(errors.password)}
                    className={`pr-10 ${errors.password ? "border-red-500" : ""}`}
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-700"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {errors.password && <p className="text-sm text-red-500">{errors.password}</p>}
              </div>
              {mode === "reset-confirm" && (
                <div className="space-y-2">
                  <Label>Confirm New Password</Label>
                  <Input
                    type="password"
                    autoComplete="new-password"
                    value={form.confirmPassword}
                    onChange={(event) => updateField("confirmPassword", event.target.value)}
                    aria-invalid={Boolean(errors.confirmPassword)}
                    className={errors.confirmPassword ? "border-red-500" : ""}
                  />
                  {errors.confirmPassword && (
                    <p className="text-sm text-red-500">{errors.confirmPassword}</p>
                  )}
                </div>
              )}
            </>
          )}
          {mode === "login" && (
            <div className="-mt-2 text-right">
              <button
                type="button"
                onClick={() => onModeChange("reset-request")}
                className="text-sm font-semibold text-[#003B7A] hover:underline"
              >
                Forgot password?
              </button>
            </div>
          )}
          {resetNotice && (
            <p className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700">{resetNotice}</p>
          )}
          <Button disabled={isSubmitting} className="w-full bg-[#003B7A] hover:bg-[#002f63]">
            {isSubmitting
              ? "Please wait..."
              : mode === "login"
                ? "Login"
                : mode === "register"
                  ? "Create Account"
                  : mode === "reset-request"
                    ? "Send Reset Link"
                    : "Reset Password"}
          </Button>
          {mode === "reset-request" || mode === "reset-confirm" ? (
            <p className="text-center text-sm text-slate-600">
              <button
                type="button"
                onClick={() => onModeChange("login")}
                className="font-semibold text-[#003B7A] hover:underline"
              >
                Back to login
              </button>
            </p>
          ) : (
            <p className="text-center text-sm text-slate-600">
              {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
              <button
                type="button"
                onClick={() => onModeChange(mode === "login" ? "register" : "login")}
                className="font-semibold text-[#003B7A] hover:underline"
              >
                {mode === "login" ? "Register here" : "Login here"}
              </button>
            </p>
          )}
          {mode !== "reset-request" && mode !== "reset-confirm" && returnTo !== "/candidate/applications" && (
            <p className="text-center text-xs text-slate-500">You will continue after signing in.</p>
          )}
        </form>
      </CardContent>
    </div>
  );
}

// Renders the Candidate Auth Modal component.
export function CandidateAuthModal({
  open,
  returnTo,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  returnTo: string;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (candidate: CandidateAccount) => void;
}) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<CandidateAuthMode>("login");

  useEffect(() => {
    if (open) {
      setMode("login");
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md rounded-2xl border-slate-200 px-6 pb-0 pt-6 shadow-xl">
        <CandidateAuthPanel
          mode={mode}
          returnTo={returnTo}
          onModeChange={setMode}
          onResetComplete={() => setMode("login")}
          onSuccess={(candidate) => {
            onOpenChange(false);
            onSuccess?.(candidate);
            if (returnTo) {
              navigate(returnTo);
            }
          }}
        />
      </DialogContent>
    </Dialog>
  );
}

// Renders the Candidate Layout component.
function CandidateLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const candidate = getStoredCandidate();
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // Provides the logout helper.
  const logout = async () => {
    try {
      await apiFetch("/candidate-auth/logout", { method: "POST" });
    } catch {
      // Local logout still clears the browser session if the server session already expired.
    }
    clearStoredCandidate();
    toast.success("Logged out");
    navigate("/careers");
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <CandidatePortalHeader
        candidate={candidate}
        onLogin={() => setAuthModalOpen(true)}
        onLogout={logout}
      />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-5 sm:px-6 sm:py-8 lg:px-8">{children}</main>
      <SharedCandidatePortalFooter />
      <CandidateAuthModal
        open={authModalOpen}
        returnTo={`${location.pathname}${location.search}`}
        onOpenChange={setAuthModalOpen}
      />
    </div>
  );
}

// Provides the require candidate helper.
function requireCandidate() {
  return getStoredCandidate();
}

// Renders the Careers Home component.
export function CareersHome() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<CareerJob[]>([]);
  const [selectedJobDetails, setSelectedJobDetails] = useState<CareerJobDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingSelectedJob, setIsLoadingSelectedJob] = useState(false);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("all");
  const [jobType, setJobType] = useState("all");
  const [selectedJobCode, setSelectedJobCode] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authReturnTo, setAuthReturnTo] = useState("/candidate/applications");
  const [appliedJobKeys, setAppliedJobKeys] = useState<Set<string>>(() => new Set());

  // Mark jobs already used by the signed-in candidate.
  const loadAppliedJobs = useCallback(() => {
    if (!getStoredCandidateToken()) {
      setAppliedJobKeys(new Set());
      return;
    }

    apiFetch<{ applications: CandidateApplication[] }>("/candidate/applications?status=all")
      .then((data) => {
        setAppliedJobKeys(
          new Set(
            data.applications.flatMap((application) => [
              ...(application.jobId ? [`id:${application.jobId}`] : []),
              ...(application.jobCode ? [`code:${application.jobCode}`] : []),
              appliedJobTextKey(application.jobTitle, application.department),
            ]),
          ),
        );
      })
      .catch(() => setAppliedJobKeys(new Set()));
  }, []);

  useEffect(() => {
    apiFetch<{ jobs: CareerJob[] }>("/career/jobs")
      .then((data) => setJobs(data.jobs))
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load careers"))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    loadAppliedJobs();

    window.addEventListener("focus", loadAppliedJobs);
    return () => window.removeEventListener("focus", loadAppliedJobs);
  }, [loadAppliedJobs]);

  const departments = useMemo(
    () => Array.from(new Set(jobs.map((job) => job.department))).sort(),
    [jobs],
  );
  const jobTypes = useMemo(
    () =>
      Array.from(
        new Set([
          "Full-time",
          "Part-time",
          "Internship",
          ...jobs.map((job) => getCareerJobEmploymentType(job)),
        ]),
      ).sort() as string[],
    [jobs],
  );
  // Apply the public search and filter controls.
  const filteredJobs = jobs.filter((job) => {
    const text = `${job.title} ${job.department} ${job.location ?? ""}`.toLowerCase();
    return (
      text.includes(search.toLowerCase()) &&
      (department === "all" || job.department === department) &&
      (jobType === "all" || getCareerJobEmploymentType(job) === jobType)
    );
  });
  const pageCount = Math.max(1, Math.ceil(filteredJobs.length / CAREERS_JOBS_PER_PAGE));
  const safeCurrentPage = Math.min(currentPage, pageCount);
  const pagedJobs = filteredJobs.slice(
    (safeCurrentPage - 1) * CAREERS_JOBS_PER_PAGE,
    safeCurrentPage * CAREERS_JOBS_PER_PAGE,
  );
  const selectedJob = pagedJobs.find((job) => job.jobCode === selectedJobCode) || pagedJobs[0] || null;
  const detailJob = selectedJobDetails?.jobCode === selectedJob?.jobCode ? selectedJobDetails : null;
  const displayJob = detailJob || selectedJob;

  useEffect(() => {
    setCurrentPage(1);
  }, [search, department, jobType]);

  useEffect(() => {
    if (currentPage > pageCount) {
      setCurrentPage(pageCount);
    }
  }, [currentPage, pageCount]);

  useEffect(() => {
    if (!pagedJobs.length) {
      setSelectedJobCode("");
      return;
    }

    if (!pagedJobs.some((job) => job.jobCode === selectedJobCode)) {
      setSelectedJobCode(pagedJobs[0].jobCode);
    }
  }, [pagedJobs, selectedJobCode]);

  useEffect(() => {
    if (!selectedJob?.jobCode) {
      setSelectedJobDetails(null);
      return;
    }

    setIsLoadingSelectedJob(true);
    apiFetch<{ job: CareerJobDetails }>(`/career/jobs/${selectedJob.jobCode}`)
      .then((data) => setSelectedJobDetails(data.job))
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load job details"))
      .finally(() => setIsLoadingSelectedJob(false));
  }, [selectedJob?.jobCode]);

  // Applies to job.
  const applyToJob = (job: CareerJob) => {
    if (!getStoredCandidate()) {
      setAuthReturnTo(`/apply/${job.jobCode}`);
      setAuthModalOpen(true);
      return;
    }

    navigate(`/apply/${job.jobCode}`);
  };

  return (
    <CandidateLayout>
     <div className="mb-6">
        <Card className="rounded-2xl border-slate-200 shadow-sm">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_220px_220px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search job title, department or location" className="pl-9 pr-10" />
              <SearchClearButton
                show={Boolean(search)}
                onClear={() => setSearch("")}
              />
            </div>
            <Select value={department} onValueChange={setDepartment}>
              <SelectTrigger>
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={jobType} onValueChange={setJobType}>
              <SelectTrigger>
                <SelectValue placeholder="Job Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Job Types</SelectItem>
                {jobTypes.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <LoadingState title="Loading careers" />
      ) : filteredJobs.length === 0 ? (
        <Card className="rounded-2xl border-slate-200 p-8 text-center text-slate-500">No active jobs match your search.</Card>
      ) : (
        <div className="space-y-3">
          <p className="px-1 text-sm font-normal text-slate-500">
            Showing <span className="font-semibold text-slate-900">{filteredJobs.length}</span> {filteredJobs.length === 1 ? "job" : "jobs"}
          </p>
          <div className="grid gap-5 lg:grid-cols-[390px_1fr]">
            <div className="space-y-3">
              {pagedJobs.map((job) => {
              const isSelected = selectedJob?.jobCode === job.jobCode;
              const hasApplied =
                job.hasApplied ||
                appliedJobKeys.has(`id:${job.id}`) ||
                appliedJobKeys.has(`code:${job.jobCode}`) ||
                appliedJobKeys.has(appliedJobTextKey(job.title, job.department));

              return (
                <button
                  key={job.jobCode}
                  type="button"
                  onClick={() => {
                    if (window.innerWidth < 1024) {
                      navigate(`/careers/${job.jobCode}`);
                      return;
                    }
                    setSelectedJobCode(job.jobCode);
                  }}
                  className={`w-full rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:border-[#003B7A] hover:shadow-md ${
                    isSelected
                      ? "border-slate-200 lg:border-[#003B7A] lg:ring-2 lg:ring-blue-100"
                      : "border-slate-200"
                  }`}
                >
                  <div className="flex flex-wrap items-start gap-2">
                    <h2 className="min-w-0 flex-1 text-lg font-semibold text-slate-950">{job.title}</h2>
                    {hasApplied && (
                      <Badge variant="outline" className="border-slate-200 bg-slate-100 text-slate-600">
                        Applied
                      </Badge>
                    )}
                    <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-slate-400 lg:hidden" />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-sm text-slate-500">
                    <span className="inline-flex items-center gap-1"><Building2 className="h-4 w-4" />{job.department}</span>
                    <span className="inline-flex items-center gap-1"><MapPin className="h-4 w-4" />{job.location || "Malaysia"}</span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600">{job.description || "Join UWC and contribute to a high-performing team."}</p>
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span>{getCareerJobEmploymentType(job)}</span>
                    <span>{formatDisplayDate(job.publishedAt || job.createdAt)}</span>
                  </div>
                </button>
              );
              })}
              {pageCount > 1 && (
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    disabled={safeCurrentPage === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-slate-600">
                    Page <span className="font-semibold text-slate-900">{safeCurrentPage}</span> of {pageCount}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((page) => Math.min(pageCount, page + 1))}
                    disabled={safeCurrentPage === pageCount}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>

            <Card className="hidden min-h-[560px] rounded-2xl border-slate-200 shadow-sm lg:sticky lg:top-24 lg:block lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
            <CardContent className="p-6">
              {displayJob && (
                <div className="space-y-6">
                  <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-[#003B7A]">{displayJob.department}</p>
                      <h1 className="mt-1 text-3xl font-bold text-slate-950">{displayJob.title}</h1>
                      <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                        <span className="inline-flex items-center gap-1"><MapPin className="h-4 w-4" />{displayJob.location || "Malaysia"}</span>
                        <span className="inline-flex items-center gap-1"><Briefcase className="h-4 w-4" />{getCareerJobEmploymentType(displayJob)}</span>
                        <span className="inline-flex items-center gap-1"><Calendar className="h-4 w-4" />{formatDisplayDate(displayJob.publishedAt || displayJob.createdAt)}</span>
                        <span className="inline-flex items-center gap-1"><Banknote className="h-4 w-4" />{displayJob.salaryRange || "Not specified"}</span>
                      </div>
                    </div>
                    <Button onClick={() => applyToJob(displayJob)} className="bg-[#003B7A] px-6 hover:bg-[#002f63]">Apply Now</Button>
                  </div>

                  {isLoadingSelectedJob && <p className="text-sm text-slate-500">Loading full job details...</p>}

                  <section>
                    <h2 className="mb-3 text-lg font-semibold text-slate-950">Job Description</h2>
                    <p className="whitespace-pre-line leading-7 text-slate-700">{displayJob.description || "Join UWC and contribute to a high-performing manufacturing and technology team."}</p>
                  </section>

                  {detailJob && (
                    <section>
                      <h2 className="mb-3 text-lg font-semibold text-slate-950">Responsibilities</h2>
                      <ul className="space-y-2 text-slate-700">
                        {detailJob.responsibilities.length > 0 ? detailJob.responsibilities.map((item, index) => (
                          <li key={index} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />{item.responsibility}</li>
                        )) : <li className="text-slate-500">Responsibilities will be shared during screening.</li>}
                      </ul>
                    </section>
                  )}

                  {detailJob && (
                    <section>
                      <div>
                        <h2 className="mb-2 font-semibold text-slate-950">Qualifications</h2>
                        <ul className="space-y-2 text-sm leading-6 text-slate-700">
                          {detailJob.qualifications.length > 0 ? detailJob.qualifications.map((item, index) => (
                            <li key={index} className="flex gap-2"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-green-600" />{item.qualification}</li>
                          )) : <li className="text-slate-500">Not specified</li>}
                        </ul>
                      </div>
                    </section>
                  )}

                  {detailJob && (
                    <section>
                      <h2 className="mb-3 text-lg font-semibold text-slate-950">Required Skills</h2>
                      <div className="flex flex-wrap gap-2">
                        {detailJob.skills.length > 0 ? detailJob.skills.map((skill) => (
                          <span key={skill.skillName} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-[#003B7A]">{skill.skillName}</span>
                        )) : <span className="text-sm text-slate-500">No specific skills listed.</span>}
                      </div>
                    </section>
                  )}
                </div>
              )}
            </CardContent>
            </Card>
          </div>
        </div>
      )}
      <CandidateAuthModal
        open={authModalOpen}
        returnTo={authReturnTo}
        onOpenChange={setAuthModalOpen}
        onSuccess={loadAppliedJobs}
      />
    </CandidateLayout>
  );
}

// Renders the Career Job Details Page component.
export function CareerJobDetailsPage() {
  const { jobCode = "" } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<CareerJobDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    apiFetch<{ job: CareerJobDetails }>(`/career/jobs/${jobCode}`)
      .then((data) => setJob(data.job))
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load job details"))
      .finally(() => setIsLoading(false));
  }, [jobCode]);

  // Provides the apply helper.
  const apply = () => {
    if (!getStoredCandidate()) {
      setAuthModalOpen(true);
      return;
    }
    navigate(`/apply/${jobCode}`);
  };

  return (
    <CandidateLayout>
      {isLoading ? (
        <LoadingState title="Loading job details" />
      ) : !job ? (
        <Card className="rounded-2xl p-8 text-center text-slate-500">This job is not available.</Card>
      ) : (
        <div className="space-y-5">
          <CandidateBreadcrumb
            items={[
              { label: "Careers", to: "/careers" },
              { label: job.title },
            ]}
          />
          <Card className="rounded-2xl border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-[#003B7A]">{job.department}</p>
                  <h1 className="mt-1 text-3xl font-bold text-slate-950">{job.title}</h1>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
                    <span className="inline-flex items-center gap-1"><MapPin className="h-4 w-4" />{job.location || "Malaysia"}</span>
                    <span className="inline-flex items-center gap-1"><Briefcase className="h-4 w-4" />{getCareerJobEmploymentType(job)}</span>
                    <span className="inline-flex items-center gap-1"><Calendar className="h-4 w-4" />Closing {job.closingDate ? formatDisplayDate(job.closingDate) : "Open until filled"}</span>
                  </div>
                </div>
                <Button onClick={apply} className="bg-[#003B7A] px-6 hover:bg-[#002f63]">Apply Now</Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-5 lg:grid-cols-[1.4fr_0.8fr]">
            <Card className="rounded-2xl border-slate-200 shadow-sm">
              <CardHeader><CardTitle>Job Description</CardTitle></CardHeader>
              <CardContent className="space-y-6 text-slate-700">
                <p className="leading-7">{job.description || "No description provided."}</p>
                <section>
                  <h2 className="mb-2 font-semibold text-slate-950">Responsibilities</h2>
                  <ul className="space-y-2">
                    {job.responsibilities.length > 0 ? job.responsibilities.map((item, index) => (
                      <li key={index} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />{item.responsibility}</li>
                    )) : <li className="text-slate-500">Responsibilities will be shared during screening.</li>}
                  </ul>
                </section>
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-slate-200 shadow-sm">
              <CardHeader><CardTitle>Requirements</CardTitle></CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">Qualifications</p>
                  <ul className="mt-2 space-y-2 text-sm text-slate-800">
                    {job.qualifications.length > 0 ? job.qualifications.map((item, index) => (
                      <li key={index} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />{item.qualification}</li>
                    )) : <li className="text-slate-500">Not specified</li>}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">Required Skills</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {job.skills.length > 0 ? job.skills.map((skill) => (
                      <span key={skill.skillName} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-[#003B7A]">{skill.skillName}</span>
                    )) : <span className="text-sm text-slate-500">No specific skills listed.</span>}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
      <CandidateAuthModal
        open={authModalOpen}
        returnTo={`/apply/${jobCode}`}
        onOpenChange={setAuthModalOpen}
      />
    </CandidateLayout>
  );
}

// Renders the Candidate Auth Form component.
function CandidateAuthForm({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resetToken = searchParams.get("token") || "";
  const initialAuthMode: CandidateAuthMode = mode === "login" && resetToken ? "reset-confirm" : mode;
  const [authMode, setAuthMode] = useState<CandidateAuthMode>(initialAuthMode);
  const returnTo = searchParams.get("returnTo") || "/candidate/applications";

  useEffect(() => {
    setAuthMode(mode === "login" && resetToken ? "reset-confirm" : mode);
  }, [mode, resetToken]);

  return (
    <CandidateLayout>
      <div className="mx-auto flex min-h-[calc(100vh-16rem)] max-w-md items-center">
        <Card className="w-full rounded-2xl border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <CandidateAuthPanel
              mode={authMode}
              returnTo={returnTo}
              resetToken={resetToken}
              onModeChange={setAuthMode}
              onResetComplete={() => navigate("/candidate/login", { replace: true })}
              onSuccess={() => navigate(returnTo)}
            />
          </CardContent>
        </Card>
      </div>
    </CandidateLayout>
  );
}

// Renders the Candidate Login component.
export function CandidateLogin() {
  return <CandidateAuthForm mode="login" />;
}

// Renders the Candidate Register component.
export function CandidateRegister() {
  return <CandidateAuthForm mode="register" />;
}

// Renders the Candidate Protected component.
function CandidateProtected({ children }: { children: React.ReactNode }) {
  // Keep private candidate pages behind candidate login.
  if (!requireCandidate()) {
    return <Navigate to="/candidate/login" replace />;
  }
  return <>{children}</>;
}

// Renders the Candidate Applications Page component.
export function CandidateApplicationsPage() {
  const [applications, setApplications] = useState<CandidateApplication[]>([]);
  const [status, setStatus] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    apiFetch<{ applications: CandidateApplication[] }>(`/candidate/applications?status=${status}`)
      .then((data) => setApplications(data.applications))
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load applications"))
      .finally(() => setIsLoading(false));
  }, [status]);

  useEffect(() => {
    setCurrentPage(1);
  }, [status]);

  const pageCount = Math.max(1, Math.ceil(applications.length / CANDIDATE_APPLICATIONS_PER_PAGE));
  const safeCurrentPage = Math.min(currentPage, pageCount);
  const pagedApplications = applications.slice(
    (safeCurrentPage - 1) * CANDIDATE_APPLICATIONS_PER_PAGE,
    safeCurrentPage * CANDIDATE_APPLICATIONS_PER_PAGE,
  );

  useEffect(() => {
    if (currentPage > pageCount) {
      setCurrentPage(pageCount);
    }
  }, [currentPage, pageCount]);

  return (
    <CandidateProtected>
      <CandidateLayout>
        <CandidateBreadcrumb
          items={[
            { label: "Careers", to: "/careers" },
            { label: "My Applications" },
          ]}
        />
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-950">My Applications</h1>
            <p className="mt-1 text-slate-600">Track your submitted applications and current status.</p>
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="h-10 w-full rounded-lg border-slate-200 bg-white md:w-44">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {CANDIDATE_STATUS_OPTIONS.map((item) => (
                <SelectItem key={item} value={item}>{item}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <LoadingState title="Loading applications" />
        ) : applications.length === 0 ? (
          <Card className="rounded-2xl border-slate-200 p-8 text-center text-slate-500">No applications found.</Card>
        ) : (
          <div className="space-y-3">
            <div className="space-y-3 md:hidden">
              {pagedApplications.map((application) => (
                <Link
                  key={application.id}
                  to={`/candidate/applications/${application.id}`}
                  className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-colors active:bg-slate-50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="break-words text-base font-semibold leading-snug text-slate-950">
                        {application.jobTitle}
                      </h2>
                      <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-slate-500">
                        <Building2 className="h-4 w-4 shrink-0" />
                        {application.department}
                      </p>
                    </div>
                    <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-100 pt-3">
                    <div>
                      <p className="text-xs font-medium uppercase text-slate-500">Submitted</p>
                      <p className="mt-1 text-sm text-slate-700">
                        {formatDisplayDate(application.submittedDate)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-slate-500">Last Updated</p>
                      <p className="mt-1 text-sm text-slate-700">
                        {formatDisplayDate(application.updatedDate)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getCandidateStatusBadgeClass(application.status)}`}>
                      {application.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>

            <Card className="hidden overflow-hidden rounded-2xl border-slate-200 shadow-sm md:block">
              <div className="overflow-x-auto">
                <table className="w-full table-fixed text-sm">
                  <colgroup>
                    <col className="w-[40%] lg:w-[34%]" />
                    <col className="w-[23%] lg:w-[20%]" />
                    <col className="hidden lg:table-column lg:w-[20%]" />
                    <col className="w-[22%] lg:w-[16%]" />
                    <col className="w-[15%] lg:w-[10%]" />
                  </colgroup>
                  <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-4 lg:px-6">Job Title</th>
                      <th className="px-4 py-4 lg:px-6">Submitted Date</th>
                      <th className="hidden px-6 py-4 lg:table-cell">Last Updated</th>
                      <th className="px-4 py-4 lg:px-6">Current Status</th>
                      <th className="px-4 py-4 lg:px-6">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pagedApplications.map((application) => (
                      <tr key={application.id} className="transition-colors hover:bg-slate-50">
                        <td className="px-4 py-3 lg:px-6">
                          <p className="break-words font-medium leading-snug text-slate-950">{application.jobTitle}</p>
                          <p className="mt-1 break-words text-xs text-slate-500">{application.department}</p>
                        </td>
                        <td className="px-4 py-3 leading-snug text-slate-600 lg:px-6">
                          {formatDisplayDate(application.submittedDate)}
                        </td>
                        <td className="hidden px-6 py-3 leading-snug text-slate-600 lg:table-cell">
                          {formatDisplayDate(application.updatedDate)}
                        </td>
                        <td className="px-4 py-3 lg:px-6">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getCandidateStatusBadgeClass(application.status)}`}>
                            {application.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 lg:px-6">
                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/candidate/applications/${application.id}`}>View</Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {pageCount > 1 && (
              <Pagination className="py-3 md:py-4">
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      aria-disabled={safeCurrentPage === 1}
                      className={safeCurrentPage === 1 ? "pointer-events-none opacity-50" : ""}
                      onClick={(event) => {
                        event.preventDefault();
                        setCurrentPage((page) => Math.max(1, page - 1));
                      }}
                    />
                  </PaginationItem>

                  {getCompactPageItems(safeCurrentPage, pageCount).map((item) => (
                    <PaginationItem key={item}>
                      {typeof item === "number" ? (
                        <PaginationLink
                          href="#"
                          isActive={item === safeCurrentPage}
                          onClick={(event) => {
                            event.preventDefault();
                            setCurrentPage(item);
                          }}
                        >
                          {item}
                        </PaginationLink>
                      ) : (
                        <PaginationEllipsis />
                      )}
                    </PaginationItem>
                  ))}

                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      aria-disabled={safeCurrentPage === pageCount}
                      className={safeCurrentPage === pageCount ? "pointer-events-none opacity-50" : ""}
                      onClick={(event) => {
                        event.preventDefault();
                        setCurrentPage((page) => Math.min(pageCount, page + 1));
                      }}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            )}
          </div>
        )}
      </CandidateLayout>
    </CandidateProtected>
  );
}

// Renders the Candidate Application Details Page component.
export function CandidateApplicationDetailsPage() {
  const { applicationId = "" } = useParams();
  const [application, setApplication] = useState<CandidateApplicationDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  // Provides the load helper.
  const load = () => {
    setIsLoading(true);
    apiFetch<{ application: CandidateApplicationDetails }>(`/candidate/applications/${applicationId}`)
      .then((data) => setApplication(data.application))
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load application"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, [applicationId]);

  const canWithdraw = application?.status === "Submitted" || application?.status === "Under Review" || application?.status === "Shortlisted";
  // Provides the withdraw helper.
  const withdraw = async () => {
    try {
      await apiFetch(`/candidate/applications/${applicationId}/withdraw`, { method: "PATCH" });
      toast.success("Application withdrawn");
      setConfirmWithdraw(false);
      load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to withdraw application");
    }
  };

  return (
    <CandidateProtected>
      <CandidateLayout>
        {isLoading ? (
          <LoadingState title="Loading application details" />
        ) : !application ? (
          <Card className="rounded-2xl p-8 text-center text-slate-500">Application not found.</Card>
        ) : (
          <div className="space-y-5">
            <CandidateBreadcrumb
              items={[
                { label: "Careers", to: "/careers" },
                { label: "My Applications", to: "/candidate/applications" },
                { label: application.jobTitle },
              ]}
            />
            <Card className="rounded-2xl border-slate-200 shadow-sm">
              <CardContent className="flex flex-col gap-4 p-6 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-medium text-[#003B7A]">{application.department}</p>
                  <h1 className="mt-1 text-3xl font-bold text-slate-950">{application.jobTitle}</h1>
                  <p className="mt-2 text-sm text-slate-500">Submitted {formatDisplayDate(application.submittedDate)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-3 py-1 text-sm font-semibold ${getCandidateStatusBadgeClass(application.status)}`}>{application.status}</span>
                  {canWithdraw && <Button variant="outline" onClick={() => setConfirmWithdraw(true)}>Withdraw</Button>}
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-5 lg:grid-cols-2">
              <Card className="rounded-2xl border-slate-200 shadow-sm">
                <CardHeader><CardTitle>Submitted Details</CardTitle></CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p><strong>Name:</strong> {application.fullName}</p>
                  <p><strong>Email:</strong> {application.email}</p>
                  <p><strong>Phone:</strong> {application.phone}</p>
                  <p><strong>CGPA:</strong> {application.currentCgpa || "-"}</p>
                  <p><strong>Notice period:</strong> {formatNoticePeriod(application.noticePeriodDays)}</p>
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-slate-200 shadow-sm">
                <CardHeader><CardTitle>Uploaded Documents</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {application.documents.length === 0 ? (
                    <p className="text-sm text-slate-500">No uploaded documents found.</p>
                  ) : application.documents.map((document) => (
                    <a key={document.id} href={document.fileUrl} target="_blank" rel="noreferrer" className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">
                      <span className="inline-flex items-center gap-2"><FileText className="h-4 w-4 text-[#003B7A]" />{document.fileName}</span>
                      <span className="text-xs text-slate-500">Open</span>
                    </a>
                  ))}
                </CardContent>
              </Card>
            </div>

            {application.interview && (
              <Card className="rounded-2xl border-slate-200 shadow-sm">
                <CardHeader><CardTitle>Interview Information</CardTitle></CardHeader>
                <CardContent className="text-sm text-slate-700">
                  <p><strong>Email sent:</strong> {application.interview.sentAt ? formatDisplayDate(application.interview.sentAt) : "-"}</p>
                  <p><strong>Scheduled interview:</strong> {application.interview.scheduledAt || "Please refer to the interview email."}</p>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        <AlertDialog open={confirmWithdraw} onOpenChange={setConfirmWithdraw}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Withdraw application?</AlertDialogTitle>
              <AlertDialogDescription>This action will mark your application as withdrawn. HR will see the updated status.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={withdraw}>Withdraw Application</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CandidateLayout>
    </CandidateProtected>
  );
}

// Renders the Candidate Profile Page component.
export function CandidateProfilePage() {
  const [candidate, setCandidate] = useState<CandidateAccount | null>(getStoredCandidate());
  const [form, setForm] = useState({
    fullName: candidate?.fullName || "",
    email: candidate?.email || "",
    phone: candidate?.phone || "",
    address: candidate?.address || "",
    education: candidate?.education || "",
  });
  const [resume, setResume] = useState<File | null>(null);
  const [passwords, setPasswords] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });

  useEffect(() => {
    apiFetch<{ candidate: CandidateAccount }>("/candidate/me")
      .then((data) => {
        setCandidate(data.candidate);
        storeCandidate(data.candidate);
        setForm({
          fullName: data.candidate.fullName,
          email: data.candidate.email,
          phone: data.candidate.phone || "",
          address: data.candidate.address || "",
          education: data.candidate.education || "",
        });
      })
      .catch((error) => toast.error(error instanceof Error ? error.message : "Failed to load profile"));
  }, []);

  // Saves profile.
  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email.trim())) {
      toast.error("Please enter a valid email address");
      return;
    }
    if (form.phone.trim()) {
      const normalizedPhone = form.phone.replace(/[\s()-]/g, "");
      if (!/^(?:\+?60|0)(?:1\d{8,9}|[3-9]\d{7,8})$/.test(normalizedPhone)) {
        toast.error("Please enter a valid Malaysian phone number");
        return;
      }
    }
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => body.append(key, value));
    if (resume) body.append("defaultResume", resume);
    try {
      const response = await apiFetch<{ candidate: CandidateAccount }>("/candidate/profile", { method: "PATCH", body });
      setCandidate(response.candidate);
      storeCandidate(response.candidate);
      setResume(null);
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update profile");
    }
  };

  // Provides the change password helper.
  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (passwords.newPassword.length < 8) {
      toast.error("Password must be at least 8 characters long.");
      return;
    }
    if (passwords.newPassword !== passwords.confirmPassword) {
      toast.error("New password and confirm password do not match.");
      return;
    }
    try {
      await apiFetch("/candidate/password", {
        method: "PATCH",
        body: JSON.stringify({
          currentPassword: passwords.currentPassword,
          newPassword: passwords.newPassword,
        }),
      });
      setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
      toast.success("Password updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update password");
    }
  };

  return (
    <CandidateProtected>
      <CandidateLayout>
        <CandidateBreadcrumb
          items={[
            { label: "Careers", to: "/careers" },
            { label: "Profile" },
          ]}
        />
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-950">Your Profile</h1>
          <p className="mt-1 text-slate-600">Manage your contact details, education and default resume.</p>
        </div>
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile">
              <User className="w-4 h-4 mr-2" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="security">
              <Shield className="w-4 h-4 mr-2" />
              Security
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-6">
            <Card className="rounded-2xl border-slate-200 shadow-sm">
              <CardContent className="pt-6">
                <form onSubmit={saveProfile} noValidate className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2"><Label>Full name</Label><Input value={form.fullName} onChange={(event) => setForm((prev) => ({ ...prev, fullName: event.target.value }))} required /></div>
                    <div className="space-y-2"><Label>Email</Label><Input type="email" inputMode="email" autoComplete="email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} required /></div>
                    <div className="space-y-2"><Label>Phone number</Label><Input type="tel" inputMode="tel" autoComplete="tel" value={form.phone} onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))} /></div>
                    <div className="space-y-2"><Label>Education</Label><Input value={form.education} onChange={(event) => setForm((prev) => ({ ...prev, education: event.target.value }))} /></div>
                  </div>
                  <div className="space-y-2"><Label>Address</Label><Input value={form.address} onChange={(event) => setForm((prev) => ({ ...prev, address: event.target.value }))} /></div>
                  <div className="space-y-2">
                    <Label>Default Resume</Label>
                    <Input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(event: ChangeEvent<HTMLInputElement>) => setResume(event.target.files?.[0] || null)} />
                    <p className="text-xs text-slate-500">{resume?.name || candidate?.defaultResumeFileName || "No default resume uploaded"}</p>
                  </div>
                  <div className="flex justify-end">
                    <Button className="bg-[#003B7A] hover:bg-[#002f63]">Save Profile</Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security" className="space-y-6">
            <Card className="rounded-2xl border-slate-200 shadow-sm">
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Update your password to keep your account secure</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={changePassword} noValidate className="space-y-4">
                  <div className="space-y-2"><Label>Current Password</Label><PasswordInput value={passwords.currentPassword} onChange={(event) => setPasswords((prev) => ({ ...prev, currentPassword: event.target.value }))} required /></div>
                  <div className="space-y-2">
                    <Label>New Password</Label>
                    <PasswordInput minLength={8} value={passwords.newPassword} onChange={(event) => setPasswords((prev) => ({ ...prev, newPassword: event.target.value }))} required />
                    <p className="text-xs text-slate-500">Password must be at least 8 characters long</p>
                  </div>
                  <div className="space-y-2"><Label>Confirm New Password</Label><PasswordInput minLength={8} value={passwords.confirmPassword} onChange={(event) => setPasswords((prev) => ({ ...prev, confirmPassword: event.target.value }))} required /></div>
                  <div className="flex justify-end">
                    <Button className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5">
                      <Lock className="w-4 h-4 mr-2" />
                      Update Password
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </CandidateLayout>
    </CandidateProtected>
  );
}
