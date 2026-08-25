// Shows the Job Details view.
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import * as XLSX from "xlsx";
import { PageLayout } from "../shared/PageLayout";
import { formatDisplayDate } from "../../lib/date";
import { Button } from "../ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Badge } from "../ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../ui/tabs";
import { Progress } from "../ui/progress";
import {
  Users,
  Calendar,
  MapPin,
  Building2,
  FileText,
  ExternalLink,
  Copy,
  ChevronDown,
  Check,
  Pencil,
  GraduationCap,
  Clock,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import {
  apiFetch,
  getJobDescriptionFileUrl,
  getStoredUser,
  type JobSummary,
} from "../../lib/api";
import { LoadingState } from "../shared/LoadingState";

type JobDetailsData = JobSummary & {
  responsibilities?: { responsibility: string }[];
  qualifications?: { qualification: string }[];
  skills?: { name: string; type: string; importance: string }[];
  criteria?: { id: number; name: string; weight: number; description: string | null; isActive?: number | boolean }[];
  eligibility?: Record<string, unknown> | null;
  eligibilityValues?: { filterKey: string; filterLabel: string; filterValue: string }[];
};

type PreviewSheet = {
  name: string;
  rows: string[][];
};

const isSpreadsheetFile = (fileName: string | null | undefined) =>
  Boolean(fileName && /\.xls[x]?$/i.test(fileName));

const isPublicFileUrl = (fileUrl: string) => {
  try {
    const hostname = new URL(fileUrl).hostname.toLowerCase();
    return !["localhost", "127.0.0.1", "::1"].includes(hostname);
  } catch {
    return false;
  }
};

const getExcelWebPreviewUrl = (fileUrl: string) =>
  `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(fileUrl)}`;

// Provides the to job status helper.
const toJobStatus = (status: JobSummary["status"]) =>
  status === "closed" ? "closed" : status === "active" ? "active" : "draft";

// Provides the map job description helper.
const mapJobDescription = (job: JobDetailsData) => {
  const responsibilities = job.responsibilities?.map((item) => item.responsibility) ?? [];
  const skills = job.skills?.map((item) => item.name) ?? [];

  if (job.description) return job.description;

  return [
    `${job.title}`,
    responsibilities.length ? `Key Responsibilities:\n${responsibilities.map((item) => `- ${item}`).join("\n")}` : "",
    skills.length ? `Required Skills:\n${skills.map((item) => `- ${item}`).join("\n")}` : "",
    job.qualifications?.length
      ? `Qualifications:\n${job.qualifications.map((item) => `- ${item.qualification}`).join("\n")}`
      : "",
  ]
    .filter(Boolean)
    .join("\n\n");
};
// Renders the Job Details component.
export function JobDetails() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<(JobDetailsData & { link: string | null; description: string }) | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>("active");
  const [isLoadingJob, setIsLoadingJob] = useState(true);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeletingJob, setIsDeletingJob] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewFileUrl, setPreviewFileUrl] = useState<string | null>(null);
  const [previewSheets, setPreviewSheets] = useState<PreviewSheet[]>([]);
  const [selectedPreviewSheet, setSelectedPreviewSheet] = useState(0);

  useEffect(() => {
    if (!jobId) return;

    setIsLoadingJob(true);
    apiFetch<{ job: JobDetailsData }>(`/jobs/${jobId}`)
      .then(({ job: loadedJob }) => {
        const status = toJobStatus(loadedJob.status);
        setJob({
          ...loadedJob,
          status,
          link: loadedJob.link
            ? `${window.location.origin}${loadedJob.link}`
            : null,
          description: mapJobDescription(loadedJob),
        });
        setCurrentStatus(status);
      })
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load job details",
        ),
      )
      .finally(() => setIsLoadingJob(false));
  }, [jobId]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (isLoadingJob) {
    return (
      <PageLayout
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Job Details" },
        ]}
        title="Job Details"
        useCard={false}
      >
        <LoadingState title="Loading job details" />
      </PageLayout>
    );
  }

  if (!job) {
    return <div>Job not found</div>;
  }

  const statusOptions = [
    { value: "active", label: "Active", color: "bg-green-600" },
    { value: "closed", label: "Closed", color: "bg-slate-600" },
  ];
  const currentStatusLabel =
    currentStatus === "draft"
      ? "DRAFT"
      : statusOptions
          .find((opt) => opt.value === currentStatus)
          ?.label.toUpperCase();
  const criteria = job.criteria ?? [];
  const eligibility = job.eligibility ?? {};
  const processableApplicants = Math.max(
    0,
    Number(job.applicants) - Number(job.filteredOutCount),
  );
  const processedApplicants =
    Number(job.interviewCount) + Number(job.rejectedCount);
  const processedRate =
    processableApplicants > 0
      ? Math.round((processedApplicants / processableApplicants) * 100)
      : 0;
  const totalCriteriaWeight = criteria.reduce(
    (sum, item) => sum + Number(item.weight),
    0,
  );
  // Gets eligibility value.
  const getEligibilityValue = (key: string) => {
    const value = eligibility[key];
    if (value === null || value === undefined || value === "") return "-";
    return String(value);
  };
  const eligibilityItems = [
    {
      key: "minCGPA",
      label: "Minimum CGPA",
      value: getEligibilityValue("minCgpa"),
      icon: GraduationCap,
    },
    {
      key: "minExperience",
      label: "Minimum Experience",
      value:
        getEligibilityValue("minYearsExperience") === "-"
          ? "-"
          : `${getEligibilityValue("minYearsExperience")} years`,
      icon: Calendar,
    },
    {
      key: "educationLevel",
      label: "Qualification",
      value: getEligibilityValue("requiredQualification"),
      icon: FileText,
    },
    {
      key: "requiredLanguage",
      label: "Language",
      value: getEligibilityValue("requiredLanguage"),
      icon: Users,
    },
    {
      key: "requiredLocation",
      label: "Location",
      value: getEligibilityValue("requiredLocation"),
      icon: MapPin,
    },
    {
      key: "maxNoticePeriod",
      label: "Max Notice Period",
      value:
        getEligibilityValue("maxNoticePeriodDays") === "-"
          ? "-"
          : `${getEligibilityValue("maxNoticePeriodDays")} days`,
      icon: Clock,
    },
  ].filter((item) =>
    Array.isArray(job.eligibilityValues)
      ? job.eligibilityValues.some((configured) => configured.filterKey === item.key)
      : item.value !== "-",
  );
  const jobDescriptionFileUrl = job.jdFileName && jobId
    ? getJobDescriptionFileUrl(Number(jobId))
    : null;
  const canOpenExcelInWeb = Boolean(
    jobDescriptionFileUrl &&
      isSpreadsheetFile(job.jdFileName) &&
      isPublicFileUrl(jobDescriptionFileUrl),
  );

  // Handles status change.
  const handleStatusChange = async (newStatus: string) => {
    if (!jobId) return;
    if (newStatus === currentStatus) return;

    const previousStatus = currentStatus;
    setCurrentStatus(newStatus);

    try {
      await apiFetch(`/jobs/${jobId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          actionUserId: getStoredUser()?.id,
        }),
      });
      toast.success("Job status updated successfully!");
      window.dispatchEvent(
        new CustomEvent("jobStatusUpdated", {
          detail: { jobId, status: newStatus },
        }),
      );
    } catch (error) {
      setCurrentStatus(previousStatus);
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update job status",
      );
    }
  };

  // Deletes the job after the confirmation dialog is accepted.
  const handleDeleteJob = async () => {
    if (!jobId || !job || isDeletingJob) return;

    setIsDeletingJob(true);
    try {
      await apiFetch(`/jobs/${jobId}`, {
        method: "DELETE",
        body: JSON.stringify({ actionUserId: getStoredUser()?.id }),
      });
      toast.success("Job deleted successfully");
      setIsDeleteDialogOpen(false);
      navigate(`/departments/${encodeURIComponent(job.department)}`, {
        replace: true,
      });
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to delete job",
      );
    } finally {
      setIsDeletingJob(false);
    }
  };

  // Copies link.
  const copyLink = async () => {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(job.link || "");
        toast.success("Job link copied to clipboard!");
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement("textarea");
        textArea.value = job.link || "";
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          document.execCommand("copy");
          toast.success("Job link copied to clipboard!");
        } catch (err) {
          toast.error("Failed to copy to clipboard");
        }
        textArea.remove();
      }
    } catch (err) {
      // Fallback method
      const textArea = document.createElement("textarea");
      textArea.value = job.link || "";
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand("copy");
        toast.success("Job link copied to clipboard!");
      } catch (error) {
        toast.error("Failed to copy to clipboard");
      }
      textArea.remove();
    }
  };

  // Copies application link.
  const copyApplicationLink = async () => {
    const appLink = job.link || `${window.location.origin}/apply`;
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(appLink);
        toast.success("Application link copied to clipboard!");
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement("textarea");
        textArea.value = appLink;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          document.execCommand("copy");
          toast.success(
            "Application link copied to clipboard!",
          );
        } catch (err) {
          toast.error("Failed to copy to clipboard");
        }
        textArea.remove();
      }
    } catch (err) {
      // Fallback method
      const textArea = document.createElement("textarea");
      textArea.value = appLink;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand("copy");
        toast.success("Application link copied to clipboard!");
      } catch (error) {
        toast.error("Failed to copy to clipboard");
      }
      textArea.remove();
    }
  };

  const closeJobDescriptionPreview = () => {
    setIsPreviewOpen(false);
    setIsLoadingPreview(false);
    setPreviewError(null);
    setPreviewSheets([]);
    setSelectedPreviewSheet(0);
    setPreviewUrl(null);
    setPreviewFileUrl(null);
  };

  const previewJobDescription = async () => {
    if (!jobId || !job.jdFileName) {
      toast.error("Job description file not found");
      return;
    }

    setIsPreviewOpen(true);
    setIsLoadingPreview(true);
    setPreviewError(null);
    setPreviewUrl(null);
    setPreviewFileUrl(null);
    setPreviewSheets([]);
    setSelectedPreviewSheet(0);

    try {
      const fileUrl = getJobDescriptionFileUrl(Number(jobId));
      setPreviewFileUrl(fileUrl);
      const response = await fetch(fileUrl);
      if (!response.ok) throw new Error("Unable to load the job description file");

      const fileBlob = await response.blob();
      const contentType = response.headers.get("content-type")?.split(";", 1)[0].toLowerCase();
      const extension = contentType === "application/pdf"
        ? "pdf"
        : contentType === "application/vnd.ms-excel"
          || contentType === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ? "xlsx"
          : job.jdFileName.split(".").pop()?.toLowerCase();

      if (extension === "pdf") {
        setPreviewUrl(URL.createObjectURL(fileBlob));
      } else if (extension === "xlsx" || extension === "xls") {
        const workbook = XLSX.read(await fileBlob.arrayBuffer(), { type: "array" });
        const sheets = workbook.SheetNames.map((name) => {
          const rows = XLSX.utils.sheet_to_json<unknown[]>(workbook.Sheets[name], {
            header: 1,
            defval: "",
          });

          return {
            name,
            rows: rows.slice(0, 200).map((row) =>
              row.slice(0, 30).map((cell) => String(cell ?? "")),
            ),
          };
        });
        setPreviewSheets(sheets);
      } else {
        throw new Error("This file type cannot be previewed");
      }
    } catch (error) {
      setPreviewError(
        error instanceof Error ? error.message : "Unable to preview this file",
      );
    } finally {
      setIsLoadingPreview(false);
    }
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: job.department, href: `/departments/${encodeURIComponent(job.department)}` },
        { label: job.title },
      ]}
      title={
        <div className="w-full">
          <h1 className="text-3xl font-bold text-slate-900">
            {job.title}
          </h1>

          <div className="flex items-end justify-between gap-4 mt-3">
            <div className="flex flex-wrap gap-3 text-sm text-slate-600">
              <div className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {job.department}
              </div>
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {job.location}
              </div>
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                Posted{" "}
                {formatDisplayDate(job.createdAt)}
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className={`h-9 min-w-[140px] justify-between px-4 ${
                      currentStatus === "active"
                        ? "border-green-600 text-green-700 hover:bg-green-50"
                        : currentStatus === "closed"
                          ? "border-slate-600 text-slate-700 hover:bg-slate-50"
                          : currentStatus === "draft"
                            ? "border-slate-400 text-slate-600 hover:bg-slate-50"
                            : "border-slate-300 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {currentStatusLabel}
                    <ChevronDown className="ml-2 h-4 w-4 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>

                <DropdownMenuContent
                  align="end"
                  className="w-[170px]"
                >
                  {statusOptions.map((option) => (
                    <DropdownMenuItem
                      key={option.value}
                      onClick={() => handleStatusChange(option.value)}
                      className="flex items-center justify-between cursor-pointer"
                    >
                      <span>{option.label}</span>
                      {currentStatus === option.value && (
                        <Check className="h-4 w-4 text-[#003B7A]" />
                      )}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      }
      useCard={false}
    >
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="shadow-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-500">
                Total Applicants
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {job.applicants}
              </div>
            </CardContent>
          </Card>

            <Card className="shadow-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-500">
                Average Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {job.avgScore}
              </div>
              <Progress value={job.avgScore} className="mt-2" />
            </CardContent>
          </Card>

            <Card className="shadow-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-500">
                Processed Rate
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{processedRate}%</div>
              <Progress value={processedRate} className="mt-2" />
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <div className="flex items-center w-full">
  <div className="flex items-center gap-2">
    <TabsList>
      <TabsTrigger value="overview">
        Overview
      </TabsTrigger>
      <TabsTrigger value="criteria">
        Screening Setup
      </TabsTrigger>
      <TabsTrigger value="sharing">Sharing</TabsTrigger>
    </TabsList>

    <Button
      className="shadow-none"
      type="button"
      variant="outline"
      onClick={() =>
        navigate(`/jobs/${jobId}/candidates`)
      }
    >
      <Users className="mr-2 h-4 w-4" />
      Candidates ({job.applicants})
    </Button>
  </div>

  <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
    <Button
      type="button"
      variant="outline"
      onClick={() => setIsDeleteDialogOpen(true)}
      disabled={isDeletingJob}
      className="border-red-200 text-red-600 shadow-sm hover:bg-red-50 hover:text-red-700"
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Delete
    </Button>
    <Button
      type="button"
      variant="outline"
      onClick={() =>
        navigate(`/jobs/${jobId}/edit`, {
          state: { job },
        })
      }
      className="shadow-sm"
    >
      <Pencil className="mr-2 h-4 w-4" />
      Edit
    </Button>
  </div>
</div>

          <TabsContent value="overview" className="space-y-6">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle>Job Description</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-slate max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm">
                    {job.description}
                  </pre>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Attached Documents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded bg-blue-100">
                      <FileText className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {job.jdFileName}
                      </p>
                      <p className="text-xs text-slate-500">
                        Saved job description
                      </p>
                    </div>
                  </div>
                  {canOpenExcelInWeb && jobDescriptionFileUrl ? (
                    <Button asChild variant="outline" size="sm">
                      <a
                        href={getExcelWebPreviewUrl(jobDescriptionFileUrl)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Preview
                      </a>
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={previewJobDescription}
                      disabled={!job.jdFileName}
                    >
                      Preview
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="criteria" className="space-y-6">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle>Eligibility Filter</CardTitle>
                <CardDescription>
                  Minimum requirements candidates must meet before ranking
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {eligibilityItems.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
                    No eligibility filters enabled for this job.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {eligibilityItems.map((item) => {
                      const Icon = item.icon;

                      return (
                        <div
                          key={item.key}
                          className="flex min-h-[72px] items-start gap-3 rounded-lg border border-slate-200 bg-white p-3"
                        >
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-blue-50 text-[#003B7A]">
                            <Icon className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                              {item.label}
                            </p>
                            <p className="mt-1 break-words text-sm font-semibold text-slate-900">
                              {item.value}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="shadow-md">
              <CardHeader>
                <CardTitle>Ranking Criteria & Weight</CardTitle>
                <CardDescription>
                  Weighted scoring criteria used after eligibility screening
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      Total Weight
                    </p>
                    <p className="text-xs text-slate-500">
                      Criteria weight should equal 100%
                    </p>
                  </div>
                  <Badge
                    className={
                      totalCriteriaWeight === 100
                        ? "bg-green-600"
                        : "bg-amber-500"
                    }
                  >
                    {totalCriteriaWeight}%
                  </Badge>
                </div>

                {criteria.length === 0 ? (
                  <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-600">
                    No criteria have been set for this job yet.
                  </div>
                ) : (
                  criteria.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg border border-slate-200 p-4"
                    >
                      <div className="mb-3 flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-900">
                            {item.name}
                          </p>
                          {item.description && (
                            <p className="mt-1 text-sm text-slate-500">
                              {item.description}
                            </p>
                          )}
                        </div>
                        <Badge
                          variant="outline"
                          className="border-blue-200 bg-blue-50 text-blue-700"
                        >
                          {Number(item.weight)}%
                        </Badge>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="sharing" className="space-y-6">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle>Application Page</CardTitle>
                <CardDescription>
                  Direct link for candidates to submit their
                  applications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={job.link || `${window.location.origin}/apply`}
                    readOnly
                    className="flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm"
                  />
                  <Button 
                    className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5 "
                    onClick={copyApplicationLink}>
                    <Copy 
                      className="mr-2 h-4 w-4" />
                    Copy
                  </Button>
                </div>

                
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog
        open={isPreviewOpen}
        onOpenChange={(open) => {
          if (!open) closeJobDescriptionPreview();
        }}
      >
        <DialogContent className="max-h-[88vh] overflow-hidden sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle>Job Description Preview</DialogTitle>
            <DialogDescription>{job.jdFileName}</DialogDescription>
          </DialogHeader>

          <div className="min-h-[240px] min-w-0">
            {isLoadingPreview && (
              <div className="flex min-h-[240px] items-center justify-center text-sm text-slate-500">
                Loading preview...
              </div>
            )}

            {!isLoadingPreview && previewError && (
              <div className="flex min-h-[240px] items-center justify-center rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
                {previewError}
              </div>
            )}

            {!isLoadingPreview && !previewError && previewUrl && (
              <iframe
                src={previewUrl}
                title={`${job.jdFileName} preview`}
                className="h-[68vh] min-h-[420px] w-full rounded-lg border border-slate-200"
              />
            )}

            {!isLoadingPreview && !previewError && previewSheets.length > 0 && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  {previewSheets.length > 1 ? (
                    <div className="flex flex-wrap gap-2">
                      {previewSheets.map((sheet, index) => (
                        <Button
                          key={sheet.name}
                          type="button"
                          size="sm"
                          variant={selectedPreviewSheet === index ? "default" : "outline"}
                          onClick={() => setSelectedPreviewSheet(index)}
                          className={selectedPreviewSheet === index ? "bg-[#003B7A] text-white hover:bg-[#002f63]" : ""}
                        >
                          {sheet.name}
                        </Button>
                      ))}
                    </div>
                  ) : <span />}

                  {previewFileUrl && isPublicFileUrl(previewFileUrl) && (
                    <Button asChild variant="outline" size="sm">
                      <a
                        href={getExcelWebPreviewUrl(previewFileUrl)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open in Excel web
                      </a>
                    </Button>
                  )}
                </div>

                {(() => {
                  const sheet = previewSheets[selectedPreviewSheet] ?? previewSheets[0];
                  const columnCount = Math.max(
                    1,
                    ...sheet.rows.map((row) => row.length),
                  );

                  return (
                    <div className="max-h-[68vh] overflow-auto rounded-lg border border-slate-200">
                      <table className="min-w-full border-collapse text-left text-sm">
                        <tbody>
                          {sheet.rows.map((row, rowIndex) => (
                            <tr
                              key={`${sheet.name}-${rowIndex}`}
                              className="border-b border-slate-200 last:border-b-0"
                            >
                              {Array.from({ length: columnCount }).map((_, columnIndex) => {
                                const value = row[columnIndex] ?? "";
                                const Cell = rowIndex === 0 ? "th" : "td";

                                return (
                                  <Cell
                                    key={`${sheet.name}-${rowIndex}-${columnIndex}`}
                                    className={
                                      rowIndex === 0
                                        ? "whitespace-nowrap bg-slate-50 px-3 py-2 font-semibold text-slate-700"
                                        : "max-w-[360px] whitespace-pre-wrap px-3 py-2 align-top text-slate-600"
                                    }
                                  >
                                    {value}
                                  </Cell>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={(open) => {
          if (!isDeletingJob) setIsDeleteDialogOpen(open);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this job?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {job.title} and its job setup. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction
              disabled={isDeletingJob}
              onClick={(event) => {
                event.preventDefault();
                void handleDeleteJob();
              }}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              {isDeletingJob ? "Deleting..." : "Delete Job"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageLayout>
  );
}
