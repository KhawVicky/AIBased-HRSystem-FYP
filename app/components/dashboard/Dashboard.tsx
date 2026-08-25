// Shows the Dashboard view.
import { useMemo, useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { getCompactPageItems } from "../../lib/pagination";
import { Button } from "../ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";
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
  Briefcase,
  Users,
  FileText,
  Plus,
  ExternalLink,
  Eye,
  Upload,
  TrendingUp,
  BarChart3,
  ChevronRight,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import {
  apiFetch,
  type JobSummary,
} from "../../lib/api";
import { LoadingState } from "../shared/LoadingState";
import { HrHeader } from "../shared/HrHeader";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Input } from "../ui/input";

type JobStatus = "active" | "closed" | "draft";

interface Job {
  id: string;
  title: string;
  department: string;
  status: JobStatus;
  applicants: number;
  newApplicants: number;
  avgScore: number;
  link: string | null;
  createdAt: string;
}

type JobPositionSearchSuggestion = {
  type: "job" | "department";
  value: string;
  detail: string;
};

type DashboardSummary = {
  activeJobs: string | number;
  recentApplications: string | number;
  pendingReview: string | number;
};

// Convert API job values for dashboard cards.
const mapApiJob = (job: JobSummary): Job => ({
  id: String(job.id),
  title: job.title,
  department: job.department,
  status: job.status === "closed" ? "closed" : job.status === "active" ? "active" : "draft",
  applicants: Number(job.applicants),
  newApplicants: Number(job.newApplicants),
  avgScore: Number(job.avgScore),
  link: job.link ? `${window.location.origin}${job.link}` : null,
  createdAt: job.createdAt,
});

const DEPARTMENTS_PER_PAGE = 10;

// Renders the Dashboard component.
export function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<DashboardSummary>({
    activeJobs: 0,
    recentApplications: 0,
    pendingReview: 0,
  });
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [departmentSearch, setDepartmentSearch] = useState("");
  const [selectedJobSearch, setSelectedJobSearch] = useState<string | null>(null);
  const [departmentSearchFocused, setDepartmentSearchFocused] = useState(false);
  const [departmentPage, setDepartmentPage] = useState(1);
  const navigate = useNavigate();

  // Load the summary and job cards in one request.
  useEffect(() => {
    setIsLoadingJobs(true);
    apiFetch<{ summary: DashboardSummary; jobs: JobSummary[] }>(
      "/dashboard",
    )
      .then((data) => {
        setSummary(data.summary);
        setJobs(data.jobs.map(mapApiJob));
      })
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load jobs",
        ),
      )
      .finally(() => setIsLoadingJobs(false));
  }, []);

  // Keep job cards current after a status change.
  useEffect(() => {
    // Handles status update.
    const handleStatusUpdate = (event: CustomEvent) => {
      const { jobId, status } = event.detail;
      setJobs((prevJobs) =>
        prevJobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: status as JobStatus,
              }
            : job,
        ),
      );
    };

    window.addEventListener(
      "jobStatusUpdated",
      handleStatusUpdate as EventListener,
    );
    return () => {
      window.removeEventListener(
        "jobStatusUpdated",
        handleStatusUpdate as EventListener,
      );
    };
  }, []);

  // Copies to clipboard.
  const copyToClipboard = async (
    text: string,
    successMessage: string,
  ) => {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        toast.success(successMessage);
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          document.execCommand("copy");
          toast.success(successMessage);
        } catch (err) {
          toast.error("Failed to copy to clipboard");
        }
        textArea.remove();
      }
    } catch (err) {
      // Fallback method
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand("copy");
        toast.success(successMessage);
      } catch (error) {
        toast.error("Failed to copy to clipboard");
      }
      textArea.remove();
    }
  };

  const activeJobs = Number(summary.activeJobs ?? 0);
  const newApplications = Number(summary.recentApplications ?? 0);
  const pendingReviews = Number(summary.pendingReview ?? 0);
  const searchTerm = departmentSearch.trim().toLowerCase();
  const jobPositionSearchSuggestions = useMemo<JobPositionSearchSuggestion[]>(() => {
    if (!searchTerm) return [];

    const suggestions = new Map<string, JobPositionSearchSuggestion>();
    jobs.forEach((job) => {
      const title = job.title.trim();
      const department = job.department.trim();

      if (title.toLowerCase().includes(searchTerm)) {
        suggestions.set(`job:${title.toLowerCase()}`, {
          type: "job",
          value: title,
          detail: department,
        });
      }

      if (department.toLowerCase().includes(searchTerm)) {
        suggestions.set(`department:${department.toLowerCase()}`, {
          type: "department",
          value: department,
          detail: `${jobs.filter((item) => item.department === department).length} positions`,
        });
      }
    });

    return Array.from(suggestions.values())
      .sort((first, second) => first.value.localeCompare(second.value, undefined, { sensitivity: "base" }))
      .slice(0, 8);
  }, [jobs, searchTerm]);
  const filteredJobs = jobs.filter((job) =>
    !searchTerm ||
    job.department.toLowerCase().includes(searchTerm) ||
    job.title.toLowerCase().includes(searchTerm),
  );
  const departments = Array.from(
    new Set(filteredJobs.map((job) => job.department)),
  ).sort((first, second) =>
    first.localeCompare(second, undefined, { sensitivity: "base" }),
  );
  const departmentPageCount = Math.max(
    1,
    Math.ceil(departments.length / DEPARTMENTS_PER_PAGE),
  );
  const pagedDepartments = departments.slice(
    (departmentPage - 1) * DEPARTMENTS_PER_PAGE,
    departmentPage * DEPARTMENTS_PER_PAGE,
  );

  useEffect(() => {
    setDepartmentPage(1);
  }, [departmentSearch, departments.length]);

  return (
    <div className="min-h-screen bg-slate-50">
      <HrHeader sticky horizontalPaddingClassName="px-4 sm:px-6 lg:px-8" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoadingJobs ? (
          <LoadingState title="Loading dashboard data" />
        ) : (
          <>
        {/* Dashboard overview */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-6">Overview</h1>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card
              className="cursor-pointer shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
              role="button"
              tabIndex={0}
              onClick={() => navigate("/jobs?status=active")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  navigate("/jobs?status=active");
                }
              }}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Active Jobs
                </CardTitle>
                <Briefcase className="h-5 w-5 text-[#003B7A]" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {activeJobs}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  View open job posts
                </p>
              </CardContent>
            </Card>

            <Card
              className="cursor-pointer shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
              role="button"
              tabIndex={0}
              onClick={() => navigate("/applications?filter=last24")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  navigate("/applications?filter=last24");
                }
              }}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  New Applications
                </CardTitle>
                <TrendingUp className="h-5 w-5 text-[#003B7A]" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {newApplications}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  In the last 24 hours
                </p>
              </CardContent>
            </Card>

            <Card
              className="cursor-pointer shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
              role="button"
              tabIndex={0}
              onClick={() => navigate("/applications?filter=pending")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  navigate("/applications?filter=pending");
                }
              }}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Pending Reviews
                </CardTitle>
                <FileText className="h-5 w-5 text-[#003B7A]" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {pendingReviews}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Applications waiting for review
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Job Posts Section */}
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center">
          <h2 className="shrink-0 text-2xl font-bold text-slate-900">
            Job Positions
          </h2>
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <div className="relative w-full sm:w-72 lg:w-80">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search job title or department"
                value={departmentSearch}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                name="job-position-filter"
                onChange={(event) => {
                  setDepartmentSearch(event.target.value);
                  setSelectedJobSearch(null);
                }}
                onFocus={() => setDepartmentSearchFocused(true)}
                onBlur={() => window.setTimeout(() => setDepartmentSearchFocused(false), 120)}
                className="pl-9 pr-10"
              />
              <SearchClearButton
                show={Boolean(departmentSearch)}
                onClear={() => {
                  setDepartmentSearch("");
                  setSelectedJobSearch(null);
                  setDepartmentSearchFocused(false);
                }}
              />
              {departmentSearchFocused && jobPositionSearchSuggestions.length > 0 && (
                <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                  {jobPositionSearchSuggestions.map((suggestion) => (
                    <button
                      key={`${suggestion.type}:${suggestion.value}`}
                      type="button"
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors hover:bg-slate-50"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => {
                        setDepartmentSearch(suggestion.value);
                        setSelectedJobSearch(
                          suggestion.type === "job" ? suggestion.value : null,
                        );
                        setDepartmentSearchFocused(false);
                      }}
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-100 text-[#003B7A]">
                        {suggestion.type === "job" ? (
                          <Briefcase className="h-4 w-4" />
                        ) : (
                          <Users className="h-4 w-4" />
                        )}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-slate-900">
                          {suggestion.value}
                        </span>
                        <span className="block truncate text-xs text-slate-500">
                          {suggestion.type === "job" ? "Job title" : "Department"} · {suggestion.detail}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button
              onClick={() => navigate("/jobs/create")}
              className="shrink-0 bg-[#003B7A] px-5 text-white shadow-sm hover:bg-[#002f63]"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create New Job
            </Button>
          </div>
        </div>

        {/* Department grouped view */}
        <div className="grid grid-cols-1 gap-6">
          {pagedDepartments.map((department) => {
            const departmentJobs = filteredJobs.filter(job => job.department === department);
            const totalApplicants = departmentJobs.reduce((sum, job) => sum + job.applicants, 0);
            const activeCount = departmentJobs.filter(job => job.status === 'active').length;

            return (
              <Card
                key={department}
                className="shadow-md cursor-pointer hover:shadow-lg transition-all duration-200"
                onClick={() => {
                  const searchParam = selectedJobSearch
                    ? `?search=${encodeURIComponent(selectedJobSearch)}`
                    : "";
                  navigate(
                    `/departments/${encodeURIComponent(department)}${searchParam}`,
                  );
                }}
              >
                <CardHeader className="hover:bg-slate-50 transition-colors px-[24px] pt-[10px] pb-[0px]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      
                      <div>
                        <CardTitle className="text-xl">{department}</CardTitle>
                        <CardDescription className="mt-1">
                          {departmentJobs.length} position{departmentJobs.length !== 1 ? 's' : ''}
                          <span className="mx-2 inline-block h-1 w-1 rounded-full bg-current align-middle" aria-hidden="true" />
                          {activeCount} active
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm text-slate-500">Total Applicants</div>
                        <div className="text-2xl font-bold text-slate-900">{totalApplicants}</div>
                      </div>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            );
          })}
          {pagedDepartments.length === 0 && (
            <Card className="shadow-md">
              <CardContent className="p-8 text-center text-slate-500">
                No job positions match your search.
              </CardContent>
            </Card>
          )}
        </div>
        {departments.length > DEPARTMENTS_PER_PAGE && (
          <Pagination className="mt-6">
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(event) => {
                    event.preventDefault();
                    setDepartmentPage((page) => Math.max(1, page - 1));
                  }}
                  className={
                    departmentPage === 1
                      ? "pointer-events-none opacity-50"
                      : ""
                  }
                />
              </PaginationItem>
              {getCompactPageItems(
                departmentPage,
                departmentPageCount,
              ).map((item) => {
                if (typeof item === "string") {
                  return (
                    <PaginationItem key={item}>
                      <PaginationEllipsis />
                    </PaginationItem>
                  );
                }

                return (
                  <PaginationItem key={item}>
                    <PaginationLink
                      href="#"
                      isActive={departmentPage === item}
                      onClick={(event) => {
                        event.preventDefault();
                        setDepartmentPage(item);
                      }}
                    >
                      {item}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(event) => {
                    event.preventDefault();
                    setDepartmentPage((page) =>
                      Math.min(departmentPageCount, page + 1),
                    );
                  }}
                  className={
                    departmentPage === departmentPageCount
                      ? "pointer-events-none opacity-50"
                      : ""
                  }
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}
          </>
        )}
      </div>
    </div>
  );
}

