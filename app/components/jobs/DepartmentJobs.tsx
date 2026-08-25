// Shows the Department Jobs view.
import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router";
import { getCompactPageItems } from "../../lib/pagination";
import { formatDisplayDate } from "../../lib/date";
import { PageLayout } from "../shared/PageLayout";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import {
  Users,
  Eye,
  ExternalLink,
  Search,
  ChevronDown,
  Pencil,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  apiFetch,
  getStoredUser,
  type JobSummary,
} from "../../lib/api";
import { LoadingState } from "../shared/LoadingState";
import { SearchClearButton } from "../shared/SearchClearButton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";

type JobStatus = "active" | "closed" | "draft";

interface Job {
  id: string;
  title: string;
  department: string;
  status: JobStatus;
  applicants: number;
  newApplicants: number;
  avgScore: number;
  processRate: number;
  link: string | null;
  createdAt: string;
}

// Gets processed rate.
const getProcessedRate = (job: JobSummary) => {
  const processableApplicants = Math.max(
    0,
    Number(job.applicants) - Number(job.filteredOutCount),
  );
  const processedApplicants =
    Number(job.interviewCount) + Number(job.rejectedCount);

  return processableApplicants > 0
    ? Math.round((processedApplicants / processableApplicants) * 100)
    : 0;
};

// Provides the map api job helper.
const mapApiJob = (job: JobSummary): Job => ({
  id: String(job.id),
  title: job.title,
  department: job.department,
  status:
    job.status === "closed"
      ? "closed"
      : job.status === "active"
        ? "active"
        : "draft",
  applicants: Number(job.applicants),
  newApplicants: Number(job.newApplicants),
  avgScore: Number(job.avgScore),
  processRate: getProcessedRate(job),
  link: job.link ? `${window.location.origin}${job.link}` : null,
  createdAt: job.createdAt,
});

const JOBS_PER_PAGE = 10;

// Renders the Department Jobs component.
export function DepartmentJobs() {
  const { department } = useParams<{ department: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [searchQuery, setSearchQuery] = useState(
    () => searchParams.get("search") ?? "",
  );
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "closed" | "draft">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [isDepartmentEditOpen, setIsDepartmentEditOpen] = useState(false);
  const [departmentDraft, setDepartmentDraft] = useState("");
  const [isSavingDepartment, setIsSavingDepartment] = useState(false);
  const [isDepartmentDeleteOpen, setIsDepartmentDeleteOpen] = useState(false);
  const [isDeletingDepartment, setIsDeletingDepartment] = useState(false);

  useEffect(() => {
    setIsLoadingJobs(true);
    apiFetch<{ jobs: JobSummary[] }>("/jobs")
      .then((data) => setJobs(data.jobs.map(mapApiJob)))
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load jobs",
        ),
      )
      .finally(() => setIsLoadingJobs(false));
  }, []);

  // Continue a job search passed from the dashboard suggestion.
  useEffect(() => {
    setSearchQuery(searchParams.get("search") ?? "");
  }, [searchParams]);

  // Copies to clipboard.
  const copyToClipboard = (text: string, message: string) => {
    navigator.clipboard.writeText(text);
    toast.success(message);
  };

  // Updates the department for every job in this department.
  const handleUpdateDepartment = async () => {
    if (!department || isSavingDepartment) return;

    const nextDepartment = departmentDraft.trim();
    if (!nextDepartment) {
      toast.error("Department name is required");
      return;
    }

    if (nextDepartment === department) {
      setIsDepartmentEditOpen(false);
      return;
    }

    setIsSavingDepartment(true);
    try {
      const result = await apiFetch<{ updatedJobCount: number }>(
        "/departments",
        {
          method: "PATCH",
          body: JSON.stringify({
            department,
            newDepartment: nextDepartment,
            actionUserId: getStoredUser()?.id,
          }),
        },
      );

      setJobs((currentJobs) =>
        currentJobs.map((job) =>
          job.department === department
            ? { ...job, department: nextDepartment }
            : job,
        ),
      );
      setIsDepartmentEditOpen(false);
      toast.success(
        `Department updated for ${result.updatedJobCount} job${result.updatedJobCount === 1 ? "" : "s"}`,
      );
      navigate(`/departments/${encodeURIComponent(nextDepartment)}`, {
        replace: true,
      });
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update department",
      );
    } finally {
      setIsSavingDepartment(false);
    }
  };

  // Deletes every job that belongs to this department after confirmation.
  const handleDeleteDepartment = async () => {
    if (!department || isDeletingDepartment) return;

    setIsDeletingDepartment(true);
    try {
      const result = await apiFetch<{ deletedJobCount: number }>(
        "/departments",
        {
          method: "DELETE",
          body: JSON.stringify({
            department,
            actionUserId: getStoredUser()?.id,
          }),
        },
      );

      toast.success(
        `${result.deletedJobCount} job${result.deletedJobCount === 1 ? "" : "s"} deleted with the department`,
      );
      setIsDepartmentDeleteOpen(false);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to delete department",
      );
    } finally {
      setIsDeletingDepartment(false);
    }
  };

  const departmentJobs = useMemo(() => {
    return jobs.filter((job) => job.department === department);
  }, [jobs, department]);

  const filteredJobs = useMemo(() => {
    let filtered = departmentJobs;

    // Apply status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter((job) => job.status === statusFilter);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((job) =>
        job.title.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [departmentJobs, statusFilter, searchQuery]);
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
  }, [searchQuery, statusFilter, department]);

  const totalApplicants = departmentJobs.reduce(
    (sum, job) => sum + job.applicants,
    0,
  );
  const activeCount = departmentJobs.filter(
    (job) => job.status === "active",
  ).length;

  if (isLoadingJobs) {
    return (
      <PageLayout
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: department || "Department" },
        ]}
        title={`${department || "Department"} Department`}
        useCard={false}
      >
        <LoadingState title="Loading department jobs" />
      </PageLayout>
    );
  }

  if (!department || departmentJobs.length === 0) {
    return (
      <PageLayout
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Departments" },
        ]}
        title="Department Not Found"
        useCard={false}
      >
        <Card className="shadow-md">
          <CardContent className="pt-6">
            <p className="text-slate-600">
              No jobs found for this department.
            </p>
          </CardContent>
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: department },
      ]}
      title={
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="mb-2 text-3xl font-bold text-slate-900">
            {department} Department
          </h1>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setDepartmentDraft(department);
                setIsDepartmentEditOpen(true);
              }}
              aria-label="Edit department"
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit Department
            </Button>
          </div>
        </div>
      }
      subtitle={
        <div className="flex items-center gap-6">
          <span className="text-slate-600">
            {departmentJobs.length} position
            {departmentJobs.length !== 1 ? "s" : ""}
            <span className="mx-2 inline-block h-1 w-1 rounded-full bg-current align-middle" aria-hidden="true" />
            {activeCount} active
          </span>
          <span className="text-slate-600">
            {totalApplicants} total applicants
          </span>
        </div>
      }
      useCard={false}
    >
      {/* Search and Filter Section */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          {/* Search Bar */}
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search job positions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-10"
            />
            <SearchClearButton
              show={Boolean(searchQuery)}
              onClear={() => setSearchQuery("")}
            />
          </div>

          {/* Status Filter Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="min-w-[140px]">
                Status: {statusFilter === "all" ? "All" : statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)}
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => setStatusFilter("all")}>
                <div className="flex items-center justify-between w-full">
                  <span>All</span>
                  <Badge variant="outline" className="ml-2">
                    {departmentJobs.length}
                  </Badge>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("active")}>
                <div className="flex items-center justify-between w-full">
                  <span>Active</span>
                  <Badge variant="outline" className="ml-2 bg-green-50 text-green-700 border-green-200">
                    {departmentJobs.filter(j => j.status === "active").length}
                  </Badge>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("closed")}>
                <div className="flex items-center justify-between w-full">
                  <span>Closed</span>
                  <Badge variant="outline" className="ml-2 bg-slate-100 text-slate-600 border-slate-200">
                    {departmentJobs.filter(j => j.status === "closed").length}
                  </Badge>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("draft")}>
                <div className="flex items-center justify-between w-full">
                  <span>Draft</span>
                  <Badge variant="outline" className="ml-2 bg-amber-50 text-amber-700 border-amber-200">
                    {departmentJobs.filter(j => j.status === "draft").length}
                  </Badge>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Results count */}
        {(searchQuery || statusFilter !== "all") && (
          <div className="text-sm text-slate-600">
            Showing {filteredJobs.length} of {departmentJobs.length} position{filteredJobs.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6">
        {filteredJobs.length === 0 ? (
          <Card className="shadow-md">
            <CardContent className="pt-6 text-center">
              <p className="text-slate-600">
                No positions found matching your search criteria.
              </p>
            </CardContent>
          </Card>
        ) : (
          pagedJobs.map((job) => (
          <Card
            key={job.id}
            className="hover:shadow-lg transition-shadow duration-200 shadow-md"
          >
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-xl mb-2">
                    {job.title}
                  </CardTitle>
                  <CardDescription>
                    Created on{" "}
                    {formatDisplayDate(job.createdAt)}
                  </CardDescription>
                </div>
                <Badge
                  variant={
                    job.status === "active"
                      ? "default"
                      : job.status === "closed"
                        ? "secondary"
                        : "outline"
                  }
                  className={
                    job.status === "active"
                      ? "bg-green-600 text-white"
                      : job.status === "closed"
                        ? "bg-slate-600 text-white"
                        : ""
                  }
                >
                  {job.status.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-sm text-slate-500 mb-1">
                    Applicants
                  </div>
                  <div className="text-2xl font-semibold flex items-center gap-2">
                    {job.applicants}
                    {job.newApplicants > 0 && (
                      <Badge variant="outline" className="text-xs">
                        +{job.newApplicants} new
                      </Badge>
                    )}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-500 mb-1">
                    Avg Score
                  </div>
                  <div className="text-2xl font-semibold">
                    {job.avgScore > 0 ? job.avgScore : "—"}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-500 mb-1">
                    Process Rate
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={job.processRate}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium">
                      {job.processRate}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/jobs/${job.id}`)}
                >
                  <Eye className="w-4 h-4 mr-2" />
                  View Details
                </Button>

                {job.status === "active" && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        navigate(`/jobs/${job.id}/candidates`)
                      }
                    >
                      <Users className="w-4 h-4 mr-2" />
                      View Candidates
                    </Button>

                    {job.link && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          copyToClipboard(
                            job.link!,
                            "Job link copied to clipboard!",
                          )
                        }
                      >
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Copy Link
                      </Button>
                    )}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
          ))
        )}
      </div>
      {filteredJobs.length > JOBS_PER_PAGE && (
        <Pagination className="mt-6">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(event) => {
                  event.preventDefault();
                  setCurrentPage((page) => Math.max(1, page - 1));
                }}
                className={
                  currentPage === 1
                    ? "pointer-events-none opacity-50"
                    : ""
                }
              />
            </PaginationItem>
            {getCompactPageItems(currentPage, pageCount).map((item) => {
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
                    isActive={currentPage === item}
                    onClick={(event) => {
                      event.preventDefault();
                      setCurrentPage(item);
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
                  setCurrentPage((page) =>
                    Math.min(pageCount, page + 1),
                  );
                }}
                className={
                  currentPage === pageCount
                    ? "pointer-events-none opacity-50"
                    : ""
                }
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      <Dialog
        open={isDepartmentEditOpen}
        onOpenChange={(open) => {
          if (!isSavingDepartment) setIsDepartmentEditOpen(open);
        }}
      >
        <DialogContent
          className="sm:max-w-lg"
          onOpenAutoFocus={(event) => event.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Edit Department</DialogTitle>
            <DialogDescription>
              Rename this department. All jobs currently under it will be
              updated together.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label
              htmlFor="department-name"
              className="text-sm font-medium text-slate-900"
            >
              Department Name
            </label>
            <Input
              id="department-name"
              value={departmentDraft}
              onChange={(event) => setDepartmentDraft(event.target.value)}
              maxLength={120}
              disabled={isSavingDepartment}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              className="mr-auto border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700"
              onClick={() => {
                setIsDepartmentEditOpen(false);
                setIsDepartmentDeleteOpen(true);
              }}
              disabled={isSavingDepartment}
              aria-label="Delete department"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Department
            </Button>
            <Button
              type="button"
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
              onClick={() => void handleUpdateDepartment()}
              disabled={isSavingDepartment}
            >
              {isSavingDepartment ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={isDepartmentDeleteOpen}
        onOpenChange={(open) => {
          if (!isDeletingDepartment) setIsDepartmentDeleteOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Delete this department?</DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-3">
                <p>
                  This will permanently delete the department and all jobs
                  under it. The following jobs will be removed:
                </p>
                <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <ul className="space-y-2 text-sm text-slate-700">
                    {departmentJobs.map((job) => (
                      <li
                        key={job.id}
                        className="flex items-center justify-between gap-3 rounded-md bg-white px-3 py-2"
                      >
                        <span className="min-w-0 truncate font-medium text-slate-900">
                          {job.title}
                        </span>
                        <Badge
                          variant="outline"
                          className="shrink-0 text-xs uppercase"
                        >
                          {job.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </div>
                <p className="font-medium text-red-600">
                  This action cannot be undone.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              disabled={isDeletingDepartment}
              onClick={() => void handleDeleteDepartment()}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              {isDeletingDepartment ? "Deleting..." : "Delete Department"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageLayout>
  );
}


