// Shows the Candidate Score Breakdown view.
import { ChevronDown, Info } from "lucide-react";
import type { Candidate } from "./CandidateCard";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";

interface CandidateScoreBreakdownProps {
  candidate: Candidate;
  displayScore: number | null;
  totalMaxScore: number;
}

// Renders the Candidate Score Breakdown component.
export function CandidateScoreBreakdown({
  candidate,
  displayScore,
  totalMaxScore,
}: CandidateScoreBreakdownProps) {
  return (
    <div className="pt-2">
      <div className="flex items-end justify-between mb-4">
        <h4 className="text-[22px] font-semibold text-slate-900">
          Score Breakdown
        </h4>

        <div className="text-right">
          <div className="flex items-center justify-end gap-1 text-sm text-slate-500">
            <span>Total Score</span>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center text-slate-400 hover:text-slate-600"
                  >
                    <Info className="w-4 h-4" />
                  </button>
                </TooltipTrigger>

                <TooltipContent
                  side="top"
                  className="max-w-[320px] text-sm leading-6"
                >
                  Total score and weighted contributions are read from the
                  persisted candidate scoring result. Criterion scores use the
                  backend&apos;s 0–10 scale.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div className="text-[20px] font-bold text-green-600 leading-none mt-1">
            {displayScore === null ? "—" : displayScore.toFixed(1)}
            {displayScore !== null && (
              <span className="text-slate-400 font-medium">
                {" "}
                / {totalMaxScore}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {candidate.scoreBreakdown.map((item, index) => (
          <div
            key={`${candidate.id}-${item.id}-${index}`}
            className="rounded-2xl border border-slate-200 bg-[#f5f9ff] p-5"
          >
            <div className="flex gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <h5 className="text-[18px] font-semibold text-slate-900">
                    Criteria {index + 1}: {item.title}
                  </h5>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 md:border-l md:border-slate-200/80 md:pl-4">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-medium text-slate-500">Weight</span>
                      <span className="text-sm font-semibold text-slate-900">{item.weight}%</span>
                    </div>

                    <span className="hidden h-4 w-px bg-slate-300 sm:block" aria-hidden="true" />

                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-medium text-slate-500">Criteria score</span>
                      <span className="text-sm font-semibold text-[#003B7A]">
                        {item.criteriaScore}<span className="font-medium text-slate-400"> / 10</span>
                      </span>
                    </div>

                    {item.weightedScore !== undefined && (
                      <>
                        <span className="hidden h-4 w-px bg-slate-300 sm:block" aria-hidden="true" />
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs font-medium text-slate-500">Mark</span>
                          <span className="text-sm font-semibold text-slate-900">
                            {item.weightedScore.toFixed(1)}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {item.criterionType && (
                  <p className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-400">
                    {item.criterionType.replace(/_/g, " ")}
                  </p>
                )}

                <p className="mt-4 text-[15px] text-slate-600">
                  <span className="font-semibold text-slate-900">
                    Score Justification:
                  </span>{" "}
                  {item.justification || "No persisted explanation is available."}
                </p>

                <details className="group mt-4 rounded-xl border border-slate-200 bg-white p-4">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-left [&::-webkit-details-marker]:hidden">
                    <span className="text-sm font-semibold text-slate-900">
                      Matched Resume Evidence
                    </span>
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      {item.matchLevel || "none"}
                      {item.grounded ? " · grounded" : ""}
                    </span>
                    <ChevronDown className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-180" aria-hidden="true" />
                  </summary>

                  {item.matchedEvidence.length > 0 ? (
                    <div className="mt-3 space-y-3">
                      {item.matchedEvidence.map((evidence) => (
                        <div
                          key={`${item.id}-${evidence.sourceId}`}
                          className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-3 text-sm"
                        >
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span className="font-semibold text-[#003B7A]">
                              {evidence.sourceId}
                            </span>
                            {evidence.sourceSection && (
                              <span className="text-xs font-medium text-slate-500">
                                {evidence.sourceSection}
                              </span>
                            )}
                          </div>
                          <p className="mt-2 break-words whitespace-pre-wrap text-sm leading-6 text-slate-600">
                            {evidence.sourceText}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-slate-500">
                      No matching resume evidence was persisted for this criterion.
                    </p>
                  )}
                </details>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
