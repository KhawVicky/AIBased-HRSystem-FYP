// Shows the Create Job view.
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  useLocation,
  useNavigate,
  useParams,
} from "react-router";
import { PageLayout } from "../shared/PageLayout";
import { Step1UploadJD } from "./create-job/Step1UploadJD";
import { Step2ApplicationQuestions } from "./create-job/Step2ApplicationQuestions";
import { Step2SetCriteria } from "./create-job/Step2SetCriteria";
import { Step3ReviewConfirm } from "./create-job/Step3ReviewConfirm";
import { JobCreationStepper } from "./create-job/JobCreationStepper";
import type {
  JDCriterionType,
  ParsedJDData,
} from "../../lib/jdParsingApi";
import { apiFetch, getStoredUser } from "../../lib/api";

export interface JobData {
  title: string;
  department: string;
  employmentType: "Full-time" | "Part-time" | "Internship";
  employmentTypeManuallySet?: boolean;
  salary: string;
  location: string;
  description: string;
  jdFile: File | null;
  savedJdFileName: string | null;
  savedJdFilePath: string | null;
  parsedJD: ParsedJDData | null;
}

export interface Criteria {
  id: string;
  category?: string;
  type: JDCriterionType;
  name: string;
  weight: number;
  status: "active" | "inactive";
  sourceText: string;
  evidenceRule?: string;
  jdEvidence?: string[];
  explanation: string;
  resumeEvidenceToCheck?: string;
  isAutoDetected: boolean;
}

export interface ApplicationQuestion {
  id: string;
  question: string;
  fieldType: "text" | "textarea" | "number" | "dropdown";
  required: boolean;
  options: string[];
}

export interface CustomEligibilityFilter {
  id: string;
  label: string;
  value: string;
}

export interface EligibilityFilterDefinition {
  id: number;
  filterKey: string;
  filterName: string;
  filterType: "dropdown" | "text" | "number";
  options: string[];
  isSystem: boolean;
  sortOrder: number;
}

export interface EligibilityFilters {
  minCGPA: number;
  minExperience: string;
  educationLevel: string;
  maxNoticePeriod: string;
  requiredLanguage: string;
  requiredLocation: string;
  customFilters: CustomEligibilityFilter[];
  enabledFilters: string[];
}

// These values are shared by the criteria and review steps.
const defaultEligibilityFilters: EligibilityFilters = {
  minCGPA: 0,
  minExperience: "",
  educationLevel: "",
  maxNoticePeriod: "",
  requiredLanguage: "",
  requiredLocation: "",
  customFilters: [],
  enabledFilters: [],
};

const systemEligibilityKeys = new Set([
  "minCGPA",
  "minExperience",
  "educationLevel",
  "maxNoticePeriod",
  "requiredLanguage",
  "requiredLocation",
]);

// Provides the restored eligibility filters helper.
function restoredEligibilityFilters(
  values?: {
    filterKey: string;
    filterLabel: string;
    filterValue: string;
  }[],
): EligibilityFilters {
  // Build the form state from values saved in the database.
  if (!values?.length) return defaultEligibilityFilters;

  const restored: EligibilityFilters = {
    ...defaultEligibilityFilters,
    customFilters: [],
    enabledFilters: [],
  };
  values.forEach(({ filterKey, filterLabel, filterValue }) => {
    if (filterKey === "internshipAccepted") return;
    restored.enabledFilters.push(filterKey);
    if (systemEligibilityKeys.has(filterKey)) {
      if (filterKey === "minCGPA") {
        restored.minCGPA = Number(filterValue) || 0;
      } else {
        (restored as unknown as Record<string, string>)[filterKey] = filterValue;
      }
    } else {
      restored.customFilters.push({
        id: filterKey,
        label: filterLabel,
        value: filterValue,
      });
    }
  });
  return restored;
}

// Renders the Create Job component.
export function CreateJob() {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId } = useParams();

  const editingJob = location.state?.job;
  const isEditMode = Boolean(jobId && editingJob);

  const [currentStep, setCurrentStep] = useState(1);
  const [persistedJobId, setPersistedJobId] = useState<number | null>(
    jobId ? Number(jobId) : null,
  );
  const [isSaving, setIsSaving] = useState(false);
  const [autoSaveState, setAutoSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [lastAutoSavedAt, setLastAutoSavedAt] = useState<string | null>(null);
  const skipInitialAutoSave = useRef(isEditMode);
  const autoSaveInFlight = useRef(false);
  const autoSaveQueued = useRef(false);
  const [autoSaveRevision, setAutoSaveRevision] = useState(0);

  const existingResponsibilities =
    editingJob?.responsibilities?.map(
      (item: { responsibility: string }) => item.responsibility,
    ) || [];
  const existingQualifications =
    editingJob?.qualifications?.map(
      (item: { qualification: string }) => item.qualification,
    ) || [];

  // Keep all Create Job steps in one shared state.
  const [jobData, setJobData] = useState<JobData>({
    title: editingJob?.title || "",
    department: editingJob?.department || "",
    employmentType:
      editingJob?.employmentType === "Part-time"
        ? "Part-time"
        : editingJob?.employmentType === "Internship"
          ? "Internship"
          : "Full-time",
    employmentTypeManuallySet: Boolean(editingJob?.employmentType),
    salary: editingJob?.salaryRange || "",
    location: editingJob?.location || "Batu Kawan, Penang",
    description: editingJob?.description || "",
    jdFile: null,
    savedJdFileName: editingJob?.jdFileName || null,
    savedJdFilePath: editingJob?.jdFilePath || null,
    parsedJD: editingJob
      ? {
          sheetName: editingJob.jdFileName || "Existing job description",
          jobTitle: editingJob.title || "",
          department: editingJob.department || "",
          salary: editingJob.salaryRange || "",
          description: editingJob.description || "",
          responsibilities: existingResponsibilities,
          qualifications: existingQualifications,
          requirements: [...existingQualifications],
          rawText: editingJob.description || "",
        }
      : null,
  });

  const [criteria, setCriteria] = useState<Criteria[]>(
    editingJob?.criteria?.map(
      (criterion: {
        id: number;
        type?: JDCriterionType;
        name: string;
        weight: number | string;
        description?: string | null;
        sourceText?: string | null;
        evidenceRule?: string | null;
        isActive?: number | boolean;
      }) => ({
        id: String(criterion.id),
        category: criterion.type || "relevant_skill",
        type: criterion.type || "relevant_skill",
        name: criterion.name,
        weight: Number(criterion.weight),
        status: criterion.isActive === 0 ? "inactive" : "active",
        sourceText: criterion.sourceText || "",
        evidenceRule: criterion.evidenceRule || undefined,
        explanation: criterion.description || "",
        isAutoDetected: false,
      }),
    ) || [],
  );

  const [applicationQuestions, setApplicationQuestions] = useState<
    ApplicationQuestion[]
  >(
    editingJob?.applicationQuestions?.map(
      (question: {
        id: number;
        question: string;
        fieldType: ApplicationQuestion["fieldType"];
        required: boolean;
        options: string[];
      }) => ({
        id: String(question.id),
        question: question.question,
        fieldType: question.fieldType,
        required: Boolean(question.required),
        options: question.options || [],
      }),
    ) || [],
  );

  const [eligibilityFilters, setEligibilityFilters] =
    useState<EligibilityFilters>(
      restoredEligibilityFilters(editingJob?.eligibilityValues),
    );
  const [criteriaGenerationSource, setCriteriaGenerationSource] =
    useState<string | null>(null);

  // Handles next.
  const handleNext = () => {
    setCurrentStep((prev) => Math.min(prev + 1, 4));
  };

  // Handles back.
  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  // Provides the persist job helper.
  const persistJob = async (status: "draft" | "active") => {
    const user = getStoredUser();
    if (!user) {
      throw new Error("Please log in again before saving the job.");
    }
    if (!jobData.parsedJD && !isEditMode) {
      throw new Error("Import the job description before saving.");
    }

    const persistedEligibilityFilters = {
      ...eligibilityFilters,
      enabledFilters: (eligibilityFilters.enabledFilters ?? []).filter(
        (filterKey) => filterKey !== "internshipAccepted",
      ),
      customFilters: (eligibilityFilters.customFilters ?? []).filter(
        (filter) => filter.id !== "internshipAccepted",
      ),
    };

    // Send all steps as one job payload.
    const payload = {
      createdByUserId: user.id,
      actionUserId: user.id,
      title: jobData.title,
      department: jobData.department,
      employmentType: jobData.employmentType,
      location: jobData.location,
      salaryRange: jobData.salary,
      description: jobData.description,
      removeJdFile:
        isEditMode &&
        Boolean(editingJob?.jdFilePath) &&
        !jobData.savedJdFilePath &&
        !jobData.jdFile,
      responsibilities: jobData.parsedJD?.responsibilities || [],
      qualifications: jobData.parsedJD?.qualifications || [],
      applicationQuestions,
      criteria,
      eligibilityFilters: persistedEligibilityFilters,
      status,
    };
    // FormData keeps the JSON and Excel file in one request.
    const formData = new FormData();
    formData.append("payload", JSON.stringify(payload));
    if (jobData.jdFile) {
      formData.append("jdFile", jobData.jdFile);
    }

    const path = persistedJobId ? `/jobs/${persistedJobId}` : "/jobs";
    const result = await apiFetch<{
      job: {
        id: number;
        jdFileName?: string | null;
        jdFilePath?: string | null;
        applicationQuestions?: {
          id: number;
          question: string;
          fieldType: ApplicationQuestion["fieldType"];
          required: boolean;
          options: string[];
        }[];
      };
    }>(path, {
      method: "POST",
      body: formData,
    });
    setPersistedJobId(Number(result.job.id));
    if (jobData.jdFile && result.job.jdFileName && result.job.jdFilePath) {
      setJobData((current) => ({
        ...current,
        jdFile: null,
        savedJdFileName: result.job.jdFileName || current.savedJdFileName,
        savedJdFilePath: result.job.jdFilePath || current.savedJdFilePath,
      }));
    }
    // Keep the local question state authoritative. The API intentionally skips
    // incomplete blank questions, so replacing local state with its response
    // would make a newly added question disappear while it is being edited.
    return result.job;
  };

  // This value changes when any saved field changes.
  const autoSaveSignature = JSON.stringify({
    title: jobData.title,
    department: jobData.department,
    employmentType: jobData.employmentType,
    location: jobData.location,
    salary: jobData.salary,
    description: jobData.description,
    savedJdFilePath: jobData.savedJdFilePath,
    jdFileName: jobData.jdFile?.name || null,
    responsibilities: jobData.parsedJD?.responsibilities || [],
    qualifications: jobData.parsedJD?.qualifications || [],
    applicationQuestions,
    criteria,
    eligibilityFilters,
  });
  const canAutoSave =
    Boolean(jobData.parsedJD) &&
    jobData.title.trim() !== "" &&
    jobData.department.trim() !== "";
  const autoSaveStatus: "draft" | "active" =
    isEditMode && editingJob?.status === "active" ? "active" : "draft";

  useEffect(() => {
    if (!canAutoSave || isSaving) return;
    if (skipInitialAutoSave.current) {
      skipInitialAutoSave.current = false;
      return;
    }
    if (autoSaveInFlight.current) {
      autoSaveQueued.current = true;
      return;
    }

    // Wait briefly so fast edits use one save request.
    setAutoSaveState("saving");
    const timer = window.setTimeout(() => {
      if (autoSaveInFlight.current) {
        autoSaveQueued.current = true;
        return;
      }
      autoSaveInFlight.current = true;
      persistJob(autoSaveStatus)
        .then(() => {
          setAutoSaveState("saved");
          setLastAutoSavedAt(
            new Date().toLocaleString("en-GB", {
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            }),
          );
        })
        .catch((error) => {
          setAutoSaveState("error");
          toast.error(
            error instanceof Error
              ? `Auto-save failed: ${error.message}`
              : "Auto-save failed",
          );
        })
        .finally(() => {
          autoSaveInFlight.current = false;
          if (autoSaveQueued.current) {
            autoSaveQueued.current = false;
            setAutoSaveRevision((revision) => revision + 1);
          }
        });
    }, 1200);

    return () => window.clearTimeout(timer);
  }, [autoSaveRevision, autoSaveSignature, canAutoSave, autoSaveStatus, isSaving]);

  // Handles publish.
  const handlePublish = async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      await persistJob("active");
      toast.success(isEditMode ? "Job updated successfully" : "Job published successfully");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to publish job");
    } finally {
      setIsSaving(false);
    }
  };

  const pageTitle = isEditMode ? "Edit Job" : "Create Job";
  const jobTitle = jobData.title.trim();

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        ...(isEditMode
          ? [
              {
                label: jobData.department || "Department",
                href: jobData.department
                  ? `/departments/${encodeURIComponent(jobData.department)}`
                  : "/jobs",
              },
              {
                label: jobData.title || "Job Details",
                href: jobId ? `/jobs/${jobId}` : undefined,
              },
              { label: "Edit Job" },
            ]
          : [{ label: "Create Job" }]),
      ]}
      title={jobTitle ? `${pageTitle} - ${jobTitle}` : pageTitle}
      subtitle={
        currentStep === 1
          ? isEditMode
            ? "Review and update the job details before continuing."
            : "Upload the job description Excel file and review the imported details."
          : currentStep === 2
            ? "Choose the additional questions candidates must answer."
            : currentStep === 3
              ? "Set the evaluation criteria and eligibility filters for this job."
              : isEditMode
                ? "Review the updated setup before saving the job changes."
                : "Review the full setup before publishing the job and sharing the application link."
      }
      useCard={false}
    >
      <JobCreationStepper
        currentStep={currentStep}
        isEditMode={isEditMode}
        onStepClick={setCurrentStep}
      />

      {canAutoSave && (
        <div className="flex justify-end text-sm font-medium text-slate-500">
          {autoSaveState === "saving" && "Saving changes..."}
          {(autoSaveState === "saved" || autoSaveState === "idle") &&
            lastAutoSavedAt &&
            `Saved on ${lastAutoSavedAt}`}
          {autoSaveState === "error" && (
            <span className="text-red-600">Auto-save failed</span>
          )}
        </div>
      )}

      {currentStep === 1 && (
        <Step1UploadJD
          jobData={jobData}
          setJobData={setJobData}
          onNext={handleNext}
          onCancel={() => navigate("/dashboard")}
          isSaving={isSaving}
          isEditMode={isEditMode}
          jobId={persistedJobId}
        />
      )}

      {currentStep === 2 && (
        <Step2ApplicationQuestions
          questions={applicationQuestions}
          setQuestions={setApplicationQuestions}
          onNext={handleNext}
          onBack={handleBack}
          isSaving={isSaving}
        />
      )}

      {currentStep === 3 && (
        <Step2SetCriteria
          criteria={criteria}
          setCriteria={setCriteria}
          jdData={
            jobData.parsedJD
              ? {
                  ...jobData.parsedJD,
                  jobTitle: jobData.title,
                  department: jobData.department,
                  description: jobData.description,
                }
              : null
          }
          lastGeneratedSource={criteriaGenerationSource}
          setLastGeneratedSource={setCriteriaGenerationSource}
          eligibilityFilters={eligibilityFilters}
          setEligibilityFilters={setEligibilityFilters}
          onNext={handleNext}
          onBack={handleBack}
          isSaving={isSaving}
        />
      )}

      {currentStep === 4 && (
        <Step3ReviewConfirm
          jobData={jobData}
          applicationQuestions={applicationQuestions}
          criteria={criteria}
          eligibilityFilters={eligibilityFilters}
          onBack={handleBack}
          onPublish={handlePublish}
          isEditMode={isEditMode}
          isSaving={isSaving}
        />
      )}
    </PageLayout>
  );
}
