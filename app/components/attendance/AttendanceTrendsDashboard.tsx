// Shows the Attendance Trends Dashboard view.
import { useEffect, useMemo, useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { TabsContent } from "../ui/tabs";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Calendar as DatePickerCalendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  BriefcaseBusiness,
  Calendar as CalendarIcon,
  Clock,
  Info,
  Maximize2,
  Search,
  ShieldPlus,
  TrendingUp,
  UserX,
  X,
  type LucideIcon,
} from "lucide-react";
import { SearchClearButton } from "../shared/SearchClearButton";

type AttendanceRecord = {
  date: string;
  employeeId?: string;
  name?: string;
  department?: string;
  jobTitle?: string;
  status: "Attend" | "Late" | "Absent" | "MC" | "Leave";
};

type AttendanceTrendsDashboardProps = Record<string, any>;
type TrendChartKey = "rate" | "issues" | "weekday";

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const ALL_FILTER_VALUE = "all";
const weekdayOrder = [
  { label: "Monday", index: 1 },
  { label: "Tuesday", index: 2 },
  { label: "Wednesday", index: 3 },
  { label: "Thursday", index: 4 },
  { label: "Friday", index: 5 },
];

// Parses date.
const parseDate = (value: string) => new Date(`${value}T00:00:00`);

// Provides the days between inclusive helper.
const daysBetweenInclusive = (start: string, end: string) => {
  const startDate = parseDate(start);
  const endDate = parseDate(end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return 0;
  return Math.floor((endDate.getTime() - startDate.getTime()) / MS_PER_DAY) + 1;
};

// Gets working days between.
const getWorkingDaysBetween = (start: string, end: string) => {
  const startDate = parseDate(start);
  const endDate = parseDate(end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return 0;

  let workingDays = 0;
  for (let time = startDate.getTime(); time <= endDate.getTime(); time += MS_PER_DAY) {
    const day = new Date(time).getDay();
    if (day >= 1 && day <= 5) workingDays += 1;
  }
  return workingDays;
};

// Adds days.
const addDays = (value: string, days: number) => {
  const date = parseDate(value);
  date.setDate(date.getDate() + days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Adds months.
const addMonths = (value: string, months: number) => {
  const date = parseDate(value);
  if (Number.isNaN(date.getTime())) return value;
  date.setMonth(date.getMonth() + months);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Gets month key.
const getMonthKey = (value: string) => value.slice(0, 7);

// Gets trend label.
const getTrendLabel = (key: string, groupedByMonth: boolean) => {
  const date = groupedByMonth ? new Date(`${key}-01T00:00:00`) : parseDate(key);
  if (Number.isNaN(date.getTime())) return key;

  return groupedByMonth
    ? date.toLocaleDateString("en-GB", { month: "short", year: "2-digit" })
    : date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};

// Gets range records.
const getRangeRecords = (records: AttendanceRecord[], start: string, end: string) =>
  records.filter((record) => record.date >= start && record.date <= end);

// Gets attendance rate.
const getAttendanceRate = (records: AttendanceRecord[]) => {
  if (records.length === 0) return 0;
  const presentRecords = records.filter((record) => record.status === "Attend" || record.status === "Late").length;
  return Math.round((presentRecords / records.length) * 1000) / 10;
};

// Gets issue totals.
const getIssueTotals = (records: AttendanceRecord[]) => ({
  late: records.filter((record) => record.status === "Late").length,
  absent: records.filter((record) => record.status === "Absent").length,
  mc: records.filter((record) => record.status === "MC").length,
  leave: records.filter((record) => record.status === "Leave").length,
});

// Builds grouped trend data.
const buildGroupedTrendData = (
  records: AttendanceRecord[],
  groupedByMonth: boolean,
) => {
  const map = records.reduce<Record<string, AttendanceRecord[]>>((groups, record) => {
    const key = groupedByMonth ? getMonthKey(record.date) : record.date;
    groups[key] = [...(groups[key] ?? []), record];
    return groups;
  }, {});

  return Object.entries(map)
    .sort(([first], [second]) => first.localeCompare(second))
    .map(([key, groupRecords]) => ({
      key,
      label: getTrendLabel(key, groupedByMonth),
      attendanceRate: getAttendanceRate(groupRecords),
      Late: groupRecords.filter((record) => record.status === "Late").length,
      Absent: groupRecords.filter((record) => record.status === "Absent").length,
      MC: groupRecords.filter((record) => record.status === "MC").length,
      Leave: groupRecords.filter((record) => record.status === "Leave").length,
    }));
};

// Builds weekday pattern data.
const buildWeekdayPatternData = (records: AttendanceRecord[]) =>
  weekdayOrder.map((weekday) => {
    const weekdayRecords = records.filter((record) => {
      const date = parseDate(record.date);
      return !Number.isNaN(date.getTime()) && date.getDay() === weekday.index;
    });

    return {
      day: weekday.label,
      Absent: weekdayRecords.filter((record) => record.status === "Absent").length,
      MC: weekdayRecords.filter((record) => record.status === "MC").length,
      Leave: weekdayRecords.filter((record) => record.status === "Leave").length,
    };
  });

// Renders the Attendance Trends Dashboard component.
export function AttendanceTrendsDashboard(props: AttendanceTrendsDashboardProps) {
  const {
    attendanceData = [],
    ATTENDANCE_ISSUE_COLORS,
    formatDateInputValue,
    formatShortDate,
    fullInsightEndDate,
    fullInsightStartDate,
  } = props;

  const records = attendanceData as AttendanceRecord[];
  const issueColors = ATTENDANCE_ISSUE_COLORS ?? {
    Late: "#f59e0b",
    Absent: "#ef4444",
    MC: "#3b82f6",
    Leave: "#64748b",
  };
  const availableDates = useMemo(
    () => [...new Set(records.map((record) => record.date))].filter(Boolean).sort(),
    [records],
  );
  const todayDate = formatDateInputValue(new Date());
  const minDate = availableDates[0] ?? fullInsightStartDate ?? "";
  const dataMaxDate = availableDates[availableDates.length - 1] ?? fullInsightEndDate ?? "";
  const maxDate = [dataMaxDate, todayDate].filter(Boolean).sort().at(-1) ?? todayDate;
  const defaultTrendEndDate = todayDate;
  const defaultTrendStartDate = addMonths(defaultTrendEndDate, -1);
  const minSelectableDate = [minDate, defaultTrendStartDate].filter(Boolean).sort()[0] ?? minDate;

  const [trendStartDate, setTrendStartDate] = useState("");
  const [trendEndDate, setTrendEndDate] = useState("");
  const [appliedTrendStartDate, setAppliedTrendStartDate] = useState("");
  const [appliedTrendEndDate, setAppliedTrendEndDate] = useState("");
  const [expandedTrendStartDate, setExpandedTrendStartDate] = useState("");
  const [expandedTrendEndDate, setExpandedTrendEndDate] = useState("");
  const [expandedAppliedTrendStartDate, setExpandedAppliedTrendStartDate] = useState("");
  const [expandedAppliedTrendEndDate, setExpandedAppliedTrendEndDate] = useState("");
  const [startPickerOpen, setStartPickerOpen] = useState(false);
  const [endPickerOpen, setEndPickerOpen] = useState(false);
  const [expandedStartPickerOpen, setExpandedStartPickerOpen] = useState(false);
  const [expandedEndPickerOpen, setExpandedEndPickerOpen] = useState(false);
  const [expandedSearch, setExpandedSearch] = useState("");
  const [expandedSelectedEmployeeId, setExpandedSelectedEmployeeId] = useState("");
  const [expandedSearchFocused, setExpandedSearchFocused] = useState(false);
  const [expandedDepartmentFilter, setExpandedDepartmentFilter] = useState(ALL_FILTER_VALUE);
  const [expandedJobTitleFilter, setExpandedJobTitleFilter] = useState(ALL_FILTER_VALUE);
  const [expandedChart, setExpandedChart] = useState<TrendChartKey | null>(null);

  useEffect(() => {
    if (!minDate || !maxDate) return;
    setTrendStartDate((current) => current || defaultTrendStartDate);
    setTrendEndDate((current) => current || defaultTrendEndDate);
    setAppliedTrendStartDate((current) => current || defaultTrendStartDate);
    setAppliedTrendEndDate((current) => current || defaultTrendEndDate);
    setExpandedTrendStartDate((current) => current || defaultTrendStartDate);
    setExpandedTrendEndDate((current) => current || defaultTrendEndDate);
    setExpandedAppliedTrendStartDate((current) => current || defaultTrendStartDate);
    setExpandedAppliedTrendEndDate((current) => current || defaultTrendEndDate);
  }, [defaultTrendEndDate, defaultTrendStartDate, maxDate, minDate]);

  const rangeLength = daysBetweenInclusive(appliedTrendStartDate, appliedTrendEndDate);
  const groupedByMonth = rangeLength > 90;
  const rangeSelectedRecords = getRangeRecords(records, appliedTrendStartDate, appliedTrendEndDate);
  const expandedRangeLength = daysBetweenInclusive(expandedAppliedTrendStartDate, expandedAppliedTrendEndDate);
  const expandedWorkingDays = getWorkingDaysBetween(
    expandedAppliedTrendStartDate,
    expandedAppliedTrendEndDate,
  );
  const expandedGroupedByMonth = expandedRangeLength > 90;
  const expandedRangeSelectedRecords = getRangeRecords(
    records,
    expandedAppliedTrendStartDate,
    expandedAppliedTrendEndDate,
  );
  const departmentOptions = useMemo(
    () => [...new Set(expandedRangeSelectedRecords.map((record) => record.department).filter(Boolean) as string[])].sort(),
    [expandedRangeSelectedRecords],
  );
  const jobTitleOptions = useMemo(
    () =>
      [
        ...new Set(
          expandedRangeSelectedRecords
            .filter(
              (record) =>
                expandedDepartmentFilter === ALL_FILTER_VALUE ||
                record.department === expandedDepartmentFilter,
            )
            .map((record) => record.jobTitle)
            .filter(Boolean) as string[],
        ),
      ].sort(),
    [expandedDepartmentFilter, expandedRangeSelectedRecords],
  );
  const employeeSuggestions = useMemo(() => {
    const searchTerm = expandedSearch.trim().toLowerCase();
    if (!searchTerm || expandedSelectedEmployeeId) return [];

    const employeeMap = new Map<string, { employeeId: string; name: string }>();
    expandedRangeSelectedRecords
      .filter((record) => {
        const matchesDepartment =
          expandedDepartmentFilter === ALL_FILTER_VALUE || record.department === expandedDepartmentFilter;
        const matchesJobTitle =
          expandedJobTitleFilter === ALL_FILTER_VALUE || record.jobTitle === expandedJobTitleFilter;
        return matchesDepartment && matchesJobTitle;
      })
      .forEach((record) => {
        const employeeId = String(record.employeeId ?? "").trim();
        const name = String(record.name ?? "").trim();
        if (!employeeId || !name || employeeMap.has(employeeId)) return;

        const matchesSearch =
          employeeId.toLowerCase().startsWith(searchTerm) ||
          name.toLowerCase().startsWith(searchTerm);
        if (matchesSearch) {
          employeeMap.set(employeeId, { employeeId, name });
        }
      });

    return [...employeeMap.values()]
      .sort((first, second) => first.name.localeCompare(second.name, undefined, { sensitivity: "base" }))
      .slice(0, 8);
  }, [
    expandedDepartmentFilter,
    expandedJobTitleFilter,
    expandedSearch,
    expandedSelectedEmployeeId,
    expandedRangeSelectedRecords,
  ]);
  const expandedSelectedRecords = expandedRangeSelectedRecords.filter((record) => {
        const searchTerm = expandedSearch.trim().toLowerCase();
        const matchesSearch =
          expandedSelectedEmployeeId !== ""
            ? String(record.employeeId ?? "") === expandedSelectedEmployeeId
            : searchTerm === "" ||
              String(record.employeeId ?? "").toLowerCase().includes(searchTerm) ||
              String(record.name ?? "").toLowerCase().includes(searchTerm);
        const matchesDepartment =
          expandedDepartmentFilter === ALL_FILTER_VALUE || record.department === expandedDepartmentFilter;
        const matchesJobTitle =
          expandedJobTitleFilter === ALL_FILTER_VALUE || record.jobTitle === expandedJobTitleFilter;
        return matchesSearch && matchesDepartment && matchesJobTitle;
      });
  const previousEndDate = appliedTrendStartDate ? addDays(appliedTrendStartDate, -1) : "";
  const previousStartDate = previousEndDate ? addDays(previousEndDate, -(rangeLength - 1)) : "";
  const previousRecords =
    previousStartDate && previousEndDate ? getRangeRecords(records, previousStartDate, previousEndDate) : [];
  const averageAttendanceRate = getAttendanceRate(rangeSelectedRecords);
  const previousAttendanceRate = getAttendanceRate(previousRecords);
  const attendanceRateChange = Math.round((averageAttendanceRate - previousAttendanceRate) * 10) / 10;
  const issueTotals = getIssueTotals(rangeSelectedRecords);
  const groupedTrendData = useMemo(
    () => buildGroupedTrendData(rangeSelectedRecords, groupedByMonth),
    [groupedByMonth, rangeSelectedRecords],
  );
  const weekdayPatternData = useMemo(
    () => buildWeekdayPatternData(rangeSelectedRecords),
    [rangeSelectedRecords],
  );
  const expandedPreviousEndDate = expandedAppliedTrendStartDate
    ? addDays(expandedAppliedTrendStartDate, -1)
    : "";
  const expandedPreviousStartDate = expandedPreviousEndDate
    ? addDays(expandedPreviousEndDate, -(expandedRangeLength - 1))
    : "";
  const expandedPreviousRecords =
    expandedPreviousStartDate && expandedPreviousEndDate
      ? getRangeRecords(records, expandedPreviousStartDate, expandedPreviousEndDate)
      : [];
  const expandedAverageAttendanceRate = getAttendanceRate(expandedSelectedRecords);
  const expandedPreviousAttendanceRate = getAttendanceRate(expandedPreviousRecords);
  const expandedAttendanceRateChange =
    Math.round((expandedAverageAttendanceRate - expandedPreviousAttendanceRate) * 10) / 10;
  const expandedIssueTotals = getIssueTotals(expandedSelectedRecords);
  const expandedGroupedTrendData = useMemo(
    () => buildGroupedTrendData(expandedSelectedRecords, expandedGroupedByMonth),
    [expandedGroupedByMonth, expandedSelectedRecords],
  );
  const expandedWeekdayPatternData = useMemo(
    () => buildWeekdayPatternData(expandedSelectedRecords),
    [expandedSelectedRecords],
  );

  // Selects trend start date.
  const selectTrendStartDate = (value: string) => {
    setTrendStartDate(value);
    setAppliedTrendStartDate(value);
    if (trendEndDate) setAppliedTrendEndDate(trendEndDate);
  };

  // Selects trend end date.
  const selectTrendEndDate = (value: string) => {
    setTrendEndDate(value);
    setAppliedTrendEndDate(value);
    if (trendStartDate) setAppliedTrendStartDate(trendStartDate);
  };

  // Selects expanded trend start date.
  const selectExpandedTrendStartDate = (value: string) => {
    setExpandedTrendStartDate(value);
    setExpandedAppliedTrendStartDate(value);
    if (expandedTrendEndDate) setExpandedAppliedTrendEndDate(expandedTrendEndDate);
  };

  // Selects expanded trend end date.
  const selectExpandedTrendEndDate = (value: string) => {
    setExpandedTrendEndDate(value);
    setExpandedAppliedTrendEndDate(value);
    if (expandedTrendStartDate) setExpandedAppliedTrendStartDate(expandedTrendStartDate);
  };

  // Opens expanded chart.
  const openExpandedChart = (chart: TrendChartKey) => {
    setExpandedTrendStartDate(appliedTrendStartDate || defaultTrendStartDate);
    setExpandedTrendEndDate(appliedTrendEndDate || defaultTrendEndDate);
    setExpandedAppliedTrendStartDate(appliedTrendStartDate || defaultTrendStartDate);
    setExpandedAppliedTrendEndDate(appliedTrendEndDate || defaultTrendEndDate);
    setExpandedChart(chart);
  };

  // Resets trend filter.
  const resetTrendFilter = () => {
    setTrendStartDate(defaultTrendStartDate);
    setTrendEndDate(defaultTrendEndDate);
    setAppliedTrendStartDate(defaultTrendStartDate);
    setAppliedTrendEndDate(defaultTrendEndDate);
  };

  // Resets expanded filters.
  const resetExpandedFilters = () => {
    setExpandedTrendStartDate(appliedTrendStartDate || defaultTrendStartDate);
    setExpandedTrendEndDate(appliedTrendEndDate || defaultTrendEndDate);
    setExpandedAppliedTrendStartDate(appliedTrendStartDate || defaultTrendStartDate);
    setExpandedAppliedTrendEndDate(appliedTrendEndDate || defaultTrendEndDate);
    setExpandedSearch("");
    setExpandedSelectedEmployeeId("");
    setExpandedSearchFocused(false);
    setExpandedDepartmentFilter(ALL_FILTER_VALUE);
    setExpandedJobTitleFilter(ALL_FILTER_VALUE);
  };

  // Resets expanded filter controls.
  const resetExpandedFilterControls = () => {
    setExpandedTrendStartDate(defaultTrendStartDate);
    setExpandedTrendEndDate(defaultTrendEndDate);
    setExpandedAppliedTrendStartDate(defaultTrendStartDate);
    setExpandedAppliedTrendEndDate(defaultTrendEndDate);
    setExpandedSearch("");
    setExpandedSelectedEmployeeId("");
    setExpandedSearchFocused(false);
    setExpandedDepartmentFilter(ALL_FILTER_VALUE);
    setExpandedJobTitleFilter(ALL_FILTER_VALUE);
  };

  // Renders expanded search filter.
  const renderExpandedSearchFilter = () => (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Search</label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          inputMode="search"
          value={expandedSearch}
          onChange={(event) => {
            setExpandedSearch(event.target.value);
            setExpandedSelectedEmployeeId("");
          }}
          onFocus={() => setExpandedSearchFocused(true)}
          onBlur={() => window.setTimeout(() => setExpandedSearchFocused(false), 120)}
          placeholder="Search employee name or ID"
          className="h-10 w-full rounded-md border border-slate-200 bg-white pl-10 pr-10 text-sm text-slate-950 shadow-sm outline-none transition-[color,box-shadow] placeholder:text-slate-400 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <SearchClearButton
          show={Boolean(expandedSearch)}
          onClear={() => {
            setExpandedSearch("");
            setExpandedSelectedEmployeeId("");
            setExpandedSearchFocused(false);
          }}
        />
        {expandedSearchFocused && employeeSuggestions.length > 0 && (
          <div className="absolute left-0 right-0 top-[44px] z-[95] overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
            {employeeSuggestions.map((employee) => (
              <button
                key={employee.employeeId}
                type="button"
                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  setExpandedSelectedEmployeeId(employee.employeeId);
                  setExpandedSearch(`${employee.name} (${employee.employeeId})`);
                  setExpandedSearchFocused(false);
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
  );

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

  // Renders date button.
  const renderDateButton = (
    label: string,
    value: string,
    isOpen: boolean,
    setOpen: (open: boolean) => void,
    onSelect: (value: string) => void,
    minValue: string,
    maxValue: string,
  ) => (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</label>
      <Popover open={isOpen} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            className="h-10 w-full justify-start bg-white px-3 text-left text-sm font-normal text-slate-950 shadow-sm"
          >
            <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
            {value ? formatShortDate(value) : "Select date"}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="z-[80] w-auto p-0" align="start">
          <DatePickerCalendar
            mode="single"
            defaultMonth={value ? parseDate(value) : undefined}
            selected={value ? parseDate(value) : undefined}
            onSelect={(date) => {
              if (!date) return;
              onSelect(formatDateInputValue(date));
              setOpen(false);
            }}
            disabled={(date) => {
              const nextValue = formatDateInputValue(date);
              return nextValue < minValue || nextValue > maxValue;
            }}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );

  const chartHasData = rangeSelectedRecords.length > 0 && groupedTrendData.length > 0;
  const expandedChartHasData = expandedSelectedRecords.length > 0 && expandedGroupedTrendData.length > 0;

  // Renders rate chart.
  const renderRateChart = (heightClass = "h-72", data = groupedTrendData) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
          <YAxis
            domain={[0, 100]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12, fill: "#64748b" }}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip formatter={(value) => [`${value}%`, "Attendance Rate"]} />
          <Line
            type="monotone"
            dataKey="attendanceRate"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ r: 3, strokeWidth: 2, fill: "#ffffff" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  // Renders issue chart.
  const renderIssueChart = (heightClass = "h-72", data = groupedTrendData) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
          <Tooltip />
          <Legend verticalAlign="top" height={32} iconType="line" />
          <Line type="monotone" dataKey="Late" stroke={issueColors.Late} strokeWidth={2} dot={{ r: 2 }} />
          <Line type="monotone" dataKey="Absent" stroke={issueColors.Absent} strokeWidth={2} dot={{ r: 2 }} />
          <Line type="monotone" dataKey="MC" stroke={issueColors.MC} strokeWidth={2} dot={{ r: 2 }} />
          <Line type="monotone" dataKey="Leave" stroke={issueColors.Leave} strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  // Renders weekday chart.
  const renderWeekdayChart = (heightClass = "h-80", data = weekdayPatternData) => (
    <div className={heightClass}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 18, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
          <Tooltip />
          <Legend verticalAlign="top" height={32} />
          <Bar dataKey="Absent" fill={issueColors.Absent} radius={[4, 4, 0, 0]} />
          <Bar dataKey="MC" fill={issueColors.MC} radius={[4, 4, 0, 0]} />
          <Bar dataKey="Leave" fill={issueColors.Leave} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const chartTitle = {
    rate: "Attendance Rate Trend",
    issues: "Attendance Issue Trend",
    weekday: "Weekday Absence Pattern",
  } as const;

  // Renders rate summary.
  const renderRateSummary = (
    rate = averageAttendanceRate,
    change = attendanceRateChange,
    days = rangeLength,
  ) => (
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <SummaryMetric
        label="Average Attendance Rate"
        value={`${rate}%`}
        Icon={TrendingUp}
        iconClassName="text-[#003B7A]"
        valueClassName="text-[#003B7A]"
      />
      <SummaryMetric
        label={`Change vs previous ${days} days`}
        value={`${change >= 0 ? "+" : ""}${change}%`}
        Icon={change >= 0 ? ArrowUpRight : ArrowDownRight}
        iconClassName={change >= 0 ? "text-green-600" : "text-red-600"}
        valueClassName={change >= 0 ? "text-green-600" : "text-red-600"}
      />
    </div>
  );

  // Renders issue summary.
  const renderIssueSummary = (totals = issueTotals) => (
    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <SummaryMetric
        label="Total Late"
        value={totals.late}
        Icon={Clock}
        iconClassName="text-amber-600"
        labelClassName="whitespace-nowrap"
        valueClassName="text-amber-600"
      />
      <SummaryMetric
        label="Total Absent"
        value={totals.absent}
        Icon={UserX}
        iconClassName="text-red-600"
        labelClassName="whitespace-nowrap"
        valueClassName="text-red-600"
      />
      <SummaryMetric
        label="Total MC"
        value={totals.mc}
        Icon={ShieldPlus}
        iconClassName="text-blue-600"
        labelClassName="whitespace-nowrap"
        valueClassName="text-blue-600"
      />
      <SummaryMetric
        label="Total Leave"
        value={totals.leave}
        Icon={BriefcaseBusiness}
        iconClassName="text-slate-600"
        labelClassName="whitespace-nowrap"
        valueClassName="text-slate-600"
      />
    </div>
  );

  // Renders expanded date filter.
  const renderExpandedDateFilter = () => (
    <div className="grid gap-3 border-b border-slate-200 bg-slate-50 px-5 py-3 xl:grid-cols-[1fr_auto] xl:items-end">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(220px,320px)_180px_180px_220px_220px]">
        {renderExpandedSearchFilter()}
        {renderDateButton(
          "Start Date",
          expandedTrendStartDate,
          expandedStartPickerOpen,
          setExpandedStartPickerOpen,
          selectExpandedTrendStartDate,
          minSelectableDate,
          expandedTrendEndDate || maxDate,
        )}
        {renderDateButton(
          "End Date",
          expandedTrendEndDate,
          expandedEndPickerOpen,
          setExpandedEndPickerOpen,
          selectExpandedTrendEndDate,
          expandedTrendStartDate || minSelectableDate,
          maxDate,
        )}
        {renderExpandedSelectFilter(
          "Department",
          expandedDepartmentFilter,
          (value) => {
            setExpandedDepartmentFilter(value);
            setExpandedJobTitleFilter(ALL_FILTER_VALUE);
            setExpandedSelectedEmployeeId("");
            setExpandedSearch("");
          },
          "All Departments",
          departmentOptions,
        )}
        {renderExpandedSelectFilter(
          "Job Title",
          expandedJobTitleFilter,
          (value) => {
            setExpandedJobTitleFilter(value);
            setExpandedSelectedEmployeeId("");
            setExpandedSearch("");
          },
          "All Job Titles",
          jobTitleOptions,
        )}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Button type="button" variant="outline" className="bg-white" onClick={resetExpandedFilterControls}>
          Reset
        </Button>
      </div>
    </div>
  );

  // Provides the expanded chart content helper.
  const expandedChartContent = () => {
    if (!expandedChartHasData) {
      return (
        <div className="flex h-[52vh] items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500">
          No attendance data found for the selected expanded filters.
        </div>
      );
    }

    if (expandedChart === "rate") {
      return (
        <>
          {renderRateChart("h-[40vh]", expandedGroupedTrendData)}
          {renderRateSummary(
            expandedAverageAttendanceRate,
            expandedAttendanceRateChange,
            expandedRangeLength,
          )}
        </>
      );
    }
    if (expandedChart === "issues") {
      return (
        <>
          {renderIssueChart("h-[40vh]", expandedGroupedTrendData)}
          {renderIssueSummary(expandedIssueTotals)}
        </>
      );
    }
    if (expandedChart === "weekday") return renderWeekdayChart("h-[52vh]", expandedWeekdayPatternData);
    return null;
  };

  return (
    <TabsContent value="trends" className="space-y-6">
      <section className="space-y-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold tracking-tight text-slate-950">Attendance Trends</h2>
            <span className="hidden h-8 w-px bg-slate-300 sm:block" />
            <div className="grid w-full gap-3 sm:grid-cols-2 lg:w-auto lg:grid-cols-[180px_180px] lg:items-end">
              {renderDateButton(
                "Start Date",
                trendStartDate,
                startPickerOpen,
                setStartPickerOpen,
                selectTrendStartDate,
                minSelectableDate,
                trendEndDate || maxDate,
              )}
              {renderDateButton(
                "End Date",
                trendEndDate,
                endPickerOpen,
                setEndPickerOpen,
                selectTrendEndDate,
                trendStartDate || minSelectableDate,
                maxDate,
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" className="bg-white" onClick={resetTrendFilter}>
              Reset
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
          <span>
            Showing records from{" "}
            <span className="font-medium text-slate-700">
              {appliedTrendStartDate ? formatShortDate(appliedTrendStartDate) : "-"}
            </span>{" "}
            to{" "}
            <span className="font-medium text-slate-700">
              {appliedTrendEndDate ? formatShortDate(appliedTrendEndDate) : "-"}
            </span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Info className="h-4 w-4" />
            Data is based on all employees
          </span>
        </div>
      </section>

      {!records.length ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
          No attendance data found. Upload attendance records to view trends.
        </div>
      ) : !chartHasData ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
          No attendance data found in the selected date range.
        </div>
      ) : (
        <>
          <div className="grid gap-5 xl:grid-cols-2">
            <Card className="shadow-md">
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div>
                  <CardTitle className="inline-flex items-center gap-2">
                    Attendance Rate Trend
                  </CardTitle>
                  <CardDescription>
                    Shows how the overall attendance rate changes over the selected date range.
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 text-slate-500 hover:text-[#003B7A]"
                  onClick={() => openExpandedChart("rate")}
                  aria-label="Expand attendance rate trend"
                >
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent className="pb-0">
                {renderRateChart()}
                {renderRateSummary()}
              </CardContent>
            </Card>

            <Card className="shadow-md">
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div>
                  <CardTitle className="inline-flex items-center gap-2">
                    Attendance Issue Trend
                  </CardTitle>
                  <CardDescription>
                    Shows how Late, Absent, MC and Leave records change over the selected date range.
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 text-slate-500 hover:text-[#003B7A]"
                  onClick={() => openExpandedChart("issues")}
                  aria-label="Expand attendance issue trend"
                >
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent className="pb-0">
                {renderIssueChart()}
                {renderIssueSummary()}
              </CardContent>
            </Card>
          </div>

          <Card className="shadow-md">
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <CardTitle className="inline-flex items-center gap-2">
                  Weekday Absence Pattern
                </CardTitle>
                <CardDescription>
                  Shows which weekdays have higher Absent, MC and Leave records in the selected date range.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 text-slate-500 hover:text-[#003B7A]"
                onClick={() => openExpandedChart("weekday")}
                aria-label="Expand weekday absence pattern"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>{renderWeekdayChart()}</CardContent>
          </Card>

          <Dialog
            open={expandedChart !== null}
            onOpenChange={(open) => {
              if (open) return;
              resetExpandedFilters();
              setExpandedChart(null);
              setExpandedStartPickerOpen(false);
              setExpandedEndPickerOpen(false);
            }}
          >
            <DialogContent className="max-h-[88vh] w-[85vw] max-w-[85vw] grid-rows-[auto_auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-[85vw] [&>button]:hidden">
              <DialogHeader className="flex-row items-start justify-between gap-4 border-b border-slate-200 px-5 py-3 text-left">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <DialogTitle>{expandedChart ? chartTitle[expandedChart] : "Attendance Trend"}</DialogTitle>
                    <div className="inline-flex items-center gap-2 px-2.5 py-1 text-xs font-medium text-slate-600">
                      <CalendarIcon className="h-3.5 w-3.5 text-slate-500" />
                      <span>Date range:</span>
                      <span className="font-semibold text-slate-900">
                        {formatShortDate(expandedAppliedTrendStartDate)} - {formatShortDate(expandedAppliedTrendEndDate)}
                        {expandedWorkingDays > 0 ? ` (${expandedWorkingDays} working days)` : ""}
                      </span>
                    </div>
                  </div>
                  <DialogDescription className="mt-1">
                    Showing all employee attendance trend data in the selected date range.
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

              {renderExpandedDateFilter()}

              <div className="min-h-0 overflow-hidden bg-white px-5 py-4">{expandedChartContent()}</div>
            </DialogContent>
          </Dialog>
        </>
      )}
    </TabsContent>
  );
}

// Renders the Summary Metric component.
function SummaryMetric({
  label,
  value,
  Icon,
  iconClassName,
  labelClassName = "",
  valueClassName,
}: {
  label: string;
  value: number | string;
  Icon: LucideIcon;
  iconClassName: string;
  labelClassName?: string;
  valueClassName: string;
}) {
  return (
    <div className="flex min-h-[76px] items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/70 p-4">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center ${iconClassName}`}>
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className={`text-xs font-medium text-slate-500 ${labelClassName}`}>{label}</p>
        <p className={`mt-1 text-lg font-bold ${valueClassName}`}>{value}</p>
      </div>
    </div>
  );
}
