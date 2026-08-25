// Shows the Excel upload step.
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  BriefcaseBusiness,
  Building2,
  Check,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  GripVertical,
  Layers3,
  ListChecks,
  LoaderCircle,
  Banknote,
  MapPin,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import type { JobData } from "../CreateJob";
import {
  extractJDSheet,
  inferEmploymentType,
  listJDSheets,
  type JDSheetSummary,
  type ParsedJDData,
} from "../../../lib/jdParsingApi";
import { fetchJobDescriptionFile } from "../../../lib/api";
import { Button } from "../../ui/button";
import { Card, CardContent } from "../../ui/card";
import { Input } from "../../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../ui/dialog";
import { RadioGroup, RadioGroupItem } from "../../ui/radio-group";
import { Textarea } from "../../ui/textarea";

interface Step1Props {
  jobData: JobData;
  setJobData: (data: JobData) => void;
  onNext: () => void;
  onCancel: () => void;
  isEditMode?: boolean;
  isSaving?: boolean;
  jobId?: number | null;
}

type JobDetailList = "qualifications" | "responsibilities";

interface DraggedJobDetail {
  list: JobDetailList;
  index: number;
}

// Renders the Step1 Upload JD component.
export function Step1UploadJD({
  jobData,
  setJobData,
  onNext,
  onCancel,
  isEditMode = false,
  isSaving = false,
  jobId = null,
}: Step1Props) {
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [isParsing, setIsParsing] = useState(false);
  const [availableSheets, setAvailableSheets] = useState<JDSheetSummary[]>([]);
  const [selectedSheetName, setSelectedSheetName] = useState("");
  const [sheetDialogOpen, setSheetDialogOpen] = useState(false);
  const [savedFile, setSavedFile] = useState<File | null>(null);
  const [draggedJobDetail, setDraggedJobDetail] =
    useState<DraggedJobDetail | null>(null);
  const [dragOverList, setDragOverList] = useState<JobDetailList | null>(null);
  const displayedFileName = jobData.jdFile?.name || jobData.savedJdFileName;

  // Load the saved Excel file whenever the current job already has one.
  useEffect(() => {
    if (
      !jobId ||
      !jobData.savedJdFileName ||
      !jobData.savedJdFilePath ||
      savedFile
    ) {
      return;
    }

    let cancelled = false;
    fetchJobDescriptionFile(jobId, jobData.savedJdFileName)
      .then(async (file) => {
        const result = await listJDSheets(file);
        if (cancelled) return;
        setSavedFile(file);
        setAvailableSheets(result.sheets);
        setSelectedSheetName(result.sheets[0]?.sheetName || "");
      })
      .catch(() => {
        if (!cancelled) {
          toast.error("The saved Excel file could not be loaded");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    jobId,
    jobData.savedJdFileName,
    jobData.savedJdFilePath,
    savedFile,
  ]);

  // Restore the worksheet list when HR returns to this step.
  useEffect(() => {
    if (
      !jobData.jdFile ||
      !jobData.parsedJD ||
      availableSheets.length > 0
    ) {
      return;
    }

    const currentSheetName = jobData.parsedJD.sheetName;
    let cancelled = false;
    listJDSheets(jobData.jdFile)
      .then((result) => {
        if (cancelled) return;
        setAvailableSheets(result.sheets);
        setSelectedSheetName(
          result.sheets.some(
            (sheet) => sheet.sheetName === currentSheetName,
          )
            ? currentSheetName
            : result.sheets[0]?.sheetName || "",
        );
      })
      .catch(() => {
        if (!cancelled) {
          toast.error("The worksheet list could not be restored");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    availableSheets.length,
    jobData.jdFile,
    jobData.parsedJD,
  ]);

  // Parse one worksheet and copy its values into the form.
  const importSheet = async (file: File, sheetName: string) => {
    const result = await extractJDSheet(file, sheetName);
    const parsedJD: ParsedJDData = result.data;
    const inferredEmploymentType = inferEmploymentType(
      parsedJD.jobTitle,
      file.name,
    );

    setJobData({
      ...jobData,
      title: parsedJD.jobTitle,
      department: parsedJD.department,
      salary: parsedJD.salary,
      description: parsedJD.description,
      jdFile: file === savedFile ? jobData.jdFile : file,
      parsedJD,
      employmentType: jobData.employmentTypeManuallySet
        ? jobData.employmentType
        : inferredEmploymentType || "Full-time",
    });
    setErrors({});
    setSheetDialogOpen(false);

    result.warnings.forEach((warning) => toast.warning(warning));
    toast.success(`${parsedJD.sheetName} imported successfully`);
  };

  // Handles file upload.
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) return;

    // Check the file before sending it to the parsing service.
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (extension !== "xlsx") {
      setErrors({ file: "Only XLSX files are accepted" });
      toast.error("Only XLSX files are accepted");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setErrors({ file: "File size must be less than 5MB" });
      toast.error("File size must be less than 5MB");
      return;
    }

    setIsParsing(true);
    setAvailableSheets([]);
    setSelectedSheetName("");
    setJobData({ ...jobData, jdFile: file, parsedJD: null });
    setErrors({});

    try {
      const result = await listJDSheets(file);

      if (result.sheets.length === 1) {
        await importSheet(file, result.sheets[0].sheetName);
        return;
      }

      setAvailableSheets(result.sheets);
      setSelectedSheetName(result.sheets[0]?.sheetName || "");
      setSheetDialogOpen(true);
      toast.info("Select the worksheet to import");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The Excel file could not be processed.";
      setJobData({ ...jobData, jdFile: null, parsedJD: null });
      setErrors({ file: message });
      toast.error(message);
    } finally {
      setIsParsing(false);
    }
  };

  // Handles sheet import.
  const handleSheetImport = async () => {
    const file = jobData.jdFile || savedFile;
    if (!file || !selectedSheetName) return;

    setIsParsing(true);
    try {
      await importSheet(file, selectedSheetName);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The selected worksheet could not be imported.";
      setErrors({ file: message });
      toast.error(message);
    } finally {
      setIsParsing(false);
    }
  };

  // Removes file.
  const removeFile = () => {
    setJobData({
      ...jobData,
      jdFile: null,
      savedJdFileName: null,
      savedJdFilePath: null,
      parsedJD: isEditMode ? jobData.parsedJD : null,
    });
    setSavedFile(null);
    setAvailableSheets([]);
    setSelectedSheetName("");
    setSheetDialogOpen(false);
    setErrors({});
    toast.info("File removed");
  };

  // Updates job title.
  const updateJobTitle = (jobTitle: string) => {
    if (!jobData.parsedJD) return;
    setJobData({
      ...jobData,
      title: jobTitle,
      parsedJD: { ...jobData.parsedJD, jobTitle },
    });
  };

  // Updates department.
  const updateDepartment = (department: string) => {
    if (!jobData.parsedJD) return;
    setJobData({
      ...jobData,
      department,
      parsedJD: { ...jobData.parsedJD, department },
    });
  };

  // Updates salary.
  const updateSalary = (salary: string) => {
    if (!jobData.parsedJD) return;
    setJobData({
      ...jobData,
      salary,
      parsedJD: { ...jobData.parsedJD, salary },
    });
  };

  // Updates location.
  const updateLocation = (location: string) => {
    setJobData({ ...jobData, location });
  };

  // Updates the job type selected by HR.
  const updateEmploymentType = (employmentType: JobData["employmentType"]) => {
    setJobData({ ...jobData, employmentType, employmentTypeManuallySet: true });
  };

  // Updates responsibilities.
  const updateResponsibilities = (responsibilities: string[]) => {
    if (!jobData.parsedJD) return;
    setJobData({
      ...jobData,
      parsedJD: { ...jobData.parsedJD, responsibilities },
    });
  };

  // Updates responsibility.
  const updateResponsibility = (index: number, value: string) => {
    if (!jobData.parsedJD) return;
    const responsibilities = [...jobData.parsedJD.responsibilities];
    responsibilities[index] = value;
    updateResponsibilities(responsibilities);
  };

  // Provides the delete responsibility helper.
  const deleteResponsibility = (index: number) => {
    if (!jobData.parsedJD) return;
    updateResponsibilities(
      jobData.parsedJD.responsibilities.filter(
        (_, responsibilityIndex) => responsibilityIndex !== index,
      ),
    );
  };

  // Adds responsibility.
  const addResponsibility = () => {
    if (!jobData.parsedJD) return;
    updateResponsibilities([...jobData.parsedJD.responsibilities, ""]);
  };

  // Updates qualifications.
  const updateQualifications = (qualifications: string[]) => {
    if (!jobData.parsedJD) return;
    setJobData({
      ...jobData,
      parsedJD: {
        ...jobData.parsedJD,
        qualifications,
        requirements: [...qualifications],
      },
    });
  };

  // Updates qualification.
  const updateQualification = (index: number, value: string) => {
    if (!jobData.parsedJD) return;
    const qualifications = [...jobData.parsedJD.qualifications];
    qualifications[index] = value;
    updateQualifications(qualifications);
  };

  // Provides the delete qualification helper.
  const deleteQualification = (index: number) => {
    if (!jobData.parsedJD) return;
    updateQualifications(
      jobData.parsedJD.qualifications.filter(
        (_, qualificationIndex) => qualificationIndex !== index,
      ),
    );
  };

  // Adds qualification.
  const addQualification = () => {
    if (!jobData.parsedJD) return;
    updateQualifications([...jobData.parsedJD.qualifications, ""]);
  };

  // Starts a native drag so items can move between the two detail cards.
  const startJobDetailDrag = (
    event: React.DragEvent<HTMLButtonElement>,
    list: JobDetailList,
    index: number,
  ) => {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `${list}:${index}`);
    setDraggedJobDetail({ list, index });
  };

  // Clears the drag highlight after a drop or when dragging is cancelled.
  const clearJobDetailDrag = () => {
    setDraggedJobDetail(null);
    setDragOverList(null);
  };

  // Moves a detail to the other card and keeps requirements in sync.
  const moveJobDetail = (targetList: JobDetailList) => {
    if (!jobData.parsedJD || !draggedJobDetail) {
      clearJobDetailDrag();
      return;
    }

    if (draggedJobDetail.list === targetList) {
      clearJobDetailDrag();
      return;
    }

    const sourceItems = [
      ...jobData.parsedJD[draggedJobDetail.list],
    ];
    const [movedItem] = sourceItems.splice(draggedJobDetail.index, 1);
    if (movedItem === undefined) {
      clearJobDetailDrag();
      return;
    }

    const targetItems = [...jobData.parsedJD[targetList], movedItem];
    const responsibilities =
      targetList === "responsibilities" ? targetItems : sourceItems;
    const qualifications =
      targetList === "qualifications" ? targetItems : sourceItems;

    setJobData({
      ...jobData,
      parsedJD: {
        ...jobData.parsedJD,
        responsibilities,
        qualifications,
        requirements: [...qualifications],
      },
    });
    clearJobDetailDrag();
  };

  const handleJobDetailDragOver = (
    event: React.DragEvent<HTMLDivElement>,
    list: JobDetailList,
  ) => {
    if (!draggedJobDetail || draggedJobDetail.list === list) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setDragOverList(list);
  };

  const handleJobDetailDrop = (
    event: React.DragEvent<HTMLDivElement>,
    list: JobDetailList,
  ) => {
    event.preventDefault();
    moveJobDetail(list);
  };

  // Validates step.
  const validateStep = () => {
    const newErrors: Record<string, string> = {};
    const hasSavedFile = Boolean(
      jobData.savedJdFileName || jobData.savedJdFilePath,
    );
    const hasFile = Boolean(jobData.jdFile || savedFile || hasSavedFile);

    if (!hasFile) {
      newErrors.file = "Excel file is required";
    } else if (!jobData.parsedJD) {
      newErrors.file = "Select and import a worksheet before continuing";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handles continue.
  const handleContinue = () => {
    if (validateStep()) {
      onNext();
    } else {
      toast.error("Please complete the Excel import");
    }
  };

  return (
    <div className="space-y-8">
      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
          <div className="mb-6">
            <h2 className="mb-2 text-xl font-semibold text-black">
              Excel Upload
            </h2>
            <p className="text-sm text-slate-600">
              Upload an XLSX job description to import the job details.
            </p>
          </div>

          {!displayedFileName ? (
            <label
              htmlFor="jd-file"
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors hover:bg-slate-50 ${
                errors.file
                  ? "border-red-400 bg-red-50"
                  : "border-slate-300"
              }`}
            >
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
                <Upload className="h-7 w-7 text-[#003B7A]" />
              </div>
              <p className="mb-1 text-center text-base font-semibold text-slate-700">
                Drag and drop your Excel file here or Browse file
              </p>
              <p className="text-sm text-slate-500">XLSX only, max 5MB</p>
              <input
                id="jd-file"
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 p-5">
              <div className="flex min-w-0 items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-100">
                  <FileSpreadsheet className="h-6 w-6 text-[#003B7A]" />
                </div>
                <div className="min-w-0">
                  <p
                    className="truncate text-sm font-semibold text-slate-700"
                    title={displayedFileName}
                  >
                    {displayedFileName}
                  </p>
                  <p className="text-xs text-slate-500">
                    {jobData.jdFile || savedFile
                      ? `${((jobData.jdFile || savedFile)!.size / 1024).toFixed(2)} KB`
                      : "Saved Excel file"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {isParsing ? (
                  <span className="flex items-center gap-2 text-sm font-medium text-[#003B7A]">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Reading Excel
                  </span>
                ) : jobData.parsedJD ? (
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100"
                    title="Worksheet imported"
                  >
                    <Check className="h-5 w-5 text-green-600" />
                  </div>
                ) : null}

                {!isParsing && availableSheets.length > 1 ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setSheetDialogOpen(true)}
                    className="border-blue-200 text-[#003B7A] hover:bg-blue-50"
                  >
                    <Layers3 className="h-4 w-4" />
                    {jobData.parsedJD
                      ? "Change worksheet"
                      : "Select worksheet"}
                  </Button>
                ) : null}

                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={removeFile}
                  disabled={isParsing}
                  aria-label="Remove Excel file"
                  title="Remove file"
                >
                  <X className="h-5 w-5" />
                </Button>
                <input
                  id="jd-file"
                  type="file"
                  accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  onChange={handleFileUpload}
                  disabled={isParsing}
                  className="hidden"
                />
              </div>
            </div>
          )}

          {errors.file && (
            <p className="mt-2 text-sm text-red-500">{errors.file}</p>
          )}
        </CardContent>
      </Card>

      {jobData.parsedJD && (
        <div className="flex flex-col gap-8">
          <Card className="order-1 border border-slate-200 shadow-sm">
            <CardContent className="p-8">
              <div className="mb-5 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-semibold text-[#003B7A]">
                    Job Details
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Review and edit the information from the selected worksheet.
                  </p>
                </div>
                <span className="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-[#003B7A]">
                  {jobData.parsedJD.sheetName}
                </span>
              </div>

              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-5">
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <BriefcaseBusiness className="h-5 w-5 shrink-0 text-[#003B7A]" />
                    <label
                      htmlFor="imported-job-title"
                      className="text-xs font-medium uppercase text-slate-500"
                    >
                      Job Title
                    </label>
                  </div>
                  <Input
                    id="imported-job-title"
                    value={jobData.parsedJD.jobTitle}
                    onChange={(event) => updateJobTitle(event.target.value)}
                    placeholder="Enter job title"
                    className="mt-2 border-slate-300 bg-white"
                  />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <Building2 className="h-5 w-5 shrink-0 text-[#003B7A]" />
                    <label
                      htmlFor="imported-department"
                      className="text-xs font-medium uppercase text-slate-500"
                    >
                      Department
                    </label>
                  </div>
                  <Input
                    id="imported-department"
                    value={jobData.parsedJD.department}
                    onChange={(event) => updateDepartment(event.target.value)}
                    placeholder="Enter department"
                    className="mt-2 border-slate-300 bg-white"
                  />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <BriefcaseBusiness className="h-5 w-5 shrink-0 text-[#003B7A]" />
                    <label
                      htmlFor="imported-employment-type"
                      className="text-xs font-medium uppercase text-slate-500"
                    >
                      Job Type
                    </label>
                  </div>
                  <Select
                    value={jobData.employmentType}
                    onValueChange={(value) =>
                      updateEmploymentType(value as JobData["employmentType"])
                    }
                  >
                    <SelectTrigger
                      id="imported-employment-type"
                      className="mt-2 border-slate-300 bg-white"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Full-time">Full-time</SelectItem>
                      <SelectItem value="Part-time">Part-time</SelectItem>
                      <SelectItem value="Internship">Internship</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <MapPin className="h-5 w-5 shrink-0 text-[#003B7A]" />
                    <label
                      htmlFor="imported-location"
                      className="text-xs font-medium uppercase text-slate-500"
                    >
                      Location
                    </label>
                  </div>
                  <Input
                    id="imported-location"
                    type="text"
                    value={jobData.location}
                    onChange={(event) => updateLocation(event.target.value)}
                    placeholder="Enter job location"
                    className="mt-2 border-slate-300 bg-white"
                  />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <Banknote className="h-5 w-5 shrink-0 text-[#003B7A]" />
                    <label
                      htmlFor="imported-salary"
                      className="text-xs font-medium uppercase text-slate-500"
                    >
                      Salary
                    </label>
                    <span className="text-xs normal-case text-slate-400">
                      Optional
                    </span>
                  </div>
                  <Input
                    id="imported-salary"
                    type="text"
                    value={jobData.salary}
                    onChange={(event) => updateSalary(event.target.value)}
                    placeholder="Enter salary or salary range"
                    className="mt-2 border-slate-300 bg-white"
                  />
                </div>
              </div>

            </CardContent>
          </Card>

          <Card className="order-2 border border-slate-200 shadow-sm">
            <CardContent className="p-8">
              <div className="mb-3 flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#003B7A]" />
                <label
                  htmlFor="imported-job-description"
                  className="text-sm font-semibold text-slate-800"
                >
                  Job Description
                </label>
                <span className="text-xs text-slate-400">Optional</span>
              </div>
              <Textarea
                id="imported-job-description"
                value={jobData.description}
                onChange={(event) =>
                  setJobData({ ...jobData, description: event.target.value })
                }
                rows={3}
                placeholder="Enter a short description of the position"
                className="min-h-24 resize-y border-slate-300 bg-white leading-6"
              />
            </CardContent>
          </Card>

          <Card
            className={`order-4 border border-slate-200 shadow-sm ${
              dragOverList === "responsibilities"
                ? "ring-2 ring-blue-200"
                : ""
            }`}
            onDragOver={(event) =>
              handleJobDetailDragOver(event, "responsibilities")
            }
            onDrop={(event) => handleJobDetailDrop(event, "responsibilities")}
          >
            <CardContent className="p-8">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ListChecks className="h-5 w-5 text-[#003B7A]" />
                    <h4 className="text-sm font-semibold text-slate-800">
                      Responsibilities
                    </h4>
                    <span className="text-xs text-slate-500">
                      ({jobData.parsedJD.responsibilities.length})
                    </span>
                    <span className="text-xs text-slate-400">Optional</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addResponsibility}
                    className="border-blue-200 text-[#003B7A] hover:bg-blue-50"
                  >
                    <Plus className="h-4 w-4" />
                    Add responsibility
                  </Button>
                </div>

                {jobData.parsedJD.responsibilities.length > 0 ? (
                  <ol className="divide-y divide-slate-100 border-t border-slate-100">
                    {jobData.parsedJD.responsibilities.map(
                      (responsibility, index) => (
                        <li
                          key={index}
                          className="flex items-center gap-3 py-3"
                        >
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            draggable
                            onDragStart={(event) =>
                              startJobDetailDrag(
                                event,
                                "responsibilities",
                                index,
                              )
                            }
                            onDragEnd={clearJobDetailDrag}
                            aria-label={`Drag responsibility ${index + 1} to another section`}
                            title="Drag to another section"
                            className="h-6 w-6 shrink-0 cursor-grab text-slate-400 hover:bg-blue-50 hover:text-[#003B7A] active:cursor-grabbing"
                          >
                            <GripVertical className="h-4 w-4" />
                          </Button>
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-[#003B7A]">
                            {index + 1}
                          </span>
                          <Textarea
                            rows={1}
                            value={responsibility}
                            onChange={(event) =>
                              updateResponsibility(index, event.target.value)
                            }
                            aria-label={`Responsibility ${index + 1}`}
                            placeholder="Enter responsibility"
                            className="min-h-9 flex-1 resize-y border-slate-300 bg-white py-2 leading-5"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteResponsibility(index)}
                            aria-label={`Delete responsibility ${index + 1}`}
                            title="Delete responsibility"
                            className="shrink-0 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </li>
                      ),
                    )}
                  </ol>
                ) : (
                  <p className="border-t border-slate-100 py-4 text-sm text-slate-500">
                    No responsibilities added. You can continue without one.
                  </p>
                )}
            </CardContent>
          </Card>

          <Card
            className={`order-3 border border-slate-200 shadow-sm ${
              dragOverList === "qualifications" ? "ring-2 ring-blue-200" : ""
            }`}
            onDragOver={(event) =>
              handleJobDetailDragOver(event, "qualifications")
            }
            onDrop={(event) => handleJobDetailDrop(event, "qualifications")}
          >
            <CardContent className="p-8">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="h-5 w-5 text-[#003B7A]" />
                    <h4 className="text-sm font-semibold text-slate-800">
                      Qualifications
                    </h4>
                    <span className="text-xs text-slate-500">
                      ({jobData.parsedJD.qualifications.length})
                    </span>
                    <span className="text-xs text-slate-400">Optional</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addQualification}
                    className="border-blue-200 text-[#003B7A] hover:bg-blue-50"
                  >
                    <Plus className="h-4 w-4" />
                    Add qualification
                  </Button>
                </div>

                {jobData.parsedJD.qualifications.length > 0 ? (
                  <ol className="divide-y divide-slate-100 border-t border-slate-100">
                    {jobData.parsedJD.qualifications.map(
                      (qualification, index) => (
                        <li key={index} className="flex items-center gap-3 py-3">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            draggable
                            onDragStart={(event) =>
                              startJobDetailDrag(event, "qualifications", index)
                            }
                            onDragEnd={clearJobDetailDrag}
                            aria-label={`Drag qualification ${index + 1} to another section`}
                            title="Drag to another section"
                            className="h-6 w-6 shrink-0 cursor-grab text-slate-400 hover:bg-blue-50 hover:text-[#003B7A] active:cursor-grabbing"
                          >
                            <GripVertical className="h-4 w-4" />
                          </Button>
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-[#003B7A]">
                            {index + 1}
                          </span>
                          <Textarea
                            rows={1}
                            value={qualification}
                            onChange={(event) =>
                              updateQualification(index, event.target.value)
                            }
                            aria-label={`Qualification ${index + 1}`}
                            placeholder="Enter qualification"
                            className="min-h-9 flex-1 resize-y border-slate-300 bg-white py-2 leading-5"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteQualification(index)}
                            aria-label={`Delete qualification ${index + 1}`}
                            title="Delete qualification"
                            className="shrink-0 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </li>
                      ),
                    )}
                  </ol>
                ) : (
                  <p className="border-t border-slate-100 py-4 text-sm text-slate-500">
                    No qualifications added. You can continue without one.
                  </p>
                )}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="flex items-center justify-end pt-4">
        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSaving}
            className="border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleContinue}
            disabled={isParsing || isSaving}
            className="bg-[#003B7A] text-white hover:bg-[#002f63]"
          >
            Continue to Set Criteria
          </Button>
        </div>
      </div>

      <Dialog open={sheetDialogOpen} onOpenChange={setSheetDialogOpen}>
        <DialogContent className="max-h-[85vh] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-[#003B7A]">
              Select a worksheet
            </DialogTitle>
            <DialogDescription>
              This workbook contains multiple worksheets. Choose the job
              description you want to import.
            </DialogDescription>
          </DialogHeader>

          <RadioGroup
            value={selectedSheetName}
            onValueChange={setSelectedSheetName}
            className="min-h-0 gap-2 overflow-y-auto py-2 pr-2"
          >
            {availableSheets.map((sheet) => {
              const inputId = `sheet-${sheet.sheetName.replace(/\W+/g, "-")}`;
              return (
                <label
                  key={sheet.sheetName}
                  htmlFor={inputId}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border p-4 transition-colors ${
                    selectedSheetName === sheet.sheetName
                      ? "border-[#003B7A] bg-blue-50"
                      : "border-slate-200 hover:border-blue-200 hover:bg-slate-50"
                  }`}
                >
                  <RadioGroupItem
                    id={inputId}
                    value={sheet.sheetName}
                    className="border-slate-400 text-[#003B7A]"
                  />
                  <div className="min-w-0">
                    <p className="break-words text-sm font-semibold text-slate-800">
                      {sheet.sheetName}
                    </p>
                    <p className="mt-1 break-words text-xs text-slate-500">
                      {sheet.jobTitle || "Job title not found"}
                      {sheet.department ? ` · ${sheet.department}` : ""}
                    </p>
                  </div>
                </label>
              );
            })}
          </RadioGroup>

          <DialogFooter className="border-t border-slate-200 pt-4">
            <Button
              type="button"
              onClick={handleSheetImport}
              disabled={!selectedSheetName || isParsing}
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
            >
              {isParsing ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" />
              )}
              Import worksheet
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
