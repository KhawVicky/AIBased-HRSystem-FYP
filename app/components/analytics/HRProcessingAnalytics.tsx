// Shows HR processing analytics.
import { useEffect, useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Download,
  Info,
  Mail,
  Maximize2,
  RotateCcw,
  TrendingUp,
  UsersRound,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDisplayDate } from "../../lib/date";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { useIsMobile } from "../ui/use-mobile";

export type ProcessingAnalyticsItem = {
  candidateName: string;
  candidateEmail: string;
  jobId: number;
  jobTitle: string;
  jobDepartment: string;
  currentStatus?:
    | "new"
    | "reviewed"
    | "shortlisted"
    | "interview"
    | "interviewed"
    | "hired"
    | "rejected"
    | "withdrawn"
    | "filtered_out";
  applicationDate: string;
  lastActionDate: string | null;
  processingMinutes: number | null;
  processingStatus:
    | "reviewed"
    | "shortlisted"
    | "interview"
    | "interviewed"
    | "hired"
    | "rejected"
    | "withdrawn"
    | "filtered_out"
    | "interview_email_sent"
    | "rejection_email_sent";
  followUpStatus?: "rejected" | "interviewed" | "rejection_email_sent" | null;
  emailOutcome: "interview" | "reject" | null;
  hrAssigned: string;
};

export type ProcessingAnalyticsJobOption = {
  id: number;
  title: string;
  department: string;
  status: string;
};

type DateRangeFilter = "last7" | "last30" | "last3months" | "custom";
type ExpandedChart = "trend" | "hr" | null;

type AnalyticsFilters = {
  dateRange: DateRangeFilter;
  jobId: string;
  department: string;
  emailOutcome: "all" | "interview" | "reject";
  customStart: string;
  customEnd: string;
};

const initialFilters: AnalyticsFilters = {
  dateRange: "last30",
  jobId: "all",
  department: "all",
  emailOutcome: "all",
  customStart: "",
  customEnd: "",
};

// Checks the completed processing item condition.
const isCompletedProcessingItem = (item: ProcessingAnalyticsItem) =>
  item.processingMinutes !== null &&
  (item.currentStatus === "hired" ||
    item.currentStatus === "rejected" ||
    item.processingStatus === "hired" ||
    item.processingStatus === "rejected" ||
    item.processingStatus === "rejection_email_sent");

// Parses date.
const parseDate = (value: string) =>
  new Date(value.includes(" ") ? value.replace(" ", "T") : value);

// Starts of day.
const startOfDay = (date: Date) => {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  return result;
};

// Provides the end of day helper.
const endOfDay = (date: Date) => {
  const result = new Date(date);
  result.setHours(23, 59, 59, 999);
  return result;
};

// Formats duration.
const formatDuration = (minutes: number) => {
  const roundedMinutes = Math.max(0, Math.round(minutes));
  if (roundedMinutes < 60) {
    return `${roundedMinutes} ${roundedMinutes === 1 ? "minute" : "minutes"}`;
  }

  const totalHours = Math.floor(roundedMinutes / 60);
  if (totalHours < 24) {
    return `${totalHours} ${totalHours === 1 ? "hour" : "hours"}`;
  }

  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  return hours === 0
    ? `${days} ${days === 1 ? "day" : "days"}`
    : `${days} ${days === 1 ? "day" : "days"} ${hours} ${
        hours === 1 ? "hour" : "hours"
      }`;
};

// Formats days.
const formatDays = (minutes: number) => `${(minutes / 1440).toFixed(1)} days`;

// Escapes csv.
const escapeCsv = (value: string | number) =>
  `"${String(value).replace(/"/g, '""')}"`;

// Downloads csv.
const downloadCsv = (fileName: string, rows: Array<Array<string | number>>) => {
  const content = rows.map((row) => row.map(escapeCsv).join(",")).join("\r\n");
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
};

// Formats long date.
const formatLongDate = (value: string) =>
  parseDate(value).toLocaleDateString("en-MY", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

// Formats short date.
const formatShortDate = (value: string) =>
  parseDate(value).toLocaleDateString("en-MY", {
    day: "2-digit",
    month: "short",
  });

// Renders the Trend Tooltip component.
function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TrendPoint }>;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg">
      <p className="font-medium text-slate-900">
        Completion Date: {formatLongDate(point.rawDate)}
      </p>
      <p className="mt-1 text-slate-600">
        Completed Applications: {point.completedApplications}
      </p>
      <p className="mt-1 text-slate-600">
        Average Processing Time: {formatDuration(point.averageMinutes)}
      </p>
    </div>
  );
}

// Renders the Hr Tooltip component.
function HrTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: HrPoint }>;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg">
      <p className="font-medium text-slate-900">{point.name}</p>
      <p className="mt-1 text-slate-600">
        Average Processing Time: {formatDuration(point.averageMinutes)}
      </p>
      <p className="mt-1 text-slate-600">
        Completed Applications: {point.completedApplications}
      </p>
    </div>
  );
}

type TrendPoint = {
  rawDate: string;
  date: string;
  averageDays: number;
  averageMinutes: number;
  completedApplications: number;
};

type HrPoint = {
  name: string;
  averageDays: number;
  averageMinutes: number;
  completedApplications: number;
  minMinutes: number;
  maxMinutes: number;
};

// Renders the Filter Field component.
function FilterField({
  label,
  icon,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-600">
        {icon}
        {label}
      </label>
      {children}
    </div>
  );
}

// Renders the Chart Filters component.
function ChartFilters({
  filters,
  jobs,
  departments,
  onChange,
  onReset,
  compact = false,
}: {
  filters: AnalyticsFilters;
  jobs: Array<{ id: number; title: string; department: string }>;
  departments: string[];
  onChange: (next: AnalyticsFilters) => void;
  onReset: () => void;
  compact?: boolean;
}) {
  // Updates the current form value.
  const update = <K extends keyof AnalyticsFilters>(
    key: K,
    value: AnalyticsFilters[K],
  ) => onChange({ ...filters, [key]: value });

  const matchingJobs =
    filters.department === "all"
      ? []
      : jobs.filter((job) => job.department === filters.department);

  // Updates department.
  const updateDepartment = (department: string) => {
    const selectedJobStillMatches =
      filters.jobId === "all" ||
      jobs.some(
        (job) =>
          String(job.id) === filters.jobId &&
          (department === "all" || job.department === department),
      );

    onChange({
      ...filters,
      department,
      jobId: selectedJobStillMatches ? filters.jobId : "all",
    });
  };

  return (
    <div
      className={`border-y border-slate-200 bg-slate-50 px-5 ${
        compact ? "py-2" : "py-3"
      }`}
    >
      <div
        className={`grid items-end md:grid-cols-2 xl:grid-cols-[repeat(4,minmax(0,1fr))_auto] ${
          compact ? "gap-2" : "gap-3"
        }`}
      >
        <FilterField
          label="Date Range"
          icon={<CalendarDays className="h-3.5 w-3.5" />}
        >
          <Select
            value={filters.dateRange}
            onValueChange={(value) =>
              update("dateRange", value as DateRangeFilter)
            }
          >
            <SelectTrigger className="bg-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="last7">Last 7 Days</SelectItem>
              <SelectItem value="last30">Last 30 Days</SelectItem>
              <SelectItem value="last3months">Last 3 Months</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField
          label="Job"
          icon={<BriefcaseBusiness className="h-3.5 w-3.5" />}
        >
          <Select
            value={filters.jobId}
            onValueChange={(value) => update("jobId", value)}
          >
            <SelectTrigger className="bg-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Jobs</SelectItem>
              {matchingJobs.map((job) => (
                <SelectItem key={job.id} value={String(job.id)}>
                  {job.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField
          label="Department"
          icon={<Building2 className="h-3.5 w-3.5" />}
        >
          <Select
            value={filters.department}
            onValueChange={updateDepartment}
          >
            <SelectTrigger className="bg-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent
              className="max-h-72"
              viewportClassName="max-h-64 overflow-y-scroll"
            >
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map((department) => (
                <SelectItem key={department} value={department}>
                  {department}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FilterField>

        <FilterField
          label="Email Outcome"
          icon={<Mail className="h-3.5 w-3.5" />}
        >
          <Select
            value={filters.emailOutcome}
            onValueChange={(value) =>
              update(
                "emailOutcome",
                value as AnalyticsFilters["emailOutcome"],
              )
            }
          >
            <SelectTrigger className="bg-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Completed Actions</SelectItem>
              <SelectItem value="interview">Interview Email Sent</SelectItem>
              <SelectItem value="reject">Rejection Email Sent</SelectItem>
            </SelectContent>
          </Select>
        </FilterField>

        <Button
          type="button"
          variant="outline"
          onClick={onReset}
          className="gap-2 bg-white text-[#004a91]"
        >
          <RotateCcw className="h-4 w-4" />
          Reset Filters
        </Button>
      </div>

      {filters.dateRange === "custom" && (
        <div className="mt-2 grid max-w-xl gap-3 sm:grid-cols-2">
          <FilterField label="Start Date">
            <Input
              type="date"
              value={filters.customStart}
              onChange={(event) => update("customStart", event.target.value)}
              className="bg-white"
            />
          </FilterField>
          <FilterField label="End Date">
            <Input
              type="date"
              value={filters.customEnd}
              onChange={(event) => update("customEnd", event.target.value)}
              className="bg-white"
            />
          </FilterField>
        </div>
      )}
    </div>
  );
}

// Renders the Trend Chart component.
function TrendChart({
  data,
  height,
}: {
  data: TrendPoint[];
  height: number | string;
}) {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-slate-500"
        style={{ height }}
      >
        No completed applications match the selected filters.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 20, left: 4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          interval="preserveStartEnd"
          minTickGap={54}
          tick={{ fontSize: 12 }}
        />
        <YAxis
          domain={[0, "auto"]}
          allowDecimals={false}
          tickFormatter={(value) => `${value}`}
          tick={{ fontSize: 12 }}
        />
        <Tooltip content={<TrendTooltip />} />
        <Line
          type="monotone"
          dataKey="completedApplications"
          stroke="#003B7A"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Renders the Hr Chart component.
function HrChart({
  data,
  height,
  showLabels = false,
}: {
  data: HrPoint[];
  height: number | string;
  showLabels?: boolean;
}) {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-slate-500"
        style={{ height }}
      >
        No assigned HR users match the selected filters.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 20, left: 4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="name"
          interval={0}
          tick={{ fontSize: 12 }}
          tickFormatter={(value) =>
            String(value).length > 18
              ? `${String(value).slice(0, 17)}...`
              : String(value)
          }
        />
        <YAxis
          domain={[0, "auto"]}
          tickFormatter={(value) => `${value}d`}
          tick={{ fontSize: 12 }}
        />
        <Tooltip content={<HrTooltip />} />
        <Bar dataKey="averageDays" fill="#003B7A" maxBarSize={90}>
          {showLabels && (
            <LabelList
              dataKey="averageDays"
              position="top"
              formatter={(value: number) => `${value.toFixed(1)}d`}
              className="fill-slate-700 text-xs"
            />
          )}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Renders the Summary Metric component.
function SummaryMetric({
  icon,
  label,
  value,
  accent = "text-[#0054b4]",
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 rounded-md border border-slate-200 bg-white px-3 py-2">
      <div className={accent}>{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-slate-500">{label}</p>
        <p className="truncate text-sm font-semibold text-slate-900">
          {value}
        </p>
      </div>
    </div>
  );
}

// Renders the Processing Note component.
function ProcessingNote() {
  return (
    <div className="flex items-start gap-2 text-xs text-slate-500">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        Processing time is calculated from application submission time to
        the final hired or rejected action time. Only completed applications
        are included.
      </p>
    </div>
  );
}

// Renders the Trend Expanded Content component.
function TrendExpandedContent({
  data,
  items,
}: {
  data: TrendPoint[];
  items: ProcessingAnalyticsItem[];
}) {
  const isMobile = useIsMobile();
  const daysPerPage = isMobile ? 7 : 10;
  const [breakdownPage, setBreakdownPage] = useState(1);
  const totalCompleted = items.length;
  const totalMinutes = items.reduce(
    (sum, item) => sum + (item.processingMinutes ?? 0),
    0,
  );
  const averageMinutes = totalCompleted === 0 ? 0 : totalMinutes / totalCompleted;
  const completionDates = items
    .map((item) => item.lastActionDate)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => parseDate(a).getTime() - parseDate(b).getTime());
  const earliestDate = completionDates[0] ?? null;
  const latestDate = completionDates.at(-1) ?? null;
  const selectedPeriod =
    earliestDate && latestDate
      ? `${formatLongDate(earliestDate)} - ${formatLongDate(latestDate)}`
      : "-";

  const exportRows: Array<Array<string | number>> = [
    ["Completion Date", "Average Processing Time", "Completed Applications"],
    ...data.map((point) => [
      point.rawDate,
      formatDuration(point.averageMinutes),
      point.completedApplications,
    ]),
  ];
  const breakdownPageCount = Math.max(
    1,
    Math.ceil(data.length / daysPerPage),
  );
  const latestBreakdownDate = data.at(-1)?.rawDate ?? "";
  const visibleBreakdownData = data.slice(
    (breakdownPage - 1) * daysPerPage,
    breakdownPage * daysPerPage,
  );
  const emptyBreakdownCells = Array.from({
    length: Math.max(0, daysPerPage - visibleBreakdownData.length),
  });

  useEffect(() => {
    setBreakdownPage(breakdownPageCount);
  }, [breakdownPageCount, daysPerPage, latestBreakdownDate]);

  return (
    <div className="space-y-2">
      <div>
        <div className="mb-1 flex items-center gap-2 text-xs font-medium text-slate-600">
          Completed Applications
          <Info className="h-3.5 w-3.5" />
        </div>
        <TrendChart data={data} height={220} />
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <SummaryMetric
          icon={<Clock3 className="h-6 w-6" />}
          label="Average Processing Time (Selected Period)"
          value={totalCompleted === 0 ? "-" : formatDays(averageMinutes)}
        />
        <SummaryMetric
          icon={<CheckCircle2 className="h-6 w-6" />}
          label="Completed Applications"
          value={totalCompleted}
          accent="text-emerald-600"
        />
        <SummaryMetric
          icon={<CalendarDays className="h-6 w-6" />}
          label="Selected Period"
          value={selectedPeriod}
          accent="text-orange-500"
        />
      </div>

      <div className="overflow-hidden rounded-md border border-slate-200">
        <div className="border-b border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-800">
          Daily Breakdown 
        </div>
        <div>
          <table className="w-full table-fixed text-sm">
            <tbody>
              <tr className="border-b border-slate-200">
                <th className="w-[24%] bg-white px-3 py-1 text-left font-medium">
                  Date
                </th>
                {visibleBreakdownData.map((point) => (
                  <th
                    key={point.rawDate}
                    className="px-1.5 py-1 text-center text-xs sm:text-sm"
                  >
                    {formatShortDate(point.rawDate)}
                  </th>
                ))}
                {emptyBreakdownCells.map((_, index) => (
                  <th
                    key={`empty-date-${index}`}
                    className="px-1.5 py-1"
                    aria-hidden="true"
                  />
                ))}
              </tr>
              <tr className="border-b border-slate-200 bg-slate-50/60">
                <th className="bg-slate-50 px-3 py-1 text-left font-normal leading-snug">
                  Average Processing Time
                </th>
                {visibleBreakdownData.map((point) => (
                  <td
                    key={point.rawDate}
                    className="px-1.5 py-1 text-center text-xs sm:text-sm"
                  >
                    {(point.averageMinutes / 1440).toFixed(1)}d
                  </td>
                ))}
                {emptyBreakdownCells.map((_, index) => (
                  <td
                    key={`empty-average-${index}`}
                    className="px-1.5 py-1"
                    aria-hidden="true"
                  />
                ))}
              </tr>
              <tr>
                <th className="bg-white px-3 py-1 text-left font-normal leading-snug">
                  Completed Applications
                </th>
                {visibleBreakdownData.map((point) => (
                  <td
                    key={point.rawDate}
                    className="px-1.5 py-1 text-center text-xs sm:text-sm"
                  >
                    {point.completedApplications}
                  </td>
                ))}
                {emptyBreakdownCells.map((_, index) => (
                  <td
                    key={`empty-completed-${index}`}
                    className="px-1.5 py-1"
                    aria-hidden="true"
                  />
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        {data.length > daysPerPage && (
          <div className="flex items-center justify-between gap-3 border-t border-slate-200 bg-white px-3 py-1.5 text-sm">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={breakdownPage === 1}
              onClick={() =>
                setBreakdownPage((page) => Math.max(1, page - 1))
              }
            >
              Previous days
            </Button>
            <span className="text-xs font-medium text-slate-500 sm:text-sm">
              Page {breakdownPage} of {breakdownPageCount}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={breakdownPage === breakdownPageCount}
              onClick={() =>
                setBreakdownPage((page) =>
                  Math.min(breakdownPageCount, page + 1),
                )
              }
            >
              Next days
            </Button>
          </div>
        )}
      </div>

    </div>
  );
}

// Renders the Hr Expanded Content component.
function HrExpandedContent({
  data,
  items,
}: {
  data: HrPoint[];
  items: ProcessingAnalyticsItem[];
}) {
  const totalCompleted = data.reduce(
    (sum, point) => sum + point.completedApplications,
    0,
  );
  const totalMinutes = data.reduce(
    (sum, point) => sum + point.averageMinutes * point.completedApplications,
    0,
  );
  const overallAverage =
    totalCompleted === 0 ? 0 : totalMinutes / totalCompleted;
  const completionDates = items
    .map((item) => item.lastActionDate)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => parseDate(a).getTime() - parseDate(b).getTime());
  const firstDate = completionDates[0] ?? null;
  const lastDate = completionDates.at(-1) ?? null;
  const selectedPeriod =
    firstDate && lastDate
      ? `${formatLongDate(firstDate)} - ${formatLongDate(lastDate)}`
      : "-";

  const exportRows: Array<Array<string | number>> = [
    [
      "HR User",
      "Completed Applications",
      "Average Processing Time",
      "Minimum Processing Time",
      "Maximum Processing Time",
    ],
    ...data.map((point) => [
      point.name,
      point.completedApplications,
      formatDuration(point.averageMinutes),
      formatDuration(point.minMinutes),
      formatDuration(point.maxMinutes),
    ]),
  ];

  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1.5 flex items-center justify-between gap-4 text-xs font-medium text-slate-600">
          <span className="flex items-center gap-2">
            Average Processing Time <span className="font-normal">(in days)</span>
            <Info className="h-3.5 w-3.5" />
          </span>
          <span className="flex items-center gap-2 font-normal">
            <span className="h-3 w-3 rounded-sm bg-[#003B7A]" />
            Average Processing Time (days)
          </span>
        </div>
        <HrChart data={data} height={205} showLabels />
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryMetric
          icon={<Clock3 className="h-6 w-6" />}
          label="Overall Average Processing Time"
          value={totalCompleted === 0 ? "-" : formatDays(overallAverage)}
        />
        <SummaryMetric
          icon={<CheckCircle2 className="h-6 w-6" />}
          label="Total Completed Applications"
          value={totalCompleted}
          accent="text-emerald-600"
        />
        <SummaryMetric
          icon={<UsersRound className="h-6 w-6" />}
          label="HR Users Included"
          value={data.length}
          accent="text-violet-600"
        />
        <SummaryMetric
          icon={<CalendarDays className="h-6 w-6" />}
          label="Selected Period"
          value={selectedPeriod}
          accent="text-orange-500"
        />
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-800">
          HR Summary 
        </p>
        <div className="overflow-x-auto rounded-md border border-slate-200">
          <table className="w-full min-w-[900px] text-sm">
            <thead className="bg-slate-50 text-left text-slate-700">
              <tr>
                <th className="px-3 py-2 font-medium">HR User</th>
                <th className="px-3 py-2 font-medium">Completed Applications</th>
                <th className="px-3 py-2 font-medium">Average Processing Time</th>
                <th className="px-3 py-2 font-medium">Min Processing Time</th>
                <th className="px-3 py-2 font-medium">Max Processing Time</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point) => (
                <tr key={point.name} className="border-t border-slate-200">
                  <td className="px-3 py-2">{point.name}</td>
                  <td className="px-3 py-2">{point.completedApplications}</td>
                  <td className="px-3 py-2">{formatDuration(point.averageMinutes)}</td>
                  <td className="px-3 py-2">{formatDuration(point.minMinutes)}</td>
                  <td className="px-3 py-2">{formatDuration(point.maxMinutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

// Renders the HR Processing Analytics component.
export function HRProcessingAnalytics({
  items,
  jobs: availableJobs,
}: {
  items: ProcessingAnalyticsItem[];
  jobs: ProcessingAnalyticsJobOption[];
}) {
  const [expandedChart, setExpandedChart] = useState<ExpandedChart>(null);
  const [filters, setFilters] = useState(initialFilters);

  // Incomplete applications are not used in processing time charts.
  const completedItems = useMemo(
    () => items.filter(isCompletedProcessingItem),
    [items],
  );

  const jobs = useMemo(() => {
    return availableJobs
      .filter((job) => job.status === "active")
      .map((job) => ({
        id: job.id,
        title: job.title,
        department: job.department,
      }))
      .sort((a, b) => a.title.localeCompare(b.title));
  }, [availableJobs]);

  const departments = useMemo(
    () =>
      Array.from(
        new Set(
          availableJobs
            .filter((job) => job.status === "active")
            .map((job) => job.department)
            .filter(Boolean),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [availableJobs],
  );

  // Apply the same filters to every chart.
  const filteredCompletedItems = useMemo(() => {
    const now = new Date();
    let rangeStart: Date | null = null;
    let rangeEnd: Date | null = endOfDay(now);

    if (filters.dateRange === "last7") {
      rangeStart = startOfDay(new Date(now.getTime() - 6 * 86400000));
    } else if (filters.dateRange === "last30") {
      rangeStart = startOfDay(new Date(now.getTime() - 29 * 86400000));
    } else if (filters.dateRange === "last3months") {
      rangeStart = startOfDay(new Date(now.getFullYear(), now.getMonth() - 3, now.getDate()));
    } else {
      rangeStart = filters.customStart
        ? startOfDay(new Date(`${filters.customStart}T00:00:00`))
        : null;
      rangeEnd = filters.customEnd
        ? endOfDay(new Date(`${filters.customEnd}T00:00:00`))
        : null;
    }

    return completedItems.filter((item) => {
      const completedAt = parseDate(item.lastActionDate ?? item.applicationDate);
      if (rangeStart && completedAt < rangeStart) return false;
      if (rangeEnd && completedAt > rangeEnd) return false;
      if (filters.jobId !== "all" && String(item.jobId) !== filters.jobId) {
        return false;
      }
      if (
        filters.department !== "all" &&
        item.jobDepartment !== filters.department
      ) {
        return false;
      }
      if (
        filters.emailOutcome !== "all" &&
        item.emailOutcome !== filters.emailOutcome
      ) {
        return false;
      }
      return true;
    });
  }, [completedItems, filters]);

  // Group completed work by day for the trend chart.
  const trendData = useMemo(() => {
    const grouped = new Map<
      string,
      { totalMinutes: number; completedApplications: number }
    >();

    filteredCompletedItems.forEach((item) => {
      const date = (item.lastActionDate ?? item.applicationDate).slice(0, 10);
      const current = grouped.get(date) ?? {
        totalMinutes: 0,
        completedApplications: 0,
      };
      current.totalMinutes += item.processingMinutes ?? 0;
      current.completedApplications += 1;
      grouped.set(date, current);
    });

    return Array.from(grouped.entries())
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([rawDate, group]) => {
        const averageMinutes =
          group.totalMinutes / group.completedApplications;
        return {
          rawDate,
          date: formatDisplayDate(rawDate),
          averageDays: averageMinutes / 1440,
          averageMinutes,
          completedApplications: group.completedApplications,
        };
      });
  }, [filteredCompletedItems]);

  // Group completed work by HR owner for comparison.
  const hrData = useMemo(() => {
    const grouped = new Map<
      string,
      {
        totalMinutes: number;
        completedApplications: number;
        processingMinutes: number[];
      }
    >();

    filteredCompletedItems.forEach((item) => {
      if (!item.hrAssigned || item.hrAssigned === "Unassigned") return;
      const current = grouped.get(item.hrAssigned) ?? {
        totalMinutes: 0,
        completedApplications: 0,
        processingMinutes: [],
      };
      const processingMinutes = item.processingMinutes ?? 0;
      current.totalMinutes += processingMinutes;
      current.completedApplications += 1;
      current.processingMinutes.push(processingMinutes);
      grouped.set(item.hrAssigned, current);
    });

    return Array.from(grouped.entries())
      .map(([name, group]) => {
        const averageMinutes =
          group.totalMinutes / group.completedApplications;
        return {
          name,
          averageDays: averageMinutes / 1440,
          averageMinutes,
          completedApplications: group.completedApplications,
          minMinutes: Math.min(...group.processingMinutes),
          maxMinutes: Math.max(...group.processingMinutes),
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [filteredCompletedItems]);

  // Provides the chart header helper.
  const chartHeader = (
    title: string,
    subtitle: string,
    chart: Exclude<ExpandedChart, null>,
  ) => (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h3 className="font-semibold text-slate-900">{title}</h3>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        title={`Expand ${title}`}
        aria-label={`Expand ${title}`}
        onClick={() => setExpandedChart(chart)}
        className="text-slate-500 hover:text-[#003B7A]"
      >
        <Maximize2 />
      </Button>
    </div>
  );

  const expandedTitle =
    expandedChart === "trend"
      ? "Completed Applications Trend"
      : "Average Processing Time by HR";
  const expandedSubtitle =
    expandedChart === "trend"
      ? "Number of completed applications over time"
      : "Average completed application processing time by assigned HR";

  return (
    <>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-md">
          {chartHeader(
            "Completed Applications Trend",
            "Number of completed applications over time",
            "trend",
          )}
          <div className="mt-5">
            <TrendChart data={trendData} height={300} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-md">
          {chartHeader(
            "Average Processing Time by HR",
            "Average completed application processing time by assigned HR",
            "hr",
          )}
          <div className="mt-5">
            <HrChart data={hrData} height={300} />
          </div>
        </div>
      </div>

      <Dialog
        open={expandedChart !== null}
        onOpenChange={(open) => {
          if (!open) setExpandedChart(null);
        }}
      >
        <DialogContent className="max-h-[88vh] w-[85vw] max-w-[85vw] grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0 sm:max-w-[85vw] [&>button]:hidden">
          <DialogHeader
            className="flex-row items-start justify-between gap-4 border-b border-slate-200 px-5 text-left py-3"
          >
            <div className="flex items-center gap-3">
              <div className="text-[#003B7A]">
                {expandedChart === "trend" ? (
                  <TrendingUp className="h-6 w-6" />
                ) : (
                  <UsersRound className="h-6 w-6" />
                )}
              </div>
              <div>
                <DialogTitle>{expandedTitle}</DialogTitle>
                <DialogDescription className="mt-1">
                  {expandedSubtitle}
                </DialogDescription>
              </div>
            </div>
            <DialogClose asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                title="Close"
                aria-label="Close"
                className="shrink-0 text-slate-500 hover:text-slate-900"
              >
                <X />
              </Button>
            </DialogClose>
          </DialogHeader>

          <ChartFilters
            filters={filters}
            jobs={jobs}
            departments={departments}
            onChange={setFilters}
            onReset={() => setFilters(initialFilters)}
            compact={expandedChart === "trend"}
          />

          <div
            className={`uwc-scrollbar min-h-0 overflow-y-auto bg-white px-5 ${
              expandedChart === "trend" ? "py-2.5" : "py-[18px]"
            }`}
          >
            {expandedChart === "trend" ? (
              <TrendExpandedContent
                data={trendData}
                items={filteredCompletedItems}
              />
            ) : (
              <HrExpandedContent
                data={hrData}
                items={filteredCompletedItems}
              />
            )}
          </div>
          
        </DialogContent>
      </Dialog>
    </>
  );
}
