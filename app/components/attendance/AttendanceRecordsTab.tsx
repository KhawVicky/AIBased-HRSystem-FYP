// Shows the Attendance Records Tab view.
import { useMemo, useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { TabsContent } from "../ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { SearchClearButton } from "../shared/SearchClearButton";
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
  Pencil,
  Maximize2,
  Search,
  ShieldPlus,
  TrendingUp,
  UserX,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getCompactPageItems } from "../../lib/pagination";


type AttendanceRecordsTabProps = Record<string, any>;

// Formats schedule time label.
const formatScheduleTimeLabel = (value: string) => {
  const [hourText, minuteText] = value.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return value;

  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${minute.toString().padStart(2, "0")} ${period}`;
};

const scheduleTimeOptions = Array.from({ length: 33 }, (_, index) => {
  const totalMinutes = 6 * 60 + index * 30;
  const hour = Math.floor(totalMinutes / 60);
  const minute = totalMinutes % 60;
  const value = `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`;

  return {
    value,
    label: formatScheduleTimeLabel(value),
  };
});

// Renders the Attendance Records Tab component.
export function AttendanceRecordsTab(props: AttendanceRecordsTabProps) {
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
  applyInsightDateFilter,
  attendancePageCount,
  attendanceRate,
  attendanceData,
  attendanceSearch,
  attendanceSearchEmployeeId,
  canEditAttendanceSchedule,
  dateRangeWeekdayBreakdown,
  defaultInsightStartDate,
  earlyClockInCount,
  employeeInsights,
  employeeInsightsPageCount,
  employeeInsightsSearch,
  expandedEndDate,
  expandedEndPickerOpen,
  expandedEmployeeIssueData,
  expandedFilterEnd,
  expandedFilterStart,
  expandedInsightChart,
  expandedStartDate,
  expandedStartPickerOpen,
  expandedWeekdayBreakdown,
  filteredAttendanceData,
  formatCompactDate,
  formatDateInputValue,
  formatRecordDateLabel,
  formatShortDate,
  fullInsightEndDate,
  fullInsightStartDate,
  getEmployeeInitials,
  getDurationDisplay,
  getStatusBadge,
  getTimeDisplay,
  handleAttendanceSort,
  hasAttendanceRecords,
  hasFilteredRecords,
  insightEndDate,
  insightEndPickerOpen,
  insightStartDate,
  insightStartPickerOpen,
  invalidCount,
  isSavingAttendanceSchedule,
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
  setAttendanceSearchEmployeeId,
  saveAttendanceSchedule,
  setEmployeeInsightsPage,
  setEmployeeInsightsSearch,
  setExpandedEndDate,
  setExpandedEndPickerOpen,
  setExpandedInsightChart,
  setExpandedStartDate,
  setExpandedStartPickerOpen,
  setInsightEndDate,
  setInsightEndPickerOpen,
  setInsightStartDate,
  setInsightStartPickerOpen,
  setSelectedEmployeeDetailOpen,
  setSelectedEmployeeId,
  setStatusFilter,
  statusFilter,
  topAttendanceIssueEmployees,
  totalEmployeesCount,
  workEndTime,
  workingDaysInRange,
  workStartTime,
} = props;

  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [draftWorkStartTime, setDraftWorkStartTime] = useState(workStartTime);
  const [draftWorkEndTime, setDraftWorkEndTime] = useState(workEndTime);
  const [scheduleError, setScheduleError] = useState("");
  const [attendanceSearchFocused, setAttendanceSearchFocused] = useState(false);
  const attendanceSearchSuggestions = useMemo(() => {
    const searchTerm = attendanceSearch.trim().toLowerCase();
    if (!searchTerm || attendanceSearchEmployeeId) return [];

    const employeeMap = new Map<string, { employeeId: string; name: string }>();
    attendanceData
      .filter((record: any) => {
        const matchesDate = record.date === selectedDate;
        const matchesStatus = statusFilter === ALL_STATUSES || record.status === statusFilter;
        return matchesDate && matchesStatus;
      })
      .forEach((record: any) => {
        const employeeId = String(record.employeeId ?? "").trim();
        const name = String(record.name ?? "").trim();
        if (!employeeId || !name || employeeMap.has(employeeId)) return;

        const matchesSearch =
          employeeId.toLowerCase().startsWith(searchTerm) ||
          name.toLowerCase().startsWith(searchTerm);
        if (matchesSearch) employeeMap.set(employeeId, { employeeId, name });
      });

    return [...employeeMap.values()]
      .sort((first, second) => first.name.localeCompare(second.name, undefined, { sensitivity: "base" }))
      .slice(0, 8);
  }, [ALL_STATUSES, attendanceData, attendanceSearch, attendanceSearchEmployeeId, selectedDate, statusFilter]);

  // Opens schedule dialog.
  const openScheduleDialog = () => {
    setDraftWorkStartTime(workStartTime);
    setDraftWorkEndTime(workEndTime);
    setScheduleError("");
    setScheduleDialogOpen(true);
  };

  // Saves schedule.
  const saveSchedule = async () => {
    if (!draftWorkStartTime || !draftWorkEndTime) {
      setScheduleError("Please select both start and end time.");
      return;
    }

    if (draftWorkStartTime >= draftWorkEndTime) {
      setScheduleError("End time must be later than start time.");
      return;
    }

    try {
      await saveAttendanceSchedule(draftWorkStartTime, draftWorkEndTime);
      setScheduleDialogOpen(false);
    } catch {
      // The parent shows the error toast.
    }
  };

  return (
        <TabsContent value="records">
          <section className="space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-2xl font-bold tracking-tight text-slate-950">Attendance</h2>
                <span className="hidden h-8 w-px bg-slate-300 sm:block" />
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 bg-white"
                    onClick={() => moveSelectedDate(-1)}
                    aria-label="Previous day"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </Button>
                  <span className="min-w-48 text-center text-lg font-semibold text-slate-950">
                    {formatRecordDateLabel(selectedDate)}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 bg-white"
                    onClick={() => moveSelectedDate(1)}
                    aria-label="Next day"
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-50 text-[#003B7A]">
                      <CheckCircle className="h-4 w-4" />
                    </span>
                    <h3 className="font-semibold text-slate-950">Present Summary</h3>
                  </div>
                  {canEditAttendanceSchedule && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0 text-slate-500 hover:bg-blue-50 hover:text-[#003B7A]"
                      title="Edit working hours"
                      aria-label="Edit working hours"
                      onClick={openScheduleDialog}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <div className="mb-5 flex items-center justify-between gap-4">
                  <p className="text-sm font-medium text-slate-500">Present</p>
                  <p className="text-3xl font-bold text-slate-950">{presentCount}</p>
                </div>
                <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 pt-4">
                  <div className="pr-3">
                    <p className="text-sm text-slate-500">On time</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{onTimeCount}</p>
                  </div>
                  <div className="px-3 text-center">
                    <p className="text-sm text-slate-500">Late</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{lateClockInCount}</p>
                  </div>
                  <div className="pl-3 text-right">
                    <p className="text-sm text-slate-500">Early Clock-in</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{earlyClockInCount}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-red-50 text-red-600">
                    <AlertTriangle className="h-4 w-4" />
                  </span>
                  <h3 className="font-semibold text-slate-950">Absence Summary</h3>
                </div>
                <div className="mb-5 flex items-center justify-between gap-4">
                  <p className="text-sm font-medium text-slate-500">Not Present</p>
                  <p className="text-3xl font-bold text-slate-950">{notPresentCount}</p>
                </div>
                <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 pt-4">
                  <div className="pr-3">
                    <p className="text-sm text-slate-500">Absent</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{absentCount}</p>
                  </div>
                  <div className="px-3 text-center">
                    <p className="text-sm text-slate-500">MC</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{mcCount}</p>
                  </div>
                  <div className="pl-3 text-right">
                    <p className="text-sm text-slate-500">Leave</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{leaveCount}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-50 text-emerald-600">
                    <CalendarIcon className="h-4 w-4" />
                  </span>
                  <h3 className="font-semibold text-slate-950">Attendance Health</h3>
                </div>
                <div className="mb-5 flex items-center justify-between gap-4">
                  <p className="text-sm font-medium text-slate-500">Attendance Rate</p>
                  <p className="text-3xl font-bold text-slate-950">{attendanceRate}%</p>
                </div>
                <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 pt-4">
                  <div className="pr-3">
                    <p className="text-sm text-slate-500">No clock-out</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{noClockOutCount}</p>
                  </div>
                  <div className="px-3 text-center">
                    <p className="text-sm text-slate-500">Invalid</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{invalidCount}</p>
                  </div>
                  <div className="pl-3 text-right">
                    <p className="text-sm text-slate-500">Total Employees</p>
                    <p className="mt-1 text-xl font-bold text-slate-950">{totalEmployeesCount}</p>
                  </div>
                </div>
              </div>
            </div>

            <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
              <DialogContent className="sm:max-w-[440px]" onOpenAutoFocus={(event) => event.preventDefault()}>
                <DialogHeader>
                  <DialogTitle>Edit Working Hours</DialogTitle>
                  <DialogDescription>
                    Set the daily start and end time used for the Present Summary.
                  </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-2 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">
                      Start Time
                    </label>
                    <Select
                      value={draftWorkStartTime}
                      onValueChange={(value) => {
                        setDraftWorkStartTime(value);
                        setScheduleError("");
                      }}
                    >
                      <SelectTrigger className="h-12 rounded-lg border-slate-200 bg-slate-50 px-4 text-left shadow-xs transition-colors hover:bg-slate-100">
                        <Clock className="h-4 w-4 text-slate-500" />
                        <SelectValue placeholder="Select time" />
                      </SelectTrigger>
                      <SelectContent className="max-h-80 rounded-lg border-slate-200 shadow-lg">
                        {scheduleTimeOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value} className="py-2.5 text-sm">
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">
                      End Time
                    </label>
                    <Select
                      value={draftWorkEndTime}
                      onValueChange={(value) => {
                        setDraftWorkEndTime(value);
                        setScheduleError("");
                      }}
                    >
                      <SelectTrigger className="h-12 rounded-lg border-slate-200 bg-slate-50 px-4 text-left shadow-xs transition-colors hover:bg-slate-100">
                        <Clock className="h-4 w-4 text-slate-500" />
                        <SelectValue placeholder="Select time" />
                      </SelectTrigger>
                      <SelectContent className="max-h-80 rounded-lg border-slate-200 shadow-lg">
                        {scheduleTimeOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value} className="py-2.5 text-sm">
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {scheduleError && <p className="text-sm text-red-600">{scheduleError}</p>}

                <DialogFooter>
                  <Button
                    type="button"
                    className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                    onClick={saveSchedule}
                    disabled={isSavingAttendanceSchedule}
                  >
                    {isSavingAttendanceSchedule ? "Saving..." : "Save Changes"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative w-full sm:max-w-xs">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  inputMode="search"
                  value={attendanceSearch}
                  onChange={(event) => {
                    setAttendanceSearch(event.target.value);
                    setAttendanceSearchEmployeeId("");
                  }}
                  onFocus={() => setAttendanceSearchFocused(true)}
                  onBlur={() => window.setTimeout(() => setAttendanceSearchFocused(false), 120)}
                  placeholder="Search name or employee ID"
                  className="h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-10 text-sm text-slate-950 shadow-sm outline-none transition-[color,box-shadow] placeholder:text-slate-400 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                />
                <SearchClearButton
                  show={Boolean(attendanceSearch)}
                  onClear={() => {
                    setAttendanceSearch("");
                    setAttendanceSearchEmployeeId("");
                    setAttendanceSearchFocused(false);
                  }}
                />
                {attendanceSearchFocused && attendanceSearchSuggestions.length > 0 && (
                  <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                    {attendanceSearchSuggestions.map((employee) => (
                      <button
                        key={employee.employeeId}
                        type="button"
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setAttendanceSearchEmployeeId(employee.employeeId);
                          setAttendanceSearch(`${employee.name} (${employee.employeeId})`);
                          setAttendanceSearchFocused(false);
                        }}
                      >
                        <span className="font-medium text-slate-950">{employee.name}</span>
                        <span className="text-xs text-slate-500">{employee.employeeId}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex justify-start">
                <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}>
                  <SelectTrigger className="h-10 w-35 border-slate-200 bg-white shadow-sm transition-colors hover:bg-slate-50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_STATUSES}>All Statuses</SelectItem>
                    {ATTENDANCE_STATUSES.map((status: any) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {isLoading ? (
                <div className="rounded-lg border border-slate-200 p-8 text-center text-slate-500">
                  Loading attendance records...
                </div>
              ) : !hasAttendanceRecords ? (
                <div className="rounded-lg border border-slate-200 p-8 text-center text-slate-500">
                  Upload a valid Excel file to preview attendance records.
                </div>
              ) : !hasFilteredRecords ? (
                <div className="rounded-lg border border-slate-200 p-8 text-center text-slate-500">
                  No attendance records match the selected date and status.
                </div>
              ) : (
                <>
                  <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                    <table className="w-full table-fixed bg-white text-sm">
                      <colgroup>
                        <col className="w-[24%]" />
                        <col className="w-[22%]" />
                        <col className="w-[22%]" />
                        <col className="w-[22%]" />
                        <col className="w-[10%]" />
                      </colgroup>
                      <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-4 py-4">Employee</th>
                          <th className="px-4 py-2">
                            <button
                              type="button"
                              onClick={() => handleAttendanceSort("clockIn")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Clock In
                              {renderSortIcon("clockIn")}
                            </button>
                          </th>
                          <th className="px-4 py-2">
                            <button
                              type="button"
                              onClick={() => handleAttendanceSort("clockOut")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Clock Out
                              {renderSortIcon("clockOut")}
                            </button>
                          </th>
                          <th className="px-4 py-2">
                            <button
                              type="button"
                              onClick={() => handleAttendanceSort("duration")}
                              className="inline-flex items-center gap-1.5 rounded-md text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-slate-900"
                            >
                              Duration
                              {renderSortIcon("duration")}
                            </button>
                          </th>
                          <th className="px-4 py-2">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {pagedAttendanceData.map((record: any) => (
                          <tr
                            key={record.recordId ?? `${record.employeeId}-${record.date}-${record.status}`}
                            className="transition-colors hover:bg-slate-50"
                          >
                            <td className="px-4 py-2">
                              <div className="font-medium text-slate-950">{record.name}</div>
                              <div className="mt-0.5 text-sm text-slate-500">{record.employeeId}</div>
                              {(record.department || record.jobTitle) && (
                                <div className="mt-0.5 text-xs text-slate-500">
                                  {[record.department, record.jobTitle].filter(Boolean).join(" - ")}
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-2 text-slate-600">
                              {getTimeDisplay(record, "clockIn")}
                            </td>
                            <td className="px-4 py-2 text-slate-600">
                              {getTimeDisplay(record, "clockOut")}
                            </td>
                            <td className="px-4 py-2 text-slate-600">
                              {getDurationDisplay(record)}
                            </td>
                            <td className="px-4 py-2">{getStatusBadge(record.status)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {filteredAttendanceData.length > ATTENDANCE_RECORDS_PER_PAGE && (
                      <Pagination className="border-t border-slate-100 bg-white py-4">
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious
                              href="#"
                              aria-disabled={safeAttendancePage === 1}
                              className={
                                safeAttendancePage === 1
                                  ? "pointer-events-none opacity-50"
                                  : ""
                              }
                              onClick={(event) => {
                                event.preventDefault();
                                setAttendancePage((page: any) => Math.max(1, page - 1));
                              }}
                            />
                          </PaginationItem>

                          {getCompactPageItems(safeAttendancePage, attendancePageCount).map((item) => (
                            <PaginationItem key={item}>
                              {typeof item === "number" ? (
                                <PaginationLink
                                  href="#"
                                  isActive={item === safeAttendancePage}
                                  onClick={(event) => {
                                    event.preventDefault();
                                    setAttendancePage(item);
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
                              aria-disabled={safeAttendancePage === attendancePageCount}
                              className={
                                safeAttendancePage === attendancePageCount
                                  ? "pointer-events-none opacity-50"
                                  : ""
                              }
                              onClick={(event) => {
                                event.preventDefault();
                                  setAttendancePage((page: any) =>
                                  Math.min(attendancePageCount, page + 1),
                                );
                              }}
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    )}
                  </div>
                </>
              )}
          </section>
        </TabsContent>


  );
}
