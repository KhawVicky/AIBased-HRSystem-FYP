// Shows the Application List view.
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  ArrowDownUp,
  ArrowDown,
  ArrowUp,
  Calendar,
  Search,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "../../lib/api";
import { getApplicationStatusBadgeClass } from "../../lib/applicationStatus";
import { formatDisplayDateTime } from "../../lib/date";
import { getCompactPageItems } from "../../lib/pagination";
import { LoadingState } from "../shared/LoadingState";
import { PageLayout } from "../shared/PageLayout";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
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

type ApplicationListItem = {
  applicationId: number;
  candidateName: string;
  candidateEmail: string;
  jobId: number;
  jobTitle: string;
  jobDepartment: string;
  submittedDate: string;
  eligibilityStatus: string;
  score: string | number | null;
  status: string;
  scoreStatus: string;
};

const APPLICATIONS_PER_PAGE = 15;

const filterLabels: Record<string, string> = {
  all: "All Applications",
  last24: "New Applications",
  pending: "Pending Reviews",
};

// Provides the eligibility badge class helper.
const eligibilityBadgeClass = (status: string) => {
  if (status === "eligible") return "bg-green-50 text-green-700 border-green-200";
  if (status === "filtered_out") return "bg-slate-100 text-slate-600 border-slate-200";
  return "bg-amber-50 text-amber-700 border-amber-200";
};

// Formats date.
const formatDate = (value: string) => formatDisplayDateTime(value);

// Formats status.
const formatStatus = (value: string) =>
  value.replace(/_/g, " ").toUpperCase();

// Provides the score value helper.
const scoreValue = (value: string | number | null) => {
  if (value === null || value === "") return Number.NEGATIVE_INFINITY;

  const score = Number(value);
  return Number.isNaN(score) ? Number.NEGATIVE_INFINITY : score;
};

// Renders the Application List component.
export function ApplicationList() {
  const [searchParams] = useSearchParams();
  const filter = searchParams.get("filter") || "all";
  const [applications, setApplications] = useState<ApplicationListItem[]>(
    [],
  );
  const [isLoadingApplications, setIsLoadingApplications] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [searchFocused, setSearchFocused] = useState(false);
  const [scoreSort, setScoreSort] = useState<"none" | "desc" | "asc">(
    "none",
  );
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setIsLoadingApplications(true);
    setSelectedApplicationId(null);
    apiFetch<{ applications: ApplicationListItem[] }>(
      `/applications?filter=${filter}`,
    )
      .then((data) => setApplications(data.applications))
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load applications",
        ),
      )
      .finally(() => setIsLoadingApplications(false));
  }, [filter]);

  const filteredApplications = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    const filtered = selectedApplicationId !== null
      ? applications.filter((application) => application.applicationId === selectedApplicationId)
      : keyword
      ? applications.filter(
          (application) =>
            application.candidateName.toLowerCase().includes(keyword) ||
            application.candidateEmail.toLowerCase().includes(keyword) ||
            application.jobTitle.toLowerCase().includes(keyword) ||
            application.jobDepartment.toLowerCase().includes(keyword),
        )
      : applications;

    if (scoreSort === "none") return filtered;

    return [...filtered].sort((a, b) => {
      const scoreA = scoreValue(a.score);
      const scoreB = scoreValue(b.score);
      const scoreDiff =
        scoreSort === "desc" ? scoreB - scoreA : scoreA - scoreB;

      if (scoreDiff !== 0) return scoreDiff;

      return (
        new Date(b.submittedDate).getTime() -
        new Date(a.submittedDate).getTime()
      );
    });
  }, [applications, searchQuery, scoreSort, selectedApplicationId]);

  const applicationSearchSuggestions = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword || selectedApplicationId !== null) return [];

    return applications
      .filter(
        (application) =>
          application.candidateName.toLowerCase().startsWith(keyword) ||
          application.candidateEmail.toLowerCase().startsWith(keyword) ||
          application.jobTitle.toLowerCase().startsWith(keyword) ||
          application.jobDepartment.toLowerCase().startsWith(keyword),
      )
      .sort((first, second) =>
        first.candidateName.localeCompare(second.candidateName, undefined, { sensitivity: "base" }),
      )
      .slice(0, 8);
  }, [applications, searchQuery, selectedApplicationId]);

  const pageCount = Math.max(
    1,
    Math.ceil(filteredApplications.length / APPLICATIONS_PER_PAGE),
  );
  const pagedApplications = filteredApplications.slice(
    (currentPage - 1) * APPLICATIONS_PER_PAGE,
    currentPage * APPLICATIONS_PER_PAGE,
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [filter, searchQuery, scoreSort, selectedApplicationId]);

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: filterLabels[filter] || "Applications" },
      ]}
      title={filterLabels[filter] || "Applications"}
      subtitle="Review candidate applications across job posts."
      useCard={false}
    >
      {isLoadingApplications ? (
        <LoadingState title="Loading applications" />
      ) : (
        <div className="space-y-6">
          <Card className="shadow-md">
            <CardContent className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
              <div className="relative w-full md:w-[420px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search candidate, email, job or department"
                  value={searchQuery}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck={false}
                  name="application-list-filter"
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    setSelectedApplicationId(null);
                  }}
                  onFocus={() => setSearchFocused(true)}
                  onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
                  className="pl-9 pr-10"
                />
                <SearchClearButton
                  show={Boolean(searchQuery)}
                  onClear={() => {
                    setSearchQuery("");
                    setSelectedApplicationId(null);
                    setSearchFocused(false);
                  }}
                />
                {searchFocused && applicationSearchSuggestions.length > 0 && (
                  <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                    {applicationSearchSuggestions.map((application) => (
                      <button
                        key={application.applicationId}
                        type="button"
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setSelectedApplicationId(application.applicationId);
                          setSearchQuery(`${application.candidateName}`);
                          setSearchFocused(false);
                        }}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-slate-950">
                            {application.candidateName}
                          </span>
                          <span className="block truncate text-xs text-slate-500">
                            {application.candidateEmail}
                          </span>
                        </span>
                        <span className="shrink-0 text-right text-xs text-slate-500">
                          <span className="block max-w-32 truncate">{application.jobTitle}</span>
                          <span className="block max-w-32 truncate">{application.jobDepartment}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {[
                  ["all", "All"],
                  ["last24", "Last 24 Hours"],
                  ["pending", "Pending Review"],
                ].map(([value, label]) => (
                  <Button
                    key={value}
                    variant={filter === value ? "default" : "outline"}
                    className={
                      filter === value
                        ? "bg-[#003B7A] text-white hover:bg-[#002f63]"
                        : ""
                    }
                    asChild
                  >
                    <Link to={`/applications?filter=${value}`}>
                      {label}
                    </Link>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-md">
            <table className="w-full min-w-[1120px] table-fixed text-sm">
              <colgroup>
                <col className="w-[30%]" />
                <col className="w-[18%]" />
                <col className="w-[20%]" />
                <col className="w-[12%]" />
                <col className="w-[8%]" />
                <col className="w-[12%]" />
              </colgroup>
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-4">Candidate</th>
                  <th className="px-6 py-4">Job Applied</th>
                  <th className="px-6 py-4">Submitted Date</th>
                  <th className="px-6 py-4">Eligibility Status</th>
                  <th className="px-6 py-4">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-[#003B7A]"
                      onClick={() =>
                        setScoreSort((current) =>
                          current === "none"
                            ? "desc"
                            : current === "desc"
                              ? "asc"
                              : "none",
                        )
                      }
                    >
                      Score
                      {scoreSort === "asc" ? (
                        <ArrowUp className="h-3.5 w-3.5" />
                      ) : scoreSort === "desc" ? (
                        <ArrowDown className="h-3.5 w-3.5" />
                      ) : (
                        <ArrowDownUp className="h-3.5 w-3.5 text-slate-300" />
                      )}
                    </button>
                  </th>
                  <th className="px-6 py-4">Current Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pagedApplications.map((application) => (
                  <tr
                    key={application.applicationId}
                    className="transition-colors hover:bg-slate-50"
                  >
                    <td className="px-6 py-5">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="shrink-0 rounded-full bg-blue-50 p-2">
                          <UserRound className="h-4 w-4 text-[#003B7A]" />
                        </span>
                        <div className="min-w-0">
                          <Link
                            to={`/jobs/${application.jobId}/candidates?search=${encodeURIComponent(application.candidateEmail)}`}
                            className="block max-w-full break-words font-medium leading-snug text-slate-900 hover:text-[#003B7A]"
                          >
                            {application.candidateName}
                          </Link>
                          <p className="mt-1 break-all text-xs text-slate-500">
                            {application.candidateEmail}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5 align-top">
                      <Link
                        to={`/jobs/${application.jobId}`}
                        className="block break-words font-medium leading-snug text-[#003B7A] hover:underline"
                      >
                        {application.jobTitle}
                      </Link>
                      <p className="text-xs text-slate-500">
                        {application.jobDepartment}
                      </p>
                    </td>
                    <td className="whitespace-nowrap px-6 py-5 text-slate-700">
                      <span className="inline-flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-slate-400" />
                        {formatDate(application.submittedDate)}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <Badge
                        variant="outline"
                        className={eligibilityBadgeClass(
                          application.eligibilityStatus,
                        )}
                      >
                        {formatStatus(application.eligibilityStatus)}
                      </Badge>
                    </td>
                    <td className="px-6 py-5 text-slate-700">
                      {application.score === null ||
                      application.score === ""
                        ? application.scoreStatus
                        : Number(application.score).toFixed(1)}
                    </td>
                    <td className="px-6 py-5">
                      <Badge className={getApplicationStatusBadgeClass(application.status)}>
                        {formatStatus(application.status)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredApplications.length === 0 && (
              <div className="p-12 text-center text-slate-500">
                No applications match this filter.
              </div>
            )}
          </div>

          {filteredApplications.length > APPLICATIONS_PER_PAGE && (
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
