// Shows the final job summary.
import { Button } from "../../ui/button";
import { Card, CardContent } from "../../ui/card";
import {
  AlignLeft,
  Banknote,
  BriefcaseBusiness,
  Building2,
  Filter,
  GraduationCap,
  Hash,
  Languages,
  List,
  LoaderCircle,
  MapPin,
  Timer,
  Type,
} from "lucide-react";
import type {
  JobData,
  Criteria,
  EligibilityFilters,
  ApplicationQuestion,
} from "../CreateJob";

interface Step3Props {
  jobData: JobData;
  applicationQuestions: ApplicationQuestion[];
  criteria: Criteria[];
  eligibilityFilters: EligibilityFilters;
  onBack: () => void;
  onPublish: () => void;
  isEditMode?: boolean;
  isSaving?: boolean;
}

// Renders the Step3 Review Confirm component.
export function Step3ReviewConfirm({
  jobData,
  applicationQuestions,
  criteria,
  eligibilityFilters,
  onBack,
  onPublish,
  isEditMode = false,
  isSaving = false,
}: Step3Props) {
  // Checks the eligibility enabled condition.
  const isEligibilityEnabled = (key: string) =>
    (eligibilityFilters.enabledFilters ?? []).includes(key);
  // Show only filters selected by HR.
  const enabledEligibilityItems = [
    isEligibilityEnabled("minCGPA")
      ? {
          key: "minCGPA",
          label: "Minimum CGPA",
          value: eligibilityFilters.minCGPA.toFixed(2),
          icon: GraduationCap,
        }
      : null,
    isEligibilityEnabled("minExperience")
      ? {
          key: "minExperience",
          label: "Minimum Experience",
          value: eligibilityFilters.minExperience,
          icon: BriefcaseBusiness,
        }
      : null,
    isEligibilityEnabled("educationLevel")
      ? {
          key: "educationLevel",
          label: "Education Level",
          value: eligibilityFilters.educationLevel,
          icon: GraduationCap,
        }
      : null,
    isEligibilityEnabled("maxNoticePeriod")
      ? {
          key: "maxNoticePeriod",
          label: "Maximum Notice Period",
          value: eligibilityFilters.maxNoticePeriod,
          icon: Timer,
        }
      : null,
    isEligibilityEnabled("requiredLanguage")
      ? {
          key: "requiredLanguage",
          label: "Required Language",
          value: eligibilityFilters.requiredLanguage,
          icon: Languages,
        }
      : null,
    isEligibilityEnabled("requiredLocation")
      ? {
          key: "requiredLocation",
          label: "Required Location",
          value: eligibilityFilters.requiredLocation,
          icon: MapPin,
        }
      : null,
    ...(eligibilityFilters.customFilters ?? [])
      .filter((filter) => isEligibilityEnabled(filter.id))
      .map((filter) => ({
        key: filter.id,
        label: filter.label,
        value: filter.value,
        icon: Filter,
      })),
  ].filter((item): item is NonNullable<typeof item> => item !== null);
  const questionFieldDetails = {
    text: { label: "Text", icon: Type },
    textarea: { label: "Long text", icon: AlignLeft },
    number: { label: "Number", icon: Hash },
    dropdown: { label: "Dropdown", icon: List },
  };

  // Handles publish.
  const handlePublish = () => {
    onPublish();
  };

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-semibold text-[#003B7A]">
        Setup Summary
      </h2>

      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
              <h3 className="text-sm font-semibold text-[#003B7A] mb-3">
                Job Details
              </h3>
              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-5">
                {[
                  {
                    label: "Job Title",
                    value: jobData.title,
                    icon: BriefcaseBusiness,
                  },
                  {
                    label: "Department",
                    value: jobData.department,
                    icon: Building2,
                  },
                  {
                    label: "Job Type",
                    value: jobData.employmentType,
                    icon: BriefcaseBusiness,
                  },
                  {
                    label: "Location",
                    value: jobData.location,
                    icon: MapPin,
                  },
                  {
                    label: "Salary Range",
                    value: jobData.salary,
                    icon: Banknote,
                    optional: true,
                  },
                ].map(({ label, value, icon: Icon, optional }) => (
                  <div key={label} className="min-w-0">
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 shrink-0 text-[#003B7A]" />
                      <span className="text-xs font-medium uppercase text-slate-500">
                        {label}
                      </span>
                      {optional && (
                        <span className="text-xs normal-case text-slate-400">
                          Optional
                        </span>
                      )}
                    </div>
                    <div className="mt-2 min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                      {value?.trim() || "-"}
                    </div>
                  </div>
                ))}
              </div>
        </CardContent>
      </Card>

      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-sm font-semibold text-[#003B7A]">
                  Candidate Questions
                </h3>
                <span className="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-[#003B7A]">
                  {applicationQuestions.length} {applicationQuestions.length === 1 ? "Question" : "Questions"}
                </span>
              </div>
              <div className="space-y-3 text-sm text-slate-700">
                {applicationQuestions.length > 0 ? (
                  applicationQuestions.map((question, index) => {
                    const fieldDetails = questionFieldDetails[question.fieldType];
                    const FieldIcon = fieldDetails.icon;

                    return (
                      <div
                        key={question.id}
                        className="grid min-h-16 items-center gap-3 rounded-md border border-blue-100 bg-slate-50/70 px-4 py-3 md:grid-cols-[40px_minmax(0,1fr)_140px_100px]"
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-[#003B7A]">
                          {index + 1}
                        </div>
                        <p className="min-w-0 font-medium text-slate-800">
                          {question.question}
                        </p>
                        <div className="flex items-center gap-2 border-slate-200 text-slate-600 md:border-l md:pl-5">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full border border-blue-300 text-[#003B7A]">
                            <FieldIcon className="h-3.5 w-3.5" />
                          </span>
                          <span>{fieldDetails.label}</span>
                        </div>
                        <span className={`w-fit rounded-full px-3 py-1 text-xs font-medium ${
                          question.required
                            ? "bg-blue-100 text-[#003B7A]"
                            : "bg-slate-200 text-slate-600"
                        }`}>
                          {question.required ? "Required" : "Optional"}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-slate-500">No additional candidate questions</p>
                )}
              </div>
        </CardContent>
      </Card>

      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
              <h3 className="text-sm font-semibold text-[#003B7A] mb-3">
                Eligibility Filters
              </h3>
              {enabledEligibilityItems.length > 0 ? (
                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {enabledEligibilityItems.map(({ key, label, value, icon: Icon }) => (
                    <div key={key} className="min-w-0">
                      <div className="flex items-center gap-3">
                        <Icon className="h-5 w-5 shrink-0 text-[#003B7A]" />
                        <span className="text-xs font-medium uppercase text-slate-500">
                          {label}
                        </span>
                      </div>
                      <div className="mt-2 min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                        {value?.trim() || "-"}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  No eligibility filters enabled
                </p>
              )}
        </CardContent>
      </Card>

      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
              <h3 className="text-sm font-semibold text-[#003B7A] mb-4">
                Criteria
              </h3>

              <div className="space-y-3">
                {criteria.map((criterion, index) => (
                  <div
                    key={criterion.id}
                    className="rounded-md border border-blue-100 bg-[#f3f3f5] p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-[#003B7A]">
                        Criteria {index + 1}
                      </span>

                      <span
                        className={`text-xs px-2 py-1 rounded border ${
                          criterion.isAutoDetected
                            ? "bg-blue-50 text-blue-600 border-blue-200"
                            : "bg-slate-100 text-slate-700 border-slate-200"
                        }`}
                      >
                        {criterion.isAutoDetected
                          ? "Auto-detected from JD"
                          : "Manual"}
                      </span>
                    </div>

                    <div className="space-y-1 text-sm text-slate-700">
                      <p>
                        <span className="font-medium">
                          Name:
                        </span>{" "}
                        {criterion.name}
                      </p>
                      <p>
                        <span className="font-medium">
                          Weight:
                        </span>{" "}
                        {criterion.weight}
                      </p>
                      <p>
                        <span className="font-medium">
                          Explanation:
                        </span>{" "}
                        {criterion.explanation || "-"}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between pt-4">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={isSaving}
          className="border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          Back to Edit
        </Button>

        <Button
          type="button"
          onClick={handlePublish}
          disabled={isSaving}
          className="bg-[#003B7A] hover:bg-[#002f63] px-8"
        >
          {isSaving && <LoaderCircle className="h-4 w-4 animate-spin" />}
          {isEditMode ? "Save Changes" : "Publish Job"}
        </Button>
      </div>
    </div>
  );
}
