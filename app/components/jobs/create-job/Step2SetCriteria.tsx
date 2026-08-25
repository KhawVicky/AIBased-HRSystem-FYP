// Shows the criteria setup step.
import { useState, useEffect, useRef } from "react";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { Textarea } from "../../ui/textarea";
import { Card, CardContent } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Checkbox } from "../../ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../ui/select";
import { toast } from "sonner";
import { AlertTriangle, BriefcaseBusiness, Filter, GraduationCap, Languages, LoaderCircle, MapPin, Pencil, RefreshCw, Timer, Trash2, Plus, X, type LucideIcon } from "lucide-react";
import { apiFetch } from "../../../lib/api";
import {
  applyCriterionTypeWeights,
  generateJDCriteria,
  inferEligibilitySuggestions,
  JD_CRITERION_TYPES,
  type JDCriterionType,
  type GeneratedEligibilitySuggestions,
  type ParsedJDData,
} from "../../../lib/jdParsingApi";
import type {
  Criteria,
  EligibilityFilterDefinition,
  EligibilityFilters,
} from "../CreateJob";

interface Step2Props {
  criteria: Criteria[];
  setCriteria: (criteria: Criteria[]) => void;
  jdData: ParsedJDData | null;
  lastGeneratedSource: string | null;
  setLastGeneratedSource: (source: string) => void;
  eligibilityFilters: EligibilityFilters;
  setEligibilityFilters: React.Dispatch<React.SetStateAction<EligibilityFilters>>;
  onNext: () => void;
  onBack: () => void;
  isSaving?: boolean;
}

const TOTAL_WEIGHT = 100;

const eligibilityFilterIcons: Record<string, LucideIcon> = {
  minCGPA: GraduationCap,
  minExperience: BriefcaseBusiness,
  educationLevel: GraduationCap,
  maxNoticePeriod: Timer,
  requiredLanguage: Languages,
  requiredLocation: MapPin,
};

// Renders the Step2 Set Criteria component.
export function Step2SetCriteria({
  criteria,
  setCriteria,
  jdData,
  lastGeneratedSource,
  setLastGeneratedSource,
  eligibilityFilters,
  setEligibilityFilters,
  onNext,
  onBack,
  isSaving = false,
}: Step2Props) {
  const [isCustomModalOpen, setIsCustomModalOpen] =
    useState(false);
  const [customCriterionName, setCustomCriterionName] =
    useState("");
  const [customCriterionWeight, setCustomCriterionWeight] =
    useState(5);
  const [customCriterionType, setCustomCriterionType] =
    useState<JDCriterionType>("relevant_skill");
  const [customCriterionNote, setCustomCriterionNote] =
    useState("");
  const [isEligibilityModalOpen, setIsEligibilityModalOpen] =
    useState(false);
  const [eligibilityFilterDefinitions, setEligibilityFilterDefinitions] =
    useState<EligibilityFilterDefinition[]>([]);
  const [isLoadingEligibilityFilters, setIsLoadingEligibilityFilters] =
    useState(true);
  const [isDetectingEligibilityFilters, setIsDetectingEligibilityFilters] =
    useState(false);
  const [eligibilityDetectionError, setEligibilityDetectionError] =
    useState<string | null>(null);
  const [isGeneratingCriteria, setIsGeneratingCriteria] = useState(false);
  const [workingCriteria, setWorkingCriteria] =
    useState<Criteria[]>(criteria);
  const generationRequestedSource = useRef<string | null>(null);
  const eligibilityDetectionRequestedSource = useRef<string | null>(null);
  // Track the JD text used for the latest criteria result.
  const currentCriteriaSource = jdData
    ? JSON.stringify({
        jobTitle: jdData.jobTitle,
        department: jdData.department,
        responsibilities: jdData.responsibilities,
        requirements: jdData.requirements,
      })
    : null;
  const criteriaSourceChanged =
    Boolean(lastGeneratedSource) &&
    Boolean(currentCriteriaSource) &&
    lastGeneratedSource !== currentCriteriaSource;

  // Updates eligibility filter.
  const updateEligibilityFilter = <K extends keyof EligibilityFilters>(
    key: K,
    value: EligibilityFilters[K],
  ) => {
    setEligibilityFilters({
      ...eligibilityFilters,
      [key]: value,
    });
  };

  const selectTriggerClass =
    "mt-2 !h-11 min-h-11 border-slate-200 bg-slate-50 px-4 text-slate-700 shadow-sm transition-colors hover:bg-slate-100";
  // Checks the eligibility enabled condition.
  const isEligibilityEnabled = (key: string) =>
    (eligibilityFilters.enabledFilters ?? []).includes(key);
  // Toggles eligibility filter.
  const toggleEligibilityFilter = (key: string) => {
    const enabledFilters = isEligibilityEnabled(key)
      ? (eligibilityFilters.enabledFilters ?? []).filter((item) => item !== key)
      : [...(eligibilityFilters.enabledFilters ?? []), key];

    updateEligibilityFilter("enabledFilters", enabledFilters);
  };

  const applyEligibilitySuggestions = (
    suggestions: GeneratedEligibilitySuggestions,
  ) => {
    setEligibilityFilters((current) => ({
      ...current,
      minCGPA: suggestions.minCGPA ?? current.minCGPA,
      minExperience: suggestions.minExperience ?? current.minExperience,
      educationLevel: suggestions.educationLevel ?? current.educationLevel,
      maxNoticePeriod:
        suggestions.maxNoticePeriod ?? current.maxNoticePeriod,
      requiredLanguage:
        suggestions.requiredLanguage ?? current.requiredLanguage,
      requiredLocation:
        suggestions.requiredLocation ?? current.requiredLocation,
      enabledFilters: Array.from(
        new Set([
          ...(current.enabledFilters ?? []),
          ...suggestions.enabledFilters,
        ]),
      ).filter((filterKey) => filterKey !== "internshipAccepted"),
    }));
  };
  // Updates custom eligibility filter.
  const updateCustomEligibilityFilter = (
    id: string,
    value: string,
  ) => {
    const definition = eligibilityFilterDefinitions.find(
      (filter) => filter.filterKey === id,
    );
    const label = definition?.filterName || id;
    const existing = eligibilityFilters.customFilters ?? [];
    const nextCustomFilters = existing.some((filter) => filter.id === id)
      ? existing.map((filter) =>
          filter.id === id ? { ...filter, label, value } : filter,
        )
      : [...existing, { id, label, value }];

    setEligibilityFilters({
      ...eligibilityFilters,
      customFilters: nextCustomFilters,
    });
  };
  // Renders the Field Label component.
  const FieldLabel = ({
    icon: Icon,
    children,
  }: {
    icon: LucideIcon;
    children: React.ReactNode;
  }) => (
    <Label className="mb-2 flex items-center gap-2 font-medium text-slate-700">
      <Icon className="h-4 w-4 text-[#003B7A]" />
      {children}
    </Label>
  );

  // Load filters that HR can manage in Settings.
  useEffect(() => {
    setIsLoadingEligibilityFilters(true);
    apiFetch<{ filters: EligibilityFilterDefinition[] }>(
      "/eligibility-filter-definitions",
    )
      .then((data) => {
        setEligibilityFilterDefinitions(
          (data.filters || []).filter(
            (definition) => definition.filterKey !== "internshipAccepted",
          ),
        );
      })
      .catch((error) => {
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load eligibility filters",
        );
      })
      .finally(() => setIsLoadingEligibilityFilters(false));
  }, []);

  const detectEligibilityFilters = async () => {
    if (
      !jdData ||
      (jdData.responsibilities.length === 0 &&
        jdData.requirements.length === 0)
    ) {
      setIsDetectingEligibilityFilters(false);
      return;
    }

    setIsDetectingEligibilityFilters(true);
    setEligibilityDetectionError(null);
    try {
      const suggestions = inferEligibilitySuggestions(jdData);
      applyEligibilitySuggestions(suggestions);
    } catch (error) {
      setEligibilityDetectionError(
        error instanceof Error
          ? error.message
          : "Eligibility filters could not be detected.",
      );
    } finally {
      setIsDetectingEligibilityFilters(false);
    }
  };

  const retryEligibilityDetection = () => {
    eligibilityDetectionRequestedSource.current = null;
    void detectEligibilityFilters();
  };

  // Detect system-owned filters as soon as the reviewed JD is available. This
  // is independent from the slower criteria generation request.
  useEffect(() => {
    if (
      !jdData ||
      !currentCriteriaSource ||
      (jdData.responsibilities.length === 0 &&
        jdData.requirements.length === 0)
    ) {
      setIsDetectingEligibilityFilters(false);
      return;
    }

    if (
      eligibilityDetectionRequestedSource.current === currentCriteriaSource
    ) {
      return;
    }

    eligibilityDetectionRequestedSource.current = currentCriteriaSource;
    void detectEligibilityFilters();
  }, [currentCriteriaSource, jdData]);

  // Ask the criteria service for a new HR-reviewable result.
  const handleGenerateCriteria = async () => {
    if (
      !jdData ||
      (jdData.responsibilities.length === 0 &&
        jdData.requirements.length === 0)
    ) {
      toast.error(
        "Add responsibilities or requirements before generating criteria.",
      );
      return;
    }

    setIsGeneratingCriteria(true);
    try {
      const result = await generateJDCriteria(jdData);
      const generatedCriteria = applyCriterionTypeWeights(
        result.data.criteria.map((criterion) => ({
          id: criterion.id,
          category: criterion.category,
          type: criterion.type,
          name: criterion.name,
          weight: criterion.weight,
          status: "active" as const,
          sourceText: criterion.jdEvidence.join(" | "),
          evidenceRule: criterion.resumeEvidenceToCheck,
          jdEvidence: criterion.jdEvidence,
          explanation: criterion.explanation,
          resumeEvidenceToCheck: criterion.resumeEvidenceToCheck,
          isAutoDetected: true,
        })),
      );
      const detectedEligibility = inferEligibilitySuggestions(jdData);
      const serviceEligibility = result.data.eligibilitySuggestions || {
        minCGPA: null,
        minExperience: null,
        educationLevel: null,
        maxNoticePeriod: null,
        requiredLanguage: null,
        requiredLocation: null,
        enabledFilters: [],
      };
      const suggestions = {
        minCGPA: serviceEligibility.minCGPA ?? detectedEligibility.minCGPA,
        minExperience:
          serviceEligibility.minExperience ?? detectedEligibility.minExperience,
        educationLevel:
          serviceEligibility.educationLevel ?? detectedEligibility.educationLevel,
        maxNoticePeriod:
          serviceEligibility.maxNoticePeriod ?? detectedEligibility.maxNoticePeriod,
        requiredLanguage:
          serviceEligibility.requiredLanguage ?? detectedEligibility.requiredLanguage,
        requiredLocation:
          serviceEligibility.requiredLocation ?? detectedEligibility.requiredLocation,
        enabledFilters: Array.from(
          new Set([
            ...detectedEligibility.enabledFilters,
            ...(serviceEligibility.enabledFilters || []),
          ]),
        ).filter((filterKey) => filterKey !== "internshipAccepted"),
      };
      setWorkingCriteria(generatedCriteria);
      applyEligibilitySuggestions(suggestions);
      if (currentCriteriaSource) {
        setLastGeneratedSource(currentCriteriaSource);
      }
      toast.success("Suggested criteria generated for HR review");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Suggested criteria could not be generated.",
      );
    } finally {
      setIsGeneratingCriteria(false);
    }
  };

  // Keep generated and edited criteria in the shared Create Job state so they
  // survive navigation between steps and component remounts.
  useEffect(() => {
    setCriteria(workingCriteria);
  }, [setCriteria, workingCriteria]);

  useEffect(() => {
    const hasJDContent =
      Boolean(jdData) &&
      Boolean(currentCriteriaSource) &&
      Boolean(jdData?.responsibilities.length || jdData?.requirements.length);

    if (!hasJDContent || !currentCriteriaSource) {
      return;
    }

    const shouldGenerate =
      (workingCriteria.length === 0 && !lastGeneratedSource) ||
      criteriaSourceChanged;

    if (
      !shouldGenerate ||
      generationRequestedSource.current === currentCriteriaSource
    ) {
      return;
    }

    generationRequestedSource.current = currentCriteriaSource;
    void handleGenerateCriteria();
  }, [
    criteriaSourceChanged,
    currentCriteriaSource,
    jdData,
    lastGeneratedSource,
    workingCriteria.length,
  ]);

  const totalWeight = workingCriteria.reduce(
    (sum, item) => sum + item.weight,
    0,
  );

  // Normalizes criteria to100.
  const normalizeCriteriaTo100 = (
    currentCriteria: Criteria[],
  ) => {
    // Keep every criterion while making the total exactly 100.
    if (currentCriteria.length === 0) return [];

    if (currentCriteria.length === 1) {
      return [{ ...currentCriteria[0], weight: TOTAL_WEIGHT }];
    }

    const currentTotal = currentCriteria.reduce(
      (sum, c) => sum + c.weight,
      0,
    );

    let normalized = currentCriteria.map((c) => ({
      ...c,
      weight: Math.max(
        1,
        Math.floor((c.weight / currentTotal) * TOTAL_WEIGHT),
      ),
    }));

    let assigned = normalized.reduce(
      (sum, c) => sum + c.weight,
      0,
    );
    let diff = TOTAL_WEIGHT - assigned;
    let index = 0;

    while (diff !== 0 && normalized.length > 0) {
      const item = normalized[index % normalized.length];

      if (diff > 0) {
        item.weight += 1;
        diff -= 1;
      } else if (diff < 0 && item.weight > 1) {
        item.weight -= 1;
        diff += 1;
      }

      index++;
      if (index > 1000) break;
    }

    return normalized;
  };

  // Handles delete criteria.
  const handleDeleteCriteria = (id: string) => {
    setWorkingCriteria(
      workingCriteria.filter((criterion) => criterion.id !== id),
    );
    toast.success("Criterion deleted");
  };

  // Handles update criteria.
  const handleUpdateCriteria = (
    id: string,
    field: keyof Criteria,
    value: string | number | boolean,
  ) => {
    setWorkingCriteria(
      workingCriteria.map((criterion) =>
        criterion.id === id
          ? { ...criterion, [field]: value }
          : criterion,
      ),
    );
  };

  // Opens custom modal.
  const openCustomModal = () => {
    setCustomCriterionName("");
    setCustomCriterionWeight(5);
    setCustomCriterionType("relevant_skill");
    setCustomCriterionNote("");
    setIsCustomModalOpen(true);
  };

  // Closes custom modal.
  const closeCustomModal = () => {
    setIsCustomModalOpen(false);
  };

  // Handles confirm custom criteria.
  const handleConfirmCustomCriteria = () => {
    if (!customCriterionName.trim()) {
      toast.error("Please enter a criterion name");
      return;
    }

    const safeCustomWeight = Math.max(
      1,
      Math.min(customCriterionWeight, TOTAL_WEIGHT),
    );

    const newCriterion: Criteria = {
      id: Date.now().toString(),
      category: customCriterionType,
      type: customCriterionType,
      name: customCriterionName,
      weight: safeCustomWeight,
      status: "active",
      sourceText: "",
      explanation: customCriterionNote,
      isAutoDetected: false,
    };

    const combined = [...workingCriteria, newCriterion];
    const normalized = normalizeCriteriaTo100(combined);

    setWorkingCriteria(normalized);
    setIsCustomModalOpen(false);
    toast.success("Custom criterion added");
  };

  // Handles continue.
  const handleContinue = () => {
    // Stop only when a value cannot be saved safely.
    if (workingCriteria.length === 0) {
      toast.error("Please add at least one criterion");
      return;
    }

    if (
      workingCriteria.some(
        (criterion) => criterion.name.trim() === "",
      )
    ) {
      toast.error("Every criterion must have a name");
      return;
    }

    if (
      workingCriteria.some(
        (criterion) =>
          !JD_CRITERION_TYPES.includes(criterion.type),
      )
    ) {
      toast.error("Every criterion must use an allowed type");
      return;
    }

    if (
      workingCriteria.some(
        (criterion) =>
          !Number.isFinite(criterion.weight) ||
          criterion.weight <= 0,
      )
    ) {
      toast.error("Every criterion weight must be greater than 0");
      return;
    }

    if (totalWeight !== TOTAL_WEIGHT) {
      toast.error("Total weight must be exactly 100%");
      return;
    }

    setCriteria(workingCriteria);
    onNext();
  };

  // Gets definition options.
  const getDefinitionOptions = (
    definition: EligibilityFilterDefinition,
    fallback: string[],
  ) => (definition.options.length > 0 ? definition.options : fallback);

  // Gets custom eligibility value.
  const getCustomEligibilityValue = (key: string) =>
    (eligibilityFilters.customFilters ?? []).find((filter) => filter.id === key)
      ?.value || "";

  // Renders eligibility field.
  const renderEligibilityField = (
    definition: EligibilityFilterDefinition,
  ) => {
    // System filters use fixed controls. HR filters use their saved type.
    const Icon = eligibilityFilterIcons[definition.filterKey] || Filter;

    if (definition.filterKey === "minCGPA") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Input
            type="number"
            step="0.01"
            min="0"
            max="4.0"
            value={eligibilityFilters.minCGPA}
            onChange={(event) =>
              updateEligibilityFilter("minCGPA", parseFloat(event.target.value) || 0)
            }
            className="mt-2 !h-11 min-h-11 border-slate-200 bg-slate-50 px-4 text-slate-700 shadow-sm"
          />
        </div>
      );
    }

    if (definition.filterKey === "minExperience") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Select
            value={eligibilityFilters.minExperience}
            onValueChange={(value) => updateEligibilityFilter("minExperience", value)}
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select experience" />
            </SelectTrigger>
            <SelectContent>
              {getDefinitionOptions(definition, ["Internship", "0 year", "1 year", "2 years", "3 years", "4 years", "5+ years"]).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (definition.filterKey === "educationLevel") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Select
            value={eligibilityFilters.educationLevel}
            onValueChange={(value) => updateEligibilityFilter("educationLevel", value)}
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select education level" />
            </SelectTrigger>
            <SelectContent>
              {getDefinitionOptions(definition, ["SPM", "STPM / Foundation / Matriculation", "Diploma", "Bachelor Degree", "Master Degree", "PhD"]).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (definition.filterKey === "maxNoticePeriod") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Select
            value={eligibilityFilters.maxNoticePeriod}
            onValueChange={(value) => updateEligibilityFilter("maxNoticePeriod", value)}
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select notice period" />
            </SelectTrigger>
            <SelectContent>
              {getDefinitionOptions(definition, ["Any", "Immediate", "14 days", "30 days", "60 days", "90 days"]).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (definition.filterKey === "requiredLanguage") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Select
            value={eligibilityFilters.requiredLanguage}
            onValueChange={(value) => updateEligibilityFilter("requiredLanguage", value)}
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select language" />
            </SelectTrigger>
            <SelectContent>
              {getDefinitionOptions(definition, ["Any", "English", "Bahasa Malaysia", "Mandarin", "Tamil", "Japanese", "Korean"]).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (definition.filterKey === "requiredLocation") {
      return (
        <div key={definition.filterKey}>
          <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
          <Select
            value={eligibilityFilters.requiredLocation}
            onValueChange={(value) => updateEligibilityFilter("requiredLocation", value)}
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select location" />
            </SelectTrigger>
            <SelectContent>
              {getDefinitionOptions(definition, ["Any", "Penang", "Kuala Lumpur", "Selangor", "Johor", "Perak", "Malaysia only", "Open to relocation"]).map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      );
    }

    const customValue = getCustomEligibilityValue(definition.filterKey);

    return (
      <div key={definition.filterKey}>
        <FieldLabel icon={Icon}>{definition.filterName}</FieldLabel>
        {definition.filterType === "dropdown" ? (
          <Select
            value={customValue}
            onValueChange={(value) =>
              updateCustomEligibilityFilter(definition.filterKey, value)
            }
          >
            <SelectTrigger className={selectTriggerClass}>
              <SelectValue placeholder="Select option" />
            </SelectTrigger>
            <SelectContent>
              {definition.options.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            type={definition.filterType === "number" ? "number" : "text"}
            value={customValue}
            onChange={(event) =>
              updateCustomEligibilityFilter(
                definition.filterKey,
                event.target.value,
              )
            }
            placeholder="Enter requirement"
            className="mt-2 !h-11 min-h-11 border-slate-200 bg-slate-50 px-4 text-slate-700 shadow-sm"
          />
        )}
      </div>
    );
  };

  const selectedEligibilityDefinitions = eligibilityFilterDefinitions.filter(
    (definition) => isEligibilityEnabled(definition.filterKey),
  );
  const eligibilityIsLoading =
    isLoadingEligibilityFilters || isDetectingEligibilityFilters;

  return (
    <>
      <div className="space-y-8">
        <Card className="border border-slate-200 shadow-sm">
          <CardContent className="p-8">
  <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
    <div>
      <h2 className="mb-2 text-xl font-semibold text-[#003B7A]">
        Eligibility Filters
      </h2>
      <p className="text-sm text-slate-600">
        Filters are separated from scoring criteria so
        HR can set minimum requirements clearly.
      </p>
    </div>
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => setIsEligibilityModalOpen(true)}
      disabled={eligibilityIsLoading}
      className="shrink-0 border-[#003B7A] text-[#003B7A] hover:bg-blue-50"
    >
      <Pencil className="mr-2 h-4 w-4" />
      Manage Filters
    </Button>
  </div>

  <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
    {eligibilityIsLoading ? (
      <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50/50 p-5 text-sm text-[#003B7A] md:col-span-2 xl:col-span-4">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        {isLoadingEligibilityFilters
          ? "Loading available eligibility filters..."
          : "Detecting eligibility requirements from the JD..."}
      </div>
    ) : eligibilityDetectionError ? (
      <div className="flex items-center justify-between gap-4 rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-700 md:col-span-2 xl:col-span-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{eligibilityDetectionError}</span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={retryEligibilityDetection}
          className="shrink-0 border-red-300 text-red-700 hover:bg-red-100"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    ) : selectedEligibilityDefinitions.length > 0 ? (
      selectedEligibilityDefinitions.map(renderEligibilityField)
    ) : (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500 md:col-span-2 xl:col-span-4">
        No eligibility filters selected. Use Manage Filters to choose which requirements to apply.
      </div>
    )}
  </div>
</CardContent>
        </Card>

        <Dialog open={isEligibilityModalOpen} onOpenChange={setIsEligibilityModalOpen}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Choose Eligibility Filters</DialogTitle>
            </DialogHeader>

            <div className="grid gap-3 py-2 sm:grid-cols-2">
              {isLoadingEligibilityFilters ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 sm:col-span-2">
                  Loading eligibility filters...
                </div>
              ) : eligibilityFilterDefinitions.length > 0 ? (
                eligibilityFilterDefinitions.map((definition) => {
                  const checked = isEligibilityEnabled(definition.filterKey);
                  const Icon = eligibilityFilterIcons[definition.filterKey] || Filter;

                  return (
                    <div
                      key={definition.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => toggleEligibilityFilter(definition.filterKey)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          toggleEligibilityFilter(definition.filterKey);
                        }
                      }}
                      className={`flex items-center gap-3 rounded-lg border p-4 text-left transition-colors ${
                        checked
                          ? "border-[#003B7A] bg-blue-50"
                          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleEligibilityFilter(definition.filterKey)}
                        onClick={(event) => event.stopPropagation()}
                        aria-label={`Select ${definition.filterName}`}
                      />
                      <span className="flex min-w-0 flex-1 items-center gap-3">
                        <Icon className="h-4 w-4 shrink-0 text-[#003B7A]" />
                        <span className="block min-w-0 truncate font-semibold text-slate-950">
                          {definition.filterName}
                        </span>
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500 sm:col-span-2">
                  No eligibility filters found.
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                onClick={() => setIsEligibilityModalOpen(false)}
              >
                Done
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Card className="border border-slate-200 shadow-sm">
          <CardContent className="p-8">
            <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[#003B7A] mb-2">
                  Criteria
                </h2>
                <p className="text-sm text-slate-600">
                  Review and edit the criteria generated from the reviewed JD
                  before they are saved.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={openCustomModal}
                  disabled={isGeneratingCriteria}
                  className="border-[#003B7A] text-[#003B7A] hover:bg-blue-50"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Criterion
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              {isGeneratingCriteria ? (
                <div className="flex min-h-28 items-center justify-center gap-3 rounded-md border border-dashed border-blue-200 bg-blue-50/40 text-sm text-[#003B7A]">
                  <LoaderCircle className="h-5 w-5 animate-spin" />
                  Generating criteria from the reviewed JD...
                </div>
              ) : workingCriteria.length === 0 ? (
                <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
                  No criteria were generated from the current job description.
                  Add a criterion manually if needed.
                </div>
              ) : (
                workingCriteria.map((criterion, index) => (
                  <div
                    key={criterion.id}
                    className="rounded-lg border border-slate-200 bg-white p-5 transition-colors hover:border-blue-200"
                  >
                    <div className="mb-3 flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="pr-[5px] text-sm font-semibold text-[#003B7A]">
                          Criteria {index + 1}
                        </span>
                        <Badge
                          variant="outline"
                          className={
                            criterion.isAutoDetected
                              ? "border-blue-200 bg-blue-50 text-xs text-blue-600"
                              : "border-slate-200 bg-slate-100 text-xs text-slate-700"
                          }
                        >
                          {criterion.isAutoDetected
                            ? "Auto-detected from JD"
                            : "Manual"}
                        </Badge>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteCriteria(criterion.id)}
                        className="-mr-2 text-red-500 hover:bg-red-50 hover:text-red-700"
                        title="Delete criterion"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    <div className="mb-4 grid items-end gap-4 md:grid-cols-[1fr_140px]">
                      <div>
                        <Label className="mb-2 block text-xs text-slate-600">
                          Criterion Name
                        </Label>
                        <Input
                          value={criterion.name}
                          onChange={(event) =>
                            handleUpdateCriteria(
                              criterion.id,
                              "name",
                              event.target.value,
                            )
                          }
                          className="text-sm"
                          placeholder="Enter criterion name"
                        />
                      </div>

                      <div>
                        <Label className="mb-2 block text-xs text-slate-600">
                          Weight
                        </Label>
                        <Input
                          type="number"
                          min="1"
                          max="100"
                          value={criterion.weight}
                          onChange={(event) =>
                            handleUpdateCriteria(
                              criterion.id,
                              "weight",
                              Number(event.target.value),
                            )
                          }
                          className="text-center text-sm"
                        />
                      </div>
                    </div>

                    <div>
                      <Label className="mb-2 block text-xs text-slate-600">
                        Explanation
                      </Label>
                      <Textarea
                        value={criterion.explanation || ""}
                        onChange={(event) =>
                          handleUpdateCriteria(
                            criterion.id,
                            "explanation",
                            event.target.value,
                          )
                        }
                        className="min-h-[64px] text-sm"
                        placeholder={
                          criterion.isAutoDetected
                            ? "Enter note or explanation"
                            : "Enter optional note"
                        }
                      />
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 mx-[0px] mt-[20px] mb-[16px] hover:border-blue-200 transition-colors">
              <div>
                <p className="text-sm font-medium text-slate-800">
                  Total Weight
                </p>
                <p className="text-xs text-slate-500">
                  Scoring criteria must always total 100%
                </p>
              </div>
              <div className="text-lg font-bold text-[#003B7A]">
                {totalWeight}%
              </div>
            </div>
          </CardContent>
        </Card>
            
        <div className="flex items-center justify-between pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            className="border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            Back
          </Button>

          <Button
            type="button"
            onClick={handleContinue}
            disabled={isSaving || isGeneratingCriteria}
            className="bg-[#003B7A] hover:bg-[#002f63] px-8"
          >
            Confirm Criteria
          </Button>
        </div>
      </div>

      {isCustomModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={closeCustomModal}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-[#003B7A]">
                Add Custom Criteria
              </h3>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={closeCustomModal}
                aria-label="Close"
                title="Close"
                className="text-slate-500 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <Label className="mb-2 block font-medium text-slate-700">
                  Criterion Type
                </Label>
                <Select
                  value={customCriterionType}
                  onValueChange={(value: JDCriterionType) =>
                    setCustomCriterionType(value)
                  }
                >
                  <SelectTrigger className="mt-2 h-11 border-slate-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {JD_CRITERION_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-[1fr_140px] gap-4 items-end">
                <div>
                  <Label className="text-slate-700 font-medium mb-2 block">
                    Criterion Name
                  </Label>
                  <Input
                    value={customCriterionName}
                    onChange={(e) =>
                      setCustomCriterionName(e.target.value)
                    }
                    placeholder="e.g., Communication with stakeholders"
                    className="mt-2"
                  />
                </div>

                <div>
                  <Label className="text-slate-700 font-medium mb-2 block">
                    Weight
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={customCriterionWeight}
                    onChange={(e) =>
                      setCustomCriterionWeight(
                        parseInt(e.target.value) || 1,
                      )
                    }
                    className="mt-2"
                  />
                </div>
              </div>

              <div>
                <Label className="text-slate-700 font-medium mb-2">
                  Explanation
                </Label>
                <Textarea
                  value={customCriterionNote}
                  onChange={(e) =>
                    setCustomCriterionNote(e.target.value)
                  }
                  placeholder="Enter optional note"
                  className="mt-2 min-h-[72px]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
              <Button
                type="button"
                variant="outline"
                onClick={closeCustomModal}
                className="border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </Button>

              <Button
                type="button"
                onClick={handleConfirmCustomCriteria}
                className="bg-[#003B7A] hover:bg-[#002f63]"
              >
                Add Criterion
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
