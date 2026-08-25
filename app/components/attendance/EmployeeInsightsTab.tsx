// Shows the Employee Insights Tab view.
import { useEffect, useMemo, useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { TabsContent } from "../ui/tabs";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../ui/pagination";
import { Calendar as DatePickerCalendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  AlertTriangle,
  BriefcaseBusiness,
  Calendar as CalendarIcon,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Maximize2,
  Search,
  ShieldPlus,
  TrendingUp,
  UserX,
  X,
} from "lucide-react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { getCompactPageItems } from "../../lib/pagination";
import { SearchClearButton } from "../shared/SearchClearButton";


type EmployeeInsightsTabProps = Record<string, any>;

const MS_PER_DAY = 24 * 60 * 60 * 1000;

// Gets working days between.
const getWorkingDaysBetween = (start: string, end: string) => {
  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return 0;

  let workingDays = 0;
  for (let time = startDate.getTime(); time <= endDate.getTime(); time += MS_PER_DAY) {
    const day = new Date(time).getDay();
    if (day >= 1 && day <= 5) workingDays += 1;
  }
  return workingDays;
};

// Renders the Employee Insights Tab component.
export function EmployeeInsightsTab(props: EmployeeInsightsTabProps) {
  const {
  ALL_STATUSES,
  ATTENDANCE_CHART_BADGE_CLASSES,
  ATTENDANCE_ISSUE_COLORS,
  ATTENDANCE_ISSUE_LABELS,
  ATTENDANCE_RECORDS_PER_PAGE,
  ATTENDANCE_STATUSES,
  EMPLOYEE_INSIGHTS_PER_PAGE,
  absentCount,
  appliedInsightEndDate,
  appliedInsightStartDate,
  applyExpandedDateFilter,
  attendancePageCount,
  attendanceRate,
  attendanceSearch,
  defaultInsightStartDate,
  earlyClockInCount,
  employeeInsights,
  allEmployeeInsights,
  employeeInsightsPageCount,
  employeeInsightsSearch,
  employeeInsightsSearchEmployeeId,
  expandedEndDate,
  expandedEndPickerOpen,
  expandedDepartmentFilter,
  expandedDepartmentOptions,
  expandedEmployeeIssueData,
  expandedFilterEnd,
  expandedFilterStart,
  expandedInsightChart,
  expandedJobTitleFilter,
  expandedJobTitleOptions,
  expandedStartDate,
  expandedStartPickerOpen,
  filteredAttendanceData,
  formatCompactDate,
  formatDateInputValue,
  formatRecordDateLabel,
  formatShortDate,
  fullInsightEndDate,
  fullInsightStartDate,
  getEmployeeInitials,
  getStatusBadge,
  getTimeDisplay,
  handleAttendanceSort,
  handleEmployeeInsightsSort,
  hasAttendanceRecords,
  hasFilteredRecords,
  insightEndDate,
  insightEndPickerOpen,
  insightMaxDate,
  insightStartDate,
  insightStartPickerOpen,
  invalidCount,
  isLoading,
  lateClockInCount,
  leaveCount,
  mcCount,
  moveSelectedDate,
  noClockOutCount,
  notPresentCount,
  onTimeCount,
  openExpandedInsightChart,
  pagedAttendanceData,
  pagedEmployeeInsights,
  presentCount,
  renderEmployeeInsightsSortIcon,
  renderSortIcon,
  resetExpandedDateFilter,
  resetInsightDateFilter,
  safeAttendancePage,
  safeEmployeeInsightsPage,
  selectedAttendanceChartTotal,
  selectedAttendanceIssueBreakdown,
  selectedDate,
  selectedEmployee,
  selectedEmployeeDetailOpen,
  selectedIssuesByWeekday,
  selectedIssuesMax,
  selectedIssuesPeakDay,
  selectedWorkedDays,
  setAttendancePage,
  setAttendanceSearch,
  setEmployeeInsightsPage,
  setEmployeeInsightsSearch,
  setEmployeeInsightsSearchEmployeeId,
  setExpandedEndDate,
  setExpandedEndPickerOpen,
  setExpandedDepartmentFilter,
  setExpandedInsightChart,
  setExpandedJobTitleFilter,
  setExpandedStartDate,
  setExpandedStartPickerOpen,
  setInsightEndDate,
  setInsightEndPickerOpen,
  setInsightStartDate,
  setInsightStartPickerOpen,
  selectInsightEndDate,
  selectInsightStartDate,
  setSelectedEmployeeDetailOpen,
  setSelectedEmployeeId,
  setStatusFilter,
  statusFilter,
  topAttendanceIssueEmployees,
  totalEmployeesCount,
  workingDaysInRange,
} = props;

  const [expandedIssueSearch, setExpandedIssueSearch] = useState("");
  const [expandedIssueSelectedEmployeeId, setExpandedIssueSelectedEmployeeId] = useState("");
  const [expandedIssueSearchFocused, setExpandedIssueSearchFocused] = useState(false);
  const [expandedIssueStatuses, setExpandedIssueStatuses] = useState<string[]>([]);
  const [expandedIssuePage, setExpandedIssuePage] = useState(1);
  const [employeeInsightsSearchFocused, setEmployeeInsightsSearchFocused] = useState(false);
  const ALL_FILTER_VALUE = "all";
  const EXPANDED_ISSUE_PAGE_SIZE = 20;
  const issueSegments = [
      { key: "late", label: "Late", color: ATTENDANCE_ISSUE_COLORS.Late },
      { key: "absent", label: "Absent", color: ATTENDANCE_ISSUE_COLORS.Absent },
      { key: "mc", label: "MC", color: ATTENDANCE_ISSUE_COLORS.MC },
      { key: "leave", label: "Leave", color: ATTENDANCE_ISSUE_COLORS.Leave },
    ];
  const expandedFilterSegments = [
      { key: "attend", label: "Present", color: ATTENDANCE_ISSUE_COLORS.Present },
      ...issueSegments,
    ];

  // Gets issue count.
  const getIssueCount = (employee: any, activeSegments = issueSegments) =>
    activeSegments.reduce((sum, segment) => sum + (employee[segment.key] ?? 0), 0);

  const expandedActiveSegments =
    expandedIssueStatuses.length > 0
      ? expandedFilterSegments.filter((segment) => expandedIssueStatuses.includes(segment.key))
      : issueSegments;

  const expandedIssueSearchTerm = expandedIssueSearch.trim().toLowerCase();
  const employeeInsightsSearchTerm = employeeInsightsSearch.trim().toLowerCase();
  const employeeInsightsSearchSuggestions = useMemo(() => {
    if (!employeeInsightsSearchTerm || employeeInsightsSearchEmployeeId) return [];

    return allEmployeeInsights
      .filter((employee: any) => {
        const employeeId = String(employee.employeeId ?? "").toLowerCase();
        const name = String(employee.name ?? "").toLowerCase();
        return employeeId.startsWith(employeeInsightsSearchTerm) || name.startsWith(employeeInsightsSearchTerm);
      })
      .map((employee: any) => ({
        employeeId: String(employee.employeeId ?? ""),
        name: String(employee.name ?? ""),
      }))
      .filter((employee: any) => employee.employeeId && employee.name)
      .slice(0, 8);
  }, [allEmployeeInsights, employeeInsightsSearchEmployeeId, employeeInsightsSearchTerm]);
  const expandedIssueEmployeeSuggestions = useMemo(() => {
    if (!expandedIssueSearchTerm || expandedIssueSelectedEmployeeId) return [];

    const employeeMap = new Map<string, { employeeId: string; employeeName: string }>();
    expandedEmployeeIssueData.forEach((employee: any) => {
      const employeeId = String(employee.employeeId ?? "").trim();
      const employeeName = String(employee.employeeName ?? employee.name ?? "").trim();
      if (!employeeId || !employeeName || employeeMap.has(employeeId)) return;

      const matchesSearch =
        employeeId.toLowerCase().startsWith(expandedIssueSearchTerm) ||
        employeeName.toLowerCase().startsWith(expandedIssueSearchTerm);
      if (matchesSearch) employeeMap.set(employeeId, { employeeId, employeeName });
    });

    return [...employeeMap.values()]
      .sort((first, second) =>
        first.employeeName.localeCompare(second.employeeName, undefined, { sensitivity: "base" }),
      )
      .slice(0, 8);
  }, [expandedEmployeeIssueData, expandedIssueSearchTerm, expandedIssueSelectedEmployeeId]);
  const expandedIssueDateRangeStart = expandedFilterStart || appliedInsightStartDate || fullInsightStartDate;
  const expandedIssueDateRangeEnd = expandedFilterEnd || appliedInsightEndDate || fullInsightEndDate;
  const expandedIssueWorkingDays =
    expandedIssueDateRangeStart && expandedIssueDateRangeEnd
      ? getWorkingDaysBetween(expandedIssueDateRangeStart, expandedIssueDateRangeEnd)
      : 0;
  const expandedIssueDateRangeLabel =
    expandedIssueDateRangeStart && expandedIssueDateRangeEnd
      ? `${formatShortDate(expandedIssueDateRangeStart)} - ${formatShortDate(expandedIssueDateRangeEnd)}${
          expandedIssueWorkingDays > 0 ? ` (${expandedIssueWorkingDays} working days)` : ""
        }`
      : "All available dates";
  const expandedIssueEmployees = expandedEmployeeIssueData
    .map((employee: any) => ({
      employeeId: employee.employeeId,
      employeeName: employee.employeeName ?? employee.name,
      employeeLabel: employee.employeeLabel ?? `${employee.employeeName ?? employee.name} (${employee.employeeId})`,
      attend: employee.attend,
      late: employee.late,
      absent: employee.absent,
      mc: employee.mc,
      leave: employee.leave,
    }))
    .map((employee: any) => ({
      ...employee,
      issueCount: getIssueCount(employee, expandedActiveSegments),
    }))
    .filter((employee: any) => {
      const matchesSearch =
        expandedIssueSelectedEmployeeId !== ""
          ? employee.employeeId === expandedIssueSelectedEmployeeId
          : expandedIssueSearchTerm === "" ||
            employee.employeeId.toLowerCase().includes(expandedIssueSearchTerm) ||
            employee.employeeName.toLowerCase().includes(expandedIssueSearchTerm);
      const matchesIssue = expandedIssueStatuses.length === 0 || employee.issueCount > 0;
      return matchesSearch && matchesIssue;
    })
    .sort((first: any, second: any) => {
      const issueDifference = second.issueCount - first.issueCount;
      if (issueDifference !== 0) return issueDifference;
      return first.employeeName.localeCompare(second.employeeName, undefined, { sensitivity: "base" });
    });

  const expandedIssuePageCount = Math.max(
    1,
    Math.ceil(expandedIssueEmployees.length / EXPANDED_ISSUE_PAGE_SIZE),
  );
  const safeExpandedIssuePage = Math.min(expandedIssuePage, expandedIssuePageCount);
  const pagedExpandedIssueEmployees = expandedIssueEmployees.slice(
    (safeExpandedIssuePage - 1) * EXPANDED_ISSUE_PAGE_SIZE,
    safeExpandedIssuePage * EXPANDED_ISSUE_PAGE_SIZE,
  );

  useEffect(() => {
    setExpandedIssuePage(1);
  }, [
    expandedDepartmentFilter,
    expandedInsightChart,
    expandedIssueSearch,
    expandedIssueStatuses.join("|"),
    expandedJobTitleFilter,
  ]);

  // Renders expanded select filter.
  const renderExpandedSelectFilter = (
    label: string,
    value: string,
    onValueChange: (value: string) => void,
    placeholder: string,
    options: string[],
  ) => (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="h-10 border-slate-200 bg-white shadow-sm transition-colors hover:bg-slate-50">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="z-[90]">
          <SelectItem value={ALL_FILTER_VALUE}>{placeholder}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );

  // Renders issue breakdown table.
  const renderIssueBreakdownTable = (
    employees: any[],
    expanded = false,
    activeSegments = issueSegments,
    rankOffset = 0,
  ) => {
    const maxIssues = Math.max(1, ...employees.map((employee) => getIssueCount(employee, activeSegments)));
    // Provides the rank class helper.
    const rankClass = (rank: number) => {
      if (rank === 1) return "bg-amber-300 text-slate-950";
      if (rank === 2) return "bg-slate-300 text-slate-700";
      if (rank === 3) return "bg-orange-300 text-slate-950";
      return "bg-slate-100 text-slate-600";
    };

    return (
      <div className="space-y-3">
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="grid grid-cols-[48px_minmax(140px,190px)_minmax(240px,1fr)_104px] border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <div>Rank</div>
            <div>Employee</div>
            <div>Issue Breakdown</div>
            <div className="text-right">Total Issues</div>
          </div>
          <div className="divide-y divide-slate-100">
            {employees.map((employee, index) => {
              const rank = rankOffset + index + 1;
              const employeeIssueCount = getIssueCount(employee, activeSegments);
              const barWidth = `${Math.max(8, (employeeIssueCount / maxIssues) * 100)}%`;

              return (
                <div
                  key={employee.employeeId}
                  className={`grid grid-cols-[48px_minmax(140px,190px)_minmax(240px,1fr)_104px] items-center gap-0 px-4 ${
                    expanded ? "py-2.5" : "py-1.5"
                  }`}
                >
                  <div>
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${rankClass(rank)}`}
                    >
                      {rank}
                    </span>
                  </div>
                  <div className="min-w-0 pr-4">
                    <p className="truncate text-sm font-semibold text-slate-950" title={employee.employeeName}>
                      {employee.employeeName}
                    </p>
                    <p className="text-xs text-slate-500">{employee.employeeId}</p>
                  </div>
                  <div className="min-w-0">
                    <div className="h-6 max-w-full overflow-hidden rounded" style={{ width: barWidth }}>
                      <div className="flex h-full min-w-10">
                        {activeSegments.map((segment) => {
                          const value = employee[segment.key] ?? 0;
                          if (value <= 0 || employeeIssueCount <= 0) return null;

                          return (
                            <div
                              key={segment.key}
                              className="flex min-w-6 items-center justify-center border-r border-white/70 text-xs font-semibold text-white last:border-r-0"
                              title={`${segment.label}: ${value}`}
                              style={{
                                width: `${(value / employeeIssueCount) * 100}%`,
                                backgroundColor: segment.color,
                              }}
                            >
                              {value}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold text-[#003B7A]">{employeeIssueCount}</span>
                    <span className="ml-1 text-xs text-slate-500">issues</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="flex justify-center gap-6 text-xs text-slate-600">
          {activeSegments.map((segment) => (
            <span key={segment.key} className="inline-flex items-center gap-2">
              <span className="h-3.5 w-3.5 rounded" style={{ backgroundColor: segment.color }} />
              {segment.label}
            </span>
          ))}
        </div>
      </div>
    );
  };

  return (
        <TabsContent value="insights" className="space-y-6">
          <section className="space-y-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-2xl font-bold tracking-tight text-slate-950">
                  Employee Insights
                </h2>
                <span className="hidden h-8 w-px bg-slate-300 sm:block" />
                <div className="grid w-full gap-3 sm:grid-cols-2 lg:w-auto lg:grid-cols-[180px_180px] lg:items-end">
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Start Date
                    </label>
                    <Popover open={insightStartPickerOpen} onOpenChange={setInsightStartPickerOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-10 w-full justify-start bg-white px-3 text-left text-sm font-normal text-slate-950 shadow-sm"
                          aria-label="Start date"
                        >
                          <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                          {insightStartDate ? formatShortDate(insightStartDate) : "Select date"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <DatePickerCalendar
                          mode="single"
                          defaultMonth={insightStartDate ? new Date(`${insightStartDate}T00:00:00`) : undefined}
                          selected={insightStartDate ? new Date(`${insightStartDate}T00:00:00`) : undefined}
                          onSelect={(date) => {
                            if (date) {
                              selectInsightStartDate(formatDateInputValue(date));
                              setInsightStartPickerOpen(false);
                            }
                          }}
                          disabled={(date) => {
                            const value = formatDateInputValue(date);
                            return value > (insightEndDate || insightMaxDate || fullInsightEndDate);
                          }}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                      End Date
                    </label>
                    <Popover open={insightEndPickerOpen} onOpenChange={setInsightEndPickerOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-10 w-full justify-start bg-white px-3 text-left text-sm font-normal text-slate-950 shadow-sm"
                          aria-label="End date"
                        >
                          <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                          {insightEndDate ? formatShortDate(insightEndDate) : "Select date"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <DatePickerCalendar
                          mode="single"
                          defaultMonth={insightEndDate ? new Date(`${insightEndDate}T00:00:00`) : undefined}
                          selected={insightEndDate ? new Date(`${insightEndDate}T00:00:00`) : undefined}
                          onSelect={(date) => {
                            if (date) {
                              selectInsightEndDate(formatDateInputValue(date));
                              setInsightEndPickerOpen(false);
                            }
                          }}
                          disabled={(date) => {
                            const value = formatDateInputValue(date);
                            return value < (insightStartDate || fullInsightStartDate) || value > (insightMaxDate || fullInsightEndDate);
                          }}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button type="button" variant="outline" className="bg-white" onClick={resetInsightDateFilter}>
                  Reset
                </Button>
              </div>
            </div>
            
            <div className="text-sm text-slate-500">
              Showing records from{" "}
              <span className="font-medium text-slate-700">
                {appliedInsightStartDate ? formatShortDate(appliedInsightStartDate) : "-"}
              </span>{" "}
              to{" "}
              <span className="font-medium text-slate-700">
                {appliedInsightEndDate ? formatShortDate(appliedInsightEndDate) : "-"}
              </span>
            </div>
          </section>

          {allEmployeeInsights.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
              No attendance data found in the selected date range.
            </div>
          ) : (
            <>
              <div className="grid gap-6">
                <Card className="shadow-md">
                  <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div>
                      <CardTitle>Top Employees by Attendance Issues</CardTitle>
                      <CardDescription>
                        Showing top 10 employees with the highest Late, Absent, MC and Leave records in the selected date range.
                      </CardDescription>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      title="Expand Employees with Most Attendance Issues"
                      aria-label="Expand Employees with Most Attendance Issues"
                      className="h-8 w-8 shrink-0 text-slate-500 hover:text-[#003B7A]"
                      onClick={() => openExpandedInsightChart("issues")}
                    >
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {renderIssueBreakdownTable(topAttendanceIssueEmployees)}
                  </CardContent>
                </Card>
              </div>

              <Dialog
                open={expandedInsightChart !== null}
                onOpenChange={(open) => {
                  if (!open) setExpandedInsightChart(null);
                }}
              >
                <DialogContent className="max-h-[88vh] w-[85vw] max-w-[85vw] grid-rows-[auto_auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-[85vw] [&>button]:hidden">
                  <DialogHeader className="flex-row items-start justify-between gap-4 border-b border-slate-200 px-5 py-3 text-left">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <DialogTitle>
                          Top Employees by Attendance Issues
                        </DialogTitle>
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 text-xs font-medium text-slate-600">
                          <CalendarIcon className="h-3.5 w-3.5 text-slate-500" />
                          <span>Date range:</span>
                          <span className="font-semibold text-slate-900">{expandedIssueDateRangeLabel}</span>
                        </div>
                      </div>
                      <DialogDescription className="mt-1">
                        Showing all employees with attendance issue breakdown in the selected date range.
                      </DialogDescription>
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
                        <X className="h-4 w-4" />
                      </Button>
                    </DialogClose>
                  </DialogHeader>

                  <div className="grid gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4 xl:grid-cols-[minmax(220px,320px)_220px_220px_1fr_auto] xl:items-end">
                    <div className="relative">
                      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Search
                      </label>
                      <Search className="pointer-events-none absolute left-3 top-[34px] h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input
                        type="text"
                        inputMode="search"
                        value={expandedIssueSearch}
                        onChange={(event) => {
                          setExpandedIssueSearch(event.target.value);
                          setExpandedIssueSelectedEmployeeId("");
                        }}
                        onFocus={() => setExpandedIssueSearchFocused(true)}
                        onBlur={() => window.setTimeout(() => setExpandedIssueSearchFocused(false), 120)}
                        placeholder="Search employee name or ID"
                        className="h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-10 text-sm text-slate-950 shadow-sm outline-none transition-[color,box-shadow] placeholder:text-slate-400 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                      />
                      <SearchClearButton
                        show={Boolean(expandedIssueSearch)}
                        onClear={() => {
                          setExpandedIssueSearch("");
                          setExpandedIssueSelectedEmployeeId("");
                          setExpandedIssueSearchFocused(false);
                        }}
                      />
                      {expandedIssueSearchFocused && expandedIssueEmployeeSuggestions.length > 0 && (
                        <div className="absolute left-0 right-0 top-[66px] z-[95] overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                          {expandedIssueEmployeeSuggestions.map((employee) => (
                            <button
                              key={employee.employeeId}
                              type="button"
                              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => {
                                setExpandedIssueSelectedEmployeeId(employee.employeeId);
                                setExpandedIssueSearch(`${employee.employeeName} (${employee.employeeId})`);
                                setExpandedIssueSearchFocused(false);
                              }}
                            >
                              <span className="font-medium text-slate-950">{employee.employeeName}</span>
                              <span className="text-xs text-slate-500">{employee.employeeId}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {renderExpandedSelectFilter(
                      "Department",
                      expandedDepartmentFilter,
                      (value) => {
                        setExpandedDepartmentFilter(value);
                        setExpandedJobTitleFilter(ALL_FILTER_VALUE);
                        setExpandedIssueSelectedEmployeeId("");
                        setExpandedIssueSearch("");
                      },
                      "All Departments",
                      expandedDepartmentOptions,
                    )}
                    {renderExpandedSelectFilter(
                      "Job Title",
                      expandedJobTitleFilter,
                      (value) => {
                        setExpandedJobTitleFilter(value);
                        setExpandedIssueSelectedEmployeeId("");
                        setExpandedIssueSearch("");
                      },
                      "All Job Titles",
                      expandedJobTitleOptions,
                    )}
                    <div className="flex flex-wrap items-end gap-2">
                      {expandedFilterSegments.map((segment) => {
                        const isSelected = expandedIssueStatuses.includes(segment.key);

                        return (
                          <button
                            key={segment.key}
                            type="button"
                            onClick={() =>
                              setExpandedIssueStatuses((current) =>
                                current.includes(segment.key)
                                  ? current.filter((status) => status !== segment.key)
                                  : [...current, segment.key],
                              )
                            }
                            className={`inline-flex h-10 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors ${
                              isSelected
                                ? "border-[#003B7A] bg-blue-50 text-[#003B7A]"
                                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                            }`}
                          >
                            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: segment.color }} />
                            {segment.label}
                          </button>
                        );
                      })}
                    </div>
                    <div className="pb-2 text-sm text-slate-500 xl:text-right">
                      Showing{" "}
                      <span className="font-semibold text-slate-950">{expandedIssueEmployees.length}</span>{" "}
                      employees
                    </div>
                  </div>

                  <div className="uwc-scrollbar min-h-0 overflow-y-auto bg-white px-5 py-5">
                    {expandedIssueEmployees.length > 0 ? (
                      <>
                        {renderIssueBreakdownTable(
                          pagedExpandedIssueEmployees,
                          true,
                          expandedActiveSegments,
                          (safeExpandedIssuePage - 1) * EXPANDED_ISSUE_PAGE_SIZE,
                        )}
                        {expandedIssueEmployees.length > EXPANDED_ISSUE_PAGE_SIZE && (
                          <Pagination className="border-t border-slate-100 bg-white py-4">
                            <PaginationContent>
                              <PaginationItem>
                                <PaginationPrevious
                                  href="#"
                                  aria-disabled={safeExpandedIssuePage === 1}
                                  className={
                                    safeExpandedIssuePage === 1 ? "pointer-events-none opacity-50" : ""
                                  }
                                  onClick={(event) => {
                                    event.preventDefault();
                                    setExpandedIssuePage((page) => Math.max(1, page - 1));
                                  }}
                                />
                              </PaginationItem>

                              {getCompactPageItems(safeExpandedIssuePage, expandedIssuePageCount).map((item) => (
                                <PaginationItem key={item}>
                                  {typeof item === "number" ? (
                                    <PaginationLink
                                      href="#"
                                      isActive={item === safeExpandedIssuePage}
                                      onClick={(event) => {
                                        event.preventDefault();
                                        setExpandedIssuePage(item);
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
                                  aria-disabled={safeExpandedIssuePage === expandedIssuePageCount}
                                  className={
                                    safeExpandedIssuePage === expandedIssuePageCount
                                      ? "pointer-events-none opacity-50"
                                      : ""
                                  }
                                  onClick={(event) => {
                                    event.preventDefault();
                                    setExpandedIssuePage((page) =>
                                      Math.min(expandedIssuePageCount, page + 1),
                                    );
                                  }}
                                />
                              </PaginationItem>
                            </PaginationContent>
                          </Pagination>
                        )}
                      </>
                    ) : (
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500">
                        No employees match the selected issue filters.
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>

              <section>
                  <div className="mb-6 flex flex-wrap items-center gap-4">
                    <div className="relative w-full sm:max-w-xs">
                      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input
                        type="text"
                        inputMode="search"
                        value={employeeInsightsSearch}
                        onChange={(event) => {
                          setEmployeeInsightsSearch(event.target.value);
                          setEmployeeInsightsSearchEmployeeId("");
                        }}
                        onFocus={() => setEmployeeInsightsSearchFocused(true)}
                        onBlur={() => window.setTimeout(() => setEmployeeInsightsSearchFocused(false), 120)}
                        placeholder="Search name or employee ID"
                        className="h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-10 text-sm text-slate-950 shadow-sm outline-none transition-[color,box-shadow] placeholder:text-slate-400 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                      />
                      <SearchClearButton
                        show={Boolean(employeeInsightsSearch)}
                        onClear={() => {
                          setEmployeeInsightsSearch("");
                          setEmployeeInsightsSearchEmployeeId("");
                          setEmployeeInsightsSearchFocused(false);
                        }}
                      />
                      {employeeInsightsSearchFocused && employeeInsightsSearchSuggestions.length > 0 && (
                        <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                          {employeeInsightsSearchSuggestions.map((employee: any) => (
                            <button
                              key={employee.employeeId}
                              type="button"
                              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => {
                                setEmployeeInsightsSearchEmployeeId(employee.employeeId);
                                setEmployeeInsightsSearch(`${employee.name} (${employee.employeeId})`);
                                setEmployeeInsightsSearchFocused(false);
                              }}
                            >
                              <span className="font-medium text-slate-950">{employee.name}</span>
                              <span className="text-xs text-slate-500">{employee.employeeId}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                    <table className="w-full table-fixed text-sm">
                      <colgroup>
                        <col className="w-[24%]" />
                        <col className="w-[9%]" />
                        <col className="w-[9%]" />
                        <col className="w-[9%]" />
                        <col className="w-[9%]" />
                        <col className="w-[9%]" />
                        <col className="w-[15%]" />
                        <col className="w-[16%]" />
                      </colgroup>
                      <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-4 py-4">Employee</th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("attend")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Attend
                              {renderEmployeeInsightsSortIcon("attend")}
                            </button>
                          </th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("late")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Late
                              {renderEmployeeInsightsSortIcon("late")}
                            </button>
                          </th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("absent")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Absent
                              {renderEmployeeInsightsSortIcon("absent")}
                            </button>
                          </th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("mc")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              MC
                              {renderEmployeeInsightsSortIcon("mc")}
                            </button>
                          </th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("leave")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Leave
                              {renderEmployeeInsightsSortIcon("leave")}
                            </button>
                          </th>
                          <th className="px-4 py-4">
                            <button
                              type="button"
                              onClick={() => handleEmployeeInsightsSort("attendanceRate")}
                              className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Attendance Rate
                              {renderEmployeeInsightsSortIcon("attendanceRate")}
                            </button>
                          </th>
                          <th className="px-4 py-4">Main Pattern</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {pagedEmployeeInsights.length > 0 ? (
                          pagedEmployeeInsights.map((employee: any) => (
                            <tr
                              key={employee.employeeId}
                              onClick={() => {
                                setSelectedEmployeeId(employee.employeeId);
                                setSelectedEmployeeDetailOpen(true);
                              }}
                              className="cursor-pointer transition-colors hover:bg-slate-50"
                            >
                              <td className="px-4 py-4">
                                <div className="font-medium text-slate-950">{employee.name}</div>
                                <div className="mt-1 text-sm text-slate-500">{employee.employeeId}</div>
                              </td>
                              <td className="px-4 py-4 text-slate-700">{employee.attend}</td>
                              <td className="px-4 py-4 text-slate-700">{employee.late}</td>
                              <td className="px-4 py-4 text-slate-700">{employee.absent}</td>
                              <td className="px-4 py-4 text-slate-700">{employee.mc}</td>
                              <td className="px-4 py-4 text-slate-700">{employee.leave}</td>
                              <td className="px-4 py-4 font-semibold text-slate-950">
                                {employee.attendanceRate}%
                              </td>
                              <td className="px-4 py-4 text-slate-700">{employee.mainPattern}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-500">
                              No employees match the search filter.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  {employeeInsights.length > EMPLOYEE_INSIGHTS_PER_PAGE && (
                    <Pagination className="border-t border-slate-100 bg-white py-4">
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            href="#"
                            aria-disabled={safeEmployeeInsightsPage === 1}
                            className={
                              safeEmployeeInsightsPage === 1
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                            onClick={(event) => {
                              event.preventDefault();
                              setEmployeeInsightsPage((page: any) => Math.max(1, page - 1));
                            }}
                          />
                        </PaginationItem>

                        {getCompactPageItems(
                          safeEmployeeInsightsPage,
                          employeeInsightsPageCount,
                        ).map((item) => (
                          <PaginationItem key={item}>
                            {typeof item === "number" ? (
                              <PaginationLink
                                href="#"
                                isActive={item === safeEmployeeInsightsPage}
                                onClick={(event) => {
                                  event.preventDefault();
                                  setEmployeeInsightsPage(item);
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
                            aria-disabled={safeEmployeeInsightsPage === employeeInsightsPageCount}
                            className={
                              safeEmployeeInsightsPage === employeeInsightsPageCount
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                            onClick={(event) => {
                              event.preventDefault();
                              setEmployeeInsightsPage((page: any) =>
                                Math.min(employeeInsightsPageCount, page + 1),
                              );
                            }}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  )}
                  </div>
              </section>

              {selectedEmployee && (
                <Dialog open={selectedEmployeeDetailOpen} onOpenChange={setSelectedEmployeeDetailOpen}>
                  <DialogContent className="uwc-scrollbar max-h-[90vh] overflow-y-auto overflow-x-hidden p-0 sm:max-w-6xl [&>button]:hidden">
                  <Card className="gap-0 border-0 shadow-none">
                    <CardHeader className="flex flex-row items-center justify-between gap-4 border-b border-slate-100 px-6 !pb-1 pt-5">
                      <div className="flex items-center gap-4">
                        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-blue-50 text-lg font-semibold text-slate-950">
                          {getEmployeeInitials(selectedEmployee.name)}
                        </div>
                        <div>
                          <CardTitle className="text-xl">{selectedEmployee.name}</CardTitle>
                          <CardDescription className="mt-1 flex flex-wrap items-center gap-2 text-sm font-medium text-slate-500">
                            <span>{selectedEmployee.employeeId}</span>
                            <span className="text-slate-300">|</span>
                            <span>
                              {formatCompactDate(appliedInsightStartDate || fullInsightStartDate)} -{" "}
                              {formatCompactDate(appliedInsightEndDate || fullInsightEndDate)}
                            </span>
                            <span className="text-xs text-slate-400">
                              {workingDaysInRange} working days
                            </span>
                          </CardDescription>
                        </div>
                      </div>
                      <DialogClose asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 shrink-0 text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                          aria-label="Close employee detail"
                        >
                          <X className="h-5 w-5" />
                        </Button>
                      </DialogClose>
                    </CardHeader>
                    <CardContent className="grid items-stretch gap-5 px-6 pb-6 pt-5 lg:h-[396px] lg:grid-cols-[minmax(0,1fr)_420px]">
                      <div className="flex h-full flex-col gap-3">
                        <div className="grid gap-3 sm:grid-cols-2">
                          {[
                            {
                              label: "Worked Days",
                              value: `${selectedWorkedDays}/${workingDaysInRange}`,
                              Icon: CalendarIcon,
                              iconClass: "text-blue-600",
                            },
                            {
                              label: "Attendance Rate",
                              value: `${selectedEmployee.attendanceRate}%`,
                              Icon: TrendingUp,
                              iconClass: "text-blue-600",
                            },
                            {
                              label: "Total Late",
                              value: selectedEmployee.late,
                              Icon: Clock,
                              iconClass: "text-blue-600",
                            },
                            {
                              label: "Total Absent",
                              value: selectedEmployee.absent,
                              Icon: UserX,
                              iconClass: "text-red-600",
                            },
                            {
                              label: "Total MC",
                              value: selectedEmployee.mc,
                              Icon: ShieldPlus,
                              iconClass: "text-blue-600",
                            },
                            {
                              label: "Total Leave",
                              value: selectedEmployee.leave,
                              Icon: BriefcaseBusiness,
                              iconClass: "text-slate-600",
                            },
                          ].map(({ label, value, Icon, iconClass }: any) => (
                            <div
                              key={label}
                              className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
                            >
                              <span className={`flex h-9 w-9 shrink-0 items-center justify-center ${iconClass}`}>
                                <Icon className="h-4 w-4" />
                              </span>
                              <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                  {label}
                                </p>
                                <p className="mt-1 text-lg font-bold text-slate-950">{value}</p>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                          <span className="flex h-17 w-9 shrink-0 items-center justify-center text-blue-600">
                            <TrendingUp className="h-4 w-4" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Main Pattern
                            </p>
                            <p className="mt-1 text-lg font-bold text-slate-950">
                              {selectedEmployee.mainPattern}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="flex h-full flex-col gap-3">
                      <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                        {selectedAttendanceIssueBreakdown.length > 0 ? (
                          <div className="flex h-full w-full flex-col">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Attendance Issue Breakdown
                            </p>
                            <div className="mt-3 grid flex-1 items-center gap-3 sm:grid-cols-[minmax(0,1fr)_150px]">
                              <div className="relative h-40 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <PieChart className="outline-none [&_*]:outline-none">
                                    <Pie
                                      data={selectedAttendanceIssueBreakdown}
                                      dataKey="count"
                                      nameKey="status"
                                      cx="50%"
                                      cy="50%"
                                      innerRadius={44}
                                      outerRadius={70}
                                      paddingAngle={2}
                                      activeShape={false}
                                      isAnimationActive={false}
                                      stroke="#ffffff"
                                      strokeWidth={3}
                                    >
                                      {selectedAttendanceIssueBreakdown.map((item: any) => (
                                        <Cell
                                          key={item.status}
                                          fill={ATTENDANCE_ISSUE_COLORS[item.status]}
                                        />
                                      ))}
                                    </Pie>
                                    <Tooltip
                                      wrapperStyle={{ zIndex: 20, transform: "translate(12px, -18px)" }}
                                      contentStyle={{
                                        borderRadius: 8,
                                        borderColor: "#dbe4ef",
                                        boxShadow: "0 8px 20px rgba(15, 23, 42, 0.12)",
                                        padding: "6px 8px",
                                      }}
                                      formatter={(value, name) => [`${value}`, name]}
                                    />
                                  </PieChart>
                                </ResponsiveContainer>
                                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    Total
                                  </span>
                                  <span className="text-2xl font-bold text-slate-950">
                                    {selectedAttendanceChartTotal}
                                  </span>
                                </div>
                              </div>
                              <div className="space-y-3 text-sm">
                                {ATTENDANCE_ISSUE_LABELS.map((status: any) => {
                                  const count =
                                    selectedAttendanceIssueBreakdown.find((item: any) => item.status === status)?.count ?? 0;
                                  const percentage =
                                    selectedAttendanceChartTotal > 0
                                      ? Math.round((count / selectedAttendanceChartTotal) * 100)
                                      : 0;

                                  return (
                                    <div key={status} className="flex items-center justify-between gap-4">
                                      <span className="flex items-center gap-2 text-slate-700">
                                        <span
                                          className="h-2.5 w-2.5 rounded-full"
                                          style={{ backgroundColor: ATTENDANCE_ISSUE_COLORS[status] }}
                                        />
                                        {status}
                                      </span>
                                      <span className="font-semibold text-slate-600">
                                        {count} ({percentage}%)
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-600">
                            No Late, Absent, MC or Leave records for this employee in the selected date range.
                          </div>
                        )}
                      </div>

                      <div className="shrink-0 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Issues by Day of Week
                        </p>
                        <div className="mt-2 flex h-12 items-end gap-4 border-b border-slate-200 px-2">
                          {selectedIssuesByWeekday.map((item: any) => (
                            <div
                              key={item.day}
                              className="group relative flex flex-1 flex-col items-center justify-end gap-2"
                            >
                              <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-40 -translate-x-1/2 rounded-md border border-slate-200 bg-white p-3 text-left text-xs text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                                <p className="mb-2 font-semibold text-slate-950">{item.day}</p>
                                <div className="space-y-1">
                                  <div className="flex justify-between">
                                    <span>Total issues</span>
                                    <span className="font-semibold text-slate-900">{item.count}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Late</span>
                                    <span>{item.late}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Absent</span>
                                    <span>{item.absent}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>MC</span>
                                    <span>{item.mc}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Leave</span>
                                    <span>{item.leave}</span>
                                  </div>
                                </div>
                              </div>
                              <div
                                className={`w-4 rounded-t-sm ${
                                  item.day === selectedIssuesPeakDay && item.count > 0
                                    ? "bg-red-400"
                                    : "bg-slate-300"
                                }`}
                                style={{
                                  height: item.count > 0 ? `${Math.max(8, (item.count / selectedIssuesMax) * 34)}px` : "2px",
                                }}
                              />
                            </div>
                          ))}
                        </div>
                        <div className="mt-2 grid grid-cols-5 px-2 text-center text-xs text-slate-500">
                          {selectedIssuesByWeekday.map((item: any) => (
                            <span key={item.day}>{item.day}</span>
                          ))}
                        </div>
                      </div>
                      </div>
                    </CardContent>
                  </Card>

                  </DialogContent>
                </Dialog>
              )}
            </>
          )}
        </TabsContent>


  );
}
