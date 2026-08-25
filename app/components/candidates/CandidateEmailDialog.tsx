// Shows the Candidate Email Dialog view.
import { useEffect, useState } from "react";
import { Calendar as CalendarIcon, Clock, X } from "lucide-react";
import { Button } from "../ui/button";
import { Calendar as DatePickerCalendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { toast } from "sonner";
import type { Candidate } from "./CandidateCard";

// Formats short date.
const formatShortDate = (date: Date) => {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${date.getFullYear()}`;
};

// Formats date input value.
const formatDateInputValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

// Provides the today date input value helper.
const todayDateInputValue = () => formatDateInputValue(new Date());

// Checks the past date condition.
const isPastDate = (date: Date) => formatDateInputValue(date) < todayDateInputValue();

// Formats display time.
const formatDisplayTime = (time: string) => {
  if (!time) return "";
  const [hourText, minuteText = "00"] = time.split(":");
  const hour = Number(hourText);
  if (Number.isNaN(hour)) return time;
  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${minuteText} ${period}`;
};

// Parses interview date time.
const parseInterviewDateTime = (value: string) => {
  const match = value.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:,\s*(\d{1,2}):(\d{2})\s*(AM|PM)?)?/i);
  if (!match) return { date: undefined as Date | undefined, time: "" };

  const [, dayText, monthText, yearText, hourText, minuteText, periodText] = match;
  const day = Number(dayText);
  const month = Number(monthText);
  const year = Number(yearText);
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) return { date: undefined as Date | undefined, time: "" };

  if (!hourText || !minuteText) return { date, time: "" };

  let hour = Number(hourText);
  const minute = Number(minuteText);
  const period = periodText?.toUpperCase();
  if (period === "PM" && hour < 12) hour += 12;
  if (period === "AM" && hour === 12) hour = 0;

  return {
    date,
    time: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
  };
};

// Builds interview date time.
const buildInterviewDateTime = (date: Date | undefined, time: string) => {
  if (!date) return "";
  const displayDate = formatShortDate(date);
  const displayTime = formatDisplayTime(time);
  return displayTime ? `${displayDate}, ${displayTime}` : displayDate;
};

// Parses interview options.
const parseInterviewOptions = (value: string) =>
  value
    .split(/\s+\/\s+/)
    .map((option) => {
      const parsed = parseInterviewDateTime(option.trim());
      return parsed.date
        ? {
            ...parsed,
            label: buildInterviewDateTime(parsed.date, parsed.time),
          }
        : null;
    })
    .filter(
      (option): option is { date: Date; time: string; label: string } =>
        Boolean(option?.label),
    );

// Provides the sort interview options helper.
const sortInterviewOptions = (
  options: { date: Date; time: string; label: string }[],
) =>
  [...options].sort((first, second) => {
    const firstDate = new Date(first.date);
    const secondDate = new Date(second.date);
    const [firstHour = "0", firstMinute = "0"] = first.time.split(":");
    const [secondHour = "0", secondMinute = "0"] = second.time.split(":");
    firstDate.setHours(Number(firstHour), Number(firstMinute), 0, 0);
    secondDate.setHours(Number(secondHour), Number(secondMinute), 0, 0);
    return firstDate.getTime() - secondDate.getTime();
  });

const TIME_OPTIONS = Array.from({ length: 25 }, (_, index) => {
  const hour = 8 + Math.floor(index / 2);
  const minute = index % 2 === 0 ? "00" : "30";
  const value = `${String(hour).padStart(2, "0")}:${minute}`;
  return { value, label: formatDisplayTime(value) };
});

interface CandidateEmailDialogProps {
  jobTitle: string;
  interviewCandidate: Candidate | null;
  rejectCandidate: Candidate | null;
  reasonCandidate: Candidate | null;
  interviewDateTime: string;
  interviewEmailPreview: { subject: string; body: string } | null;
  sendRejectEmail: boolean;
  rejectEmailStep: 1 | 2;
  rejectEmailPreview: { subject: string; body: string } | null;
  rejectReasonType: string;
  rejectReasonDetails: string;
  sendingEmailCandidateIds: Set<string>;
  renderReasonFields: (
    reasonType: string,
    setReasonType: (value: string) => void,
    reasonDetails: string,
    setReasonDetails: (value: string) => void,
  ) => React.ReactNode;
  onInterviewDateTimeChange: (value: string) => void;
  onSendRejectEmailChange: (value: boolean) => void;
  onRejectEmailStepChange: (value: 1 | 2) => void;
  onRejectReasonTypeChange: (value: string) => void;
  onRejectReasonDetailsChange: (value: string) => void;
  onCloseInterview: () => void;
  onCloseReject: () => void;
  onCloseReason: () => void;
  onConfirmInterview: () => void;
  onConfirmReject: () => void;
  onSaveReason: () => void;
}

// Renders the Candidate Email Dialog component.
export function CandidateEmailDialog({
  jobTitle,
  interviewCandidate,
  rejectCandidate,
  reasonCandidate,
  interviewDateTime,
  interviewEmailPreview,
  sendRejectEmail,
  rejectEmailStep,
  rejectEmailPreview,
  rejectReasonType,
  rejectReasonDetails,
  sendingEmailCandidateIds,
  renderReasonFields,
  onInterviewDateTimeChange,
  onSendRejectEmailChange,
  onRejectEmailStepChange,
  onRejectReasonTypeChange,
  onRejectReasonDetailsChange,
  onCloseInterview,
  onCloseReject,
  onCloseReason,
  onConfirmInterview,
  onConfirmReject,
  onSaveReason,
}: CandidateEmailDialogProps) {
  const [interviewDatePickerOpen, setInterviewDatePickerOpen] = useState(false);
  const [draftInterviewDate, setDraftInterviewDate] = useState<Date | undefined>();
  const [draftInterviewTime, setDraftInterviewTime] = useState("");
  const interviewOptions = parseInterviewOptions(interviewDateTime);

  useEffect(() => {
    if (!interviewCandidate) return;

    const firstOption = parseInterviewOptions(interviewDateTime)[0];
    setDraftInterviewDate(firstOption?.date);
    setDraftInterviewTime(firstOption?.time ?? "");
    setInterviewDatePickerOpen(false);
  }, [interviewCandidate?.id]);

  // Adds interview option.
  const addInterviewOption = () => {
    const nextOption = buildInterviewDateTime(draftInterviewDate, draftInterviewTime);
    if (!nextOption || !draftInterviewDate) return;

    if (isPastDate(draftInterviewDate)) {
      toast.error("Please select today or a future interview date.");
      return;
    }

    const optionLabels = interviewOptions.map((option) => option.label);
    if (optionLabels.includes(nextOption)) {
      toast.error("This interview date and time has already been added.");
      return;
    }

    const sortedOptions = sortInterviewOptions([
      ...interviewOptions,
      {
        date: draftInterviewDate,
        time: draftInterviewTime,
        label: nextOption,
      },
    ]);

    onInterviewDateTimeChange(sortedOptions.map((option) => option.label).join(" / "));
  };

  // Removes interview option.
  const removeInterviewOption = (optionToRemove: string) => {
    onInterviewDateTimeChange(
      sortInterviewOptions(interviewOptions)
        .filter((option) => option.label !== optionToRemove)
        .map((option) => option.label)
        .join(" / "),
    );
  };

  return (
    <>
      {interviewCandidate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={onCloseInterview}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Interview Email Preview
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Review the draft email and enter the interview date and time
                    before sending.
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-full p-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                  onClick={onCloseInterview}
                  aria-label="Close"
                  title="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="uwc-scrollbar-hidden flex-1 space-y-5 overflow-y-auto px-6 py-5">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">
                  Interview Date and Time *
                </label>
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                  <Popover
                    open={interviewDatePickerOpen}
                    onOpenChange={setInterviewDatePickerOpen}
                  >
                    <PopoverTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        className="!h-11 justify-start gap-3 rounded-md border-slate-200 bg-slate-100 px-4 py-0 text-left font-normal leading-none text-slate-900 shadow-none hover:bg-slate-100"
                      >
                        <CalendarIcon className="h-4 w-4 text-slate-500" />
                        {draftInterviewDate
                          ? formatShortDate(draftInterviewDate)
                          : "Select interview date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent align="start" className="w-auto p-0">
                      <DatePickerCalendar
                        mode="single"
                        defaultMonth={draftInterviewDate}
                        selected={draftInterviewDate}
                        disabled={isPastDate}
                        onSelect={(date) => {
                          setDraftInterviewDate(date);
                          setInterviewDatePickerOpen(false);
                        }}
                      />
                    </PopoverContent>
                  </Popover>

                  <Select
                    value={draftInterviewTime}
                    onValueChange={setDraftInterviewTime}
                    disabled={!draftInterviewDate}
                  >
                    <SelectTrigger className="!h-11 rounded-md border-slate-200 bg-slate-100 px-4 py-0 leading-none shadow-none hover:bg-slate-100">
                      <div className="flex items-center gap-3">
                        <Clock className="h-4 w-4 text-slate-500" />
                        <SelectValue placeholder="Select time" />
                      </div>
                    </SelectTrigger>
                    <SelectContent className="max-h-64">
                      {TIME_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Button
                    type="button"
                    variant="outline"
                    className="!h-11 rounded-md px-5 py-0 leading-none shadow-none"
                    disabled={!draftInterviewDate || !draftInterviewTime || isPastDate(draftInterviewDate)}
                    onClick={addInterviewOption}
                  >
                    Add
                  </Button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {sortInterviewOptions(interviewOptions).map((option) => (
                    <span
                      key={option.label}
                      className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-[#003B7A]"
                    >
                      {option.label}
                      <button
                        type="button"
                        className="rounded-full p-0.5 text-[#003B7A] transition-colors hover:bg-blue-100"
                        onClick={() => removeInterviewOption(option.label)}
                        aria-label={`Remove ${option.label}`}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">
                  Message
                </label>
                <textarea
                  readOnly
                  rows={13}
                  className="uwc-scrollbar-hidden w-full rounded-md border border-input bg-slate-50 px-3 py-2 text-sm text-slate-700"
                  value={`Subject: ${
                    interviewEmailPreview?.subject ||
                    `Interview invitation for ${jobTitle}`
                  }\n\n${interviewEmailPreview?.body || ""}`}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4">
              <Button
                type="button"
                variant="outline"
                disabled={sendingEmailCandidateIds.has(interviewCandidate.id)}
                onClick={onCloseInterview}
              >
                Cancel
              </Button>

              <Button
                type="button"
                className="bg-[#003B7A] hover:bg-[#002f63] text-white"
                disabled={sendingEmailCandidateIds.has(interviewCandidate.id)}
                onClick={onConfirmInterview}
              >
                {sendingEmailCandidateIds.has(interviewCandidate.id)
                  ? "Sending..."
                  : "Send Email"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {rejectCandidate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={onCloseReject}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    {rejectEmailStep === 1
                      ? "Rejection Email Preview"
                      : "Provide Reason"}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {rejectEmailStep === 1
                      ? "Review the rejection action before confirming."
                      : "Please provide a reason for rejecting this candidate."}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-full p-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                  onClick={onCloseReject}
                  aria-label="Close"
                  title="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
              {rejectEmailStep === 1 ? (
                <>
                  <div className="flex items-center gap-2">
                    <input
                      id="sendRejectEmail"
                      type="checkbox"
                      checked={sendRejectEmail}
                      onChange={(event) =>
                        onSendRejectEmailChange(event.target.checked)
                      }
                      className="h-4 w-4 rounded border-slate-300"
                    />
                    <label
                      htmlFor="sendRejectEmail"
                      className="text-sm font-medium text-slate-700"
                    >
                      Send rejection email to candidate
                    </label>
                  </div>

                  {sendRejectEmail && rejectEmailPreview && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-slate-700">
                        Message
                      </label>
                      <textarea
                        readOnly
                        rows={11}
                        className="w-full rounded-md border border-input bg-slate-50 px-3 py-2 text-sm text-slate-700"
                        value={`Subject: ${rejectEmailPreview.subject}\n\n${rejectEmailPreview.body}`}
                      />
                    </div>
                  )}
                </>
              ) : (
                renderReasonFields(
                  rejectReasonType,
                  onRejectReasonTypeChange,
                  rejectReasonDetails,
                  onRejectReasonDetailsChange,
                )
              )}
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4">
              {rejectEmailStep === 2 && rejectCandidate.status !== "hired" && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={sendingEmailCandidateIds.has(rejectCandidate.id)}
                  onClick={() => onRejectEmailStepChange(1)}
                >
                  Back
                </Button>
              )}

              <Button
                type="button"
                className="bg-red-600 text-white hover:bg-red-700"
                disabled={sendingEmailCandidateIds.has(rejectCandidate.id)}
                onClick={
                  rejectEmailStep === 1
                    ? () => onRejectEmailStepChange(2)
                    : onConfirmReject
                }
              >
                {sendingEmailCandidateIds.has(rejectCandidate.id)
                  ? "Sending..."
                  : rejectEmailStep === 1
                    ? "Next"
                    : sendRejectEmail
                      ? "Send Email"
                      : "Confirm Reject"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {reasonCandidate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={onCloseReason}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Add Reason
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Add an optional reason for the latest email action.
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-full p-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                  onClick={onCloseReason}
                  aria-label="Close"
                  title="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              {renderReasonFields(
                rejectReasonType,
                onRejectReasonTypeChange,
                rejectReasonDetails,
                onRejectReasonDetailsChange,
              )}
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4">
              <Button type="button" variant="outline" onClick={onCloseReason}>
                Cancel
              </Button>
              <Button
                type="button"
                className="bg-red-600 text-white hover:bg-red-700"
                onClick={onSaveReason}
              >
                Save Reason
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
