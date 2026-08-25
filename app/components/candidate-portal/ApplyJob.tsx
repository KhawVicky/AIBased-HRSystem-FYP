// Shows the Apply Job view.
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import { toast } from "sonner";
import {
  Upload,
  FileText,
  X,
  Check,
  LoaderCircle,
  ChevronRight,
  MapPin,
  Building2,
  Eye,
  DollarSign,
} from "lucide-react";
import {
  ApiError,
  apiFetch,
  clearStoredCandidate,
  getStoredCandidate,
  type CandidateAccount,
  type JobSummary,
} from "../../lib/api";
import { LoadingState } from "../shared/LoadingState";
import { CandidateAuthModal } from "./CandidatePortal";
import {
  CandidatePortalFooter as SharedCandidatePortalFooter,
  CandidatePortalHeader,
} from "./CandidatePortalLayout";

type JobItem = {
  id: string;
  title: string;
  department: string;
  location: string;
  salary: string;
  applicationQuestions: ApplicationQuestion[];
};

type ApplicationQuestion = {
  id: number;
  question: string;
  fieldType: "text" | "textarea" | "number" | "dropdown";
  required: boolean;
  options: string[];
};

type UploadedFileItem = {
  id: string;
  file: File;
  previewUrl: string | null;
};

type LanguageItem = {
  id: string;
  language: string;
  level: string;
};

type ApplicationStepKey = "personal" | "experience" | "questions" | "review";

const baseApplicationSteps: { key: ApplicationStepKey; label: string }[] = [
  { key: "personal", label: "Personal Information" },
  { key: "experience", label: "My Experience" },
  { key: "review", label: "Review & Submit" },
];

const languageOptions = ["English", "Malay", "Mandarin", "Tamil", "Japanese", "Korean", "Other"];

const languageLevelOptions = [
  "Basic",
  "Conversational",
  "Intermediate",
  "Advanced",
  "Fluent",
  "Native",
];

const noticePeriodDaysByLabel: Record<string, number> = {
  Immediate: 0,
  "1 week": 7,
  "2 weeks": 14,
  "1 month": 30,
  "2 months": 60,
  "3 months": 90,
};

const noticePeriodToDays = (value: string) =>
  noticePeriodDaysByLabel[value] ?? 0;

const locationOptions: Record<string, Record<string, string[]>> = {
  Malaysia: {
    Johor: ["Johor Bahru", "Batu Pahat", "Muar", "Kluang", "Segamat"],
    Kedah: ["Alor Setar", "Sungai Petani", "Kulim", "Langkawi"],
    Kelantan: ["Kota Bharu", "Pasir Mas", "Tumpat"],
    Melaka: ["Melaka City", "Ayer Keroh", "Alor Gajah"],
    "Negeri Sembilan": ["Seremban", "Nilai", "Port Dickson"],
    Pahang: ["Kuantan", "Temerloh", "Bentong", "Genting Highlands"],
    Penang: ["Batu Kawan", "George Town", "Butterworth", "Bukit Mertajam", "Bayan Lepas"],
    Perak: ["Ipoh", "Taiping", "Teluk Intan", "Manjung"],
    Perlis: ["Kangar", "Arau"],
    Sabah: ["Kota Kinabalu", "Sandakan", "Tawau", "Lahad Datu"],
    Sarawak: ["Kuching", "Miri", "Sibu", "Bintulu"],
    Selangor: ["Petaling Jaya", "Shah Alam", "Subang Jaya", "Klang", "Puchong", "Kajang"],
    Terengganu: ["Kuala Terengganu", "Kemaman", "Dungun"],
    "Kuala Lumpur": ["Kuala Lumpur"],
    Labuan: ["Labuan"],
    Putrajaya: ["Putrajaya"],
  },
  Singapore: {
    Central: ["Singapore"],
    East: ["Bedok", "Tampines", "Pasir Ris"],
    North: ["Woodlands", "Yishun", "Sembawang"],
    "North-East": ["Punggol", "Sengkang", "Hougang"],
    West: ["Jurong East", "Jurong West", "Clementi"],
  },
  Indonesia: {
    "DKI Jakarta": ["Central Jakarta", "South Jakarta", "West Jakarta", "East Jakarta", "North Jakarta"],
    "West Java": ["Bandung", "Bekasi", "Bogor", "Depok"],
    "Central Java": ["Semarang", "Surakarta", "Magelang"],
    "East Java": ["Surabaya", "Malang", "Sidoarjo"],
    Bali: ["Denpasar", "Badung", "Ubud"],
    "North Sumatra": ["Medan", "Binjai", "Pematangsiantar"],
    "Riau Islands": ["Batam", "Tanjung Pinang"],
  },
  Thailand: {
    Bangkok: ["Bangkok"],
    Chonburi: ["Chonburi", "Pattaya", "Si Racha"],
    Chiangmai: ["Chiang Mai"],
    Phuket: ["Phuket"],
    Rayong: ["Rayong"],
    Songkhla: ["Hat Yai", "Songkhla"],
  },
  Philippines: {
    "Metro Manila": ["Manila", "Makati", "Quezon City", "Taguig", "Pasig"],
    Cebu: ["Cebu City", "Mandaue", "Lapu-Lapu"],
    Davao: ["Davao City"],
    Laguna: ["Calamba", "Santa Rosa"],
    Cavite: ["Dasmarinas", "Bacoor", "Imus"],
  },
  Vietnam: {
    "Ho Chi Minh City": ["Ho Chi Minh City"],
    Hanoi: ["Hanoi"],
    "Da Nang": ["Da Nang"],
    "Binh Duong": ["Thu Dau Mot", "Di An"],
    "Dong Nai": ["Bien Hoa"],
  },
  Other: {
    Other: ["Other"],
  },
};

const countryOptions = ["Malaysia"];

// Provides the map job item helper.
const mapJobItem = (
  job: Pick<
    JobSummary,
    "jobCode" | "title" | "department" | "location" | "salaryRange"
  > & { applicationQuestions?: ApplicationQuestion[] },
): JobItem => ({
  id: job.jobCode,
  title: job.title,
  department: job.department,
  location: job.location,
  salary: job.salaryRange || "Salary not specified",
  applicationQuestions: job.applicationQuestions || [],
});

// Formats file size.
function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024)
    return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

// Accepts PDFs even when a mobile file picker omits the MIME type.
function isPdfFile(file: File) {
  return (
    file.type === "application/pdf" ||
    file.name.toLowerCase().endsWith(".pdf")
  );
}

// Builds a PDF URL that mobile browsers can open directly.
function createPdfPreviewUrl(file: File) {
  const previewFile =
    file.type === "application/pdf"
      ? file
      : new Blob([file], { type: "application/pdf" });

  return URL.createObjectURL(previewFile);
}

// Renders the Apply Job component.
export function ApplyJob() {
  const { jobCode } = useParams();
  const navigate = useNavigate();
  const [signedInCandidate, setSignedInCandidate] = useState<CandidateAccount | null>(() => getStoredCandidate());
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    selectedJobId: "",
    fullName: "",
    gender: "",
    country: "",
    currentState: "",
    currentCity: "",
    email: "",
    phone: "",
    cgpa: "",
    noticePeriod: "",
    linkedIn: "",
    portfolio: "",
  });
  const [languages, setLanguages] = useState<LanguageItem[]>([
    { id: "language-1", language: "", level: "" },
  ]);
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, string>>({});

  const [files, setFiles] = useState<UploadedFileItem[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>(
    {},
  );
  const [activeStep, setActiveStep] = useState(0);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReplacingApplication, setIsReplacingApplication] = useState(false);

  // Keeps the application page on the same candidate session flow as the portal pages.
  const handleCandidateLogout = async () => {
    try {
      await apiFetch("/candidate-auth/logout", { method: "POST" });
    } catch {
      // Clear the local session even when the server session has already expired.
    }
    clearStoredCandidate();
    setSignedInCandidate(null);
    toast.success("Logged out");
    navigate("/careers");
  };

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const previewUrlsRef = useRef<Set<string>>(new Set());

  // Build the steps from the questions set by HR.
  const selectedJob = useMemo(
    () =>
      jobs.find((job) => job.id === formData.selectedJobId),
    [jobs, formData.selectedJobId],
  );
  const hasApplicationQuestions = Boolean(selectedJob?.applicationQuestions.length);
  const applicationSteps = useMemo(
    () =>
      hasApplicationQuestions
        ? [
            baseApplicationSteps[0],
            baseApplicationSteps[1],
            { key: "questions" as const, label: "Additional Questions" },
            baseApplicationSteps[2],
          ]
        : baseApplicationSteps,
    [hasApplicationQuestions],
  );
  const activeStepKey = applicationSteps[activeStep]?.key ?? "personal";

  useEffect(() => {
    setActiveStep((step) => Math.min(step, applicationSteps.length - 1));
  }, [applicationSteps.length]);

  useEffect(() => {
    if (!signedInCandidate) return;

    // Fill known details from the candidate profile.
    const [savedCity = "", savedState = ""] = (signedInCandidate.currentLocation || "")
      .split(",")
      .map((item) => item.trim());

    setFormData((prev) => ({
      ...prev,
      fullName: prev.fullName || signedInCandidate.fullName || "",
      email: prev.email || signedInCandidate.email || "",
      phone: prev.phone || signedInCandidate.phone || "",
      gender: prev.gender || signedInCandidate.gender || "",
      country: prev.country || signedInCandidate.country || "",
      currentState: prev.currentState || savedState,
      currentCity: prev.currentCity || savedCity,
    }));

    if (signedInCandidate.languages?.length) {
      setLanguages(
        signedInCandidate.languages.map((item, index) => ({
          id: `saved-language-${index}`,
          language: item.language,
          level: item.level,
        })),
      );
    }
  }, [signedInCandidate]);

  useEffect(() => {
    // Load one linked job or the full public job list.
    setIsLoadingJobs(true);
    const loadJobs = jobCode
      ? apiFetch<{
          job: Pick<
            JobSummary,
            | "jobCode"
            | "title"
            | "department"
            | "location"
            | "salaryRange"
          > & { applicationQuestions?: ApplicationQuestion[] };
        }>(`/apply/${jobCode}`).then((data) => [mapJobItem(data.job)])
      : apiFetch<{ jobs: JobSummary[] }>("/career/jobs").then((data) =>
          data.jobs.map(mapJobItem),
        );

    loadJobs
      .then((loadedJobs) => {
        setJobs(loadedJobs);
        setFormData((prev) => ({
          ...prev,
          selectedJobId:
            prev.selectedJobId || loadedJobs[0]?.id || "",
        }));
      })
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load jobs",
        ),
      )
      .finally(() => setIsLoadingJobs(false));
  }, [jobCode]);

  useEffect(() => {
    if (!formData.selectedJobId || jobCode) return;
    apiFetch<{
      job: Pick<
        JobSummary,
        "jobCode" | "title" | "department" | "location" | "salaryRange"
      > & { applicationQuestions?: ApplicationQuestion[] };
    }>(`/apply/${formData.selectedJobId}`)
      .then((data) => {
        setJobs((current) =>
          current.map((job) =>
            job.id === data.job.jobCode ? mapJobItem(data.job) : job,
          ),
        );
      })
      .catch(() => toast.error("Failed to load the application questions"));
  }, [formData.selectedJobId, jobCode]);

  useEffect(
    () => () => {
      // Release local files only when the application page closes.
      previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      previewUrlsRef.current.clear();
    },
    [],
  );

  // Handles input change.
  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  // Handles file upload.
  const handleFileUpload = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    // Only PDF resumes are accepted by this form.
    const selectedFiles = Array.from(e.target.files || []);

    if (!selectedFiles.length) return;

    const validFiles: UploadedFileItem[] = [];

    for (const file of selectedFiles) {
      if (!isPdfFile(file)) {
        toast.error(
          `${file.name} is not supported. Please upload PDF files only.`,
        );
        continue;
      }

      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name} exceeds 10MB.`);
        continue;
      }

      const previewUrl = createPdfPreviewUrl(file);
      previewUrlsRef.current.add(previewUrl);

      validFiles.push({
        id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
        file,
        previewUrl,
      });
    }

    if (!validFiles.length) return;

    setFiles((current) => {
      const existingKeys = new Set(
        current.map((item) => `${item.file.name}-${item.file.size}-${item.file.lastModified}`),
      );
      const nextFiles = validFiles.filter(
        (item) => !existingKeys.has(`${item.file.name}-${item.file.size}-${item.file.lastModified}`),
      );
      return [...current, ...nextFiles];
    });
    setErrors((prev) => ({ ...prev, files: "" }));
    toast.success("Files uploaded successfully");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Removes file.
  const removeFile = (id: string) => {
    setFiles((prev) => {
      const target = prev.find((item) => item.id === id);

      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
        previewUrlsRef.current.delete(target.previewUrl);
      }

      return prev.filter((item) => item.id !== id);
    });
  };

  // Gets validation errors.
  const getValidationErrors = (fields?: string[]) => {
    const newErrors: Record<string, string> = {};
    // Checks whether validate should run.
    const shouldValidate = (field: string) =>
      !fields || fields.includes(field);

    if (shouldValidate("selectedJobId") && !formData.selectedJobId) {
      newErrors.selectedJobId = "Please select a job";
    }

    if (shouldValidate("fullName") && !formData.fullName.trim()) {
      newErrors.fullName = "Full name is required";
    }

    if (shouldValidate("gender") && !formData.gender.trim()) {
      newErrors.gender = "Gender is required";
    }

    if (shouldValidate("country") && !formData.country.trim()) {
      newErrors.country = "Country is required";
    }

    if (shouldValidate("currentState") && !formData.currentState.trim()) {
      newErrors.currentState = "State is required";
    }

    if (shouldValidate("currentCity") && !formData.currentCity.trim()) {
      newErrors.currentCity = "City is required";
    }

    if (shouldValidate("email") && !formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (
      shouldValidate("email") &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(formData.email.trim())
    ) {
      newErrors.email = "Please enter a valid email address";
    }

    const normalizedPhone = formData.phone.replace(/[\s()-]/g, "");
    if (shouldValidate("phone") && !formData.phone.trim()) {
      newErrors.phone = "Phone number is required";
    } else if (
      shouldValidate("phone") &&
      !/^(?:\+?60|0)(?:1\d{8,9}|[3-9]\d{7,8})$/.test(normalizedPhone)
    ) {
      newErrors.phone =
        "Please enter a valid Malaysian phone number";
    }

    if (shouldValidate("cgpa") && !formData.cgpa.trim()) {
      newErrors.cgpa = "CGPA is required";
    } else {
      const cgpaValue = Number(formData.cgpa);

      if (
        shouldValidate("cgpa") &&
        Number.isNaN(cgpaValue) ||
        (shouldValidate("cgpa") && cgpaValue < 0) ||
        (shouldValidate("cgpa") && cgpaValue > 4)
      ) {
        newErrors.cgpa = "CGPA must be between 0.00 and 4.00";
      }
    }

    if (shouldValidate("noticePeriod") && !formData.noticePeriod.trim()) {
      newErrors.noticePeriod = "Notice period is required";
    }

    if (
      shouldValidate("languages") &&
      languages.some((item) => !item.language.trim() || !item.level.trim())
    ) {
      newErrors.languages = "Please select a language and level for each entry";
    }

    if (shouldValidate("files") && files.length === 0) {
      newErrors.files = "Please upload your resume or CV";
    }

    if (shouldValidate("questions")) {
      selectedJob?.applicationQuestions.forEach((question) => {
        if (question.required && !(questionAnswers[question.id] || "").trim()) {
          newErrors[`question-${question.id}`] = "This question is required";
        }
      });
    }

    return newErrors;
  };

  // Validates form.
  const validateForm = () => {
    const newErrors = getValidationErrors();

    setErrors(newErrors);

    return (
      Object.keys(newErrors).filter((key) => newErrors[key])
        .length === 0
    );
  };

  // Gets step fields.
  const getStepFields = (step: number) => {
    const stepKey = applicationSteps[step]?.key;
    if (stepKey === "personal") return ["selectedJobId", "fullName", "gender", "email", "phone", "country", "currentState", "currentCity"];
    if (stepKey === "experience") return ["cgpa", "noticePeriod", "languages", "files"];
    if (stepKey === "questions") return ["questions"];
    return [];
  };

  // Updates question answer.
  const updateQuestionAnswer = (questionId: number, value: string) => {
    setQuestionAnswers((current) => ({ ...current, [questionId]: value }));
    setErrors((current) => ({ ...current, [`question-${questionId}`]: "" }));
  };

  // Validates step.
  const validateStep = (step: number) => {
    const fields = getStepFields(step);
    const stepErrors = getValidationErrors(fields);

    setErrors((prev) => {
      const next = { ...prev };
      fields.forEach((field) => {
        delete next[field];
      });
      return { ...next, ...stepErrors };
    });

    return Object.keys(stepErrors).length === 0;
  };

  // Handles next step.
  const handleNextStep = () => {
    if (!validateStep(activeStep)) {
      toast.error("Please complete this step before continuing");
      return;
    }

    setActiveStep((step) =>
      Math.min(step + 1, applicationSteps.length - 1),
    );
  };

  // Handles previous step.
  const handlePreviousStep = () => {
    setActiveStep((step) => Math.max(step - 1, 0));
  };

  // Updates language.
  const updateLanguage = (
    id: string,
    field: "language" | "level",
    value: string,
  ) => {
    setLanguages((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, [field]: value } : item,
      ),
    );

    if (errors.languages) {
      setErrors((prev) => ({ ...prev, languages: "" }));
    }
  };

  // Adds language.
  const addLanguage = () => {
    setLanguages((prev) => [
      ...prev,
      { id: `language-${Date.now()}`, language: "", level: "" },
    ]);
  };

  // Removes language.
  const removeLanguage = (id: string) => {
    setLanguages((prev) =>
      prev.length === 1 ? prev : prev.filter((item) => item.id !== id),
    );
  };

  // Builds application data.
  const buildApplicationData = (replaceExisting: boolean) => {
    const applicationData = new FormData();
    applicationData.append("fullName", formData.fullName);
    applicationData.append("gender", formData.gender);
    applicationData.append("country", formData.country);
    applicationData.append(
      "currentLocation",
      [formData.currentCity, formData.currentState].filter(Boolean).join(", "),
    );
    applicationData.append("email", formData.email);
    applicationData.append("phone", formData.phone);
    applicationData.append("cgpa", formData.cgpa);
    applicationData.append("languages", JSON.stringify(languages));
    applicationData.append(
      "noticePeriodDays",
      String(noticePeriodToDays(formData.noticePeriod)),
    );
    applicationData.append(
      "questionAnswers",
      JSON.stringify(
        (selectedJob?.applicationQuestions || []).map((question) => ({
          questionId: question.id,
          answer: questionAnswers[question.id] || "",
        })),
      ),
    );
    files.forEach((item) => {
      applicationData.append("resume[]", item.file);
    });

    if (replaceExisting) {
      applicationData.append("replaceExisting", "1");
    }

    return applicationData;
  };

  // Submits application.
  const submitApplication = async (replaceExisting = false) => {
    if (isSubmitting) return;

    setIsSubmitting(true);
    // A duplicate application needs candidate approval before replacement.
    try {
      await apiFetch(`/apply/${formData.selectedJobId}`, {
        method: "POST",
        body: buildApplicationData(replaceExisting),
      });

      setIsSubmitted(true);
      setDuplicateDialogOpen(false);

      toast.success("Application submitted successfully!", {
        description:
          "We'll review your application and get back to you soon.",
        duration: 5000,
      });
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.data.duplicate
      ) {
        setDuplicateDialogOpen(true);
        return;
      }

      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to submit application",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handles submit application.
  const handleSubmitApplication = async () => {
    if (isSubmitting) return;

    if (!validateForm()) {
      toast.error("Please fix all errors before submitting");
      return;
    }

    await submitApplication(false);
  };

  // Handles replace application.
  const handleReplaceApplication = async () => {
    setIsReplacingApplication(true);
    try {
      await submitApplication(true);
    } finally {
      setIsReplacingApplication(false);
    }
  };

  // Renders the Candidate Application Breadcrumb component.
  function CandidateApplicationBreadcrumb() {
    const items = [
      { label: "Careers", href: "/careers" },
      {
        label: selectedJob?.title || "Application",
        href: selectedJob?.id ? `/careers/${selectedJob.id}` : undefined,
      },
      { label: "Apply" },
    ];

    return (
      <nav className="mb-6 flex flex-wrap items-center gap-2 text-sm text-[#496a94]" aria-label="Breadcrumb">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <div key={`${item.label}-${index}`} className="flex items-center gap-2">
              {index > 0 && <ChevronRight className="h-4 w-4 text-[#8aa0bd]" />}
              {item.href && !isLast ? (
                <Link to={item.href} className="transition hover:text-[#003B7A]">
                  {item.label}
                </Link>
              ) : (
                <span className={isLast ? "font-semibold text-slate-950" : ""}>{item.label}</span>
              )}
            </div>
          );
        })}
      </nav>
    );
  }

  if (isSubmitted) {
    return (
      <div className="flex min-h-screen flex-col bg-slate-100">
        <CandidatePortalHeader
          candidate={signedInCandidate}
          onLogin={() => setAuthModalOpen(true)}
          onLogout={handleCandidateLogout}
        />

        <main className="mx-auto flex w-full max-w-7xl flex-1 items-center px-6 py-10 lg:px-8">
          <Card className="mx-auto max-w-2xl rounded-2xl border-slate-200 shadow-sm">
            <CardContent className="pt-12 pb-12 text-center">
              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <Check className="h-8 w-8 text-green-600" />
              </div>

              <h2 className="mb-4 text-2xl font-bold text-slate-900">
                Application Submitted
              </h2>

              <p className="mb-6 text-slate-600">
                Thank you for your application. Our HR team will
                review your documents and contact you if you are
                shortlisted.
              </p>

              <div className="mb-6 rounded-lg bg-slate-50 p-4 text-left">
                <h3 className="mb-2 font-semibold text-slate-900">
                  Submitted for
                </h3>
                <p className="text-sm text-slate-600">
                  {selectedJob?.title || "Selected Position"}
                </p>
              </div>

              <Button
                onClick={() =>
                  signedInCandidate
                    ? navigate("/candidate/applications")
                    : setIsSubmitted(false)
                }
                className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5"
              >
                {signedInCandidate ? "View My Applications" : "Back to Form"}
              </Button>
            </CardContent>
          </Card>
        </main>

        <SharedCandidatePortalFooter />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <CandidatePortalHeader
        candidate={signedInCandidate}
        onLogin={() => setAuthModalOpen(true)}
        onLogout={handleCandidateLogout}
      />

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-5 lg:px-8">
        <CandidateApplicationBreadcrumb />
        <div className="mb-8 text-center md:text-left">
          <h1 className="mb-2 text-3xl font-bold text-slate-900">
            {selectedJob?.title || "Application"}
          </h1>
          {selectedJob ? (
            <div className="flex flex-wrap justify-center gap-4 text-slate-600 md:justify-start">
              <div className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {selectedJob.department}
              </div>

              <div className="flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {selectedJob.location}
              </div>

              <div className="flex items-center gap-1">
                <DollarSign className="h-4 w-4" />
                {selectedJob.salary}
              </div>
            </div>
          ) : (
            <p className="text-slate-600">
              Complete each step and upload your application documents.
            </p>
          )}
        </div>

        {isLoadingJobs ? (
          <LoadingState title="Loading application form" />
        ) : (
        <div className="space-y-5">
            <div className="overflow-x-auto py-2">
              <div className="mx-auto flex min-w-[760px] max-w-4xl items-center justify-between">
                {applicationSteps.map((step, index) => {
                  const stepNumber = index + 1;
                  const currentStep = activeStep + 1;
                  const isActive = stepNumber === currentStep;
                  const isCompleted = stepNumber < currentStep;

                  return (
                    <div key={step.key} className="flex flex-1 items-center">
                      <button
                        type="button"
                        onClick={() => {
                          if (index <= activeStep || validateStep(activeStep)) {
                            setActiveStep(index);
                          }
                        }}
                        className="relative flex flex-col items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#003B7A] focus-visible:ring-offset-2"
                      >
                        <span
                          className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-all ${
                            isActive
                              ? "bg-[#003B7A] text-white ring-4 ring-blue-100"
                              : isCompleted
                                ? "bg-[#003B7A] text-white"
                                : "border-2 border-[#003B7A] bg-white text-[#003B7A]"
                          }`}
                        >
                          {stepNumber}
                        </span>

                        <span
                          className={`mt-2 whitespace-nowrap text-sm font-medium ${
                            isActive
                              ? "text-[#003B7A]"
                              : isCompleted
                                ? "text-slate-700"
                                : "text-slate-400"
                          }`}
                        >
                          {step.label}
                        </span>
                      </button>

                      {index < applicationSteps.length - 1 && (
                        <div className="mx-4 mb-6 h-0.5 flex-1">
                          <div
                            className={`h-full transition-all ${
                              isCompleted ? "bg-[#003B7A]" : "bg-slate-300"
                            }`}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

        {errors.selectedJobId && (
          <p className="text-sm text-red-500">
            {errors.selectedJobId}
          </p>
        )}

        <Card className="rounded-2xl border-slate-200 shadow-sm pt-6">

          <CardContent>
            <form onSubmit={(event) => event.preventDefault()} noValidate className="space-y-6">
              {activeStepKey === "personal" && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-slate-900">
                  Personal Information
                </h3>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full Name *</Label>
                    <Input
                      id="fullName"
                      placeholder="John Doe"
                      value={formData.fullName}
                      onChange={(e) =>
                        handleInputChange(
                          "fullName",
                          e.target.value,
                        )
                      }
                      className={
                        errors.fullName ? "border-red-500" : ""
                      }
                    />

                    {errors.fullName && (
                      <p className="text-sm text-red-500">
                        {errors.fullName}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="gender">Gender *</Label>
                    <Select
                      value={formData.gender}
                      onValueChange={(value) =>
                        handleInputChange("gender", value)
                      }
                    >
                      <SelectTrigger
                        id="gender"
                        className={errors.gender ? "border-red-500" : ""}
                      >
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Male">Male</SelectItem>
                        <SelectItem value="Female">Female</SelectItem>
                        <SelectItem value="Prefer not to say">
                          Prefer not to say
                        </SelectItem>
                      </SelectContent>
                    </Select>

                    {errors.gender && (
                      <p className="text-sm text-red-500">
                        {errors.gender}
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <div id="email" className="pt-2 text-sm font-medium text-slate-900">
                      {formData.email || "No email available"}
                    </div>

                    {errors.email && (
                      <p className="text-sm text-red-500">
                        {errors.email}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">
                      Phone Number *
                    </Label>
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="+60 12-345 6789"
                      value={formData.phone}
                      onChange={(e) =>
                        handleInputChange(
                          "phone",
                          e.target.value,
                        )
                      }
                      className={
                        errors.phone ? "border-red-500" : ""
                      }
                    />

                    {errors.phone && (
                      <p className="text-sm text-red-500">
                        {errors.phone}
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="country">Country *</Label>
                    <Select
                      value={formData.country}
                      onValueChange={(value) => {
                        setFormData((prev) => ({
                          ...prev,
                          country: value,
                          currentState: "",
                          currentCity: "",
                        }));
                        if (errors.country || errors.currentState || errors.currentCity) {
                          setErrors((prev) => ({
                            ...prev,
                            country: "",
                            currentState: "",
                            currentCity: "",
                          }));
                        }
                      }}
                    >
                      <SelectTrigger
                        id="country"
                        className={errors.country ? "border-red-500" : ""}
                      >
                        <SelectValue placeholder="Select country" />
                      </SelectTrigger>
                      <SelectContent>
                        {countryOptions.map((country) => (
                          <SelectItem key={country} value={country}>
                            {country}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {errors.country && (
                      <p className="text-sm text-red-500">
                        {errors.country}
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="currentState">State *</Label>
                    <Select
                      value={formData.currentState}
                      onValueChange={(value) => {
                        setFormData((prev) => ({
                          ...prev,
                          currentState: value,
                          currentCity: "",
                        }));
                        if (errors.currentState || errors.currentCity) {
                          setErrors((prev) => ({
                            ...prev,
                            currentState: "",
                            currentCity: "",
                          }));
                        }
                      }}
                      disabled={!formData.country}
                    >
                      <SelectTrigger
                        id="currentState"
                        className={errors.currentState ? "border-red-500" : ""}
                      >
                        <SelectValue placeholder="Select state" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(locationOptions[formData.country] ?? {}).map((state) => (
                          <SelectItem key={state} value={state}>
                            {state}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {errors.currentState && (
                      <p className="text-sm text-red-500">
                        {errors.currentState}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="currentCity">City *</Label>
                    <Select
                      value={formData.currentCity}
                      onValueChange={(value) =>
                        handleInputChange("currentCity", value)
                      }
                      disabled={!formData.currentState}
                    >
                      <SelectTrigger
                        id="currentCity"
                        className={errors.currentCity ? "border-red-500" : ""}
                      >
                        <SelectValue placeholder="Select city" />
                      </SelectTrigger>
                      <SelectContent>
                        {(locationOptions[formData.country]?.[formData.currentState] ?? []).map((city) => (
                          <SelectItem key={city} value={city}>
                            {city}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {errors.currentCity && (
                      <p className="text-sm text-red-500">
                        {errors.currentCity}
                      </p>
                    )}
                  </div>
                  </div>
                </div>
              </div>
              )}

              {activeStepKey === "experience" && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-slate-900">
                  My Experience
                </h3>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="cgpa">CGPA *</Label>
                    <Input
                      id="cgpa"
                      type="number"
                      min="0"
                      max="4"
                      step="0.01"
                      placeholder="3.50"
                      value={formData.cgpa}
                      onChange={(e) =>
                        handleInputChange(
                          "cgpa",
                          e.target.value,
                        )
                      }
                      className={
                        errors.cgpa ? "border-red-500" : ""
                      }
                    />

                    {errors.cgpa && (
                      <p className="text-sm text-red-500">
                        {errors.cgpa}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="noticePeriod">
                      Notice Period *
                    </Label>

                    <Select
                      value={formData.noticePeriod}
                      onValueChange={(value) =>
                        handleInputChange("noticePeriod", value)
                      }
                    >
                      <SelectTrigger
                        id="noticePeriod"
                        className={errors.noticePeriod ? "border-red-500" : ""}
                      >
                        <SelectValue placeholder="Select notice period" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Immediate">Immediate</SelectItem>
                        <SelectItem value="1 week">1 week</SelectItem>
                        <SelectItem value="2 weeks">2 weeks</SelectItem>
                        <SelectItem value="1 month">1 month</SelectItem>
                        <SelectItem value="2 months">2 months</SelectItem>
                        <SelectItem value="3 months">3 months</SelectItem>
                      </SelectContent>
                    </Select>

                    {errors.noticePeriod && (
                      <p className="text-sm text-red-500">
                        {errors.noticePeriod}
                      </p>
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Languages *</Label>

                  <div className="space-y-3">
                    {languages.map((item, index) => (
                      <div
                        key={item.id}
                        className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_auto]"
                      >
                        <Select
                          value={item.language}
                          onValueChange={(value) =>
                            updateLanguage(item.id, "language", value)
                          }
                        >
                          <SelectTrigger
                            className={errors.languages ? "border-red-500" : ""}
                          >
                            <SelectValue placeholder="Select language" />
                          </SelectTrigger>
                          <SelectContent>
                            {languageOptions.map((language) => (
                              <SelectItem key={language} value={language}>
                                {language}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <Select
                          value={item.level}
                          onValueChange={(value) =>
                            updateLanguage(item.id, "level", value)
                          }
                        >
                          <SelectTrigger
                            className={errors.languages ? "border-red-500" : ""}
                          >
                            <SelectValue placeholder="Select level" />
                          </SelectTrigger>
                          <SelectContent>
                            {languageLevelOptions.map((level) => (
                              <SelectItem key={level} value={level}>
                                {level}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeLanguage(item.id)}
                          disabled={languages.length === 1}
                          aria-label={`Remove language ${index + 1}`}
                          className="justify-self-start text-slate-500 hover:text-red-600 md:justify-self-end"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addLanguage}
                  >
                    Add Language
                  </Button>

                  {errors.languages && (
                    <p className="text-sm text-red-500">
                      {errors.languages}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="linkedIn">
                      LinkedIn Profile
                    </Label>
                    <Input
                      id="linkedIn"
                      placeholder="https://linkedin.com/in/johndoe"
                      value={formData.linkedIn}
                      onChange={(e) =>
                        handleInputChange(
                          "linkedIn",
                          e.target.value,
                        )
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="portfolio">
                      Portfolio / Website
                    </Label>
                    <Input
                      id="portfolio"
                      placeholder="https://johndoe.com"
                      value={formData.portfolio}
                      onChange={(e) =>
                        handleInputChange(
                          "portfolio",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                <Label>Resume / CV *</Label>

                <div className="space-y-3">
                  <label
                    htmlFor="applicationFiles"
                    className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors hover:bg-slate-50 ${
                      errors.files
                        ? "border-red-500"
                        : "border-slate-300"
                    }`}
                  >
                    <Upload className="mb-3 h-12 w-12 text-slate-400" />
                    <p className="mb-1 text-sm font-medium text-slate-700">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-center text-xs text-slate-500">
                      Upload your resume or CV files
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      PDF only. Max 10MB each.
                    </p>

                    <input
                      ref={fileInputRef}
                      id="applicationFiles"
                      type="file"
                      accept=".pdf,application/pdf"
                      multiple
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>

                  {errors.files && (
                    <p className="text-sm text-red-500">
                      {errors.files}
                    </p>
                  )}

                  {files.length > 0 && (
                    <div className="space-y-3">
                      {files.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between rounded-lg border border-slate-300 bg-slate-50 p-4"
                        >
                          <div className="flex min-w-0 flex-1 items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded bg-blue-100">
                              <FileText className="h-5 w-5 text-blue-600" />
                            </div>

                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-medium text-slate-700">
                                {item.file.name}
                              </p>
                              <p className="text-xs text-slate-500">
                                {formatFileSize(item.file.size)}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {item.previewUrl && (
                              <Button
                                asChild
                                variant="outline"
                                size="sm"
                              >
                                <a
                                  href={item.previewUrl}
                                  target="_blank"
                                  rel="noopener"
                                  aria-label={`Preview ${item.file.name}`}
                                >
                                  <Eye className="mr-2 h-4 w-4" />
                                  Preview
                                </a>
                              </Button>
                            )}

                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                removeFile(item.id)
                              }
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              </div>
              )}

              {activeStepKey === "questions" && selectedJob?.applicationQuestions.length ? (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-slate-900">
                    Additional Questions
                  </h3>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {selectedJob.applicationQuestions.map((question) => {
                      const error = errors[`question-${question.id}`];
                      const fieldId = `application-question-${question.id}`;
                      return (
                        <div
                          key={question.id}
                          className={question.fieldType === "textarea" ? "space-y-2 md:col-span-2" : "space-y-2"}
                        >
                          <Label htmlFor={fieldId}>
                            {question.question}{question.required ? " *" : ""}
                          </Label>
                          {question.fieldType === "dropdown" ? (
                            <Select
                              value={questionAnswers[question.id] || ""}
                              onValueChange={(value) => updateQuestionAnswer(question.id, value)}
                            >
                              <SelectTrigger id={fieldId} className={error ? "border-red-500" : ""}>
                                <SelectValue placeholder="Select an option" />
                              </SelectTrigger>
                              <SelectContent>
                                {question.options.map((option) => (
                                  <SelectItem key={option} value={option}>
                                    {option}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : question.fieldType === "textarea" ? (
                            <Textarea
                              id={fieldId}
                              value={questionAnswers[question.id] || ""}
                              onChange={(event) => updateQuestionAnswer(question.id, event.target.value)}
                              rows={3}
                              placeholder="Enter your answer"
                              className={error ? "border-red-500" : ""}
                            />
                          ) : (
                            <Input
                              id={fieldId}
                              type={question.fieldType === "number" ? "number" : "text"}
                              value={questionAnswers[question.id] || ""}
                              onChange={(event) => updateQuestionAnswer(question.id, event.target.value)}
                              placeholder="Enter your answer"
                              className={error ? "border-red-500" : ""}
                            />
                          )}
                          {error && <p className="text-sm text-red-500">{error}</p>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {activeStepKey === "review" && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-slate-900">
                    Review & Submit
                  </h3>

                  <div className="space-y-4">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-3 text-sm font-semibold text-slate-900">
                        Personal Information
                      </div>
                      <div className="space-y-2 text-sm text-slate-600">
                        <div className="flex justify-between gap-4">
                          <span>Full Name</span>
                          <span className="font-medium text-slate-900">{formData.fullName || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Email</span>
                          <span className="font-medium text-slate-900">{formData.email || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Gender</span>
                          <span className="font-medium text-slate-900">{formData.gender || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Country</span>
                          <span className="font-medium text-slate-900">{formData.country || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Current Location</span>
                          <span className="font-medium text-slate-900">
                            {[formData.currentCity, formData.currentState].filter(Boolean).join(", ") || "-"}
                          </span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Phone</span>
                          <span className="font-medium text-slate-900">{formData.phone || "-"}</span>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-3 text-sm font-semibold text-slate-900">
                        My Experience
                      </div>
                      <div className="space-y-2 text-sm text-slate-600">
                        <div className="flex justify-between gap-4">
                          <span>CGPA</span>
                          <span className="font-medium text-slate-900">{formData.cgpa || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Notice Period</span>
                          <span className="font-medium text-slate-900">{formData.noticePeriod || "-"}</span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Languages</span>
                          <span className="text-right font-medium text-slate-900">
                            {languages
                              .filter((item) => item.language || item.level)
                              .map((item) =>
                                [item.language, item.level].filter(Boolean).join(" - "),
                              )
                              .join(", ") || "-"}
                          </span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span>Resume / CV</span>
                          <span className="font-medium text-slate-900">
                            {files.length} file{files.length === 1 ? "" : "s"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {selectedJob?.applicationQuestions.length ? (
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 text-sm font-semibold text-slate-900">
                          Additional Questions
                        </div>
                        <div className="space-y-2 text-sm text-slate-600">
                          {selectedJob.applicationQuestions.map((question) => (
                            <div key={question.id} className="flex justify-between gap-4">
                              <span>{question.question}</span>
                              <span className="text-right font-medium text-slate-900">
                                {questionAnswers[question.id] || "-"}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={handlePreviousStep}
            disabled={activeStep === 0 || isSubmitting}
          >
            Back
          </Button>

          {activeStep < applicationSteps.length - 1 ? (
            <Button
              type="button"
              className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setDuplicateDialogOpen(false);
                handleNextStep();
              }}
            >
              Next
            </Button>
          ) : (
            <Button
              type="button"
              className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5"
              onClick={handleSubmitApplication}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit Application"
              )}
            </Button>
          )}
        </div>
        </div>
        )}
      </main>

      <AlertDialog
        open={duplicateDialogOpen}
        onOpenChange={setDuplicateDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Replace existing application?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This email has already submitted an application for this
              job. If you continue, the latest form and resume will
              replace the existing application, and the previous
              submission will be kept in history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isReplacingApplication}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void handleReplaceApplication();
              }}
              disabled={isReplacingApplication}
              className="bg-[#003B7A] hover:bg-[#002f63]"
            >
              {isReplacingApplication ? "Replacing..." : "Replace"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <CandidateAuthModal
        open={authModalOpen}
        returnTo={jobCode ? `/apply/${jobCode}` : "/apply"}
        onOpenChange={(open) => {
          setAuthModalOpen(open);
          if (!open) {
            setSignedInCandidate(getStoredCandidate());
          }
        }}
      />

      <SharedCandidatePortalFooter />
    </div>
  );
}
