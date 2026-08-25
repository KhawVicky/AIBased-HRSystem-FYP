// Shows the Candidate Card view.
import type { ReactNode } from "react";
import { Award, Calendar, Mail, Phone, Star, TrendingDown, TrendingUp } from "lucide-react";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "../ui/tooltip";
import { formatDisplayDate } from "../../lib/date";
import {
  isAnalysisProcessing as isProcessingAnalysis,
} from "../../lib/candidateData";
import type {
  Candidate,
  CandidateStatus,
  ScoreBreakdownItem,
} from "../../lib/candidateData";

export type {
  Candidate,
  CandidateStatus,
  CandidateDocument,
  ScoreBreakdownItem,
} from "../../lib/candidateData";

// Gets candidate status color.
export const getCandidateStatusColor = (status: string) => {
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

// Gets candidate status label.
export const getCandidateStatusLabel = (status: string) => {
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

interface CandidateCardProps {
  candidate: Candidate;
  isExpanded: boolean;
  isShortlisted: boolean;
  hasInterviewSent: boolean;
  displayScore: number | null;
  scorePercentage: number | null;
  totalMaxScore: number;
  scoreColor: string;
  onToggleShortlist: (candidate: Candidate) => void;
  onEditHiredStartDate: (candidate: Candidate) => void;
  onOpenReason: (candidate: Candidate) => void;
  children: ReactNode;
}

// Renders the Candidate Card component.
export function CandidateCard({
  candidate,
  isExpanded,
  isShortlisted,
  hasInterviewSent,
  displayScore,
  scorePercentage,
  totalMaxScore,
  scoreColor,
  onToggleShortlist,
  onEditHiredStartDate,
  onOpenReason,
  children,
}: CandidateCardProps) {
  const hasRejectionReason = Boolean(
    candidate.latestEmailReasonType || candidate.latestEmailReasonDetails,
  );
  const isFilteredOut = candidate.filteredOut || candidate.status === "filtered_out";
  const analysisStatus = candidate.analysisStatus?.toLowerCase() ?? "";
  const processing = isProcessingAnalysis(candidate.analysisStatus);
  const analysisFailed =
    analysisStatus === "failed" ||
    candidate.resumeParsingStatus?.toLowerCase() === "failed";
  const displayRank = processing ? null : candidate.rank;
  const visibleDisplayScore = processing
    ? null
    : analysisFailed
      ? 0
      : displayScore;
  const visibleScorePercentage = processing
    ? null
    : analysisFailed
      ? 0
      : scorePercentage;

  // Renders rejected badge.
  const renderRejectedBadge = () => (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={() => onOpenReason(candidate)}
          className="inline-flex rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
          aria-label={hasRejectionReason ? "Click to edit reason" : "Click to add reason"}
        >
          <Badge className={`${getCandidateStatusColor(candidate.status)} cursor-pointer hover:bg-red-700`}>
            {getCandidateStatusLabel(candidate.status)}
          </Badge>
        </button>
      </TooltipTrigger>
      <TooltipContent>
        {hasRejectionReason ? "Click to edit reason" : "Click to add reason"}
      </TooltipContent>
    </Tooltip>
  );

  return (
    <Card
      className={`shadow-md transition-all duration-200 ${
        isExpanded
          ? "shadow-lg border-[#cfd8e3]"
          : "hover:shadow-lg border-[#cfd8e3]"
      }`}
    >
      <CardContent className="p-6">
        <div className="space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4 flex-1">
              <Avatar className="w-12 h-12">
                <AvatarFallback className="bg-blue-600 text-white">
                  {candidate.name
                    .split(" ")
                    .map((namePart) => namePart[0])
                    .join("")}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{candidate.name}</h3>

                    {candidate.status !== "rejected" &&
                      candidate.status !== "hired" &&
                      candidate.status !== "withdrawn" && (
                        <button
                          type="button"
                          onClick={() => onToggleShortlist(candidate)}
                          className="inline-flex items-center justify-center"
                          title={
                            isShortlisted
                              ? "Remove from shortlisted"
                              : "Add to shortlisted"
                          }
                        >
                          <Star
                            className={`w-4 h-4 transition-colors ${
                              isShortlisted
                                ? "text-yellow-500 fill-yellow-500"
                                : "text-slate-300 hover:text-yellow-500"
                            }`}
                          />
                        </button>
                      )}
                  </div>

                  {candidate.status === "hired" ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          onClick={() => onEditHiredStartDate(candidate)}
                          className="inline-flex rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
                          aria-label={
                            candidate.hiredStartDate
                              ? "Click to edit start date"
                              : "Click to set start date"
                          }
                        >
                          <Badge className="cursor-pointer bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100 hover:bg-emerald-100">
                            {candidate.hiredStartDate
                              ? `HIRED - ${formatDisplayDate(candidate.hiredStartDate)}`
                              : getCandidateStatusLabel(candidate.status)}
                          </Badge>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        {candidate.hiredStartDate
                          ? "Click to edit start date"
                          : "Click to set start date"}
                      </TooltipContent>
                    </Tooltip>
                  ) : candidate.status === "rejected" && candidate.wasHired ? (
                    <>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge className="bg-slate-100 text-slate-600 ring-1 ring-slate-200">
                            {candidate.hiredStartDate
                              ? `HIRED - ${formatDisplayDate(candidate.hiredStartDate)}`
                              : "HIRED"}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent>
                          Previously hired
                        </TooltipContent>
                      </Tooltip>
                      {renderRejectedBadge()}
                    </>
                  ) : candidate.status === "rejected" ? (
                    renderRejectedBadge()
                  ) : (
                    <Badge className={getCandidateStatusColor(candidate.status)}>
                      {getCandidateStatusLabel(candidate.status)}
                    </Badge>
                  )}
                  {isFilteredOut && candidate.status !== "filtered_out" && (
                    <Badge className="bg-slate-100 text-slate-600 ring-1 ring-slate-200">
                      {getCandidateStatusLabel("filtered_out")}
                    </Badge>
                  )}
                  {isShortlisted &&
                    candidate.status !== "shortlisted" &&
                    candidate.status !== "rejected" &&
                    candidate.status !== "hired" &&
                    candidate.status !== "withdrawn" && (
                      <Badge className="bg-amber-500">SHORTLISTED</Badge>
                    )}
                  {hasInterviewSent &&
                    candidate.status !== "interview" &&
                    candidate.status !== "interviewed" &&
                    candidate.status !== "hired" &&
                    candidate.status !== "rejected" && (
                      <Badge className="bg-blue-600">INTERVIEW</Badge>
                    )}
                  {processing && (
                    <Badge className="bg-blue-50 text-blue-700 ring-1 ring-blue-100">
                      PROCESSING
                    </Badge>
                  )}
                  {candidate.currentSubmissionNo > 1 && (
                    <Badge className="bg-slate-600">
                      {getCandidateStatusLabel(candidate.currentSubmissionLabel)}
                    </Badge>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-slate-600">
                  <div className="flex min-w-0 items-start gap-1">
                    <Mail className="mt-0.5 h-3 w-3 shrink-0" />
                    <span className="min-w-0 break-all">{candidate.email}</span>
                  </div>

                  <div className="flex min-w-0 items-start gap-1">
                    <Phone className="mt-0.5 h-3 w-3 shrink-0" />
                    <span className="min-w-0 break-words">{candidate.phone}</span>
                  </div>

                  <div className="flex min-w-0 items-start gap-1">
                    <Calendar className="mt-0.5 h-3 w-3 shrink-0" />
                    <span>{formatDisplayDate(candidate.appliedDate)}</span>
                  </div>

                  {candidate.experience && (
                    <div className="flex min-w-0 items-start gap-1">
                      <Award className="mt-0.5 h-3 w-3 shrink-0" />
                      <span className="min-w-0 break-words">{candidate.experience} experience</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-6">
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">RANK</div>
                <div className="flex items-center gap-1">
                  <span className="text-2xl font-bold">
                    {isFilteredOut ||
                    candidate.status === "rejected" ||
                    candidate.status === "hired" ||
                    candidate.status === "withdrawn" ||
                    displayRank === null
                      ? "-"
                      : `#${displayRank}`}
                  </span>
                  {!isFilteredOut &&
                    candidate.status !== "rejected" &&
                    candidate.status !== "hired" &&
                    candidate.status !== "withdrawn" &&
                    displayRank !== null &&
                    displayRank <= 3 && (
                      <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    )}
                </div>
              </div>

              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">SCORE</div>

                <div className="flex items-center justify-center gap-1">
                  <span className={`text-2xl font-bold ${scoreColor}`}>
                    {visibleDisplayScore === null
                      ? "-"
                      : visibleDisplayScore.toFixed(1)}
                  </span>

                  {!analysisFailed && visibleScorePercentage !== null && visibleScorePercentage >= 90 ? (
                    <TrendingUp className="w-4 h-4 text-green-600" />
                  ) : !analysisFailed && visibleScorePercentage !== null && visibleScorePercentage < 75 ? (
                    <TrendingDown className="w-4 h-4 text-red-600" />
                  ) : null}
                </div>

                {visibleDisplayScore !== null && (
                  <div className="mt-1 text-xs text-slate-400">
                    / {totalMaxScore}
                  </div>
                )}
              </div>
            </div>
          </div>

          {children}
        </div>
      </CardContent>
    </Card>
  );
}
