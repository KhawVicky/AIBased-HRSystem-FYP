// Shows the Job Management view.
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Briefcase, MapPin, Search } from "lucide-react";
import { toast } from "sonner";

import { apiFetch, getStoredUser, type JobSummary } from "../../lib/api";
import { formatDisplayDate } from "../../lib/date";
import { getCompactPageItems } from "../../lib/pagination";
import { LoadingState } from "../shared/LoadingState";
import { PageLayout } from "../shared/PageLayout";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Input } from "../ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "../ui/tooltip";

const JOBS_PER_PAGE = 10;

// Provides the status badge class helper.
const statusBadgeClass = (status: string) => {
  if (status === "closed") return "bg-slate-600 text-white";
  if (status === "draft") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "bg-green-600 text-white";
};

// Gets job ui status.
const getJobUiStatus = (status: string) =>
  status === "closed" ? "closed" : status === "draft" ? "draft" : "active";

// Provides the status label helper.
const statusLabel = (status: string) =>
  getJobUiStatus(status) === "closed"
    ? "CLOSED"
    : getJobUiStatus(status) === "draft"
      ? "DRAFT"
      : "OPEN";

// Provides the next status helper.
const nextStatus = (status: string) =>
  getJobUiStatus(status) === "closed" ? "active" : "closed";

// Provides the status action label helper.
const statusActionLabel = (status: string) =>
  getJobUiStatus(status) === "closed" ? "open job" : "close job";

// Provides the status action title helper.
const statusActionTitle = (status: string) =>
  getJobUiStatus(status) === "closed"
    ? "Click to open job"
    : "Click to close job";

const statusFilterOptions = [
  { value: "all", label: "All" },
  { value: "active", label: "Open" },
  { value: "closed", label: "Closed" },
  { value: "draft", label: "Draft" },
];

// Normalizes status filter.
const normalizeStatusFilter = (status: string | null) =>
  status === "active" || status === "closed" || status === "draft"
    ? status
    : "all";

// Formats date.
const formatDate = (value: string | null) => {
  return formatDisplayDate(value);
};

// Renders the Job Management component.
export function JobManagement() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialStatus = normalizeStatusFilter(searchParams.get("status"));
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [currentPage, setCurrentPage] = useState(1);
  const [statusConfirmJob, setStatusConfirmJob] =
    useState<JobSummary | null>(null);
  const [savingStatusJobIds, setSavingStatusJobIds] = useState<Set<number>>(
    new Set(),
  );

  useEffect(() => {
    setIsLoadingJobs(true);
    apiFetch<{ jobs: JobSummary[] }>("/jobs")
      .then((data) => setJobs(data.jobs))
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load job posts",
        ),
      )
      .finally(() => setIsLoadingJobs(false));
  }, []);

  useEffect(() => {
    setStatusFilter(normalizeStatusFilter(searchParams.get("status")));
  }, [searchParams]);

  const filteredJobs = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();

    return jobs.filter((job) => {
      const matchesStatus =
        statusFilter === "all" || getJobUiStatus(job.status) === statusFilter;
      const matchesSearch =
        !keyword ||
        job.title.toLowerCase().includes(keyword) ||
        job.department.toLowerCase().includes(keyword) ||
        job.location.toLowerCase().includes(keyword);

      return matchesStatus && matchesSearch;
    });
  }, [jobs, searchQuery, statusFilter]);

  const pageCount = Math.max(
    1,
    Math.ceil(filteredJobs.length / JOBS_PER_PAGE),
  );
  const pagedJobs = filteredJobs.slice(
    (currentPage - 1) * JOBS_PER_PAGE,
    currentPage * JOBS_PER_PAGE,
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, statusFilter]);

  // Handles status change.
  const handleStatusChange = async (jobId: number, nextStatus: string) => {
    const currentJob = jobs.find((job) => job.id === jobId);
    if (!currentJob || currentJob.status === nextStatus) return;

    const previousStatus = currentJob.status;
    setSavingStatusJobIds((current) => new Set(current).add(jobId));
    setJobs((current) =>
      current.map((job) =>
        job.id === jobId ? { ...job, status: nextStatus as JobSummary["status"] } : job,
      ),
    );

    try {
      await apiFetch(`/jobs/${jobId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: nextStatus,
          actionUserId: getStoredUser()?.id,
        }),
      });
      toast.success("Job status updated successfully");
    } catch (error) {
      setJobs((current) =>
        current.map((job) =>
          job.id === jobId ? { ...job, status: previousStatus } : job,
        ),
      );
      toast.error(
        error instanceof Error ? error.message : "Failed to update job status",
      );
    } finally {
      setSavingStatusJobIds((current) => {
        const next = new Set(current);
        next.delete(jobId);
        return next;
      });
    }
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: "Job Management" },
      ]}
      title="Job Management"
      subtitle="View and manage job posts by status."
      useCard={false}
    >
      {isLoadingJobs ? (
        <LoadingState title="Loading job posts" />
      ) : (
        <div className="space-y-6">
          <Card className="shadow-md">
            <CardContent className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
              <div className="relative w-full md:w-[420px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search job title or department"
                  value={searchQuery}
                  onChange={(event) =>
                    setSearchQuery(event.target.value)
                  }
                  className="pl-9 pr-10"
                />
                <SearchClearButton
                  show={Boolean(searchQuery)}
                  onClear={() => setSearchQuery("")}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                {statusFilterOptions.map((status) => (
                  <Button
                    key={status.value}
                    variant={
                      statusFilter === status.value ? "default" : "outline"
                    }
                    className={
                      statusFilter === status.value
                        ? "bg-[#003B7A] text-white hover:bg-[#002f63]"
                        : ""
                    }
                    onClick={() => setStatusFilter(status.value)}
                  >
                    {status.label}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md">
            <table className="w-full min-w-[920px] text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-4">Job Title</th>
                  <th className="px-6 py-4">Department</th>
                  <th className="px-6 py-4">Location</th>
                  <th className="px-6 py-4">Applications</th>
                  <th className="px-6 py-4">Published Date</th>
                  <th className="px-6 py-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pagedJobs.map((job) => (
                  <tr
                    key={job.id}
                    className="cursor-pointer transition-colors hover:bg-slate-50"
                    onClick={() => navigate(`/jobs/${job.id}`)}
                  >
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <span className="rounded-lg bg-blue-50 p-2">
                          <Briefcase className="h-4 w-4 text-[#003B7A]" />
                        </span>
                        <span className="font-medium text-slate-900">
                          {job.title}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-slate-700">
                      {job.department}
                    </td>
                    <td className="px-6 py-5 text-slate-700">
                      <span className="inline-flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-slate-400" />
                        {job.location}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-slate-700">
                      {job.applicants}
                    </td>
                    <td className="px-6 py-5 text-slate-700">
                      {formatDate(job.publishedAt || job.createdAt)}
                    </td>
                    <td className="px-6 py-5">
                      {getJobUiStatus(job.status) === "draft" ? (
                        <Badge className={statusBadgeClass("draft")}>
                          DRAFT
                        </Badge>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setStatusConfirmJob(job);
                              }}
                              onPointerDown={(event) => event.stopPropagation()}
                              disabled={savingStatusJobIds.has(job.id)}
                              className="inline-flex rounded-full disabled:cursor-not-allowed disabled:opacity-70"
                              aria-label={statusActionTitle(job.status)}
                            >
                              <Badge
                                className={`${statusBadgeClass(
                                  getJobUiStatus(job.status),
                                )} cursor-pointer transition-opacity hover:opacity-85`}
                              >
                                {savingStatusJobIds.has(job.id)
                                  ? "SAVING"
                                  : statusLabel(job.status)}
                              </Badge>
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            {statusActionTitle(job.status)}
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredJobs.length === 0 && (
              <div className="p-12 text-center text-slate-500">
                No job posts match this filter.
              </div>
            )}
          </div>

          <Dialog
            open={Boolean(statusConfirmJob)}
            onOpenChange={(open) => {
              if (!open) setStatusConfirmJob(null);
            }}
          >
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>
                  {statusConfirmJob &&
                  getJobUiStatus(statusConfirmJob.status) === "closed"
                    ? "Open this job?"
                    : "Close this job?"}
                </DialogTitle>
                <DialogDescription>
                  {statusConfirmJob
                    ? `This will ${statusActionLabel(statusConfirmJob.status)} for ${statusConfirmJob.title}.`
                    : ""}
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  className="border-slate-300 text-slate-700 hover:bg-slate-50"
                  onClick={() => setStatusConfirmJob(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  className={
                    statusConfirmJob &&
                    getJobUiStatus(statusConfirmJob.status) === "closed"
                      ? "bg-[#003B7A] text-white hover:bg-[#002f63]"
                      : "bg-slate-700 text-white hover:bg-slate-800"
                  }
                  onClick={() => {
                    if (!statusConfirmJob) return;
                    handleStatusChange(
                      statusConfirmJob.id,
                      nextStatus(statusConfirmJob.status),
                    );
                    setStatusConfirmJob(null);
                  }}
                >
                  {statusConfirmJob &&
                  getJobUiStatus(statusConfirmJob.status) === "closed"
                    ? "Open Job"
                    : "Close Job"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {filteredJobs.length > JOBS_PER_PAGE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    className={
                      currentPage === 1
                        ? "pointer-events-none opacity-50"
                        : ""
                    }
                    onClick={(event) => {
                      event.preventDefault();
                      setCurrentPage((page) => Math.max(1, page - 1));
                    }}
                  />
                </PaginationItem>
                {getCompactPageItems(currentPage, pageCount).map(
                  (item) => (
                    <PaginationItem key={item}>
                      {typeof item === "number" ? (
                        <PaginationLink
                          href="#"
                          isActive={item === currentPage}
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
                  ),
                )}
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    className={
                      currentPage === pageCount
                        ? "pointer-events-none opacity-50"
                        : ""
                    }
                    onClick={(event) => {
                      event.preventDefault();
                      setCurrentPage((page) =>
                        Math.min(pageCount, page + 1),
                      );
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )}
        </div>
      )}
    </PageLayout>
  );
}
