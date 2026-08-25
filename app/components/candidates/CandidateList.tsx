// Shows the Candidate List view.
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { getCompactPageItems } from "../../lib/pagination";
import { PageLayout } from "../shared/PageLayout";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  Calendar as CalendarIcon,
  Clock3,
  FileText,
  Languages,
  MapPin,
  Mail,
  Pencil,
  Search,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, getStoredUser } from "../../lib/api";
import { formatDisplayDate, parseDatabaseDateTime } from "../../lib/date";
import {
  getAnalysisStatusClass,
  getAnalysisStatusLabel,
  getEligibilityStatusClass,
  getEligibilityStatusLabel,
  isAnalysisProcessing,
  mapApiCandidate,
  type ApiCandidate,
} from "../../lib/candidateData";
import { LoadingState } from "../shared/LoadingState";
import { CandidateActions } from "./CandidateActions";
import {
  CandidateCard,
  getCandidateStatusColor,
  getCandidateStatusLabel,
  type Candidate,
  type CandidateStatus,
} from "./CandidateCard";
import { CandidateEmailDialog } from "./CandidateEmailDialog";
import { CandidateScoreBreakdown } from "./CandidateScoreBreakdown";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Calendar as DatePickerCalendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "../ui/tooltip";

type EmailTemplate = {
  subject: string;
  body: string;
  isActive?: boolean;
};

const CANDIDATES_PER_PAGE = 15;
const JOB_HISTORY_PER_PAGE = 5;

// Formats date input value.
const formatDateInputValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Parses date input value.
const parseDateInputValue = (value?: string | null) =>
  value ? new Date(`${value}T00:00:00`) : undefined;

// Provides the today date input value helper.
const todayDateInputValue = () => formatDateInputValue(new Date());

// Gets email type label.
const getEmailTypeLabel = (type?: string | null) => {
  if (type === "interview") return "Interview";
  if (type === "reject") return "Reject";
  return "Email";
};

const defaultRejectTemplate: EmailTemplate = {
  subject: "Update on your job application",
  body:
    "Dear {candidateName},\n\n" +
    "Thank you for your interest in {jobTitle}. After careful review, we regret to inform you that you have not been selected for this role.\n\n" +
    "We appreciate your time and interest in {companyName}.\n\n" +
    "Regards,\n{companyName}",
};

const defaultInterviewTemplate: EmailTemplate = {
  subject: "Interview invitation for {jobTitle}",
  body:
    "Dear {candidateName},\n\n" +
    "We would like to invite you for an interview for the {jobTitle} position.\n\n" +
    "Available interview date and time options: {interviewDateOptions}\n\n" +
    "Please reply to this email with your preferred interview time. Also, please complete the attached file and reply to this email before attending the interview.\n\n" +
    "Regards,\nUWC Berhad",
};

const rejectionReasonTypes = [
  "Not a Good Fit",
  "Insufficient Skills",
  "Lack of Experience",
  "Overqualified",
  "Other",
];

type CandidateSort = "rank" | "score" | "cgpa" | "date";

// Parses candidate cgpa for sorting.
const parseCandidateCgpa = (candidate: Candidate): number | null => {
  const cgpa = Number(candidate.cgpa);
  return Number.isFinite(cgpa) ? cgpa : null;
};

// Parses the persisted application timestamp without locale-dependent ordering.
const parseCandidateDate = (value?: string | null): number | null =>
  parseDatabaseDateTime(value)?.getTime() ?? null;

// Uses the application id to keep same-time submissions in newest-first order.
const parseCandidateId = (value?: string | null): number | null => {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

// Keeps empty values at the end for every candidate sort.
const compareNullableNumbers = (
  first: number | null,
  second: number | null,
  direction: "asc" | "desc",
) => {
  if (first === null && second === null) return 0;
  if (first === null) return 1;
  if (second === null) return -1;

  return direction === "asc" ? first - second : second - first;
};

// Matches the status values shown by the candidate status filter.
const matchesCandidateStatusFilter = (
  candidate: Candidate,
  status: string,
  temporarilyVisibleCandidateIds: Set<string>,
) => {
  if (
    status === "interview" &&
    (candidate.status === "hired" || candidate.status === "rejected")
  ) {
    return false;
  }

  if (status === "all" || temporarilyVisibleCandidateIds.has(candidate.id)) {
    return true;
  }

  if (status === "shortlisted") return candidate.isShortlisted;
  if (status === "interview") return Boolean(candidate.interviewSentAt);
  if (status === "filtered_out") {
    return candidate.filteredOut || candidate.status === "filtered_out";
  }

  return candidate.status === status;
};

// Sorts candidates with deterministic tie-breaking.
const compareCandidates = (
  first: Candidate,
  second: Candidate,
  sortBy: CandidateSort,
) => {
  let order = 0;

  if (sortBy === "score") {
    order = compareNullableNumbers(first.score, second.score, "desc");
  } else if (sortBy === "cgpa") {
    order = compareNullableNumbers(
      parseCandidateCgpa(first),
      parseCandidateCgpa(second),
      "desc",
    );
  } else if (sortBy === "date") {
    order = compareNullableNumbers(
      parseCandidateDate(first.appliedAt ?? first.appliedDate),
      parseCandidateDate(second.appliedAt ?? second.appliedDate),
      "desc",
    );
  } else {
    const firstRank =
      first.filteredOut ||
      ["rejected", "withdrawn"].includes(first.status) ||
      first.rank === null
        ? null
        : first.rank;
    const secondRank =
      second.filteredOut ||
      ["rejected", "withdrawn"].includes(second.status) ||
      second.rank === null
        ? null
        : second.rank;
    order = compareNullableNumbers(firstRank, secondRank, "asc");
  }

  if (order !== 0) return order;

  if (sortBy === "date") {
    const applicationOrder = compareNullableNumbers(
      parseCandidateId(first.applicationId),
      parseCandidateId(second.applicationId),
      "desc",
    );
    if (applicationOrder !== 0) return applicationOrder;
  }

  return (
    first.name.localeCompare(second.name, undefined, { sensitivity: "base" }) ||
    first.email.localeCompare(second.email, undefined, { sensitivity: "base" })
  );
};

// Renders the Candidate List component.
export function CandidateList() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobTitle, setJobTitle] = useState("Candidates");
  const [department, setDepartment] = useState("Department");
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(true);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchCandidateId, setSearchCandidateId] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [filterStatus, setFilterStatus] = useState("all");
  const [sortBy, setSortBy] = useState<CandidateSort>("rank");
  const [currentPage, setCurrentPage] = useState(1);
  const [temporarilyVisibleCandidateIds, setTemporarilyVisibleCandidateIds] =
    useState<Set<string>>(new Set());
  const [sendingEmailCandidateIds, setSendingEmailCandidateIds] =
    useState<Set<string>>(new Set());
  const [jobHistoryPages, setJobHistoryPages] = useState<
    Record<string, number>
  >({});

  const [expandedCandidate, setExpandedCandidate] = useState<
    string | null
  >(null);

  // Applies status filter.
  const applyStatusFilter = (status: string) => {
    setFilterStatus(status);
  };

  const [interviewPopupCandidate, setInterviewPopupCandidate] =
    useState<Candidate | null>(null);
  const [rejectPopupCandidate, setRejectPopupCandidate] =
    useState<Candidate | null>(null);
  const [reasonPopupCandidate, setReasonPopupCandidate] =
    useState<Candidate | null>(null);
  const [hirePopupCandidate, setHirePopupCandidate] =
    useState<Candidate | null>(null);

  const [interviewDateTime, setInterviewDateTime] =
    useState("");
  const [hireStartDate, setHireStartDate] = useState("");
  const [hireDatePickerOpen, setHireDatePickerOpen] = useState(false);
  const [sendRejectEmail, setSendRejectEmail] = useState(true);
  const [rejectEmailStep, setRejectEmailStep] = useState<1 | 2>(1);
  const [rejectReasonType, setRejectReasonType] = useState("");
  const [rejectReasonDetails, setRejectReasonDetails] = useState("");
  const [rejectTemplate, setRejectTemplate] =
    useState<EmailTemplate>(defaultRejectTemplate);
  const [interviewTemplate, setInterviewTemplate] =
    useState<EmailTemplate>(defaultInterviewTemplate);

  useEffect(() => {
    if (!jobId) return;

    setIsLoadingCandidates(true);

    apiFetch<{
      job: { title: string; department: string };
      candidates: ApiCandidate[];
    }>(`/jobs/${jobId}/candidates`)
      .then((data) => {
        setJobTitle(data.job.title);
        setDepartment(data.job.department);
        const loadedCandidates = data.candidates.map(mapApiCandidate);
        setCandidates(loadedCandidates);
        setSearchQuery(searchParams.get("search") || "");

        const targetApplicationId = searchParams.get("applicationId");
        const targetCandidateId = searchParams.get("candidateId");
        const targetIndex = loadedCandidates.findIndex(
          (candidate) =>
            (targetApplicationId &&
              candidate.applicationId === targetApplicationId) ||
            (targetCandidateId && candidate.id === targetCandidateId),
        );

        if (targetIndex >= 0) {
          const targetCandidate = loadedCandidates[targetIndex];
          setExpandedCandidate(targetCandidate.id);
          setCurrentPage(
            Math.floor(targetIndex / CANDIDATES_PER_PAGE) + 1,
          );
          setJobHistoryPages((prev) => ({
            ...prev,
            [targetCandidate.applicationId || targetCandidate.id]: 1,
          }));
        }
      })
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load candidates",
        ),
      )
      .finally(() => setIsLoadingCandidates(false));
  }, [jobId, searchParams]);

  useEffect(() => {
    apiFetch<{
      templates?: {
        interview_invitation?: EmailTemplate;
        reject_application?: EmailTemplate;
      };
    }>("/email-templates")
      .then((data) => {
        const interview = data.templates?.interview_invitation;
        const reject = data.templates?.reject_application;

        if (interview) {
          setInterviewTemplate({
            subject: interview.subject || defaultInterviewTemplate.subject,
            body: interview.body || defaultInterviewTemplate.body,
            isActive: interview.isActive,
          });
        }

        if (reject) {
          setRejectTemplate({
            subject: reject.subject || defaultRejectTemplate.subject,
            body: reject.body || defaultRejectTemplate.body,
            isActive: reject.isActive,
          });
        }
      })
      .catch(() => {
        setInterviewTemplate(defaultInterviewTemplate);
        setRejectTemplate(defaultRejectTemplate);
      });
  }, []);

  // Gets total max score.
  const getTotalMaxScore = () => 100;

  // Gets candidate display score.
  const getCandidateDisplayScore = (candidate: Candidate) => {
    if (isAnalysisProcessing(candidate.analysisStatus)) return null;

    const analysisFailed =
      candidate.analysisStatus?.toLowerCase() === "failed" ||
      candidate.resumeParsingStatus?.toLowerCase() === "failed";
    return candidate.score ?? (analysisFailed ? 0 : null);
  };

  // Gets candidate score percentage.
  const getCandidateScorePercentage = (candidate: Candidate) =>
    getCandidateDisplayScore(candidate) === null
      ? null
      : Math.round(getCandidateDisplayScore(candidate) ?? 0);

  // Builds email preview.
  const buildEmailPreview = (
    template: EmailTemplate,
    candidate: Candidate,
    interviewOptions = "",
  ) => {
    const replacements: Record<string, string> = {
      "{candidateName}": candidate.name,
      "{jobTitle}": jobTitle,
      "{companyName}": "UWC Berhad",
      "{interviewDate}": interviewOptions || "{interviewDateOptions}",
      "{interviewDateOptions}": interviewOptions || "{interviewDateOptions}",
      "{{candidate_name}}": candidate.name,
      "{{job_title}}": jobTitle,
      "{{interview_datetime}}": interviewOptions || "a scheduled time to be confirmed",
    };

    // Replaces placeholders.
    const replacePlaceholders = (value: string) =>
      Object.entries(replacements).reduce(
        (text, [placeholder, replacement]) =>
          text.split(placeholder).join(replacement),
        value,
      );

    return {
      subject: replacePlaceholders(template.subject),
      body: replacePlaceholders(template.body).replace(/\\n/g, "\n"),
    };
  };

  // Builds reject email preview.
  const buildRejectEmailPreview = (candidate: Candidate) =>
    buildEmailPreview(rejectTemplate, candidate);

  // Builds interview email preview.
  const buildInterviewEmailPreview = (candidate: Candidate) =>
    buildEmailPreview(interviewTemplate, candidate, interviewDateTime);

  // Opens employment form.
  const openEmploymentForm = (candidate: Candidate) => {
    if (!candidate.employmentFormSubmissionId) return;
    window.open(
      `/employment-form?view=hr&submissionId=${candidate.employmentFormSubmissionId}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  // Keep search, status, and sort rules in one display list.
  const filteredCandidates = candidates
    .filter((candidate) => {
      const matchesSearch =
        searchCandidateId !== ""
          ? candidate.id === searchCandidateId ||
            candidate.applicationId === searchCandidateId
          : candidate.name
              .toLowerCase()
              .includes(searchQuery.toLowerCase()) ||
            candidate.email
              .toLowerCase()
              .includes(searchQuery.toLowerCase());

      const matchesStatus = matchesCandidateStatusFilter(
        candidate,
        filterStatus,
        temporarilyVisibleCandidateIds,
      );

      return matchesSearch && matchesStatus;
    })
    .sort((first, second) => compareCandidates(first, second, sortBy));
  const candidateSearchSuggestions = useMemo(() => {
    const searchTerm = searchQuery.trim().toLowerCase();
    if (!searchTerm || searchCandidateId) return [];

    return candidates
      .filter((candidate) => {
        const matchesStatus = matchesCandidateStatusFilter(
          candidate,
          filterStatus,
          temporarilyVisibleCandidateIds,
        );
        if (!matchesStatus) return false;

        return (
          candidate.name.toLowerCase().startsWith(searchTerm) ||
          candidate.email.toLowerCase().startsWith(searchTerm)
        );
      })
      .sort((first, second) =>
        first.name.localeCompare(second.name, undefined, { sensitivity: "base" }),
      )
      .slice(0, 8);
  }, [candidates, filterStatus, searchCandidateId, searchQuery, temporarilyVisibleCandidateIds]);
  const pageCount = Math.max(
    1,
    Math.ceil(filteredCandidates.length / CANDIDATES_PER_PAGE),
  );
  const pagedCandidates = filteredCandidates.slice(
    (currentPage - 1) * CANDIDATES_PER_PAGE,
    currentPage * CANDIDATES_PER_PAGE,
  );

  useEffect(() => {
    setCurrentPage(1);
    setTemporarilyVisibleCandidateIds(new Set());
  }, [searchQuery, filterStatus, sortBy, jobId]);

  // Gets status color.
  const getStatusColor = (status: string) => {
    switch (status) {
      case "hired":
        return "bg-emerald-600";
      case "interviewed":
        return "bg-sky-700";
      case "interview":
        return "bg-blue-600";
      case "reviewed":
        return "bg-green-600";
      case "shortlisted":
        return "bg-amber-500";
      case "new":
        return "bg-yellow-600";
      case "rejected":
        return "bg-red-600";
      case "filtered_out":
        return "bg-slate-500";
      case "withdrawn":
        return "bg-slate-400";
      default:
        return "bg-slate-600";
    }
  };

  // Gets status label.
  const getStatusLabel = (status: string) => {
    switch (status) {
      case "filtered_out":
        return "FILTERED OUT";
      case "interviewed":
        return "INTERVIEWED";
      case "hired":
        return "HIRED";
      case "withdrawn":
        return "WITHDRAWN";
      default:
        return status.replace(/_/g, " ").toUpperCase();
    }
  };

  // Gets score color.
  const getScoreColor = (score: number | null) => {
    if (score === null) return "text-slate-500";
    if (score >= 90) return "text-green-600";
    if (score >= 80) return "text-blue-600";
    if (score >= 70) return "text-yellow-600";

    return "text-slate-600";
  };

  // Updates candidate status.
  const updateCandidateStatus = async (
    candidateId: string,
    newStatus: CandidateStatus,
    options: {
      interviewDateTime?: string;
      emailAction?: boolean;
      keepVisibleUntilRefresh?: boolean;
      reasonType?: string;
      reasonDetails?: string;
      hiredStartDate?: string | null;
    } = {},
  ): Promise<boolean> => {
    // Update the screen first and restore it if the API fails.
    const currentUser = getStoredUser();
    const target = candidates.find(
      (candidate) => candidate.id === candidateId,
    );
    const previousCandidates = candidates;

    if (options.keepVisibleUntilRefresh) {
      setTemporarilyVisibleCandidateIds((prev) => {
        const next = new Set(prev);
        next.add(candidateId);
        return next;
      });
    }

    setCandidates((prev) => {
      const updated = prev.map((candidate) =>
        candidate.id === candidateId
          ? {
              ...candidate,
              status:
                newStatus === "shortlisted" ||
                newStatus === "reviewed"
                  ? candidate.status === "interview" ||
                    candidate.status === "interviewed"
                    ? candidate.status
                    : newStatus
                  : newStatus,
              isShortlisted:
                newStatus === "shortlisted"
                  ? true
                  : newStatus === "reviewed" ||
                      newStatus === "rejected"
                    ? false
                    : newStatus === "interview"
                      ? true
                      : newStatus === "interviewed"
                        ? candidate.isShortlisted
                      : newStatus === "hired"
                        ? true
                      : candidate.isShortlisted,
              interviewSentAt:
                newStatus === "interview"
                  ? candidate.interviewSentAt ||
                    new Date().toISOString()
                  : candidate.interviewSentAt,
              assignedHrUserId:
                candidate.assignedHrUserId ?? currentUser?.id ?? null,
              assignedHrName:
                candidate.assignedHrName ?? currentUser?.name ?? null,
              lastEmailType:
                options.emailAction
                  ? newStatus === "interview"
                    ? "interview"
                    : newStatus === "rejected"
                      ? "reject"
                      : candidate.lastEmailType
                  : candidate.lastEmailType,
              lastEmailSentAt:
                options.emailAction
                  ? new Date().toISOString()
                  : candidate.lastEmailSentAt,
              lastEmailSentBy:
                options.emailAction
                  ? currentUser?.name ?? candidate.lastEmailSentBy
                  : candidate.lastEmailSentBy,
              latestRejectActionType:
                newStatus === "rejected"
                  ? options.emailAction
                    ? "send_rejection_email"
                    : "reject_candidate"
                  : candidate.latestRejectActionType,
              latestRejectActionBy:
                newStatus === "rejected"
                  ? currentUser?.name ?? candidate.latestRejectActionBy
                  : candidate.latestRejectActionBy,
              latestEmailReasonType:
                options.emailAction && options.reasonType !== undefined
                  ? options.reasonType || null
                  : candidate.latestEmailReasonType,
              latestEmailReasonDetails:
                options.emailAction &&
                options.reasonDetails !== undefined
                  ? options.reasonDetails || null
                  : candidate.latestEmailReasonDetails,
              hiredStartDate:
                newStatus === "hired"
                  ? options.hiredStartDate ?? candidate.hiredStartDate ?? null
                  : candidate.hiredStartDate,
              wasHired:
                candidate.wasHired ||
                newStatus === "hired" ||
                (newStatus === "rejected" && candidate.status === "hired"),
            }
          : candidate,
      );

      return updated;
    });

    if (!target?.applicationId) {
      toast.error("Application record is missing for this candidate");
      return false;
    }

    try {
      await apiFetch(`/applications/${target.applicationId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          actionUserId: currentUser?.id,
          interviewDateTime: options.interviewDateTime,
          emailAction: options.emailAction,
          reasonType: options.reasonType,
          reasonDetails: options.reasonDetails,
          hiredStartDate: options.hiredStartDate,
        }),
      });
      return true;
    } catch (error) {
      setCandidates(previousCandidates);
      setTemporarilyVisibleCandidateIds((prev) => {
        if (!prev.has(candidateId)) return prev;

        const next = new Set(prev);
        next.delete(candidateId);
        return next;
      });
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update candidate status",
      );
      return false;
    }
  };

  // Handles view details.
  const handleViewDetails = (candidate: Candidate) => {
    const isOpening = expandedCandidate !== candidate.id;

    setExpandedCandidate((prev) =>
      prev === candidate.id ? null : candidate.id,
    );
    if (isOpening) {
      setJobHistoryPages((prev) => ({
        ...prev,
        [candidate.applicationId || candidate.id]: 1,
      }));
    }

    if (
      isOpening &&
      (candidate.status === "new" ||
        (candidate.status === "reviewed" && !candidate.assignedHrUserId))
    ) {
      updateCandidateStatus(candidate.id, "reviewed", {
        keepVisibleUntilRefresh: true,
      });
      toast.success(`${candidate.name} marked as reviewed`);
    }
  };

  // Handles toggle shortlist.
  const handleToggleShortlist = (candidate: Candidate) => {
    if (candidate.status === "rejected" || candidate.status === "withdrawn") return;

    const newStatus: CandidateStatus =
      candidate.isShortlisted
        ? "reviewed"
        : "shortlisted";

    updateCandidateStatus(candidate.id, newStatus, {
      keepVisibleUntilRefresh: true,
    });

    toast.success(
      newStatus === "shortlisted"
        ? `${candidate.name} shortlisted`
        : `${candidate.name} removed from shortlisted`,
    );
  };

  // Handles send interview email.
  const handleSendInterviewEmail = (candidate: Candidate) => {
    setInterviewPopupCandidate(candidate);
    setInterviewDateTime("");
  };

  // Closes interview email modal.
  const closeInterviewEmailModal = () => {
    setInterviewPopupCandidate(null);
    setInterviewDateTime("");
  };

  // Closes reject email modal.
  const closeRejectEmailModal = () => {
    setRejectPopupCandidate(null);
    setRejectEmailStep(1);
    setRejectReasonType("");
    setRejectReasonDetails("");
  };

  // Closes reason modal.
  const closeReasonModal = () => {
    setReasonPopupCandidate(null);
    setRejectReasonType("");
    setRejectReasonDetails("");
  };

  // Closes hire modal.
  const closeHireModal = () => {
    setHirePopupCandidate(null);
    setHireStartDate("");
    setHireDatePickerOpen(false);
  };

  // Handles confirm send interview email.
  const handleConfirmSendInterviewEmail = async () => {
    if (!interviewPopupCandidate) return;

    if (!interviewDateTime) {
      toast.error("Please select the interview date and time");
      return;
    }

    const candidateId = interviewPopupCandidate.id;
    setSendingEmailCandidateIds((prev) => {
      const next = new Set(prev);
      next.add(candidateId);
      return next;
    });

    const isSent = await updateCandidateStatus(candidateId, "interview", {
      interviewDateTime,
      emailAction: true,
    });

    setSendingEmailCandidateIds((prev) => {
      const next = new Set(prev);
      next.delete(candidateId);
      return next;
    });

    if (isSent) {
      toast.success(
        `Interview email sent to ${interviewPopupCandidate.name}`,
      );

      closeInterviewEmailModal();
    }
  };

  // Handles mark interviewed.
  const handleMarkInterviewed = async (candidate: Candidate) => {
    if (candidate.status === "interviewed" || !candidate.interviewSentAt) {
      return;
    }

    const isUpdated = await updateCandidateStatus(candidate.id, "interviewed", {
      keepVisibleUntilRefresh: true,
    });

    if (isUpdated) {
      toast.success(`${candidate.name} marked as interviewed`);
    }
  };

  // Handles hire candidate.
  const handleHireCandidate = (candidate: Candidate) => {
    if (candidate.status !== "interviewed" && candidate.status !== "hired") return;
    setHirePopupCandidate(candidate);
    setHireStartDate(candidate.hiredStartDate ?? "");
  };

  // Handles confirm hire candidate.
  const handleConfirmHireCandidate = async () => {
    if (!hirePopupCandidate) return;

    const candidate = hirePopupCandidate;
    const selectedStartDate = hireStartDate;
    closeHireModal();

    const isUpdated = await updateCandidateStatus(candidate.id, "hired", {
      hiredStartDate: selectedStartDate || null,
      keepVisibleUntilRefresh: true,
    });

    if (isUpdated) {
      toast.success(
        selectedStartDate
          ? `${candidate.name} start date saved`
          : `${candidate.name} marked as hired`,
      );
    } else {
      setHirePopupCandidate(candidate);
      setHireStartDate(selectedStartDate);
    }
  };

  // Handles reject candidate.
  const handleRejectCandidate = (candidate: Candidate) => {
    setRejectPopupCandidate(candidate);
    setSendRejectEmail(candidate.status === "hired" ? false : true);
    setRejectEmailStep(candidate.status === "hired" ? 2 : 1);
    setRejectReasonType("");
    setRejectReasonDetails("");
  };

  // Handles confirm reject candidate.
  const handleConfirmRejectCandidate = async () => {
    if (!rejectPopupCandidate) return;

    const candidate = rejectPopupCandidate;
    setSendingEmailCandidateIds((prev) => {
      const next = new Set(prev);
      next.add(candidate.id);
      return next;
    });

    const isSent = await updateCandidateStatus(candidate.id, "rejected", {
      emailAction: sendRejectEmail,
      reasonType: rejectReasonType,
      reasonDetails: rejectReasonDetails,
    });

    setSendingEmailCandidateIds((prev) => {
      const next = new Set(prev);
      next.delete(candidate.id);
      return next;
    });

    if (isSent) {
      toast.success(
        sendRejectEmail
          ? `Rejection email sent to ${candidate.name}`
          : `${candidate.name} rejected`,
      );
      closeRejectEmailModal();
    }
  };

  // Opens reason modal.
  const openReasonModal = (candidate: Candidate) => {
    setReasonPopupCandidate(candidate);
    setRejectReasonType(candidate.latestEmailReasonType || "");
    setRejectReasonDetails(
      candidate.latestEmailReasonDetails || "",
    );
  };

  // Handles save reason.
  const handleSaveReason = async () => {
    if (!reasonPopupCandidate?.applicationId) return;

    const currentUser = getStoredUser();
    const reasonType = rejectReasonType;
    const reasonDetails = rejectReasonDetails;

    try {
      await apiFetch(
        `/applications/${reasonPopupCandidate.applicationId}/reason`,
        {
          method: "PATCH",
          body: JSON.stringify({
            actionUserId: currentUser?.id,
            reasonType,
            reasonDetails,
          }),
        },
      );

      setCandidates((prev) =>
        prev.map((candidate) =>
          candidate.applicationId === reasonPopupCandidate.applicationId
            ? {
                ...candidate,
                latestEmailReasonType: reasonType || null,
                latestEmailReasonDetails: reasonDetails || null,
              }
            : candidate,
        ),
      );

      toast.success("Reason saved");
      closeReasonModal();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to save reason",
      );
    }
  };

  // Renders reason fields.
  const renderReasonFields = (
    reasonType: string,
    setReasonType: (value: string) => void,
    reasonDetails: string,
    setReasonDetails: (value: string) => void,
  ) => {
    const options = rejectionReasonTypes;
    const activeColor = "border-red-500";
    const activeDot = "bg-red-600";

    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">
            Reason Type
          </label>
          <div className="flex w-full flex-nowrap gap-1.5">
            {options.map((reason) => {
              const isSelected = reasonType === reason;

              return (
                <button
                  key={reason}
                  type="button"
                  className={`inline-flex h-9 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-full border px-2.5 py-0 text-xs font-medium leading-none transition-colors ${
                    isSelected
                      ? `${activeColor} bg-slate-50 text-slate-900`
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                  onClick={() =>
                    setReasonType(isSelected ? "" : reason)
                  }
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${
                      isSelected ? activeDot : "bg-slate-300"
                    }`}
                  />
                  {reason}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">
            Reason Details
          </label>
          <textarea
            rows={4}
            maxLength={500}
            placeholder="Enter details..."
            className="w-full rounded-md border border-input bg-white px-3 py-2 text-sm text-slate-700"
            value={reasonDetails}
            onChange={(event) => setReasonDetails(event.target.value)}
          />
          <p className="text-right text-xs text-slate-400">
            {reasonDetails.length}/500
          </p>
        </div>
      </div>
    );
  };

  const [documentCandidate, setDocumentCandidate] =
    useState<Candidate | null>(null);

  // Opens documents.
  const openDocuments = (candidate: Candidate) => {
    if (candidate.documents.length === 1) {
      window.open(candidate.documents[0].fileUrl, "_blank");
      return;
    }

    if (candidate.documents.length > 1) {
      setDocumentCandidate(candidate);
      return;
    }

    if (candidate.resumeUrl && candidate.resumeUrl !== "#") {
      window.open(candidate.resumeUrl, "_blank");
      return;
    }

    toast.error(`No uploaded documents found for ${candidate.name}`);
  };

  const formatProfileDuration = (durationMonths?: number | null) => {
    if (durationMonths === null || durationMonths === undefined || durationMonths <= 0) return "";
    if (durationMonths < 12) {
      return `${durationMonths} month${durationMonths === 1 ? "" : "s"}`;
    }
    const years = durationMonths / 12;
    return `${years.toFixed(1)} years`;
  };

  const getAnalysisStateMessage = (candidate: Candidate) => {
    if (candidate.analysisStatus === "failed" || candidate.resumeParsingStatus === "failed") {
      // State the persisted-data failure explicitly before explaining the
      // score fallback; HR should not mistake a zero for a valid assessment.
      return "Resume analysis failed. No parsed profile was persisted. No score was generated from the uploaded resume. The candidate is shown with a score of 0.";
    }

    if (candidate.analysisStatus === "completed" && candidate.resumeParsingStatus !== "parsed") {
      return "Analysis completed without a parsed resume profile.";
    }

    return "Resume profile is pending analysis.";
  };

  // Highlights factual candidate values inside the generated summary.
  const renderCandidateSummary = (candidate: Candidate) => {
    const summary = candidate.summary || getAnalysisStateMessage(candidate);
    if (!candidate.summary) return summary;

    const terms = [
      candidate.name,
      candidate.experience,
      candidate.education,
      candidate.cgpa,
      candidate.noticePeriod,
      candidate.country,
      candidate.currentLocation,
      ...(candidate.skills ?? []),
      ...(candidate.languages ?? []).flatMap((item) => [
        item.language,
        item.level,
        [item.language, item.level].filter(Boolean).join(" - "),
      ]),
    ]
      .flatMap((value) => String(value ?? "").split(/[;·]/))
      .map((value) => value.trim())
      .filter((value) => value.length > 2 && value !== "-");
    const uniqueTerms = Array.from(new Set(terms)).sort(
      (first, second) => second.length - first.length,
    );

    if (uniqueTerms.length === 0) return summary;

    const escapeRegExp = (value: string) =>
      value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = new RegExp(
      `(${uniqueTerms.map(escapeRegExp).join("|")})`,
      "gi",
    );

    return summary.split(pattern).map((part, index) => {
      const isHighlighted = uniqueTerms.some(
        (term) => term.toLowerCase() === part.toLowerCase(),
      );
      return isHighlighted ? (
        <strong key={`${candidate.id}-summary-${index}`} className="font-semibold text-slate-900">
          {part}
        </strong>
      ) : (
        part
      );
    });
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        {
          label: department,
          href: `/departments/${encodeURIComponent(department)}`,
        },
        { label: jobTitle, href: `/jobs/${jobId}` },
        { label: "Candidates" },
      ]}
      useCard={false}
    >
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          Candidates
        </h1>

        <div className="mt-2 flex items-center justify-between">
          <p className="text-lg text-[#1f4770]">{jobTitle}</p>

        </div>
      </div>

      <Card className="mb-6 shadow-sm">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by name or email..."
                  value={searchQuery}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck={false}
                  name="candidate-list-filter"
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    setSearchCandidateId("");
                  }}
                  onFocus={() => setSearchFocused(true)}
                  onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
                  className="pl-10 pr-10"
                />
                {searchQuery && (
                  <button
                    type="button"
                    aria-label="Clear search"
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      setSearchQuery("");
                      setSearchCandidateId("");
                      setSearchFocused(false);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                {searchFocused && candidateSearchSuggestions.length > 0 && (
                  <div className="absolute left-0 right-0 top-[44px] z-50 overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                    {candidateSearchSuggestions.map((candidate) => (
                      <button
                        key={candidate.applicationId || candidate.id}
                        type="button"
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-50"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => {
                          setSearchCandidateId(candidate.applicationId || candidate.id);
                          setSearchQuery(`${candidate.name} (${candidate.email})`);
                          setSearchFocused(false);
                        }}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-slate-950">{candidate.name}</span>
                          <span className="block truncate text-xs text-slate-500">{candidate.email}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <Select
                value={filterStatus}
                onValueChange={(value) => {
                  setFilterStatus(value);
                  setSearchCandidateId("");
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="reviewed">Reviewed</SelectItem>
                  <SelectItem value="shortlisted">Shortlisted</SelectItem>
                  <SelectItem value="interview">Interview</SelectItem>
                  <SelectItem value="interviewed">Interviewed</SelectItem>
                  <SelectItem value="hired">Hired</SelectItem>
                  <SelectItem value="filtered_out">Filtered Out</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="withdrawn">Withdrawn</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Select
                value={sortBy}
                onValueChange={(value) => setSortBy(value as CandidateSort)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rank">Best Rank</SelectItem>
                  <SelectItem value="score">Highest Score</SelectItem>
                  <SelectItem value="cgpa">Best CGPA</SelectItem>
                  <SelectItem value="date">Most Recent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoadingCandidates ? (
        <LoadingState title="Loading candidate data" />
      ) : (
        <>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="shadow-md">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-500">
              Total Candidates
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {candidates.length}
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
            <div className="text-2xl font-bold">
              {candidates.length === 0
                ? 0
                : Math.round(
                    candidates.reduce(
                      (sum, candidate) =>
                        sum + (candidate.score ?? 0),
                      0,
                    ) / candidates.length,
                  )}
            </div>
          </CardContent>
        </Card>

        <Tooltip>
          <TooltipTrigger asChild>
            <Card
              className="shadow-md cursor-pointer transition hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#003B7A]"
              role="button"
              tabIndex={0}
              onClick={() => applyStatusFilter("interview")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  applyStatusFilter("interview");
                }
              }}
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-500">
                  In Interview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {
                    candidates.filter(
                      (candidate) =>
                        Boolean(candidate.interviewSentAt) &&
                        candidate.status !== "hired" &&
                        candidate.status !== "rejected",
                    ).length
                  }
                </div>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            Click to filter interview candidates
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Card
              className="shadow-md cursor-pointer transition hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#003B7A]"
              role="button"
              tabIndex={0}
              onClick={() => applyStatusFilter("shortlisted")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  applyStatusFilter("shortlisted");
                }
              }}
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-500">
                  Shortlisted
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {
                    candidates.filter(
                      (candidate) => candidate.isShortlisted,
                    ).length
                  }
                </div>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            Click to filter shortlisted candidates
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="space-y-4">
        {pagedCandidates.map((candidate) => {
          const isShortlisted = candidate.isShortlisted;
          const hasInterviewSent = Boolean(
            candidate.interviewSentAt,
          );
          const isInterviewCompleted =
            candidate.status === "interviewed";
          const isEmailSending = sendingEmailCandidateIds.has(
            candidate.id,
          );
          const hasReason = Boolean(
            candidate.latestEmailReasonType ||
              candidate.latestEmailReasonDetails,
          );
          const jobHistory = candidate.appliedJobHistory ?? [];
          const jobHistoryPageKey =
            candidate.applicationId || candidate.id;
          const jobHistoryPageCount = Math.max(
            1,
            Math.ceil(jobHistory.length / JOB_HISTORY_PER_PAGE),
          );
          const jobHistoryPage = Math.min(
            jobHistoryPages[jobHistoryPageKey] ?? 1,
            jobHistoryPageCount,
          );
           const pagedJobHistory = jobHistory.slice(
             (jobHistoryPage - 1) * JOB_HISTORY_PER_PAGE,
             jobHistoryPage * JOB_HISTORY_PER_PAGE,
           );
           const profile = candidate.parsedProfile;
           const profileEducation = profile?.education ?? [];
           const profileExperience = profile?.experience ?? [];
           const profileSkills = profile?.skills ?? [];

           return (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              isExpanded={expandedCandidate === candidate.id}
              isShortlisted={isShortlisted}
              hasInterviewSent={hasInterviewSent}
              displayScore={getCandidateDisplayScore(candidate)}
              scorePercentage={getCandidateScorePercentage(candidate)}
              totalMaxScore={getTotalMaxScore()}
              scoreColor={getScoreColor(getCandidateScorePercentage(candidate))}
              onToggleShortlist={handleToggleShortlist}
              onEditHiredStartDate={handleHireCandidate}
              onOpenReason={openReasonModal}
            >
                  {expandedCandidate === candidate.id && (
                    <div className="pt-4 border-t border-slate-200 space-y-5">
                      {hasReason && (
                        <div>
                          <div className="mb-2 text-sm font-semibold text-slate-700">
                            Reason
                          </div>

                          <div className="grid grid-cols-1 gap-2">
                            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                              <div className="flex min-h-[42px] items-start justify-between gap-3">
                                <div className="min-w-0 self-center">
                                  {candidate.latestEmailReasonType && (
                                    <div className="text-sm font-semibold leading-snug text-slate-900">
                                      {candidate.latestEmailReasonType}
                                    </div>
                                  )}
                                  {candidate.latestEmailReasonDetails && (
                                    <p className="mt-0.5 text-xs leading-5 text-slate-500">
                                      {candidate.latestEmailReasonDetails}
                                    </p>
                                  )}
                                </div>
                                <button
                                  type="button"
                                  className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-slate-500 transition-colors hover:bg-white hover:text-[#003B7A]"
                                  onClick={() => openReasonModal(candidate)}
                                  aria-label="Edit reason"
                                  title="Edit reason"
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="mb-3 flex items-center gap-2">
                          <UserRound className="h-4 w-4 text-[#003B7A]" />
                          <div className="text-sm font-semibold text-slate-800">
                            Candidate Details
                          </div>
                        </div>

                        <div className="grid grid-cols-1 gap-x-6 gap-y-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4 md:grid-cols-2 lg:grid-cols-4">
                          {/* Eligibility is a decision-support result, separate from HR workflow status. */}
                          <div className="min-w-0 border-l-2 border-blue-100 pl-3">
                            <div className="text-xs font-medium text-slate-500">
                              Eligibility
                            </div>
                            <div className="mt-1">
                              <Badge className={getEligibilityStatusClass(candidate.eligibilityStatus)}>
                                {getEligibilityStatusLabel(candidate.eligibilityStatus)}
                              </Badge>
                            </div>
                          </div>

                          <div className="min-w-0 border-l-2 border-blue-100 pl-3">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <UserRound className="h-3.5 w-3.5 text-slate-400" />
                              Gender
                            </div>
                            <div className="mt-1 truncate text-sm font-semibold text-slate-900">
                              {candidate.gender || "-"}
                            </div>
                          </div>

                          <div className="min-w-0 border-l-2 border-blue-100 pl-3">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <MapPin className="h-3.5 w-3.5 text-slate-400" />
                              Location
                            </div>
                            <div className="mt-1 truncate text-sm font-semibold text-slate-900">
                              {[candidate.currentLocation, candidate.country]
                                .filter((value) => value && value !== "-")
                                .join(", ") || "-"}
                            </div>
                          </div>

                          <div className="min-w-0 border-l-2 border-blue-100 pl-3">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <Clock3 className="h-3.5 w-3.5 text-slate-400" />
                              Notice Period
                            </div>
                            <div className="mt-1 truncate text-sm font-semibold text-slate-900">
                              {candidate.noticePeriod || "-"}
                            </div>
                          </div>

                          <div className="min-w-0 border-l-2 border-blue-100 pl-3">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <Languages className="h-3.5 w-3.5 text-slate-400" />
                              Languages
                            </div>
                            <div className="mt-1 text-sm font-semibold leading-5 text-slate-900">
                              {candidate.languages?.length
                                ? candidate.languages
                                    .map((item) =>
                                      [item.language, item.level]
                                        .filter(Boolean)
                                        .join(" - "),
                                    )
                                    .join(", ")
                                : "-"}
                            </div>
                          </div>
                        </div>
                      </div>

                       <div className="hidden">
                         <div className="mb-2 text-sm font-semibold text-slate-700">
                           Parsed Resume Profile
                         </div>

                         {profile ? (
                           <div className="space-y-3">
                             {profile.profileSummary && (
                               <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700">
                                 {profile.profileSummary}
                               </div>
                             )}

                             <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
                               {profile.primaryDomain && (
                                 <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                                   <div className="text-xs font-medium text-slate-500">
                                     Primary Domain
                                   </div>
                                   <div className="mt-1 text-sm font-semibold text-slate-900">
                                     {profile.primaryDomain}
                                   </div>
                                 </div>
                               )}
                               {profile.highestEducationLevel && (
                                 <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                                   <div className="text-xs font-medium text-slate-500">
                                     Highest Education
                                   </div>
                                   <div className="mt-1 text-sm font-semibold text-slate-900">
                                     {profile.highestEducationLevel}
                                   </div>
                                 </div>
                               )}
                               {profile.cgpa !== null && profile.cgpa !== undefined && (
                                 <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                                   <div className="text-xs font-medium text-slate-500">
                                     CGPA
                                   </div>
                                   <div className="mt-1 text-sm font-semibold text-slate-900">
                                     {profile.cgpa}
                                   </div>
                                 </div>
                               )}
                               {profile.noticePeriod && (
                                 <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                                   <div className="text-xs font-medium text-slate-500">
                                     Notice Period
                                   </div>
                                   <div className="mt-1 text-sm font-semibold text-slate-900">
                                     {profile.noticePeriod}
                                   </div>
                                 </div>
                               )}
                             </div>

                             {profileSkills.length > 0 && (
                               <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                                 <div className="text-xs font-medium text-slate-500">
                                   Parsed Skills
                                 </div>
                                 <div className="mt-2 flex flex-wrap gap-2">
                                   {profileSkills.map((skill) => (
                                     <Badge
                                       key={`${candidate.id}-profile-skill-${skill.id}`}
                                       className="bg-white text-slate-700 ring-1 ring-slate-200"
                                     >
                                       {skill.name}
                                     </Badge>
                                   ))}
                                 </div>
                               </div>
                             )}

                             {profileEducation.length > 0 && (
                               <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                                 <div className="text-xs font-medium text-slate-500">
                                   Education Evidence
                                 </div>
                                 <div className="mt-2 space-y-2">
                                   {profileEducation.map((education, index) => (
                                     <div
                                       key={`${candidate.id}-education-${education.id || index}`}
                                       className="text-sm text-slate-700"
                                     >
                                       <div className="font-semibold text-slate-900">
                                         {education.rawQualification || education.qualification || education.level || "Education"}
                                       </div>
                                       <div>
                                         {[education.field, education.institution, education.graduationYear]
                                           .filter(Boolean)
                                           .join(" · ")}
                                       </div>
                                       {education.cgpa !== null && education.cgpa !== undefined && (
                                         <div className="text-xs text-slate-500">CGPA: {education.cgpa}</div>
                                       )}
                                     </div>
                                   ))}
                                 </div>
                               </div>
                             )}

                             {profileExperience.length > 0 && (
                               <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                                 <div className="text-xs font-medium text-slate-500">
                                   Work Experience Evidence
                                 </div>
                                 <div className="mt-2 space-y-3">
                                   {profileExperience.map((experience, index) => (
                                     <div
                                       key={`${candidate.id}-experience-${experience.id || index}`}
                                       className="text-sm text-slate-700"
                                     >
                                       <div className="font-semibold text-slate-900">
                                         {[experience.jobTitle, experience.company]
                                           .filter(Boolean)
                                           .join(" · ") || "Work experience"}
                                       </div>
                                       <div className="text-xs text-slate-500">
                                         {[experience.startDate, experience.isCurrent ? "Present" : experience.endDate]
                                           .filter(Boolean)
                                           .join(" - ")}
                                         {formatProfileDuration(experience.durationMonths)
                                           ? ` · ${formatProfileDuration(experience.durationMonths)}`
                                           : ""}
                                       </div>
                                       {experience.responsibilities?.length ? (
                                         <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-600">
                                           {experience.responsibilities.map((responsibility) => (
                                             <li key={`${candidate.id}-${experience.id}-${responsibility}`}>
                                               {responsibility}
                                             </li>
                                           ))}
                                         </ul>
                                       ) : null}
                                     </div>
                                   ))}
                                 </div>
                               </div>
                             )}
                           </div>
                         ) : (
                           <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
                             {getAnalysisStateMessage(candidate)}
                           </div>
                         )}
                       </div>

                       {candidate.questionAnswers?.length ? (
                        <div>
                          <div className="mb-2 text-sm font-semibold text-slate-700">
                            Application Questions
                          </div>
                          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                            {candidate.questionAnswers.map((item) => (
                              <div
                                key={item.questionId}
                                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5"
                              >
                                <div className="text-xs font-medium text-slate-500">
                                  {item.question}
                                </div>
                                <div className="mt-1 whitespace-pre-wrap text-sm font-semibold text-slate-900">
                                  {item.answer || "-"}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div>
                        <div className="font-medium mb-2 text-[22px] text-[#0f172b]">
                          Candidate Summary
                        </div>
                        <div className="text-slate-600 text-[15px] rounded-2xl border border-slate-200 bg-[#f5f9ff] p-5">
                          {renderCandidateSummary(candidate)}
                        </div>
                      </div>

                      {!isAnalysisProcessing(candidate.analysisStatus) && (
                        <CandidateScoreBreakdown
                          candidate={candidate}
                          displayScore={getCandidateDisplayScore(candidate)}
                          totalMaxScore={getTotalMaxScore()}
                        />
                      )}
                      {jobHistory.length > 0 && (
    <div>
      <div className="font-medium mb-2 text-[22px] text-[#0f172b]">
        Applied Job History
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="grid grid-cols-6 bg-[#f5f9ff] px-5 py-3 text-sm font-semibold text-slate-700">
          <div className="col-span-2">Job Title</div>
          <div>Submitted Date</div>
          <div>Score</div>
          <div>Rank</div>
          <div>Status</div>
        </div>

        {pagedJobHistory.map((job) => (
          <div
            key={`${candidate.id}-${job.historyKey}`}
            className="grid grid-cols-6 items-center border-t border-slate-200 px-5 py-4 text-sm"
          >
            <div className="col-span-2">
              <a
                href={`/jobs/${job.jobId}/candidates?candidateId=${candidate.id}`}
                className="font-semibold text-[#003B7A] hover:underline"
              >
                {job.jobTitle}
              </a>
              <p className="mt-1 text-xs text-slate-500">
                {job.department}
              </p>
            </div>

            <div className="font-semibold text-slate-800">
              {formatDisplayDate(job.submittedDate)}
            </div>

            <div className="font-semibold text-slate-800">
              {job.score}
            </div>

            <div className="font-semibold text-slate-800">
              {job.rank === null ? "-" : `#${job.rank}`}
            </div>

            <div>
              <Badge className={getCandidateStatusColor(job.status)}>
                {getCandidateStatusLabel(job.status)}
              </Badge>
            </div>
          </div>
        ))}
      </div>
      {jobHistory.length > JOB_HISTORY_PER_PAGE && (
        <Pagination className="mt-4">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(event) => {
                  event.preventDefault();
                  setJobHistoryPages((prev) => ({
                    ...prev,
                    [jobHistoryPageKey]: Math.max(
                      1,
                      jobHistoryPage - 1,
                    ),
                  }));
                }}
                className={
                  jobHistoryPage === 1
                    ? "pointer-events-none opacity-50"
                    : ""
                }
              />
            </PaginationItem>
            {getCompactPageItems(
              jobHistoryPage,
              jobHistoryPageCount,
            ).map((item) => {
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
                      isActive={jobHistoryPage === item}
                      onClick={(event) => {
                        event.preventDefault();
                        setJobHistoryPages((prev) => ({
                          ...prev,
                          [jobHistoryPageKey]: item,
                        }));
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
                  setJobHistoryPages((prev) => ({
                    ...prev,
                    [jobHistoryPageKey]: Math.min(
                      jobHistoryPageCount,
                      jobHistoryPage + 1,
                    ),
                  }));
                }}
                className={
                  jobHistoryPage === jobHistoryPageCount
                    ? "pointer-events-none opacity-50"
                    : ""
                }
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )}
                      <div>
                        <div className="mb-2 text-sm font-semibold text-slate-700">
                          Recruitment Handling
                        </div>

                        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <Users className="h-3.5 w-3.5 text-[#003B7A]" />
                              Responsible HR
                            </div>
                            <div className="mt-1 text-sm font-semibold text-slate-900">
                              {candidate.assignedHrName ||
                                "Not assigned"}
                            </div>
                          </div>

                          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                              <Mail className="h-3.5 w-3.5 text-[#003B7A]" />
                              Latest Email Sent By
                            </div>
                            <div className="mt-1 text-sm font-semibold text-slate-900">
                              {candidate.lastEmailSentBy ||
                                candidate.latestRejectActionBy ||
                                "Not sent yet"}
                            </div>
                            {(candidate.lastEmailSentBy ||
                              candidate.latestRejectActionBy) && (
                              <div className="mt-0.5 text-xs text-slate-500">
                                {candidate.lastEmailSentBy
                                  ? getEmailTypeLabel(
                                      candidate.lastEmailType,
                                    )
                                  : "Rejected without email"}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <CandidateActions
                    candidate={candidate}
                    isExpanded={expandedCandidate === candidate.id}
                    hasInterviewSent={hasInterviewSent}
                    isInterviewCompleted={isInterviewCompleted}
                    isEmailSending={isEmailSending}
                    onViewDetails={handleViewDetails}
                    onOpenDocuments={openDocuments}
                    onOpenEmploymentForm={openEmploymentForm}
                    onSendInterviewEmail={handleSendInterviewEmail}
                    onMarkInterviewed={handleMarkInterviewed}
                    onHireCandidate={handleHireCandidate}
                    onRejectCandidate={handleRejectCandidate}
                  />
            </CandidateCard>
          );
        })}

        {filteredCandidates.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <p className="text-slate-500">
                No candidates match your search criteria
              </p>
            </CardContent>
          </Card>
        )}
      </div>
      {filteredCandidates.length > CANDIDATES_PER_PAGE && (
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
        </>
      )}

      <Dialog
        open={Boolean(documentCandidate)}
        onOpenChange={(open) => {
          if (!open) setDocumentCandidate(null);
        }}
      >
        <DialogContent className="w-[calc(100vw-2rem)] max-w-xl overflow-hidden">
          <DialogHeader>
            <DialogTitle>Application Documents</DialogTitle>
            <DialogDescription>
              View all files uploaded by {documentCandidate?.name}.
            </DialogDescription>
          </DialogHeader>

          <div className="min-w-0 space-y-3 overflow-y-auto pr-1 sm:max-h-[60vh]">
            {documentCandidate?.documents.map((document) => (
              <div
                key={document.id}
                className="flex w-full min-w-0 items-center justify-between gap-3 rounded-lg border border-slate-200 p-4"
              >
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-blue-100">
                    <FileText className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {document.fileName}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {document.mimeType} ·{" "}
                      {(document.fileSize / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => window.open(document.fileUrl, "_blank")}
                >
                  Open
                </Button>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(hirePopupCandidate)}
        onOpenChange={(open) => {
          if (!open) closeHireModal();
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {hirePopupCandidate?.status === "hired" ? "Set Start Date" : "Hire Candidate"}
            </DialogTitle>
            <DialogDescription>
              {hirePopupCandidate?.status === "hired"
                ? `Select a start date for ${hirePopupCandidate?.name}.`
                : `Select a start date for ${hirePopupCandidate?.name}, or leave it blank to add later.`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <div className="text-sm font-medium text-slate-700">
              Start Date
            </div>
            <Popover
              open={hireDatePickerOpen}
              onOpenChange={setHireDatePickerOpen}
            >
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className="h-10 w-full justify-start bg-white px-3 text-left text-sm font-normal text-slate-95"
                  aria-label="Start date"
                >
                  <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                  {hireStartDate ? formatDisplayDate(hireStartDate) : "Select date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <DatePickerCalendar
                  mode="single"
                  defaultMonth={parseDateInputValue(hireStartDate)}
                  selected={parseDateInputValue(hireStartDate)}
                  onSelect={(date) => {
                    if (date) {
                      setHireStartDate(formatDateInputValue(date));
                      setHireDatePickerOpen(false);
                    }
                  }}
                  disabled={(date) =>
                    formatDateInputValue(date) < todayDateInputValue()
                  }
                  initialFocus
                />
              </PopoverContent>
            </Popover>
      
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
              onClick={handleConfirmHireCandidate}
            >
              {hirePopupCandidate?.status === "hired" ? "Confirm Start Date" : "Confirm Hire"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <CandidateEmailDialog
        jobTitle={jobTitle}
        interviewCandidate={interviewPopupCandidate}
        rejectCandidate={rejectPopupCandidate}
        reasonCandidate={reasonPopupCandidate}
        interviewDateTime={interviewDateTime}
        interviewEmailPreview={interviewPopupCandidate ? buildInterviewEmailPreview(interviewPopupCandidate) : null}
        sendRejectEmail={sendRejectEmail}
        rejectEmailStep={rejectEmailStep}
        rejectEmailPreview={rejectPopupCandidate ? buildRejectEmailPreview(rejectPopupCandidate) : null}
        rejectReasonType={rejectReasonType}
        rejectReasonDetails={rejectReasonDetails}
        sendingEmailCandidateIds={sendingEmailCandidateIds}
        renderReasonFields={renderReasonFields}
        onInterviewDateTimeChange={setInterviewDateTime}
        onSendRejectEmailChange={setSendRejectEmail}
        onRejectEmailStepChange={setRejectEmailStep}
        onRejectReasonTypeChange={setRejectReasonType}
        onRejectReasonDetailsChange={setRejectReasonDetails}
        onCloseInterview={closeInterviewEmailModal}
        onCloseReject={closeRejectEmailModal}
        onCloseReason={closeReasonModal}
        onConfirmInterview={handleConfirmSendInterviewEmail}
        onConfirmReject={handleConfirmRejectCandidate}
        onSaveReason={handleSaveReason}
      />
    </PageLayout>
  );
}
