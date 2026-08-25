// Shows the Candidate Actions view.
import { ChevronDown, ChevronUp, ClipboardList, FileText, Mail } from "lucide-react";
import type { Candidate } from "./CandidateCard";
import { Button } from "../ui/button";

interface CandidateActionsProps {
  candidate: Candidate;
  isExpanded: boolean;
  hasInterviewSent: boolean;
  isInterviewCompleted: boolean;
  isEmailSending: boolean;
  onViewDetails: (candidate: Candidate) => void;
  onOpenDocuments: (candidate: Candidate) => void;
  onOpenEmploymentForm: (candidate: Candidate) => void;
  onSendInterviewEmail: (candidate: Candidate) => void;
  onMarkInterviewed: (candidate: Candidate) => void;
  onHireCandidate: (candidate: Candidate) => void;
  onRejectCandidate: (candidate: Candidate) => void;
}

// Renders the Candidate Actions component.
export function CandidateActions({
  candidate,
  isExpanded,
  hasInterviewSent,
  isInterviewCompleted,
  isEmailSending,
  onViewDetails,
  onOpenDocuments,
  onOpenEmploymentForm,
  onSendInterviewEmail,
  onMarkInterviewed,
  onHireCandidate,
  onRejectCandidate,
}: CandidateActionsProps) {
  return (
    <div className="flex items-center justify-between pt-2">
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onViewDetails(candidate)}
        >
          {isExpanded ? (
            <>
              Show Less
              <ChevronUp className="w-4 h-4 ml-2" />
            </>
          ) : (
            <>
              View Details
              <ChevronDown className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onOpenDocuments(candidate)}
        >
          <FileText className="w-4 h-4 mr-2" />
          Resume
        </Button>

        {candidate.employmentFormSubmissionId && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenEmploymentForm(candidate)}
          >
            <ClipboardList className="w-4 h-4 mr-2" />
            Application Form
          </Button>
        )}
      </div>

      <div className="flex gap-2">
        {candidate.status !== "rejected" && candidate.status !== "withdrawn" && (
          <>
            {candidate.status !== "hired" && (
              isInterviewCompleted ? (
                <Button
                  variant="outline"
                  className="border-emerald-200 text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700 shadow-sm px-5"
                  onClick={() => onHireCandidate(candidate)}
                  disabled={isEmailSending}
                >
                  Hire Candidate
                </Button>
              ) : (
                <Button
                  className={`text-white shadow-sm px-5 ${
                    hasInterviewSent
                      ? "bg-sky-700 hover:bg-sky-800"
                      : "bg-[#003B7A] hover:bg-[#002f63]"
                  }`}
                  onClick={() => {
                    if (!hasInterviewSent) {
                      onSendInterviewEmail(candidate);
                      return;
                    }

                    onMarkInterviewed(candidate);
                  }}
                  disabled={
                    isEmailSending ||
                    candidate.status === "filtered_out"
                  }
                >
                  <Mail className="w-4 h-4 mr-2" />
                  {isEmailSending
                    ? "Sending..."
                    : hasInterviewSent
                      ? "Mark as Interviewed"
                      : "Send Interview Email"}
                </Button>
              )
            )}

            <Button
              variant="outline"
              className="border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 shadow-sm px-5"
              onClick={() => onRejectCandidate(candidate)}
              disabled={isEmailSending}
            >
              {isEmailSending ? "Sending..." : "Reject"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
