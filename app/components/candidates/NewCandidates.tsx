// Shows the New Candidates view.
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import {
  ArrowDown,
  ArrowDownUp,
  ArrowUp,
  Calendar,
  ClipboardList,
  ExternalLink,
  FileText,
  Search,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "../../lib/api";
import {
  getApplicationStatusLabel,
  getSoftApplicationStatusBadgeClass,
  type InternalApplicationStatus,
} from "../../lib/applicationStatus";
import {
  getAnalysisStatusClass,
  getAnalysisStatusLabel,
  getEligibilityStatusClass,
  getEligibilityStatusLabel,
  isAnalysisProcessing,
} from "../../lib/candidateData";
import {
  formatDatabaseDateTime,
  formatDisplayDateTime,
  parseDatabaseDateTime,
} from "../../lib/date";
import { getCompactPageItems } from "../../lib/pagination";
import { LoadingState } from "../shared/LoadingState";
import { PageLayout } from "../shared/PageLayout";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

type Application = {
  applicationId: number;
  candidateName: string;
  candidateEmail: string;
  jobId: number;
  jobTitle: string;
  jobDepartment: string;
  submittedDate: string;
  score: number | string | null;
  rank?: number | string | null;
  status: string;
  scoreStatus: string;
  analysisStatus?: string | null;
  eligibilityStatus?: string | null;
  filteredOut?: boolean | number | string;
  employmentFormSubmissionId: number | null;
  documents?: ApplicationDocument[];
};

type ApplicationDocument = {
  id: number;
  fileName: string;
  fileUrl: string;
  mimeType: string;
  fileSize: number;
  uploadedAt: string;
};

type EmploymentForm = {
  submissionId: number;
  candidateName: string;
  candidateEmail: string;
  jobId: number;
  jobTitle: string;
  jobDepartment: string;
  formSubmittedAt?: string;
  submittedDate?: string;
};

type CandidateApplication = Application & {
  applicationCount: number;
};

type Tab = "applicants" | "forms";
type SortKey = "candidate" | "score" | "date";

const PAGE_SIZE = 12;
const HISTORY_PAGE_SIZE = 5;

const STATUS_FILTER_OPTIONS: InternalApplicationStatus[] = [
  "new",
  "reviewed",
  "shortlisted",
  "interview",
  "interviewed",
  "hired",
  "rejected",
  "filtered_out",
  "withdrawn",
];

// Formats date.
const formatDate = (value: string) => formatDisplayDateTime(value);

// Reads the form's persisted submission timestamp, with a legacy API fallback.
const getEmploymentFormSubmittedAt = (form: EmploymentForm) =>
  form.formSubmittedAt || form.submittedDate || "";

// Formats database timestamps in the user's local timezone.
const formatEmploymentFormDate = (form: EmploymentForm) =>
  formatDatabaseDateTime(getEmploymentFormSubmittedAt(form));

// Renders the Sort Button component.
function SortButton({
  label,
  sortKey,
  activeKey,
  ascending,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  ascending: boolean;
  onClick: (key: SortKey) => void;
}) {
  const active = sortKey === activeKey;

  return (
    <button
      type="button"
      onClick={() => onClick(sortKey)}
      className="inline-flex items-center gap-1 rounded text-left text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-[#003B7A]"
    >
      {label}
      {active ? (
        ascending ? (
          <ArrowUp className="h-3.5 w-3.5" />
        ) : (
          <ArrowDown className="h-3.5 w-3.5" />
        )
      ) : (
        <ArrowDownUp className="h-3.5 w-3.5 text-slate-300" />
      )}
    </button>
  );
}

// Renders the New Candidates component.
export function NewCandidates() {
  const [tab, setTab] = useState<Tab>("applicants");
  const [applications, setApplications] = useState<Application[]>([]);
  const [forms, setForms] = useState<EmploymentForm[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [jobFilter, setJobFilter] = useState("all");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("candidate");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(1);
  const [opened, setOpened] = useState<Application | null>(null);
  const [documentApplication, setDocumentApplication] = useState<Application | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [selectedCandidateEmail, setSelectedCandidateEmail] = useState<string | null>(null);
  const [searchFocused, setSearchFocused] = useState(false);

  // Load applications and employment forms together.
  useEffect(() => {
    Promise.all([
      apiFetch<{ applications: Application[] }>("/applications"),
      apiFetch<{ submissions: EmploymentForm[] }>("/employment-form/submissions"),
    ])
      .then(([applicationData, formData]) => {
        setApplications(applicationData.applications);
        setForms(formData.submissions);
      })
      .catch((error) =>
        toast.error(error instanceof Error ? error.message : "Failed to load candidate records"),
      )
      .finally(() => setLoading(false));
  }, []);

  const source = tab === "applicants" ? applications : forms;

  const jobs = useMemo(
    () => Array.from(new Map(source.map((item) => [item.jobId, item.jobTitle])).entries()),
    [source],
  );

  const departments = useMemo(
    () =>
      Array.from(new Set(source.map((item) => item.jobDepartment).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b),
      ),
    [source],
  );

  const applicationCountsByEmail = useMemo(() => {
    const counts = new Map<string, number>();
    applications.forEach((application) => {
      const key = application.candidateEmail.toLowerCase();
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return counts;
  }, [applications]);

  // Provides the compare rows helper.
  const compareRows = (first: Application | EmploymentForm, second: Application | EmploymentForm) => {
    const firstSubmittedAt =
      "formSubmittedAt" in first
        ? getEmploymentFormSubmittedAt(first)
        : first.submittedDate;
    const secondSubmittedAt =
      "formSubmittedAt" in second
        ? getEmploymentFormSubmittedAt(second)
        : second.submittedDate;
    const firstValue =
      sortKey === "candidate"
        ? first.candidateName
        : sortKey === "score" && "score" in first
          ? Number(first.score ?? -1)
          : parseDatabaseDateTime(firstSubmittedAt)?.getTime() ?? Number.NEGATIVE_INFINITY;
    const secondValue =
      sortKey === "candidate"
        ? second.candidateName
        : sortKey === "score" && "score" in second
          ? Number(second.score ?? -1)
          : parseDatabaseDateTime(secondSubmittedAt)?.getTime() ?? Number.NEGATIVE_INFINITY;
    const order =
      typeof firstValue === "number" && typeof secondValue === "number"
        ? firstValue - secondValue
        : String(firstValue).localeCompare(String(secondValue));

    return ascending ? order : -order;
  };

  // Filter, group, and sort the current tab data.
  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();

    const filteredRows = [...source]
      .filter(
        (item) =>
          (selectedCandidateEmail
            ? item.candidateEmail.toLowerCase() === selectedCandidateEmail
            : !keyword ||
              item.candidateName.toLowerCase().includes(keyword) ||
              item.candidateEmail.toLowerCase().includes(keyword) ||
              item.jobTitle.toLowerCase().includes(keyword) ||
              item.jobDepartment.toLowerCase().includes(keyword)) &&
          (jobFilter === "all" || String(item.jobId) === jobFilter) &&
          (departmentFilter === "all" || item.jobDepartment === departmentFilter) &&
          (tab !== "applicants" ||
            statusFilter === "all" ||
            ("status" in item && item.status === statusFilter)),
      )
      .sort(compareRows);

    if (tab === "forms") return filteredRows;

    const grouped = new Map<string, CandidateApplication>();
    filteredRows.forEach((item) => {
      const application = item as Application;
      const key = application.candidateEmail.toLowerCase();
      if (!grouped.has(key)) {
        grouped.set(key, {
          ...application,
          applicationCount: applicationCountsByEmail.get(key) ?? 1,
        });
      }
    });

    return Array.from(grouped.values());
  }, [
    applicationCountsByEmail,
    ascending,
    departmentFilter,
    jobFilter,
    query,
    selectedCandidateEmail,
    sortKey,
    source,
    statusFilter,
    tab,
  ]);

  const searchSuggestions = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword || selectedCandidateEmail) return [];

    const suggestions = new Map<string, Application | EmploymentForm>();
    source
      .filter(
        (item) =>
          item.candidateName.toLowerCase().startsWith(keyword) ||
          item.candidateEmail.toLowerCase().startsWith(keyword) ||
          item.jobTitle.toLowerCase().startsWith(keyword) ||
          item.jobDepartment.toLowerCase().startsWith(keyword),
      )
      .sort((first, second) =>
        first.candidateName.localeCompare(second.candidateName, undefined, {
          sensitivity: "base",
        }),
      )
      .forEach((item) => {
        const key = item.candidateEmail.toLowerCase();
        if (!suggestions.has(key)) suggestions.set(key, item);
      });

    return Array.from(suggestions.values()).slice(0, 8);
  }, [query, selectedCandidateEmail, source]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const history = opened
    ? applications.filter(
        (item) => item.candidateEmail.toLowerCase() === opened.candidateEmail.toLowerCase(),
      )
    : [];
  const historyCount = Math.max(1, Math.ceil(history.length / HISTORY_PAGE_SIZE));
  const historyRows = history.slice(
    (historyPage - 1) * HISTORY_PAGE_SIZE,
    historyPage * HISTORY_PAGE_SIZE,
  );
  const formCount = opened
    ? forms.filter((item) => item.candidateEmail.toLowerCase() === opened.candidateEmail.toLowerCase())
        .length
    : 0;

  useEffect(() => {
    setPage(1);
  }, [tab, query, jobFilter, departmentFilter, statusFilter, sortKey, ascending]);

  useEffect(() => {
    setJobFilter("all");
    setDepartmentFilter("all");
    setStatusFilter("all");
    setSelectedCandidateEmail(null);
    setQuery("");
    setSortKey(tab === "applicants" ? "candidate" : "date");
    setAscending(tab === "applicants");
  }, [tab]);

  // Toggles sort.
  const toggleSort = (next: SortKey) => {
    if (next === "score") {
      if (sortKey !== "score") {
        setSortKey("score");
        setAscending(false);
      } else if (!ascending) {
        setAscending(true);
      } else {
        setSortKey("candidate");
        setAscending(true);
      }
      return;
    }

    if (next === sortKey) {
      setAscending((value) => !value);
      return;
    }

    setSortKey(next);
    setAscending(next !== "date");
  };

  // Opens details.
  const openDetails = (application: Application) => {
    setOpened(application);
    setHistoryPage(1);
  };

  // Opens resume documents.
  const openResumeDocuments = (application: Application) => {
    const documents = application.documents ?? [];

    if (documents.length === 1) {
      window.open(documents[0].fileUrl, "_blank");
      return;
    }

    if (documents.length > 1) {
      setDocumentApplication(application);
      return;
    }

    toast.error(`No uploaded resume found for ${application.candidateName}`);
  };

  // Builds the current pagination controls.
  const pagination = (current: number, count: number, change: (value: number) => void) => {
    if (count <= 1) return null;

    return (
      <Pagination className="mt-6">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              href="#"
              className={current === 1 ? "pointer-events-none opacity-50" : ""}
              onClick={(event) => {
                event.preventDefault();
                change(Math.max(1, current - 1));
              }}
            />
          </PaginationItem>
          {getCompactPageItems(current, count).map((item) => (
            <PaginationItem key={item}>
              {typeof item === "number" ? (
                <PaginationLink
                  href="#"
                  isActive={item === current}
                  onClick={(event) => {
                    event.preventDefault();
                    change(item);
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
              className={current === count ? "pointer-events-none opacity-50" : ""}
              onClick={(event) => {
                event.preventDefault();
                change(Math.min(count, current + 1));
              }}
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    );
  };

  return (
    <PageLayout
      breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Candidates" }]}
      title="Candidates"
      subtitle="Review submitted job applications and employment forms."
      useCard={false}
    >
      {loading ? (
        <LoadingState title="Loading candidates" />
      ) : (
        <div className="space-y-6">
          <div className="flex items-center justify-between gap-4">
            <Tabs value={tab} onValueChange={(value) => setTab(value as Tab)}>
              <TabsList>
                <TabsTrigger value="applicants">
                  <UserRound className="mr-2 h-4 w-4" />
                  Candidates Application
                </TabsTrigger>
                <TabsTrigger value="forms">
                  <ClipboardList className="mr-2 h-4 w-4" />
                  Employment Forms
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <span className="text-sm text-slate-500">
              {filtered.length} {tab === "applicants" ? "candidates" : "forms"}
            </span>
          </div>

          <Card className="shadow-md">
            <CardContent
              className={
                tab === "applicants"
                  ? "grid items-center gap-3 !p-4 md:grid-cols-2 lg:grid-cols-[minmax(260px,420px)_repeat(3,minmax(0,1fr))]"
                  : "grid items-center gap-3 !p-4 md:grid-cols-2 lg:grid-cols-[minmax(260px,420px)_repeat(2,minmax(0,1fr))]"
              }
            >
              <form className="relative" autoComplete="off" onSubmit={(event) => event.preventDefault()}>
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  type="text"
                  inputMode="search"
                  value={query}
                  autoComplete="new-password"
                  autoCorrect="off"
                  spellCheck={false}
                  name="candidate-table-keyword"
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setSelectedCandidateEmail(null);
                  }}
                  onFocus={() => setSearchFocused(true)}
                  onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
                  className="pl-9 pr-10"
                  placeholder="Search name, email or applied job"
                />
                <SearchClearButton
                  show={Boolean(query)}
                  onClear={() => {
                    setQuery("");
                    setSelectedCandidateEmail(null);
                    setSearchFocused(false);
                  }}
                />
                {searchFocused && searchSuggestions.length > 0 && (
                  <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                    {searchSuggestions.map((item) => (
                      <button
                        key={item.candidateEmail.toLowerCase()}
                        type="button"
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setSelectedCandidateEmail(item.candidateEmail.toLowerCase());
                          setQuery(item.candidateName);
                          setSearchFocused(false);
                        }}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-slate-950">
                            {item.candidateName}
                          </span>
                          <span className="block truncate text-xs text-slate-500">
                            {item.candidateEmail}
                          </span>
                        </span>
                        <span className="shrink-0 text-right text-xs text-slate-500">
                          <span className="block max-w-32 truncate">{item.jobTitle}</span>
                          <span className="block max-w-32 truncate">{item.jobDepartment}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </form>
              <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All departments" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All departments</SelectItem>
                  {departments.map((department) => (
                    <SelectItem key={department} value={department}>
                      {department}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={jobFilter} onValueChange={setJobFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All jobs" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All jobs</SelectItem>
                  {jobs.map(([id, title]) => (
                    <SelectItem key={id} value={String(id)}>
                      {title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {tab === "applicants" && (
                <Select
                  value={statusFilter}
                  onValueChange={setStatusFilter}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All statuses</SelectItem>
                    {STATUS_FILTER_OPTIONS.map((value) => (
                      <SelectItem key={value} value={value}>
                        {getApplicationStatusLabel(value)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </CardContent>
          </Card>

          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md">
            <table className="w-full table-fixed text-sm">
              <colgroup>
                {tab === "applicants" ? (
                  <>
                    <col className="w-[25%]" />
                    <col className="w-[25%]" />
                    <col className="w-[16%]" />
                    <col className="w-[17%]" />
                    <col className="w-[17%]" />
                  </>
                ) : (
                  <>
                    <col className="w-[30%]" />
                    <col className="w-[30%]" />
                    <col className="w-[24%]" />
                    <col className="w-[16%]" />
                  </>
                )}
              </colgroup>
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-4">
                    <SortButton
                      label="Candidate"
                      sortKey="candidate"
                      activeKey={sortKey}
                      ascending={ascending}
                      onClick={toggleSort}
                    />
                  </th>
                  <th className="px-6 py-4">Applied Job</th>
                  {tab === "applicants" && (
                    <th className="px-6 py-4">
                      <SortButton
                        label="Matching Score"
                        sortKey="score"
                        activeKey={sortKey}
                        ascending={ascending}
                        onClick={toggleSort}
                      />
                    </th>
                  )}
                  {tab === "applicants" && (
                    <th className="px-6 py-4">Status</th>
                  )}
                  {tab === "forms" && (
                    <th className="px-6 py-4">
                      <SortButton
                        label="Submission Date"
                        sortKey="date"
                        activeKey={sortKey}
                        ascending={ascending}
                        onClick={toggleSort}
                      />
                    </th>
                  )}
                  <th className="px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((item) => {
                  const applicant = item as Application;
                  const isApplicant = tab === "applicants";
                  const processing = isApplicant && isAnalysisProcessing(applicant.analysisStatus);
                  const analysisFailed =
                    isApplicant && applicant.analysisStatus?.toLowerCase() === "failed";
                  const form = item as EmploymentForm;

                  return (
                    <tr
                      key={isApplicant ? applicant.applicationId : form.submissionId}
                      onClick={() => isApplicant && openDetails(applicant)}
                      className={
                        isApplicant
                          ? "cursor-pointer transition-colors hover:bg-slate-50"
                          : "transition-colors hover:bg-slate-50"
                      }
                    >
                      <td className="px-6 py-5 align-middle">
                        <div className="flex min-w-0 items-center gap-3">
                          <span className="shrink-0 rounded-full bg-blue-50 p-2">
                            <UserRound className="h-4 w-4 text-[#003B7A]" />
                          </span>
                          <div className="min-w-0">
                            <div className="break-words font-medium leading-snug text-slate-900">
                              {item.candidateName}
                            </div>
                            <p className="mt-1 break-all text-xs text-slate-500">
                              {item.candidateEmail}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 align-middle">
                        <div className="break-words font-medium leading-snug text-[#003B7A]">
                          {item.jobTitle}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                          <span className="break-words">{item.jobDepartment}</span>
                          {isApplicant && (applicant as CandidateApplication).applicationCount > 1 && (
                            <span className="rounded-full bg-blue-50 px-2 py-0.5 font-medium text-[#003B7A]">
                              {(applicant as CandidateApplication).applicationCount} applications
                            </span>
                          )}
                        </div>
                      </td>
                      {isApplicant && (
                        <td className="px-6 py-5 align-middle font-semibold text-slate-800">
                          {processing
                            ? "-"
                            : analysisFailed
                            ? "0.0%"
                            : applicant.score === null || applicant.score === ""
                            ? "-"
                            : `${Number(applicant.score).toFixed(1)}%`}
                        </td>
                      )}
                      {isApplicant && (
                        <td className="px-6 py-5 align-middle">
                          <div className="flex flex-col items-start gap-2">
                            <Badge
                              className={`rounded-full border-transparent px-3 py-1 font-semibold ${getSoftApplicationStatusBadgeClass(applicant.status)}`}
                            >
                              {getApplicationStatusLabel(applicant.status)}
                            </Badge>
                            {processing && (
                              <Badge
                                className={`rounded-full border-transparent px-3 py-1 font-semibold ${getAnalysisStatusClass(applicant.analysisStatus)}`}
                              >
                                {/* Keep the visible analysis state tied to the persisted backend status. */}
                                {getAnalysisStatusLabel(applicant.analysisStatus)}
                              </Badge>
                            )}
                            {!processing && applicant.eligibilityStatus === "filtered_out" && (
                              <Badge
                                className={`rounded-full border-transparent px-3 py-1 font-semibold ${getEligibilityStatusClass(applicant.eligibilityStatus)}`}
                              >
                                {getEligibilityStatusLabel(applicant.eligibilityStatus)}
                              </Badge>
                            )}
                          </div>
                        </td>
                      )}
                      {!isApplicant && (
                        <td className="whitespace-nowrap px-6 py-5 align-middle text-slate-600">
                          <span className="inline-flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-slate-400" />
                            {formatEmploymentFormDate(form)}
                          </span>
                        </td>
                      )}
                      <td className="px-6 py-5 align-middle">
                        {isApplicant ? (
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(event) => {
                                event.stopPropagation();
                                openResumeDocuments(applicant);
                              }}
                            >
                              <FileText className="mr-1.5 h-3.5 w-3.5" />
                              Resume
                            </Button>

                            <Button variant="outline" size="sm" asChild>
                              <Link
                                to={`/jobs/${applicant.jobId}/candidates?applicationId=${applicant.applicationId}`}
                                onClick={(event) => event.stopPropagation()}
                              >
                                <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                                Candidate details
                              </Link>
                            </Button>

                          </div>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              window.open(
                                `/employment-form?view=hr&submissionId=${form.submissionId}`,
                                "_blank",
                              )
                            }
                          >
                            <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                            Open form
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {rows.length === 0 && (
              <div className="p-12 text-center text-slate-500">
                No records match these filters.
              </div>
            )}
          </div>

          {pagination(page, pageCount, setPage)}
        </div>
      )}

      <Dialog open={Boolean(opened)} onOpenChange={(open) => !open && setOpened(null)}>
        <DialogContent
          onOpenAutoFocus={(event) => event.preventDefault()}
          className="max-h-[84vh] w-[calc(100vw-2rem)] max-w-[calc(100vw-2rem)] overflow-y-auto sm:!w-[70vw] sm:!max-w-[70vw] [scrollbar-color:transparent_transparent] [scrollbar-width:thin] hover:[scrollbar-color:#94a3b8_transparent] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-transparent hover:[&::-webkit-scrollbar-thumb]:bg-slate-400"
        >
          <DialogHeader>
            <DialogTitle className="flex flex-wrap items-center gap-2">
              {opened?.candidateName}
              <Badge className="bg-slate-700 text-white">
                {history.length} application{history.length === 1 ? "" : "s"}
              </Badge>
              {formCount > 0 && (
                <Badge className="bg-cyan-600 text-white">
                  {formCount} form submission{formCount === 1 ? "" : "s"}
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              {opened?.candidateEmail} - Applied job history.
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Applied Job</th>
                  <th className="px-4 py-3">Department</th>
                  <th className="px-4 py-3">Submitted</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historyRows.map((item) => (
                  <tr key={item.applicationId}>
                    <td className="px-4 py-3 font-semibold text-[#003B7A]">
                      {item.jobTitle}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{item.jobDepartment}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatDate(item.submittedDate)}
                    </td>
                    <td className="px-4 py-3 font-semibold">
                      {item.score === null || item.score === ""
                        ? "-"
                        : `${Number(item.score).toFixed(1)}%`}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        className={`rounded-full border-transparent px-3 py-1 font-semibold ${getSoftApplicationStatusBadgeClass(item.status)}`}
                      >
                        {getApplicationStatusLabel(item.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" asChild>
                        <Link
                          to={`/jobs/${item.jobId}/candidates?search=${encodeURIComponent(
                            item.candidateEmail,
                          )}`}
                        >
                          View rank
                        </Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pagination(historyPage, historyCount, setHistoryPage)}
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(documentApplication)}
        onOpenChange={(open) => {
          if (!open) setDocumentApplication(null);
        }}
      >
        <DialogContent className="w-[calc(100vw-2rem)] max-w-xl overflow-hidden">
          <DialogHeader>
            <DialogTitle>Application Documents</DialogTitle>
            <DialogDescription>
              View all files uploaded by {documentApplication?.candidateName}.
            </DialogDescription>
          </DialogHeader>

          <div className="min-w-0 space-y-3 overflow-y-auto pr-1 sm:max-h-[60vh]">
            {documentApplication?.documents?.map((document) => (
              <div
                key={document.id}
                className="flex w-full min-w-0 items-center justify-between gap-3 rounded-lg border border-slate-200 p-4"
              >
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-blue-100">
                    <FileText className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {document.fileName}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {document.mimeType} · {(Number(document.fileSize) / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => window.open(document.fileUrl, "_blank")}
                >
                  Open
                </Button>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
}
