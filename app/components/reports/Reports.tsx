// Shows the Reports view.
import { useState } from "react";
import { useNavigate } from "react-router";
import { PageLayout } from "../shared/PageLayout";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Checkbox } from "../ui/checkbox";
import { Calendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  ArrowLeft,
  Download,
  FileText,
  FileSpreadsheet,
  Calendar as CalendarIcon,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { formatDisplayDate } from "../../lib/date";

// Renders the Reports component.
export function Reports() {
  const navigate = useNavigate();
  const [reportType, setReportType] = useState("candidates");
  const [dateFrom, setDateFrom] = useState<Date>();
  const [dateTo, setDateTo] = useState<Date>();
  const [selectedJobs, setSelectedJobs] = useState<string[]>([]);
  const [exportFormat, setExportFormat] = useState("csv");

  const jobOptions = [
    { id: "1", title: "Senior Frontend Developer" },
    { id: "2", title: "Product Manager" },
    { id: "3", title: "UX Designer" },
    { id: "4", title: "Backend Engineer" },
  ];

  const reportTypes = [
    {
      value: "candidates",
      label: "Candidate Report",
      description: "All candidate applications with scores and status",
      fields: ["Name", "Email", "Phone", "Job Title", "Score", "Rank", "Status", "Applied Date"],
    },
    {
      value: "attendance",
      label: "Interview Attendance Report",
      description: "Interview attendance records and patterns",
      fields: ["Candidate", "Job", "Interview Date", "Status", "Punctuality", "Notes"],
    },
    {
      value: "jobs",
      label: "Job Posting Report",
      description: "Job posting performance and statistics",
      fields: ["Job Title", "Status", "Applicants", "Avg Score", "Created Date", "Link"],
    },
    {
      value: "analytics",
      label: "Comprehensive Analytics",
      description: "Full analytics including trends and patterns",
      fields: ["All metrics", "Trends", "Patterns", "Recommendations"],
    },
  ];

  const selectedReport = reportTypes.find((r) => r.value === reportType);

  // Handles job toggle.
  const handleJobToggle = (jobId: string) => {
    setSelectedJobs((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId]
    );
  };

  // Handles export.
  const handleExport = () => {
    const reportName = selectedReport?.label || "Report";
    const fileName = `${reportName.replace(/\s+/g, "_")}_${format(new Date(), "yyyy-MM-dd")}.${exportFormat}`;
    
    toast.success("Report exported successfully!", {
      description: `${fileName} has been downloaded`,
      duration: 4000,
    });
  };

  // Handles generate preview.
  const handleGeneratePreview = () => {
    toast.info("Generating preview...", {
      description: "Please wait while we prepare your report",
    });
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Reports" },
      ]}
      title="Reports"
      subtitle="Generate and export detailed reports for analysis"
      useCard={false}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Configuration */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Report Configuration</CardTitle>
              <CardDescription>
                Select report type and configure parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Report Type */}
              <div className="space-y-2">
                <Label>Report Type</Label>
                <Select value={reportType} onValueChange={setReportType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {reportTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedReport && (
                  <p className="text-sm text-slate-500">
                    {selectedReport.description}
                  </p>
                )}
              </div>

              {/* Date Range */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>From Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {dateFrom ? formatDisplayDate(dateFrom) : "Pick a date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={dateFrom}
                        onSelect={setDateFrom}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                <div className="space-y-2">
                  <Label>To Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {dateTo ? formatDisplayDate(dateTo) : "Pick a date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={dateTo}
                        onSelect={setDateTo}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              {/* Job Selection */}
              <div className="space-y-2">
                <Label>Filter by Job Positions</Label>
                <div className="space-y-2 p-4 border border-slate-200 rounded-lg">
                  {jobOptions.map((job) => (
                    <div key={job.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`job-${job.id}`}
                        checked={selectedJobs.includes(job.id)}
                        onCheckedChange={() => handleJobToggle(job.id)}
                      />
                      <label
                        htmlFor={`job-${job.id}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {job.title}
                      </label>
                    </div>
                  ))}
                  {selectedJobs.length === 0 && (
                    <p className="text-sm text-slate-500 italic">
                      All jobs will be included
                    </p>
                  )}
                </div>
              </div>

              {/* Export Format */}
              <div className="space-y-2">
                <Label>Export Format</Label>
                <Select value={exportFormat} onValueChange={setExportFormat}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV (Excel compatible)</SelectItem>
                    <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
                    <SelectItem value="pdf">PDF Document</SelectItem>
                    <SelectItem value="json">JSON Data</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button onClick={handleExport} size="lg">
                  <Download className="w-4 h-4 mr-2" />
                  Export Report
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={handleGeneratePreview}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Preview
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Report Preview */}
          {selectedReport && (
            <Card>
              <CardHeader>
                <CardTitle>Report Fields</CardTitle>
                <CardDescription>
                  The following data will be included in your report
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  {selectedReport.fields.map((field, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 p-2 bg-slate-50 rounded"
                    >
                      <FileText className="w-4 h-4 text-slate-500" />
                      <span className="text-sm">{field}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Quick Reports */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Reports</CardTitle>
              <CardDescription>Pre-configured report templates</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => {
                  setReportType("candidates");
                  setDateFrom(new Date(2026, 2, 1));
                  setDateTo(new Date());
                  toast.info("Loaded: This Month's Candidates");
                }}
              >
                <FileText className="w-4 h-4 mr-2" />
                This Month's Candidates
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => {
                  setReportType("attendance");
                  setDateFrom(new Date(2026, 2, 24));
                  setDateTo(new Date());
                  toast.info("Loaded: Last 7 Days Attendance");
                }}
              >
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Last 7 Days Attendance
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => {
                  setReportType("jobs");
                  toast.info("Loaded: All Active Jobs");
                }}
              >
                <FileText className="w-4 h-4 mr-2" />
                All Active Jobs
              </Button>

              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => {
                  setReportType("analytics");
                  setDateFrom(new Date(2026, 0, 1));
                  setDateTo(new Date());
                  toast.info("Loaded: Year-to-Date Analytics");
                }}
              >
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Year-to-Date Analytics
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Export History</CardTitle>
              <CardDescription>Recently exported reports</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm space-y-3">
                <div className="p-3 border border-slate-200 rounded">
                  <div className="font-medium mb-1">Candidate Report</div>
                  <div className="text-xs text-slate-500">
                    Exported on 30/03/2026
                  </div>
                </div>
                <div className="p-3 border border-slate-200 rounded">
                  <div className="font-medium mb-1">Attendance Report</div>
                  <div className="text-xs text-slate-500">
                    Exported on 28/03/2026
                  </div>
                </div>
                <div className="p-3 border border-slate-200 rounded">
                  <div className="font-medium mb-1">Job Analytics</div>
                  <div className="text-xs text-slate-500">
                    Exported on 25/03/2026
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tips</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2 text-slate-600">
              <p>• Use CSV format for Excel compatibility</p>
              <p>• PDF format is best for sharing reports</p>
              <p>• JSON format for data integration</p>
              <p>• Filter by specific jobs for focused analysis</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
