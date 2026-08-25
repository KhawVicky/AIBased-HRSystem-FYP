// Shows the Attendance Analytics view.
import { useEffect, useState, type ChangeEvent } from "react";
import * as XLSX from "xlsx";
import { PageLayout } from "../shared/PageLayout";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
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
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  BriefcaseBusiness,
  Calendar as CalendarIcon,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  ShieldPlus,
  Maximize2,
  Search,
  TrendingUp,
  Upload,
  UserX,
  X,
} from "lucide-react";
import { Calendar as DatePickerCalendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { toast } from "sonner";
import { apiFetch, getStoredUser } from "../../lib/api";
import { AttendanceRecordsTab } from "./AttendanceRecordsTab";
import { EmployeeInsightsTab } from "./EmployeeInsightsTab";
import { AttendanceTrendsDashboard as AttendanceTrendsTab } from "./AttendanceTrendsDashboard";
import { getCompactPageItems } from "../../lib/pagination";

const ATTENDANCE_RECORDS_PER_PAGE = 20;
const EMPLOYEE_INSIGHTS_PER_PAGE = ATTENDANCE_RECORDS_PER_PAGE;
const ATTENDANCE_STATUSES = ["Attend", "Late", "Absent", "MC", "Leave"] as const;
const ALL_STATUSES = "all";
const ALL_FILTER_VALUE = "all";
const ATTENDANCE_ISSUE_COLORS: Record<"Present" | "Late" | "Absent" | "MC" | "Leave", string> = {
  Present: "#86efac",
  Late: "#f59e0b",
  Absent: "#ef4444",
  MC: "#3b82f6",
  Leave: "#64748b",
};
const ATTENDANCE_ISSUE_TEXT_COLORS: Record<"Present" | "Late" | "Absent" | "MC" | "Leave", string> = {
  Present: "#15803d",
  Late: "#b45309",
  Absent: "#b91c1c",
  MC: "#1d4ed8",
  Leave: "#475569",
};
const ATTENDANCE_CHART_BADGE_CLASSES: Record<"Present" | "Late" | "Absent" | "MC" | "Leave", string> = {
  Present: "bg-green-50 text-green-700 ring-green-100",
  Late: "bg-amber-50 text-amber-700 ring-amber-100",
  Absent: "bg-red-50 text-red-700 ring-red-100",
  MC: "bg-blue-50 text-blue-700 ring-blue-100",
  Leave: "bg-slate-100 text-slate-600 ring-slate-200",
};
const ATTENDANCE_ISSUE_LABELS = ["Present", "Late", "Absent", "MC", "Leave"] as const;
type ExpandedInsightChart = "issues" | null;

type AttendanceRecord = {
  recordId?: number;
  uploadId?: number;
  employeeId: string;
  name: string;
  department: string;
  jobTitle: string;
  date: string;
  clockIn: string;
  clockOut: string;
  status: (typeof ATTENDANCE_STATUSES)[number];
};

type AttendanceApiRecord = {
  recordId: number;
  uploadId: number;
  employeeId: string;
  name: string;
  department?: string | null;
  jobTitle?: string | null;
  attendanceDate: string;
  attendanceTime: string | null;
  clockInTime?: string | null;
  clockOutTime?: string | null;
  status: AttendanceRecord["status"];
};

type AttendanceSortKey = "name" | "clockIn" | "clockOut" | "duration";
type AttendanceSortDirection = "asc" | "desc";
type EmployeeInsightSortKey = "attend" | "late" | "absent" | "mc" | "leave" | "attendanceRate";
type EmployeeInsightSortDirection = "asc" | "desc";
type EmployeeInsight = {
  employeeId: string;
  name: string;
  records: AttendanceRecord[];
  attend: number;
  late: number;
  absent: number;
  mc: number;
  leave: number;
  total: number;
  attendanceRate: number;
  mainPattern: string;
};

type AttendanceUpload = {
  uploadId: number;
  fileName: string;
  filePath: string;
  uploadedBy: number | null;
  uploadedAt: string;
  totalRows: number;
};

type AttendanceSettings = {
  workStartTime: string;
  workEndTime: string;
  updatedBy?: number | null;
  updatedAt?: string | null;
};

// Normalizes header.
const normalizeHeader = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9]/g, "");

// Provides the cell string helper.
const cellString = (value: unknown) => String(value ?? "").trim();

// Checks the attendance status condition.
const isAttendanceStatus = (value: string): value is AttendanceRecord["status"] =>
  ATTENDANCE_STATUSES.some((status) => status.toLowerCase() === value.toLowerCase());

// Normalizes status.
const normalizeStatus = (value: string): AttendanceRecord["status"] | null => {
  const match = ATTENDANCE_STATUSES.find(
    (status) => status.toLowerCase() === value.trim().toLowerCase(),
  );
  return match ?? null;
};

// Normalizes date value.
const normalizeDateValue = (value: unknown) => {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString().slice(0, 10);
  }

  const text = cellString(value);
  if (!text) return "";

  const parsed = new Date(text);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10);
  }

  return text;
};

// Normalizes time value.
const normalizeTimeValue = (value: unknown) => {
  const text = cellString(value);
  if (!text || text === "-") return "";
  return text;
};

// Formats api time.
const formatApiTime = (value: string | null | undefined) => {
  if (!value) return "";
  const parts = value.split(":");
  if (parts.length < 2) return value;

  const hour = Number(parts[0]);
  const minute = Number(parts[1]);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return value;

  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour.toString().padStart(2, "0")}:${minute
    .toString()
    .padStart(2, "0")} ${period}`;
};

// Gets attendance time minutes.
const getAttendanceTimeMinutes = (value: string) => {
  if (!value || value === "-") return Number.MAX_SAFE_INTEGER;

  const match = value.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
  if (!match) return Number.MAX_SAFE_INTEGER;

  let hour = Number(match[1]);
  const minute = Number(match[2]);
  const period = match[3]?.toUpperCase();

  if (Number.isNaN(hour) || Number.isNaN(minute)) return Number.MAX_SAFE_INTEGER;
  if (period === "PM" && hour < 12) hour += 12;
  if (period === "AM" && hour === 12) hour = 0;

  return hour * 60 + minute;
};

// Gets attendance duration minutes.
const getAttendanceDurationMinutes = (record: AttendanceRecord) => {
  const clockInMinutes = getAttendanceTimeMinutes(record.clockIn);
  const clockOutMinutes = getAttendanceTimeMinutes(record.clockOut);

  if (
    clockInMinutes === Number.MAX_SAFE_INTEGER ||
    clockOutMinutes === Number.MAX_SAFE_INTEGER ||
    clockOutMinutes < clockInMinutes
  ) {
    return Number.MAX_SAFE_INTEGER;
  }

  return clockOutMinutes - clockInMinutes;
};

// Formats attendance duration.
const formatAttendanceDuration = (minutes: number) => {
  if (minutes === Number.MAX_SAFE_INTEGER) return "-";

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours === 0) return `${remainingMinutes}m`;
  if (remainingMinutes === 0) return `${hours}h`;
  return `${hours}h ${remainingMinutes}m`;
};

// Derives attendance status.
const deriveAttendanceStatus = (
  status: AttendanceRecord["status"],
  clockIn: string,
  workStartTime: string,
): AttendanceRecord["status"] => {
  // Recheck present records against the saved start time.
  if (status !== "Attend" && status !== "Late") return status;

  const clockInMinutes = getAttendanceTimeMinutes(clockIn);
  const workStartMinutes = getAttendanceTimeMinutes(workStartTime);
  if (clockInMinutes === Number.MAX_SAFE_INTEGER || workStartMinutes === Number.MAX_SAFE_INTEGER) {
    return status;
  }

  return clockInMinutes > workStartMinutes ? "Late" : "Attend";
};

// Applies attendance schedule.
const applyAttendanceSchedule = (records: AttendanceRecord[], workStartTime: string) =>
  records.map((record) => ({
    ...record,
    status: deriveAttendanceStatus(record.status, record.clockIn, workStartTime),
  }));

// Provides the map api record helper.
const mapApiRecord = (record: AttendanceApiRecord, workStartTime: string): AttendanceRecord => {
  const clockIn = formatApiTime(record.clockInTime ?? record.attendanceTime);
  const status = deriveAttendanceStatus(record.status, clockIn, workStartTime);

  return {
    recordId: record.recordId,
    uploadId: record.uploadId,
    employeeId: record.employeeId,
    name: record.name,
    department: record.department ?? "",
    jobTitle: record.jobTitle ?? "",
    date: record.attendanceDate,
    clockIn,
    clockOut: formatApiTime(record.clockOutTime),
    status,
  };
};

// Formats date input value.
const formatDateInputValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Provides the today date value helper.
const todayDateValue = () => formatDateInputValue(new Date());

// Formats record date label.
const formatRecordDateLabel = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
};

// Formats short date.
const formatShortDate = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-GB");
};

// Formats compact date.
const formatCompactDate = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

// Gets employee initials.
const getEmployeeInitials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";

// Gets one month before date.
const getOneMonthBeforeDate = (value: string) => {
  const end = new Date(`${value}T00:00:00`);
  if (Number.isNaN(end.getTime())) return value;

  const start = new Date(end);
  start.setMonth(start.getMonth() - 1);
  return formatDateInputValue(start);
};

const weekdayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
// Gets weekday name.
const getWeekdayName = (value: string) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "";

  return weekdayNames[date.getDay()];
};

// Provides the most common text helper.
const mostCommonText = (values: string[]) => {
  if (values.length === 0) return "-";

  const counts = values.reduce<Record<string, number>>((map, value) => {
    map[value] = (map[value] ?? 0) + 1;
    return map;
  }, {});

  return Object.entries(counts).sort((first, second) => second[1] - first[1])[0]?.[0] ?? "-";
};

// Gets late time range.
const getLateTimeRange = (records: AttendanceRecord[]) => {
  const lateTimes = records
    .filter((record) => record.status === "Late")
    .map((record) => getAttendanceTimeMinutes(record.clockIn))
    .filter((minutes) => minutes < Number.MAX_SAFE_INTEGER);

  if (lateTimes.length === 0) return "-";

  const buckets = lateTimes.reduce<Record<string, number>>((map, minutes) => {
    const start = Math.floor(minutes / 30) * 30;
    const end = start + 30;
    const label = `${formatMinutesAsTime(start)} - ${formatMinutesAsTime(end)}`;
    map[label] = (map[label] ?? 0) + 1;
    return map;
  }, {});

  return Object.entries(buckets).sort((first, second) => second[1] - first[1])[0]?.[0] ?? "-";
};

// Formats minutes as time.
const formatMinutesAsTime = (minutes: number) => {
  const hour24 = Math.floor(minutes / 60);
  const minute = minutes % 60;
  const period = hour24 >= 12 ? "PM" : "AM";
  const hour12 = hour24 % 12 || 12;
  return `${hour12}:${String(minute).padStart(2, "0")} ${period}`;
};

// Gets employee main pattern.
const getEmployeeMainPattern = (insight: Omit<EmployeeInsight, "mainPattern">) => {
  const leaveDay = mostCommonText(
    insight.records.filter((record) => record.status === "Leave").map((record) => getWeekdayName(record.date)),
  );
  const mcDay = mostCommonText(
    insight.records.filter((record) => record.status === "MC").map((record) => getWeekdayName(record.date)),
  );
  const absentDay = mostCommonText(
    insight.records.filter((record) => record.status === "Absent").map((record) => getWeekdayName(record.date)),
  );

  if (insight.absent >= 2 && absentDay !== "-") return `Frequent absence on ${absentDay}`;
  if (insight.mc >= 2 && mcDay !== "-") return `MC mostly on ${mcDay}`;
  if (insight.leave >= 2 && leaveDay !== "-") return `Often leave on ${leaveDay}`;
  if (insight.late >= 2) return "Repeated late clock-in";
  return "Good attendance";
};

// Renders the Attendance Analytics component.
export function AttendanceAnalytics() {
  const [selectedFileName, setSelectedFileName] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [attendanceData, setAttendanceData] = useState<AttendanceRecord[]>([]);
  const [attendancePage, setAttendancePage] = useState(1);
  const [employeeInsightsPage, setEmployeeInsightsPage] = useState(1);
  const [selectedDate, setSelectedDate] = useState(todayDateValue);
  const [attendanceSearch, setAttendanceSearch] = useState("");
  const [attendanceSearchEmployeeId, setAttendanceSearchEmployeeId] = useState("");
  const [employeeInsightsSearch, setEmployeeInsightsSearch] = useState("");
  const [employeeInsightsSearchEmployeeId, setEmployeeInsightsSearchEmployeeId] = useState("");
  const [statusFilter, setStatusFilter] = useState<typeof ALL_STATUSES | AttendanceRecord["status"]>(ALL_STATUSES);
  const [attendanceSort, setAttendanceSort] = useState<{
    key: AttendanceSortKey;
    direction: AttendanceSortDirection;
  }>({ key: "name", direction: "asc" });
  const [employeeInsightsSort, setEmployeeInsightsSort] = useState<{
    key: EmployeeInsightSortKey | null;
    direction: EmployeeInsightSortDirection;
  }>({ key: null, direction: "asc" });
  const [insightStartDate, setInsightStartDate] = useState("");
  const [insightEndDate, setInsightEndDate] = useState("");
  const [appliedInsightStartDate, setAppliedInsightStartDate] = useState("");
  const [appliedInsightEndDate, setAppliedInsightEndDate] = useState("");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");
  const [selectedEmployeeDetailOpen, setSelectedEmployeeDetailOpen] = useState(false);
  const [expandedInsightChart, setExpandedInsightChart] = useState<ExpandedInsightChart>(null);
  const [insightStartPickerOpen, setInsightStartPickerOpen] = useState(false);
  const [insightEndPickerOpen, setInsightEndPickerOpen] = useState(false);
  const [expandedStartDate, setExpandedStartDate] = useState("");
  const [expandedEndDate, setExpandedEndDate] = useState("");
  const [expandedAppliedStartDate, setExpandedAppliedStartDate] = useState("");
  const [expandedAppliedEndDate, setExpandedAppliedEndDate] = useState("");
  const [expandedStartPickerOpen, setExpandedStartPickerOpen] = useState(false);
  const [expandedEndPickerOpen, setExpandedEndPickerOpen] = useState(false);
  const [expandedDepartmentFilter, setExpandedDepartmentFilter] = useState(ALL_FILTER_VALUE);
  const [expandedJobTitleFilter, setExpandedJobTitleFilter] = useState(ALL_FILTER_VALUE);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [workStartTime, setWorkStartTime] = useState("08:00");
  const [workEndTime, setWorkEndTime] = useState("17:00");
  const [isSavingAttendanceSchedule, setIsSavingAttendanceSchedule] = useState(false);
  const currentUser = getStoredUser();
  const canEditAttendanceSchedule =
    currentUser?.roleId === 2 || currentUser?.roleKey === "hiring_manager";
  const workStartMinutes = getAttendanceTimeMinutes(workStartTime);

  // Build the daily table and summary from the same records.
  const dailyAttendanceData = attendanceData.filter((record) => record.date === selectedDate);
  const filteredAttendanceData = dailyAttendanceData.filter((record) => {
    const searchTerm = attendanceSearch.trim().toLowerCase();
    const matchesSearch =
      attendanceSearchEmployeeId !== ""
        ? record.employeeId === attendanceSearchEmployeeId
        : searchTerm === "" ||
          record.employeeId.toLowerCase().includes(searchTerm) ||
          record.name.toLowerCase().includes(searchTerm);
    const matchesStatus = statusFilter === ALL_STATUSES || record.status === statusFilter;
    return matchesSearch && matchesStatus;
  });
  const hasAttendanceRecords = attendanceData.length > 0;
  const hasFilteredRecords = filteredAttendanceData.length > 0;
  const earlyClockInCount = dailyAttendanceData.filter(
    (record) => record.status === "Attend" && getAttendanceTimeMinutes(record.clockIn) < workStartMinutes,
  ).length;
  const onTimeCount = dailyAttendanceData.filter(
    (record) =>
      record.status === "Attend" &&
      getAttendanceTimeMinutes(record.clockIn) >= workStartMinutes &&
      getAttendanceTimeMinutes(record.clockIn) < Number.MAX_SAFE_INTEGER,
  ).length;
  const lateClockInCount = dailyAttendanceData.filter((record) => record.status === "Late").length;
  const absentCount = dailyAttendanceData.filter((record) => record.status === "Absent").length;
  const mcCount = dailyAttendanceData.filter((record) => record.status === "MC").length;
  const leaveCount = dailyAttendanceData.filter((record) => record.status === "Leave").length;
  const presentCount = onTimeCount + lateClockInCount + earlyClockInCount;
  const notPresentCount = absentCount + mcCount + leaveCount;
  const attendanceRate =
    presentCount + notPresentCount > 0
      ? Math.round((presentCount / (presentCount + notPresentCount)) * 100)
      : 0;
  const noClockOutCount = dailyAttendanceData.filter(
    (record) => (record.status === "Attend" || record.status === "Late") && !record.clockOut,
  ).length;
  const invalidCount = 0;
  const totalEmployeesCount = dailyAttendanceData.length;
  const sortedAttendanceData = [...filteredAttendanceData].sort((first, second) => {
    const direction = attendanceSort.direction === "asc" ? 1 : -1;

    if (attendanceSort.key === "clockIn" || attendanceSort.key === "clockOut") {
      return (
        (getAttendanceTimeMinutes(first[attendanceSort.key]) -
          getAttendanceTimeMinutes(second[attendanceSort.key])) *
        direction
      );
    }

    if (attendanceSort.key === "duration") {
      return (getAttendanceDurationMinutes(first) - getAttendanceDurationMinutes(second)) * direction;
    }

    return first.name.localeCompare(second.name, undefined, { sensitivity: "base" }) * direction;
  });
  const attendCount = attendanceData.filter((record) => record.status === "Attend").length;
  const reviewCount = attendanceData.filter((record) =>
    ["Late", "Absent", "MC", "Leave"].includes(record.status),
  ).length;
  const attendancePageCount = Math.max(
    1,
    Math.ceil(sortedAttendanceData.length / ATTENDANCE_RECORDS_PER_PAGE),
  );
  const safeAttendancePage = Math.min(attendancePage, attendancePageCount);
  const pagedAttendanceData = sortedAttendanceData.slice(
    (safeAttendancePage - 1) * ATTENDANCE_RECORDS_PER_PAGE,
    safeAttendancePage * ATTENDANCE_RECORDS_PER_PAGE,
  );
  const availableDates = [...new Set(attendanceData.map((record) => record.date))]
    .filter(Boolean)
    .sort();
  const fullInsightStartDate = availableDates[0] ?? "";
  const fullInsightEndDate = availableDates[availableDates.length - 1] ?? "";
  const defaultInsightEndDate = todayDateValue();
  const defaultInsightStartDate = getOneMonthBeforeDate(defaultInsightEndDate);
  const insightMaxDate = [fullInsightEndDate, defaultInsightEndDate].filter(Boolean).sort().at(-1) ?? defaultInsightEndDate;
  const insightRecords = attendanceData.filter((record) => {
    const start = appliedInsightStartDate || fullInsightStartDate;
    const end = appliedInsightEndDate || fullInsightEndDate;
    if (!start || !end) return false;
    return record.date >= start && record.date <= end;
  });
  // Group records by employee for longer-term insights.
  const allEmployeeInsights = Object.values(
    insightRecords.reduce<Record<string, AttendanceRecord[]>>((map, record) => {
      map[record.employeeId] = [...(map[record.employeeId] ?? []), record];
      return map;
    }, {}),
  )
    .map((records) => {
      const attend = records.filter((record) => record.status === "Attend").length;
      const late = records.filter((record) => record.status === "Late").length;
      const absent = records.filter((record) => record.status === "Absent").length;
      const mc = records.filter((record) => record.status === "MC").length;
      const leave = records.filter((record) => record.status === "Leave").length;
      const total = records.length;
      const baseInsight = {
        employeeId: records[0].employeeId,
        name: records[0].name,
        records,
        attend,
        late,
        absent,
        mc,
        leave,
        total,
        attendanceRate: total > 0 ? Math.round(((attend + late) / total) * 100) : 0,
      };

      return {
        ...baseInsight,
        mainPattern: getEmployeeMainPattern(baseInsight),
      };
    })
    .sort((first, second) => first.name.localeCompare(second.name, undefined, { sensitivity: "base" }));
  const employeeInsightSearchTerm = employeeInsightsSearch.trim().toLowerCase();
  const filteredEmployeeInsights = allEmployeeInsights.filter(
    (employee) =>
      employeeInsightsSearchEmployeeId !== ""
        ? employee.employeeId === employeeInsightsSearchEmployeeId
        : employeeInsightSearchTerm === "" ||
          employee.employeeId.toLowerCase().includes(employeeInsightSearchTerm) ||
          employee.name.toLowerCase().includes(employeeInsightSearchTerm),
  );
  const employeeInsights = [...filteredEmployeeInsights].sort((first, second) => {
    if (!employeeInsightsSort.key) {
      return first.name.localeCompare(second.name, undefined, { sensitivity: "base" });
    }

    const direction = employeeInsightsSort.direction === "asc" ? 1 : -1;
    return (first[employeeInsightsSort.key] - second[employeeInsightsSort.key]) * direction;
  });
  const employeeInsightsPageCount = Math.max(
    1,
    Math.ceil(employeeInsights.length / EMPLOYEE_INSIGHTS_PER_PAGE),
  );
  const safeEmployeeInsightsPage = Math.min(employeeInsightsPage, employeeInsightsPageCount);
  const pagedEmployeeInsights = employeeInsights.slice(
    (safeEmployeeInsightsPage - 1) * EMPLOYEE_INSIGHTS_PER_PAGE,
    safeEmployeeInsightsPage * EMPLOYEE_INSIGHTS_PER_PAGE,
  );
  const selectedEmployee =
    employeeInsights.find((employee) => employee.employeeId === selectedEmployeeId) ?? employeeInsights[0];
  const workingDaysInRange = new Set(
    insightRecords.filter((record) => record.clockIn).map((record) => record.date),
  ).size;
  const selectedWorkedDays = selectedEmployee
    ? new Set(
        selectedEmployee.records
          .filter((record) => record.clockIn && (record.status === "Attend" || record.status === "Late"))
          .map((record) => record.date),
      ).size
    : 0;
  const topAttendanceIssueEmployees = allEmployeeInsights
    .map((employee) => ({
      employeeId: employee.employeeId,
      employeeName: employee.name,
      employeeLabel: `${employee.name} (${employee.employeeId})`,
      late: employee.late,
      absent: employee.absent,
      mc: employee.mc,
      leave: employee.leave,
      issueCount: employee.late + employee.absent + employee.mc + employee.leave,
    }))
    .sort((first, second) => second.issueCount - first.issueCount)
    .slice(0, 10);
  const expandedFilterStart = expandedAppliedStartDate || appliedInsightStartDate || fullInsightStartDate;
  const expandedFilterEnd = expandedAppliedEndDate || appliedInsightEndDate || fullInsightEndDate;
  const expandedInsightRecords = attendanceData.filter((record) => {
    if (!expandedFilterStart || !expandedFilterEnd) return false;
    const matchesDate = record.date >= expandedFilterStart && record.date <= expandedFilterEnd;
    const matchesDepartment =
      expandedDepartmentFilter === ALL_FILTER_VALUE || record.department === expandedDepartmentFilter;
    const matchesJobTitle =
      expandedJobTitleFilter === ALL_FILTER_VALUE || record.jobTitle === expandedJobTitleFilter;
    return matchesDate && matchesDepartment && matchesJobTitle;
  });
  const expandedDepartmentOptions = [
    ...new Set(
      attendanceData
        .filter((record) => {
          if (!expandedFilterStart || !expandedFilterEnd) return true;
          return record.date >= expandedFilterStart && record.date <= expandedFilterEnd;
        })
        .map((record) => record.department)
        .filter(Boolean),
    ),
  ].sort();
  const expandedJobTitleOptions = [
    ...new Set(
      attendanceData
        .filter((record) => {
          if (!expandedFilterStart || !expandedFilterEnd) return true;
          const matchesDate = record.date >= expandedFilterStart && record.date <= expandedFilterEnd;
          const matchesDepartment =
            expandedDepartmentFilter === ALL_FILTER_VALUE || record.department === expandedDepartmentFilter;
          return matchesDate && matchesDepartment;
        })
        .map((record) => record.jobTitle)
        .filter(Boolean),
    ),
  ].sort();
  const expandedEmployeeIssueData = Object.values(
    expandedInsightRecords.reduce<Record<string, AttendanceRecord[]>>((map, record) => {
      map[record.employeeId] = [...(map[record.employeeId] ?? []), record];
      return map;
    }, {}),
  )
    .map((records) => ({
      employeeId: records[0].employeeId,
      employeeName: records[0].name,
      employeeLabel: `${records[0].name} (${records[0].employeeId})`,
      attend: records.filter((record) => record.status === "Attend").length,
      late: records.filter((record) => record.status === "Late").length,
      absent: records.filter((record) => record.status === "Absent").length,
      mc: records.filter((record) => record.status === "MC").length,
      leave: records.filter((record) => record.status === "Leave").length,
      issueCount: records.filter((record) =>
        ["Late", "Absent", "MC", "Leave"].includes(record.status),
      ).length,
    }))
    .filter((employee) => employee.issueCount > 0)
    .sort((first, second) => second.issueCount - first.issueCount);
  const selectedAttendanceIssueBreakdown = selectedEmployee
    ? ([
        ["Present", "Attend"],
        ["Late", "Late"],
        ["Absent", "Absent"],
        ["MC", "MC"],
        ["Leave", "Leave"],
      ] as const)
        .map(([status, recordStatus]) => ({
          status,
          count: selectedEmployee.records.filter((record) => record.status === recordStatus).length,
        }))
        .filter((item) => item.count > 0)
    : [];
  const selectedAttendanceChartTotal = selectedAttendanceIssueBreakdown.reduce(
    (sum, item) => sum + item.count,
    0,
  );
  const selectedIssuesByWeekday = selectedEmployee
    ? ([
        ["Mon", 1],
        ["Tue", 2],
        ["Wed", 3],
        ["Thu", 4],
        ["Fri", 5],
      ] as const).map(([day, dayIndex]) => ({
        day,
        late: selectedEmployee.records.filter((record) => {
          const date = new Date(`${record.date}T00:00:00`);
          return (
            !Number.isNaN(date.getTime()) &&
            date.getDay() === dayIndex &&
            record.status === "Late"
          );
        }).length,
        absent: selectedEmployee.records.filter((record) => {
          const date = new Date(`${record.date}T00:00:00`);
          return (
            !Number.isNaN(date.getTime()) &&
            date.getDay() === dayIndex &&
            record.status === "Absent"
          );
        }).length,
        mc: selectedEmployee.records.filter((record) => {
          const date = new Date(`${record.date}T00:00:00`);
          return (
            !Number.isNaN(date.getTime()) &&
            date.getDay() === dayIndex &&
            record.status === "MC"
          );
        }).length,
        leave: selectedEmployee.records.filter((record) => {
          const date = new Date(`${record.date}T00:00:00`);
          return (
            !Number.isNaN(date.getTime()) &&
            date.getDay() === dayIndex &&
            record.status === "Leave"
          );
        }).length,
      }))
        .map((item) => ({
          ...item,
          count: item.late + item.absent + item.mc + item.leave,
        }))
    : [];
  const selectedIssuesMax = Math.max(1, ...selectedIssuesByWeekday.map((item) => item.count));
  const selectedIssuesPeakDay = selectedIssuesByWeekday.reduce(
    (peak, item) => (item.count > peak.count ? item : peak),
    { day: "", count: 0, late: 0, absent: 0, mc: 0, leave: 0 },
  ).day;
  const selectedMostLeaveDay = selectedEmployee
    ? mostCommonText(
        selectedEmployee.records
          .filter((record) => record.status === "Leave")
          .map((record) => getWeekdayName(record.date)),
      )
    : "-";
  const selectedMostMcDay = selectedEmployee
    ? mostCommonText(
        selectedEmployee.records
          .filter((record) => record.status === "MC")
          .map((record) => getWeekdayName(record.date)),
      )
    : "-";
  const selectedMostAbsentDay = selectedEmployee
    ? mostCommonText(
        selectedEmployee.records
          .filter((record) => record.status === "Absent")
          .map((record) => getWeekdayName(record.date)),
      )
    : "-";
  const selectedLateTimeRange = selectedEmployee ? getLateTimeRange(selectedEmployee.records) : "-";
  const selectedPatternSentences =
    selectedEmployee
      ? [
          selectedMostLeaveDay !== "-"
            ? `${selectedEmployee.name} takes leave most often on ${selectedMostLeaveDay}.`
            : "",
          selectedMostMcDay !== "-"
            ? `${selectedEmployee.name} takes MC most often on ${selectedMostMcDay}.`
            : "",
          selectedMostAbsentDay !== "-"
            ? `${selectedEmployee.name} is absent most often on ${selectedMostAbsentDay}.`
            : "",
          selectedLateTimeRange !== "-"
            ? `${selectedEmployee.name} has repeated late clock-in between ${selectedLateTimeRange}.`
            : "",
        ].filter(Boolean)
      : [];

  // Handles attendance sort.
  const handleAttendanceSort = (key: AttendanceSortKey) => {
    setAttendanceSort((current) => {
      if (current.key !== key) {
        return { key, direction: "asc" };
      }

      if (current.direction === "asc") {
        return { key, direction: "desc" };
      }

      return { key: "name", direction: "asc" };
    });
  };

  // Renders sort icon.
  const renderSortIcon = (key: AttendanceSortKey) => {
    if (attendanceSort.key !== key) {
      return <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />;
    }

    return attendanceSort.direction === "asc" ? (
      <ArrowUp className="h-3.5 w-3.5 text-slate-600" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-slate-600" />
    );
  };

  // Handles employee insights sort.
  const handleEmployeeInsightsSort = (key: EmployeeInsightSortKey) => {
    setEmployeeInsightsSort((current) => {
      if (current.key !== key) {
        return { key, direction: "desc" };
      }

      if (current.direction === "desc") {
        return { key, direction: "asc" };
      }

      return { key: null, direction: "asc" };
    });
  };

  // Renders employee insights sort icon.
  const renderEmployeeInsightsSortIcon = (key: EmployeeInsightSortKey) => {
    if (employeeInsightsSort.key !== key) {
      return <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />;
    }

    return employeeInsightsSort.direction === "asc" ? (
      <ArrowUp className="h-3.5 w-3.5 text-slate-600" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-slate-600" />
    );
  };

  // Moves selected date.
  const moveSelectedDate = (offset: number) => {
    const date = new Date(`${selectedDate}T00:00:00`);
    if (Number.isNaN(date.getTime())) return;

    date.setDate(date.getDate() + offset);
    setSelectedDate(formatDateInputValue(date));
  };

  // Applies insight date filter.
  const applyInsightDateFilter = () => {
    if (insightStartDate > insightEndDate) {
      toast.error("Start date cannot be after end date");
      return;
    }

    setAppliedInsightStartDate(insightStartDate);
    setAppliedInsightEndDate(insightEndDate);
    setSelectedEmployeeId("");
    setEmployeeInsightsPage(1);
  };

  // Selects insight start date.
  const selectInsightStartDate = (value: string) => {
    setInsightStartDate(value);
    setAppliedInsightStartDate(value);
    if (insightEndDate) setAppliedInsightEndDate(insightEndDate);
    setSelectedEmployeeId("");
    setEmployeeInsightsPage(1);
  };

  // Selects insight end date.
  const selectInsightEndDate = (value: string) => {
    setInsightEndDate(value);
    setAppliedInsightEndDate(value);
    if (insightStartDate) setAppliedInsightStartDate(insightStartDate);
    setSelectedEmployeeId("");
    setEmployeeInsightsPage(1);
  };

  // Resets insight date filter.
  const resetInsightDateFilter = () => {
    setInsightStartDate(defaultInsightStartDate);
    setInsightEndDate(defaultInsightEndDate);
    setAppliedInsightStartDate(defaultInsightStartDate);
    setAppliedInsightEndDate(defaultInsightEndDate);
    setSelectedEmployeeId("");
    setEmployeeInsightsPage(1);
  };

  // Opens expanded insight chart.
  const openExpandedInsightChart = (chart: Exclude<ExpandedInsightChart, null>) => {
    const start = appliedInsightStartDate || defaultInsightStartDate || fullInsightStartDate;
    const end = appliedInsightEndDate || fullInsightEndDate;
    setExpandedStartDate(start);
    setExpandedEndDate(end);
    setExpandedAppliedStartDate(start);
    setExpandedAppliedEndDate(end);
    setExpandedDepartmentFilter(ALL_FILTER_VALUE);
    setExpandedJobTitleFilter(ALL_FILTER_VALUE);
    setExpandedInsightChart(chart);
  };

  // Applies expanded date filter.
  const applyExpandedDateFilter = () => {
    if (expandedStartDate > expandedEndDate) {
      toast.error("Start date cannot be after end date");
      return;
    }

    setExpandedAppliedStartDate(expandedStartDate);
    setExpandedAppliedEndDate(expandedEndDate);
  };

  // Resets expanded date filter.
  const resetExpandedDateFilter = () => {
    const start = appliedInsightStartDate || defaultInsightStartDate || fullInsightStartDate;
    const end = appliedInsightEndDate || fullInsightEndDate;
    setExpandedStartDate(start);
    setExpandedEndDate(end);
    setExpandedAppliedStartDate(start);
    setExpandedAppliedEndDate(end);
    setExpandedDepartmentFilter(ALL_FILTER_VALUE);
    setExpandedJobTitleFilter(ALL_FILTER_VALUE);
  };

  useEffect(() => {
    if (attendancePage > attendancePageCount) {
      setAttendancePage(attendancePageCount);
    }
  }, [attendancePage, attendancePageCount]);

  useEffect(() => {
    setAttendancePage(1);
  }, [selectedDate, statusFilter, attendanceSearch, attendanceSearchEmployeeId, attendanceSort]);

  useEffect(() => {
    if (employeeInsightsPage > employeeInsightsPageCount) {
      setEmployeeInsightsPage(employeeInsightsPageCount);
    }
  }, [employeeInsightsPage, employeeInsightsPageCount]);

  useEffect(() => {
    setEmployeeInsightsPage(1);
  }, [
    appliedInsightStartDate,
    appliedInsightEndDate,
    employeeInsightsSearch,
    employeeInsightsSearchEmployeeId,
    employeeInsightsSort,
  ]);

  useEffect(() => {
    if (!fullInsightStartDate || !fullInsightEndDate) return;

    setInsightStartDate((current) => current || defaultInsightStartDate);
    setInsightEndDate((current) => current || defaultInsightEndDate);
    setAppliedInsightStartDate((current) => current || defaultInsightStartDate);
    setAppliedInsightEndDate((current) => current || defaultInsightEndDate);
  }, [defaultInsightEndDate, defaultInsightStartDate, fullInsightEndDate, fullInsightStartDate]);

  useEffect(() => {
    if (!selectedEmployeeId && employeeInsights[0]?.employeeId) {
      setSelectedEmployeeId(employeeInsights[0].employeeId);
      return;
    }

    if (
      selectedEmployeeId &&
      employeeInsights.length > 0 &&
      !employeeInsights.some((employee) => employee.employeeId === selectedEmployeeId)
    ) {
      setSelectedEmployeeId(employeeInsights[0].employeeId);
    }
  }, [employeeInsights, selectedEmployeeId]);

  useEffect(() => {
    let isMounted = true;

    apiFetch<{
      latestUpload: AttendanceUpload | null;
      records: AttendanceApiRecord[];
      settings?: AttendanceSettings;
    }>("/attendance-analytics")
      .then((data) => {
        if (!isMounted) return;
        const settings = data.settings ?? { workStartTime: "08:00", workEndTime: "17:00" };
        setWorkStartTime(settings.workStartTime);
        setWorkEndTime(settings.workEndTime);
        const records = data.records.map((record) => mapApiRecord(record, settings.workStartTime));
        setAttendanceData(records);
        const today = todayDateValue();
        const hasTodayRecords = records.some((record) => record.date === today);
        if (hasTodayRecords) {
          setSelectedDate(today);
        } else if (records[0]?.date) {
          setSelectedDate(records[0].date);
        }
        if (data.latestUpload) {
          setSelectedFileName(data.latestUpload.fileName);
          setUploadMessage(`${data.latestUpload.totalRows} attendance records loaded from database.`);
        }
      })
      .catch((error) => {
        if (!isMounted) return;
        toast.error(error instanceof Error ? error.message : "Failed to load attendance records");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Parses attendance file.
  const parseAttendanceFile = async (file: File) => {
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, {
      type: "array",
      cellDates: true,
    });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    if (!sheet) {
      throw new Error("The Excel file does not contain any worksheet.");
    }

    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
      defval: "",
      raw: false,
      dateNF: "yyyy-mm-dd",
    });

    if (rows.length === 0) {
      throw new Error("The Excel file does not contain attendance records.");
    }

    const firstRow = rows[0];
    const headers = Object.keys(firstRow).reduce<Record<string, string>>((map, header) => {
      map[normalizeHeader(header)] = header;
      return map;
    }, {});

    const requiredHeaders = {
      employeeId: headers.employeeid,
      name: headers.name,
      department: headers.department,
      jobTitle: headers.jobtitle,
      date: headers.date,
      clockIn: headers.clockin,
      clockOut: headers.clockout,
      status: headers.status,
    };

    const missingHeaders = Object.entries(requiredHeaders)
      .filter(([, header]) => !header)
      .map(([key]) => {
        if (key === "employeeId") return "Employee ID";
        if (key === "jobTitle") return "Job Title";
        if (key === "clockIn") return "Clock In";
        if (key === "clockOut") return "Clock Out";
        return key.charAt(0).toUpperCase() + key.slice(1);
      });

    if (missingHeaders.length > 0) {
      throw new Error(`Missing Excel column: ${missingHeaders.join(", ")}`);
    }

    return rows.map((row, index) => {
      const status = normalizeStatus(cellString(row[requiredHeaders.status]));
      if (!status) {
        throw new Error(`Row ${index + 2} has an unsupported status.`);
      }

      const record = {
        employeeId: cellString(row[requiredHeaders.employeeId]),
        name: cellString(row[requiredHeaders.name]),
        department: cellString(row[requiredHeaders.department]),
        jobTitle: cellString(row[requiredHeaders.jobTitle]),
        date: normalizeDateValue(row[requiredHeaders.date]),
        clockIn: normalizeTimeValue(row[requiredHeaders.clockIn]),
        clockOut: normalizeTimeValue(row[requiredHeaders.clockOut]),
        status,
      };

      if (!record.employeeId || !record.name || !record.department || !record.jobTitle || !record.date) {
        throw new Error(`Row ${index + 2} is missing employee ID, name, department, job title, or date.`);
      }

      return record;
    });
  };

  // Handles file change.
  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileName = file.name;
    const extension = fileName.split(".").pop()?.toLowerCase();

    if (extension !== "xlsx" && extension !== "xls") {
      setSelectedFileName("");
      setAttendanceData([]);
      setUploadMessage("");
      setUploadError("Unsupported file type. Please upload an .xlsx or .xls file.");
      event.target.value = "";
      toast.error("Unsupported file type", {
        description: "Attendance upload only accepts .xlsx or .xls files.",
      });
      return;
    }

    setIsUploading(true);
    setUploadError("");
    setUploadMessage("");

    try {
      const records = await parseAttendanceFile(file);
      const formData = new FormData();
      const user = getStoredUser();
      formData.append("attendanceFile", file);
      formData.append("records", JSON.stringify(records));
      if (user?.id) {
        formData.append("uploadedBy", String(user.id));
      }

      const response = await apiFetch<{
        records: AttendanceApiRecord[];
        upload: { fileName: string; totalRows: number };
      }>("/attendance-analytics/upload", {
        method: "POST",
        body: formData,
      });

      const uploadedRecords = response.records.map((record) => mapApiRecord(record, workStartTime));
      setSelectedFileName(response.upload.fileName);
      setAttendanceData(uploadedRecords);
      if (uploadedRecords[0]?.date) {
        setSelectedDate(uploadedRecords[0].date);
      }
      setStatusFilter(ALL_STATUSES);
      setAttendancePage(1);
      setUploadMessage(`${response.upload.totalRows} attendance records uploaded and saved.`);
      toast.success("Attendance file uploaded", {
        description: response.upload.fileName,
      });
    } catch (error) {
      setSelectedFileName("");
      setAttendanceData([]);
      setUploadError(error instanceof Error ? error.message : "Failed to upload attendance file.");
      toast.error("Attendance upload failed", {
        description: error instanceof Error ? error.message : "Please check the Excel file.",
      });
      event.target.value = "";
    } finally {
      setIsUploading(false);
    }
  };

  // Saves attendance schedule.
  const saveAttendanceSchedule = async (workStart: string, workEnd: string) => {
    const user = getStoredUser();
    if (!user?.id) {
      toast.error("Unable to save attendance settings", {
        description: "Please login again before changing working hours.",
      });
      return;
    }

    setIsSavingAttendanceSchedule(true);
    try {
      const response = await apiFetch<{ settings: AttendanceSettings }>("/attendance-analytics/settings", {
        method: "PUT",
        body: JSON.stringify({
          workStartTime: workStart,
          workEndTime: workEnd,
          updatedBy: user.id,
        }),
      });

      setWorkStartTime(response.settings.workStartTime);
      setWorkEndTime(response.settings.workEndTime);
      setAttendanceData((records) => applyAttendanceSchedule(records, response.settings.workStartTime));
      setStatusFilter(ALL_STATUSES);
      setAttendancePage(1);
      toast.success("Working hours updated", {
        description: `${response.settings.workStartTime} - ${response.settings.workEndTime}`,
      });
    } catch (error) {
      toast.error("Unable to save attendance settings", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
      throw error;
    } finally {
      setIsSavingAttendanceSchedule(false);
    }
  };

  // Clears file.
  const clearFile = () => {
    setSelectedFileName("");
    setUploadError("");
    setUploadMessage("");
    setAttendancePage(1);
  };

  // Gets status badge.
  const getStatusBadge = (status: AttendanceRecord["status"]) => {
    switch (status) {
      case "Attend":
        return <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">Attend</Badge>;
      case "Late":
        return <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">Late</Badge>;
      case "Absent":
        return <Badge variant="outline" className="border-red-200 bg-red-50 text-red-700">Absent</Badge>;
      case "MC":
        return <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">MC</Badge>;
      case "Leave":
        return <Badge variant="outline" className="border-slate-200 bg-slate-100 text-slate-600">Leave</Badge>;
      default:
        return <Badge variant="outline" className="border-slate-200 bg-slate-100 text-slate-600">{status}</Badge>;
    }
  };

  // Gets time display.
  const getTimeDisplay = (record: AttendanceRecord, field: "clockIn" | "clockOut") => {
    if (record.status === "Leave") {
      return "-";
    } else if (record.status === "MC") {
      return "-";
    } else if (!record[field]) {
      return "-";
    }

    return record[field];
  };

  // Gets duration display.
  const getDurationDisplay = (record: AttendanceRecord) =>
    formatAttendanceDuration(getAttendanceDurationMinutes(record));


  const attendanceTabProps = {
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
    getDurationDisplay,
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
    setAttendanceSearchEmployeeId,
    saveAttendanceSchedule,
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
    selectInsightEndDate,
    selectInsightStartDate,
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
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Attendance Analytics" },
      ]}
      useCard={false}
    >
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">
            Attendance Analytics
          </h1>
          <p className="mt-2 text-lg text-slate-600">
            Upload employee attendance records and preview the imported data
          </p>
          {uploadError && <p className="mt-2 text-sm text-red-600">{uploadError}</p>}
        </div>
        <div className="flex flex-col items-start gap-2 lg:items-end">
          <label className="inline-flex h-11 cursor-pointer items-center justify-center rounded-md bg-[#003B7A] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#002f63]">
            <Upload className="mr-2 h-4 w-4" />
            {isUploading ? "Uploading..." : "Choose Excel File"}
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
          </label>
          {selectedFileName && (
            <p className="max-w-xs truncate text-sm text-slate-600 lg:text-right" title={selectedFileName}>
              {selectedFileName}
            </p>
          )}
        </div>
      </div>

      <Tabs defaultValue="records" className="space-y-6">
        <TabsList>
          <TabsTrigger value="records">Attendance Records</TabsTrigger>
          <TabsTrigger value="insights">Employee Insights</TabsTrigger>
          <TabsTrigger value="trends">Attendance Trends</TabsTrigger>
        </TabsList>

        <AttendanceRecordsTab {...attendanceTabProps} />
        <EmployeeInsightsTab {...attendanceTabProps} />
        <AttendanceTrendsTab {...attendanceTabProps} />
      </Tabs>
    </PageLayout>
  );
}
