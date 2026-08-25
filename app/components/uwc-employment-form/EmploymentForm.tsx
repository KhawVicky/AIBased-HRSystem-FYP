// Shows the Employment Form view.
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { Check, PenLine, RotateCcw } from "lucide-react";
import uwcLogo from "../../assets/uwc-berhad-logo.png";
import { apiFetch, getStoredUser } from "../../lib/api";
import { createRows, RepeatableTable } from "./RepeatableTable";
import type { FormValues, TableColumn, TableRow } from "./types";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import "./employment-form.css";

const EMPLOYMENT_FORM_DESKTOP_WIDTH = 1280;
const EMPLOYMENT_FORM_PAGE_GUTTER = 24;
const getEmploymentFormViewportWidth = () =>
  Math.max(
    window.innerWidth,
    document.documentElement.getBoundingClientRect().width,
  );

// Renders the Bi component.
const Bi = ({ en, ms }: { en: string; ms?: string }) => (
  <>
    <span>{en}</span>
    {ms && <em> / {ms}</em>}
  </>
);

// Reads file as data url.
const readFileAsDataUrl = (file: File) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});

// Compresses image file.
const compressImageFile = (file: File) => new Promise<string>((resolve, reject) => {
  const image = new Image();
  const objectUrl = URL.createObjectURL(file);

  image.onload = () => {
    URL.revokeObjectURL(objectUrl);
    const maxSize = 420;
    const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const context = canvas.getContext("2d");

    if (!context) {
      reject(new Error("Unable to prepare photograph."));
      return;
    }

    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    resolve(canvas.toDataURL("image/jpeg", 0.72));
  };

  image.onerror = () => {
    URL.revokeObjectURL(objectUrl);
    reject(new Error("Unable to read photograph."));
  };

  image.src = objectUrl;
});

// Compresses image data url.
const compressImageDataUrl = (dataUrl: string) => new Promise<string>((resolve, reject) => {
  const image = new Image();

  image.onload = () => {
    const maxSize = 420;
    const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const context = canvas.getContext("2d");

    if (!context) {
      reject(new Error("Unable to prepare photograph."));
      return;
    }

    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    resolve(canvas.toDataURL("image/jpeg", 0.72));
  };

  image.onerror = () => reject(new Error("Unable to read photograph."));
  image.src = dataUrl;
});

// Prepares photo for submission.
const preparePhotoForSubmission = async (file: File) => {
  if (!file.type.startsWith("image/")) {
    return readFileAsDataUrl(file);
  }

  try {
    return await compressImageFile(file);
  } catch {
    return readFileAsDataUrl(file);
  }
};

// Ensures compact photo.
const ensureCompactPhoto = async (dataUrl: string) => {
  if (!dataUrl.startsWith("data:image/") || dataUrl.length < 250000) {
    return dataUrl;
  }

  try {
    return await compressImageDataUrl(dataUrl);
  } catch {
    return dataUrl;
  }
};

type EmploymentFormJob = {
  id: number;
  title: string;
  department: string;
  status?: "active" | "closed" | "draft" | "archived";
};

type EmploymentFormSubmission = {
  id: number;
  jobId: number;
  candidateData: {
    values?: FormValues;
    checks?: Record<string, string[]>;
    photo?: string;
    tables?: {
      languages?: Record<string, string>[];
      employment?: Record<string, string>[];
      qualifications?: Record<string, string>[];
      references?: Record<string, string>[];
      family?: Record<string, string>[];
      emergency?: Record<string, string>[];
    };
  };
  hrFormData?: {
    values?: FormValues;
    checks?: Record<string, string[]>;
  };
};

const optionalCandidateFieldNames = new Set([
  "employeeNo", "dateJoined", "preferredName", "leisureInterest", "epfNo", "incomeTaxNo",
  "bankName", "bankAccount", "nric", "passportNo", "passportExpiry", "availableDate",
  "currentAddress", "residentialPhone",
]);
const internalFieldNames = new Set([
  "employeeNo", "dateJoined", "hiringPosition", "startingSalary", "jobLevel", "dailyTransportClaim",
  "hiringDepartment", "maximumTransportClaim", "shiftGroup", "fuelClaim", "supervisor", "monthlyOtClaim",
  "mentor", "firstApprover", "secondApprover", "seniorHrManagerName", "seniorHrManagerSignature",
  "seniorHrManagerDate", "suitableDepartment", "interviewerComments", "hrJoiningDate", "hrOfferDate",
  "loaIssuedDate", "hrEmployeeNo", "badgeNo", "interviewerName", "interviewerSignature", "interviewerDate",
  "departmentManagerName", "departmentManagerSignature", "departmentManagerDate", "headApprovalName",
  "headApprovalSignature", "headApprovalDate",
]);

const hiringDepartmentFieldNames = new Set([
  "hiringPosition", "startingSalary", "jobLevel", "dailyTransportClaim", "hiringDepartment",
  "maximumTransportClaim", "shiftGroup", "fuelClaim", "supervisor", "monthlyOtClaim", "mentor",
  "firstApprover", "secondApprover", "suitableDepartment", "interviewerComments",
  "interviewerName", "interviewerSignature", "interviewerDate", "departmentManagerName",
  "departmentManagerSignature", "departmentManagerDate", "headApprovalName",
  "headApprovalSignature", "headApprovalDate",
]);

const hrFieldNames = new Set([
  "employeeNo", "dateJoined", "hrJoiningDate", "hrOfferDate", "loaIssuedDate", "hrEmployeeNo", "badgeNo",
  "seniorHrManagerName", "seniorHrManagerSignature", "seniorHrManagerDate",
  "epfNo", "incomeTaxNo", "bankName", "bankAccount",
]);

const employmentColumns: TableColumn[] = [
  { key: "from", label: <Bi en="From" ms="Dari" />, inputType: "date", width: "11%" },
  { key: "to", label: <Bi en="To" ms="Hingga" />, inputType: "date", width: "11%" },
  { key: "employer", label: <Bi en="Name of Employer" ms="Nama Majikan" />, width: "28%" },
  { key: "position", label: <Bi en="Position" ms="Jawatan" />, width: "18%" },
  { key: "salary", label: <Bi en="Salary" ms="Gaji" />, inputType: "number", width: "13%" },
  { key: "reason", label: <Bi en="Reason for Leaving" ms="Sebab Berhenti" />, width: "19%" },
];

const qualificationColumns: TableColumn[] = [
  { key: "from", label: <Bi en="From" ms="Dari" />, inputType: "date", width: "11%" },
  { key: "to", label: <Bi en="To" ms="Hingga" />, inputType: "date", width: "11%" },
  { key: "institution", label: <Bi en="School / College / University" ms="Sekolah / Kolej / Universiti" />, width: "38%" },
  { key: "field", label: <Bi en="Field of Study" ms="Bidang Pengajian" />, width: "22%" },
  { key: "grade", label: <Bi en="Highest Grade" ms="Kelulusan Tertinggi" />, width: "18%" },
];

const referenceColumns: TableColumn[] = [
  { key: "name", label: <Bi en="Name" ms="Nama" />, width: "25%" },
  { key: "telephone", label: <Bi en="Telephone No." ms="No. Telefon" />, width: "18%" },
  { key: "company", label: <Bi en="Company" ms="Syarikat" />, width: "20%" },
  { key: "occupation", label: <Bi en="Occupation" ms="Pekerjaan" />, width: "20%" },
  { key: "relationship", label: <Bi en="Relationship" ms="Hubungan" />, width: "17%" },
];

const familyColumns: TableColumn[] = [
  { key: "name", label: <Bi en="Name" ms="Nama" />, width: "30%" },
  { key: "relationship", label: <Bi en="Relationship" ms="Hubungan" />, width: "18%" },
  { key: "occupation", label: <Bi en="Occupation" ms="Pekerjaan" />, width: "22%" },
  { key: "company", label: <Bi en="Company Name" ms="Nama Majikan" />, width: "30%" },
];

const languageColumns: TableColumn[] = [
  { key: "language", label: <Bi en="Language" ms="Bahasa" />, width: "38%" },
  { key: "speaking", label: <Bi en="Speaking" ms="Bertutur" />, inputType: "select", options: ["1 - Basic / Asas", "2 - Average / Sederhana", "3 - Fluent / Lancar"] },
  { key: "reading", label: <Bi en="Reading" ms="Membaca" />, inputType: "select", options: ["1 - Basic / Asas", "2 - Average / Sederhana", "3 - Fluent / Lancar"] },
  { key: "writing", label: <Bi en="Writing" ms="Menulis" />, inputType: "select", options: ["1 - Basic / Asas", "2 - Average / Sederhana", "3 - Fluent / Lancar"] },
];

const emergencyColumns: TableColumn[] = [
  { key: "name", label: <Bi en="Name" ms="Nama" />, width: "24%" },
  { key: "relationship", label: <Bi en="Relationship" ms="Hubungan" />, width: "20%" },
  { key: "address", label: <Bi en="Address" ms="Alamat" />, width: "36%" },
  { key: "telephone", label: <Bi en="Telephone No." ms="No. Telefon" />, width: "20%" },
];

// Provides the hydrate rows helper.
const hydrateRows = (columns: TableColumn[], rows?: Record<string, string>[]) => {
  if (!rows?.length) return createRows(columns, 1);
  return rows.map((row) => ({
    id: crypto.randomUUID(),
    ...Object.fromEntries(columns.map((column) => [column.key, String(row[column.key] ?? "")])),
  }));
};

const disclosureQuestions = [
  {
    id: "workedBefore",
    number: "2",
    en: "Have you ever worked in UWC before?",
    ms: "Adakah anda pernah bekerja di UWC sebelum ini?",
    detailIntro: "If yes, please provide details of the position / Jika ya, sila berikan keterangan jawatan itu:",
    fields: [
      { key: "workedPosition", label: "Position / Jawatan" },
      { key: "workedDate", label: "Date Joined / Tarikh bekerja", type: "date" },
      { key: "workedSupervisor", label: "Supervisor / Penyelia" },
    ],
  },
  {
    id: "medicalCheck",
    number: "3",
    en: "Have you undergone a medical check-up in the last 12 months?",
    ms: "Adakah anda menjalani pemeriksaan kesihatan perubatan dalam tempoh 12 bulan yang lepas?",
    detailIntro: "If yes, please specify date / Jika ya, sila terangkan:",
    fields: [{ key: "medicalCheckDate", label: "Date / Tarikh", type: "date" }],
  },
  {
    id: "physicalDisability",
    number: "4",
    en: "Do you have any physical disabilities?",
    ms: "Adakah anda terdapat kecacatan fizikal?",
    detailIntro: "If yes, please specify / Jika ya, sila terangkan:",
    fields: [{ key: "physicalDisabilityDetails", label: "Details / Keterangan" }],
  },
  {
    id: "medicalCondition",
    number: "5",
    en: "Do you have any medical condition or suffer from any serious illness?",
    ms: "Adakah anda mempunyai apa-apa masalah kesihatan atau mengalami sebarang penyakit yang serius?",
    detailIntro: "If yes, please specify nature of medical condition or illness / Jika ya, sila terangkan:",
    fields: [{ key: "medicalConditionDetails", label: "Details / Keterangan" }],
  },
  {
    id: "pregnant",
    number: "6",
    en: "Are you pregnant? (for female only)",
    ms: "Adakah anda sedang hamil? (untuk wanita sahaja)",
    detailIntro: "If yes, please specify details, i.e. number of weeks or months / Jika ada, sila beri penerangan - berapa minggu atau bulan:",
    fields: [{ key: "pregnancyDetails", label: "Details / Keterangan" }],
  },
  {
    id: "drivingLicense",
    number: "8",
    en: "Do you have a valid driving license?",
    ms: "Adakah anda mempunyai lesen memandu?",
    detailIntro: "If yes, please specify type of license / Jika ya, sila nyatakan jenis lesen:",
    fields: [{ key: "drivingLicenseType", label: "Type / Jenis" }],
  },
  {
    id: "conviction",
    number: "9",
    en: "Do you have any statutory violation or criminal convictions before?",
    ms: "Adakah anda mempunyai sebarang pelanggaran undang-undang atau sabitan jenayah sebelum ini?",
    detailIntro: "If yes, please specify / Jika ya, sila nyatakan:",
    fields: [{ key: "convictionDetails", label: "Details / Keterangan" }],
  },
  { id: "relative", number: "7", en: "Do you have any relative currently working in this company?", ms: "Adakah anda mempunyai saudara-mara yang bekerja di syarikat ini?", detailIntro: "If yes, please specify the name / Jika ya, sila nyatakan nama:", fields: [{ key: "relativeName", label: "Name / Nama" }] },
  { id: "referred", number: "10", en: "Have you been referred by an existing UWC employee to apply this position?", ms: "Adakah anda telah dirujuk oleh pekerja UWC untuk memohon jawatan ini?", detailIntro: "If yes, please specify / Jika ya, sila nyatakan:", fields: [{ key: "referrerName", label: "Name / Nama" }, { key: "referrerRelationship", label: "Relationship / Perhubungan" }, { key: "referrerPosition", label: "Position / Jawatan" }, { key: "referrerDepartment", label: "Department / Jabatan" }, { key: "yearsKnown", label: "Years known / Tahun yang dikenali", type: "number" }] },
  { id: "smoker", number: "11", en: "Are you a smoker?", ms: "Adakah anda seorang perokok?", detailIntro: "", fields: [] },
  { id: "ownTransport", number: "12", en: "Do you have your own transport?", ms: "Adakah anda mempunyai kenderaan sendiri?", detailIntro: "", fields: [] },
  { id: "overtime", number: "13", en: "Will you do overtime?", ms: "Sanggupkah anda bekerja lebih masa?", detailIntro: "", fields: [] },
  { id: "shiftWork", number: "14", en: "Will you do shift work?", ms: "Sanggupkah anda bekerja syif?", detailIntro: "", fields: [] },
  { id: "vaccinated", number: "15", en: "Have you vaccinated for Covid-19?", ms: "Adakah anda sudah menerima vaksin untuk Covid-19?", detailIntro: "", fields: [] },
];

// Renders the Section Title component.
function SectionTitle({ number, en, ms }: { number?: string; en: string; ms?: string }) {
  return (
    <h2 className="employment-form__section-title">
      {number && `${number}. `}
      <Bi en={en} ms={ms} />
    </h2>
  );
}

// Renders the Labeled Input component.
function LabeledInput({ label, name, value, onChange, type = "text", className = "", required, invalid = false, disabled = false }: { label: React.ReactNode; name: string; value: string; onChange: (name: string, value: string) => void; type?: string; className?: string; required?: boolean; invalid?: boolean; disabled?: boolean }) {
  return <label className={`employment-form__field ${className}`}>
    <span>{label}</span>
    <input name={name} type={type} value={value} required={required ?? (!optionalCandidateFieldNames.has(name) && !internalFieldNames.has(name))} data-invalid={invalid || undefined} disabled={disabled} onChange={(event) => onChange(name, event.target.value)} />
  </label>;
}

// Renders the Yes No component.
function YesNo({ name, value, onChange, required = true }: { name: string; value: string; onChange: (name: string, value: string) => void; required?: boolean }) {
  return <div className="employment-form__yes-no" role="radiogroup" aria-label={`${name} answer`}>
    <label><input type="radio" name={name} value="yes" required={required} checked={value === "yes"} onChange={() => onChange(name, "yes")} /> Yes / <em>Ya</em></label>
    <label><input type="radio" name={name} value="no" checked={value === "no"} onChange={() => onChange(name, "no")} /> No / <em>Tidak</em></label>
  </div>;
}

const requiredFieldLabels: Record<string, string> = {
  positionApplied: "Position Applied",
  otherApplicationSource: "Other Application Source",
  fullName: "Full Name",
  email: "Email",
  permanentAddress: "Permanent Address",
  nationality: "Nationality",
  gender: "Gender",
  mobile: "Tel: (HP)",
  age: "Age",
  birthDate: "Date of Birth",
  birthPlace: "Place of Birth",
  raceOther: "Race - Please specify",
  religionOther: "Religion - Please specify",
  expectedSalary: "Expected Salary",
  declarationDate: "Declaration Date",
};

// Validates Malaysian mobile and landline formats used by the employment form.
const isValidMalaysianPhone = (value: string) => {
  const normalized = value.replace(/[\s()-]/g, "");
  return /^(?:\+?60|0)(?:1\d{8,9}|[3-9]\d{7,8})$/.test(normalized);
};

// Validates the common Malaysian NRIC format with optional separators.
const isValidMalaysianNric = (value: string) => {
  const normalized = value.replace(/[\s-]/g, "");
  return /^\d{12}$/.test(normalized);
};

// Collects missing fields.
function collectMissingFields({
  values,
  checks,
  photo,
  languages,
  hasIdentityDocumentError,
  hasNricFormatError,
  hasPassportExpiryError,
  missingConditionalDetails,
}: {
  values: FormValues;
  checks: Record<string, string[]>;
  photo: string;
  languages: TableRow[];
  hasIdentityDocumentError: boolean;
  hasNricFormatError: boolean;
  hasPassportExpiryError: boolean;
  missingConditionalDetails: boolean;
}) {
  // Build one clear list for the validation message.
  const missing = new Set<string>();
  const requiredValueNames = [
    "positionApplied", "fullName", "email", "permanentAddress", "nationality",
    "gender", "mobile", "age", "birthDate", "birthPlace", "expectedSalary", "declarationDate",
  ];

  requiredValueNames.forEach((name) => {
    if (!(values[name] ?? "").trim()) {
      missing.add(requiredFieldLabels[name] ?? name);
    }
  });

  if ((values.email ?? "").trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email ?? "")) {
    missing.add("Email format");
  }

  const mobile = (values.mobile ?? "").trim();
  const residentialPhone = (values.residentialPhone ?? "").trim();
  if (mobile && !isValidMalaysianPhone(mobile)) missing.add("Tel: (HP) format");
  if (residentialPhone && !isValidMalaysianPhone(residentialPhone)) {
    missing.add("Tel: (Res) format");
  }

  if (!photo) missing.add("Photograph");
  if (!checks.sources?.length) missing.add("Application Source");
  if (values.race === "Others / Lain-lain" && !(values.raceOther ?? "").trim()) missing.add(requiredFieldLabels.raceOther);
  if (!values.race) missing.add("Race");
  if (values.religion === "Others / Lain-lain" && !(values.religionOther ?? "").trim()) missing.add(requiredFieldLabels.religionOther);
  if (!values.religion) missing.add("Religion");
  if (!values.maritalStatus) missing.add("Marital Status");
  if (hasIdentityDocumentError) missing.add("NRIC or Passport No.");
  if (hasNricFormatError) missing.add("NRIC format (12 digits)");
  if (hasPassportExpiryError) missing.add("Passport Expiry Date");
  if (languages.some((row) => Object.entries(row).some(([key, value]) => key !== "id" && !value.trim()))) {
    missing.add("Languages and Dialects");
  }
  if (missingConditionalDetails) missing.add("Others Information details for Yes answers");
  if (!checks.declaration?.includes("accepted")) missing.add("Declaration confirmation");
  if (!values.candidateSignature) missing.add("Signature");

  return Array.from(missing);
}

// Renders the Approval Block component.
function ApprovalBlock({ title, prefix, values, update }: { title: string; prefix: string; values: FormValues; update: (name: string, value: string) => void }) {
  return <fieldset className="employment-form__approval"><legend>{title}</legend><div className="employment-form__approval-fields">
    <LabeledInput label="Name / Nama" name={`${prefix}Name`} value={values[`${prefix}Name`] ?? ""} onChange={update} />
    <SignatureField value={values[`${prefix}Signature`] ?? ""} onChange={(signature) => update(`${prefix}Signature`, signature)} />
    <LabeledInput label="Date / Tarikh" name={`${prefix}Date`} value={values[`${prefix}Date`] ?? ""} onChange={update} type="date" />
  </div></fieldset>;
}

// Renders the Signature Field component.
function SignatureField({ value, onChange, invalid = false }: { value: string; onChange: (value: string) => void; invalid?: boolean }) {
  const [open, setOpen] = useState(false);
  const [hasStroke, setHasStroke] = useState(Boolean(value));
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);

  useEffect(() => {
    if (!open || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    if (!context) return;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = 3;
    context.strokeStyle = "#003b7a";
    setHasStroke(Boolean(value));

    if (value) {
      const image = new Image();
      image.onload = () => context.drawImage(image, 0, 0, canvas.width, canvas.height);
      image.src = value;
    }
  }, [open, value]);

  // Gets point.
  const getPoint = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (canvas.width / rect.width),
      y: (event.clientY - rect.top) * (canvas.height / rect.height),
    };
  };

  // Starts drawing.
  const startDrawing = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const point = getPoint(event);
    const context = canvas?.getContext("2d");
    if (!canvas || !point || !context) return;

    canvas.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    context.beginPath();
    context.moveTo(point.x, point.y);
  };

  // Provides the draw helper.
  const draw = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const point = getPoint(event);
    const context = canvasRef.current?.getContext("2d");
    if (!drawingRef.current || !point || !context) return;

    context.lineTo(point.x, point.y);
    context.stroke();
    setHasStroke(true);
  };

  // Stops drawing.
  const stopDrawing = () => {
    drawingRef.current = false;
  };

  // Provides the clear helper.
  const clear = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    context.clearRect(0, 0, canvas.width, canvas.height);
    setHasStroke(false);
  };

  // Provides the save helper.
  const save = () => {
    if (!canvasRef.current || !hasStroke) return;
    onChange(canvasRef.current.toDataURL("image/png"));
    setOpen(false);
  };

  return (
    <>
      <div className="employment-form__signature-field" data-invalid={invalid || undefined}>
        <span><Bi en="Signature" ms="Tandatangan" /></span>
        <button type="button" className="employment-form__signature-trigger" onClick={() => setOpen(true)}>
          {value ? <img src={value} alt="Saved signature" /> : <><PenLine size={17} /> Click to sign</>}
        </button>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="employment-form__signature-dialog">
          <DialogHeader>
            <DialogTitle>Draw your signature</DialogTitle>
            <DialogDescription>Use your mouse, touch screen, or stylus to sign in the area below.</DialogDescription>
          </DialogHeader>
          <canvas
            ref={canvasRef}
            className="employment-form__signature-canvas"
            width={760}
            height={240}
            onPointerDown={startDrawing}
            onPointerMove={draw}
            onPointerUp={stopDrawing}
            onPointerLeave={stopDrawing}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={clear}>
              <RotateCcw /> Clear
            </Button>
            <Button type="button" onClick={save} disabled={!hasStroke}>Save signature</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Renders the Employment Form component.
export function EmploymentForm() {
  const formRef = useRef<HTMLFormElement>(null);
  const validationMessageRef = useRef<HTMLDivElement>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const [searchParams] = useSearchParams();
  const [values, setValues] = useState<FormValues>({});
  const [candidateSubmittedValues, setCandidateSubmittedValues] = useState<FormValues>({});
  const [checks, setChecks] = useState<Record<string, string[]>>({});
  const [photo, setPhoto] = useState<string>("");
  const [formScale, setFormScale] = useState(() =>
    Math.min(
      1,
      Math.max(
        getEmploymentFormViewportWidth() - EMPLOYMENT_FORM_PAGE_GUTTER,
        1,
      ) /
        EMPLOYMENT_FORM_DESKTOP_WIDTH,
    ),
  );
  const [formHeight, setFormHeight] = useState(0);
  const [jobOptions, setJobOptions] = useState<EmploymentFormJob[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState("");
  const [validationMissingFields, setValidationMissingFields] = useState<string[]>([]);
  const [showValidation, setShowValidation] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSavingInternal, setIsSavingInternal] = useState(false);
  const [internalSaveMessage, setInternalSaveMessage] = useState("");
  const [languages, setLanguages] = useState<TableRow[]>(() => createRows(languageColumns, 1));
  const [employment, setEmployment] = useState<TableRow[]>(() => createRows(employmentColumns, 1));
  const [qualifications, setQualifications] = useState<TableRow[]>(() => createRows(qualificationColumns, 1));
  const [references, setReferences] = useState<TableRow[]>(() => createRows(referenceColumns, 1));
  const [family, setFamily] = useState<TableRow[]>(() => createRows(familyColumns, 1));
  const [emergency, setEmergency] = useState<TableRow[]>(() => createRows(emergencyColumns, 1));
  const showInternalSections = searchParams.get("view") === "hr" && Boolean(getStoredUser());
  const submissionId = searchParams.get("submissionId");
  const lockCandidateFields = showInternalSections && Boolean(submissionId);

  // Clear old messages when the form mode changes.
  useEffect(() => {
    setSubmissionMessage("");
    setValidationMissingFields([]);
    setShowValidation(false);
    setInternalSaveMessage("");
  }, [showInternalSections, submissionId]);

  useEffect(() => {
    // Candidate mode loads public jobs. HR mode can also load closed jobs.
    const jobEndpoint = import.meta.env.VITE_APP_SURFACE === "candidate"
      ? "/career/jobs"
      : "/jobs";

    apiFetch<{ jobs: EmploymentFormJob[] }>(jobEndpoint)
      .then((data) => setJobOptions(
        data.jobs.filter(
          (job) =>
            job.status === undefined ||
            job.status === "active" ||
            job.status === "closed",
        ),
      ))
      .catch(() => setJobOptions([]))
      .finally(() => setIsLoadingJobs(false));
  }, []);

  useEffect(() => {
    if (!showInternalSections || !submissionId) return;

    // Merge candidate answers with fields saved later by HR.
    apiFetch<{ submission: EmploymentFormSubmission }>(`/employment-form/submissions/${submissionId}`)
      .then(({ submission }) => {
        const candidateData = submission.candidateData ?? {};
        const loadedValues = candidateData.values ?? {};
        setSubmissionMessage("");
        setValidationMissingFields([]);
        setShowValidation(false);
        setCandidateSubmittedValues(loadedValues);
        const internalValues = submission.hrFormData?.values ?? {};
        setValues({
          ...loadedValues,
          ...internalValues,
          positionApplied: String(loadedValues.positionApplied ?? submission.jobId),
        });
        setChecks({
          ...(candidateData.checks ?? {}),
          ...(submission.hrFormData?.checks ?? {}),
        });
        setPhoto(candidateData.photo ?? "");
        setLanguages(hydrateRows(languageColumns, candidateData.tables?.languages));
        setEmployment(hydrateRows(employmentColumns, candidateData.tables?.employment));
        setQualifications(hydrateRows(qualificationColumns, candidateData.tables?.qualifications));
        setReferences(hydrateRows(referenceColumns, candidateData.tables?.references));
        setFamily(hydrateRows(familyColumns, candidateData.tables?.family));
        setEmergency(hydrateRows(emergencyColumns, candidateData.tables?.emergency));
      })
      .catch((error) => {
        setSubmissionMessage(error instanceof Error ? error.message : "Unable to load employment form submission.");
      });
  }, [showInternalSections, submissionId]);

  useEffect(() => {
    // Keeps the desktop form geometry and scales the whole sheet to narrower viewports.
    const updateFormScale = () => {
      const availableWidth = Math.max(
        getEmploymentFormViewportWidth() - EMPLOYMENT_FORM_PAGE_GUTTER,
        1,
      );
      setFormScale(
        Math.min(1, availableWidth / EMPLOYMENT_FORM_DESKTOP_WIDTH),
      );
    };

    updateFormScale();
    window.addEventListener("resize", updateFormScale);
    return () => window.removeEventListener("resize", updateFormScale);
  }, []);

  useEffect(() => {
    const form = formRef.current;
    if (!form) return;

    const updateFormHeight = () => setFormHeight(form.offsetHeight);
    updateFormHeight();

    const resizeObserver = new ResizeObserver(updateFormHeight);
    resizeObserver.observe(form);
    return () => resizeObserver.disconnect();
  }, [isSubmitted, showInternalSections]);

  // Updates the current form value.
  const update = (name: string, value: string) => setValues((current) => ({ ...current, [name]: value }));
  // Toggles the current option.
  const toggle = (group: string, value: string) => setChecks((current) => {
    const selected = current[group] ?? [];
    return { ...current, [group]: selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value] };
  });
  // Checks the current option state.
  const checked = (group: string, value: string) => (checks[group] ?? []).includes(value);
  const fileName = useMemo(() => values.photoName || "No photograph selected", [values.photoName]);
  // Resets candidate form.
  const resetCandidateForm = () => {
    setValues({});
    setCandidateSubmittedValues({});
    setChecks({});
    setPhoto("");
    setShowValidation(false);
    setValidationMissingFields([]);
    setLanguages(createRows(languageColumns, 1));
    setEmployment(createRows(employmentColumns, 1));
    setQualifications(createRows(qualificationColumns, 1));
    setReferences(createRows(referenceColumns, 1));
    setFamily(createRows(familyColumns, 1));
    setEmergency(createRows(emergencyColumns, 1));
    if (photoInputRef.current) {
      photoInputRef.current.value = "";
    }
  };

  // Picks values.
  const pickValues = (names: Set<string>) => Object.fromEntries(
    Object.entries(values).filter(([key]) => names.has(key)),
  );
  // Checks whether hr fill blank candidate field is allowed.
  const canHrFillBlankCandidateField = (name: string) =>
    lockCandidateFields && !(candidateSubmittedValues[name] ?? "").trim();

  // Saves internal sections.
  const saveInternalSections = async () => {
    if (!submissionId) return;

    // Save only the fields owned by HR and the hiring team.
    setIsSavingInternal(true);
    setInternalSaveMessage("");
    try {
      await apiFetch(`/employment-form/submissions/${submissionId}/internal`, {
        method: "PATCH",
        body: JSON.stringify({
          hrFormData: {
            values: {
              ...pickValues(hiringDepartmentFieldNames),
              ...pickValues(hrFieldNames),
            },
            checks: {
              interviewStatus: checks.interviewStatus ?? [],
            },
          },
        }),
      });
      setInternalSaveMessage("HR section saved successfully.");
    } catch (error) {
      setInternalSaveMessage(error instanceof Error ? error.message : "Unable to save HR section.");
    } finally {
      setIsSavingInternal(false);
    }
  };
  const showMissingSource = showValidation && !checks.sources?.length;
  const showMissingRace = showValidation && !values.race;
  const showMissingReligion = showValidation && !values.religion;
  const showMissingMaritalStatus = showValidation && !values.maritalStatus;
  const showMissingDeclaration = showValidation && !checked("declaration", "accepted");
  const showMissingCandidateSignature = showValidation && !values.candidateSignature;
  const showMissingPhoto = showValidation && !photo;
  const hasNric = Boolean((values.nric ?? "").trim());
  const hasPassportNo = Boolean((values.passportNo ?? "").trim());
  const showMissingNricOrPassport = showValidation && !hasNric && !hasPassportNo;
  const mobile = (values.mobile ?? "").trim();
  const residentialPhone = (values.residentialPhone ?? "").trim();
  const hasMobileFormatError = Boolean(mobile) && !isValidMalaysianPhone(mobile);
  const hasResidentialPhoneFormatError =
    Boolean(residentialPhone) && !isValidMalaysianPhone(residentialPhone);
  const showMobileFormatError = showValidation && hasMobileFormatError;
  const showResidentialPhoneFormatError =
    showValidation && hasResidentialPhoneFormatError;
  const hasNricFormatError = hasNric && !isValidMalaysianNric(values.nric ?? "");
  const showNricFormatError = showValidation && hasNricFormatError;
  const showMissingPassportExpiry = showValidation && hasPassportNo && !(values.passportExpiry ?? "").trim();

  // Submits candidate form.
  const submitCandidateForm = async () => {
    // Check normal fields and conditional fields before submit.
    const jobId = Number(values.positionApplied ?? 0);
    const candidateEmail = (values.email ?? "").trim();
    const requiresOtherSource = checked("sources", "Others / Lain-lain");
    const requiresRaceOther = values.race === "Others / Lain-lain";
    const requiresReligionOther = values.religion === "Others / Lain-lain";
    const missingConditionalDetails = disclosureQuestions.some((question) =>
      values[question.id] === "yes" && question.fields.some((field) => !(values[field.key] ?? "").trim()),
    );
    const hasRequiredSelections = Boolean(
      checks.sources?.length && values.race && values.religion && values.maritalStatus,
    );
    const hasIdentityDocumentError =
      !(values.nric ?? "").trim() && !(values.passportNo ?? "").trim();
    const hasNricFormatError =
      Boolean((values.nric ?? "").trim()) && !isValidMalaysianNric(values.nric ?? "");
    const hasPassportExpiryError =
      Boolean((values.passportNo ?? "").trim()) && !(values.passportExpiry ?? "").trim();
    const hasCustomValidationError =
      !photo || !values.candidateSignature || !hasRequiredSelections ||
      (requiresOtherSource && !(values.otherApplicationSource ?? "").trim()) ||
      (requiresRaceOther && !(values.raceOther ?? "").trim()) ||
      (requiresReligionOther && !(values.religionOther ?? "").trim()) ||
      hasIdentityDocumentError ||
      hasMobileFormatError ||
      hasResidentialPhoneFormatError ||
      hasNricFormatError ||
      hasPassportExpiryError ||
      missingConditionalDetails;

    setShowValidation(true);
    if (!formRef.current?.checkValidity() || !jobId || !candidateEmail || !checked("declaration", "accepted") || hasCustomValidationError) {
      const missingFields = collectMissingFields({
        values,
        checks,
        photo,
        languages,
        hasIdentityDocumentError,
        hasNricFormatError,
        hasPassportExpiryError,
        missingConditionalDetails,
      });
      setValidationMissingFields(missingFields);
      setSubmissionMessage("Please complete all required candidate fields before submitting.");
      window.requestAnimationFrame(() => validationMessageRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }));
      return;
    }

    const candidateValues = Object.fromEntries(
      Object.entries(values).filter(([key]) => !internalFieldNames.has(key)),
    );
    const candidateChecks = Object.fromEntries(
      Object.entries(checks).filter(([key]) => key !== "interviewStatus"),
    );
    // Provides the table rows helper.
    const tableRows = (rows: TableRow[]) => rows.map(({ id, ...row }) => row);

    setIsSubmitting(true);
    setSubmissionMessage("");
    setValidationMissingFields([]);
    try {
      const compactPhoto = await ensureCompactPhoto(photo);
      setPhoto(compactPhoto);
      await apiFetch("/employment-form/submissions", {
        method: "POST",
        body: JSON.stringify({
          jobId,
          candidateEmail,
          candidateData: {
            values: candidateValues,
            checks: candidateChecks,
            photo: compactPhoto,
            tables: {
              languages: tableRows(languages),
              employment: tableRows(employment),
              qualifications: tableRows(qualifications),
              references: tableRows(references),
              family: tableRows(family),
              emergency: tableRows(emergency),
            },
          },
        }),
      });
      resetCandidateForm();
      setSubmissionMessage("");
      setIsSubmitted(true);
    } catch (error) {
      setSubmissionMessage(error instanceof Error ? error.message : "Unable to submit the employment form.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted && !showInternalSections) {
    return (
      <main className="employment-form-page employment-form-page--success">
        <section className="employment-form__submitted-card">
          <div className="employment-form__submitted-icon" aria-hidden="true">
            <Check size={38} strokeWidth={2.6} />
          </div>
          <h1>Employment Form Submitted</h1>
          <p>
            Your employment form has been submitted successfully. The form has been
            cleared for another submission.
          </p>
          <Button
            type="button"
            onClick={() => setIsSubmitted(false)}
            className="employment-form__submitted-button"
          >
            OK
          </Button>
        </section>
      </main>
    );
  }

  return <main className="employment-form-page">
    <div
      className="employment-form__scale-shell"
      style={{
        width: `${EMPLOYMENT_FORM_DESKTOP_WIDTH * formScale}px`,
        height: formHeight ? `${formHeight * formScale}px` : undefined,
      }}
    >
      <form
        ref={formRef}
        className="employment-form"
        style={{ transform: `scale(${formScale})` }}
        data-show-validation={showValidation || undefined}
        noValidate
        onSubmit={(event) => event.preventDefault()}
      >
      {submissionMessage && (
        <div
          ref={validationMessageRef}
          className={`employment-form__message ${submissionMessage.includes("successfully") ? "employment-form__message--success" : "employment-form__message--error"}`}
          role="status"
        >
          <p>{submissionMessage}</p>
          {validationMissingFields.length > 0 && (
            <ul>
              {validationMissingFields.map((field) => <li key={field}>{field}</li>)}
            </ul>
          )}
        </div>
      )}

      <header className="employment-form__masthead">
        <div className="employment-form__admin-box">
          <LabeledInput label="Employee No." name="employeeNo" value={values.employeeNo ?? ""} onChange={update} />
          <LabeledInput label="Date Joined" name="dateJoined" value={values.dateJoined ?? ""} onChange={update} type="date" />
        </div>
        <fieldset
          className="employment-form__candidate-fields employment-form__masthead-candidate-fields"
          data-locked={lockCandidateFields || undefined}
          disabled={lockCandidateFields}
        >
          <div className="employment-form__identity">
            <img src={uwcLogo} alt="UWC Berhad" />
            <address><strong>UWC BERHAD <small>(1274239-A)</small></strong><br />PMT 744, Jalan Cassia Selatan 5/1,<br />Taman Perindustrian Batu Kawan,<br />14110 Bandar Cassia, Penang.<br />T: 04 555 6937 &nbsp;&nbsp; F: 04 509 9503</address>
          </div>
          <label className="employment-form__photo" data-invalid={showMissingPhoto || undefined}>
            {photo ? <img src={photo} alt="Applicant preview" /> : <span>Attach a recent<br />photograph of<br />yourself</span>}
            <input ref={photoInputRef} type="file" accept="image/*" required onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              update("photoName", file.name);
              setPhoto(await preparePhotoForSubmission(file));
            }} />
            <small>{fileName}</small>
          </label>
        </fieldset>
      </header>

      <fieldset
        className="employment-form__candidate-fields"
        data-locked={lockCandidateFields || undefined}
        disabled={lockCandidateFields}
      >
      <div className="employment-form__title">
        <h1>EMPLOYMENT APPLICATION / PERMOHONAN PEKERJAAN</h1>
        <strong>(STRICTLY CONFIDENTIAL / SULIT)</strong>
      </div>
      <div className="employment-form__confidentiality">
        <p><strong>Confidentiality Clause:</strong> UWC is committed to maintaining the confidentiality of the candidate’s personal information and undertakes not to divulge any of the candidate’s personal information to any third party without the consent of the candidate.</p>
        <p><em><strong>Klausa Kerahsiaan:</strong> UWC komited untuk menjaga kerahsiaan maklumat peribadi calon dan berjanji untuk tidak menyebarkan maklumat peribadi calon kepada pihak ketiga tanpa persetujuan calon.</em></p>
      </div>

      <section className="employment-form__position-grid">
        <label className="employment-form__field">
          <span><Bi en="POSITION APPLIED" ms="JAWATAN DIPOHON" /></span>
          <select
            aria-label="Position applied"
            value={values.positionApplied ?? ""}
            required
            onChange={(event) => {
              const selectedJob = jobOptions.find((job) => job.id === Number(event.target.value));
              update("positionApplied", event.target.value);
              update("positionAppliedTitle", selectedJob?.title ?? "");
            }}
            disabled={isLoadingJobs}
          >
            <option value="">{isLoadingJobs ? "Loading positions..." : "Select position / Pilih jawatan"}</option>
            {jobOptions.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}{job.department ? ` — ${job.department}` : ""}
              </option>
            ))}
          </select>
        </label>
        <fieldset data-invalid={showMissingSource || undefined}><legend><Bi en="APPLICATION SOURCE" ms="SUMBER PERMOHONAN" /></legend><div className="employment-form__check-grid">
          {["Internet", "Poster / Banner", "Newspaper / Surat Khabar", "Friend / Relative — Kawan / Saudara", "Department of Labour / Jabatan Tenaga Kerja"].map((source) => <label key={source}><input type="checkbox" checked={checked("sources", source)} onChange={() => toggle("sources", source)} />{source}</label>)}
          <label className="employment-form__source-other">
            <span>Others / Lain-lain</span>
            <div>
              <input type="checkbox" checked={checked("sources", "Others / Lain-lain")} onChange={() => toggle("sources", "Others / Lain-lain")} />
              <input aria-label="Other application source" required={checked("sources", "Others / Lain-lain")} value={values.otherApplicationSource ?? ""} onChange={(event) => update("otherApplicationSource", event.target.value)} />
            </div>
          </label>
        </div></fieldset>
      </section>

      <section>
        <SectionTitle number="1" en="PERSONAL INFORMATION" ms="MAKLUMAT PERIBADI" />
        <div className="employment-form__grid employment-form__personal-grid">
          <LabeledInput className="employment-form__field--full" label={<Bi en="Full Name" ms="Nama Penuh" />} name="fullName" value={values.fullName ?? ""} onChange={update} />
          <LabeledInput className="employment-form__field--wide" label={<Bi en="Preferred Name" ms="Nama Pilihan" />} name="preferredName" value={values.preferredName ?? ""} onChange={update} />
          <LabeledInput className="employment-form__field--narrow" label="Email" name="email" value={values.email ?? ""} onChange={update} type="email" />
          <label className="employment-form__field employment-form__field--textarea employment-form__field--wide"><span><Bi en="Permanent Address" ms="Alamat Tetap" /></span><textarea required value={values.permanentAddress ?? ""} onChange={(event) => update("permanentAddress", event.target.value)} /></label>
          <label className="employment-form__field employment-form__field--textarea employment-form__field--narrow"><span><Bi en="Current Address" ms="Alamat Semasa" /> <small>(If different / Sekiranya berbeza)</small></span><textarea value={values.currentAddress ?? ""} onChange={(event) => update("currentAddress", event.target.value)} /></label>
          <LabeledInput className="employment-form__field--wide" label={<Bi en="Nationality" ms="Kewarganegaraan" />} name="nationality" value={values.nationality ?? ""} onChange={update} />
          <label className="employment-form__field employment-form__field--narrow"><span><Bi en="Gender" ms="Jantina" /></span><select required value={values.gender ?? ""} onChange={(event) => update("gender", event.target.value)}><option value="">Select / Pilih</option><option>Male / Lelaki</option><option>Female / Perempuan</option><option>Prefer not to say / Tidak mahu nyatakan</option></select></label>
          <LabeledInput className="employment-form__field--mobile" label="Tel: (HP)" name="mobile" value={values.mobile ?? ""} onChange={update} type="tel" invalid={showMobileFormatError} />
          <LabeledInput className="employment-form__field--residential" label="Tel: (Res)" name="residentialPhone" value={values.residentialPhone ?? ""} onChange={update} type="tel" invalid={showResidentialPhoneFormatError} />
          <LabeledInput className="employment-form__field--wide" label="NRIC / No. KP" name="nric" value={values.nric ?? ""} onChange={update} invalid={showMissingNricOrPassport || showNricFormatError} />
          <LabeledInput className="employment-form__field--narrow" label={<Bi en="Age" ms="Umur" />} name="age" value={values.age ?? ""} onChange={update} type="number" />
          <LabeledInput className="employment-form__field--wide" label={<Bi en="Passport No." ms="No. Pasport" />} name="passportNo" value={values.passportNo ?? ""} onChange={update} invalid={showMissingNricOrPassport} />
          <LabeledInput className="employment-form__field--narrow" label={<Bi en="Passport Expiry Date" ms="Tarikh Pasport Tamat" />} name="passportExpiry" value={values.passportExpiry ?? ""} onChange={update} type="date" invalid={showMissingPassportExpiry} />
          <LabeledInput className="employment-form__field--wide" label={<Bi en="Date of Birth" ms="Tarikh Lahir" />} name="birthDate" value={values.birthDate ?? ""} onChange={update} type="date" />
          <LabeledInput className="employment-form__field--narrow" label={<Bi en="Place of Birth" ms="Tempat Lahir" />} name="birthPlace" value={values.birthPlace ?? ""} onChange={update} />
        </div>
        <div className="employment-form__option-block employment-form__race-block" data-invalid={showMissingRace || undefined}><strong><Bi en="Race" ms="Keturunan" /></strong><div>
          {["Chinese / Cina", "Malay / Melayu", "Indian / India", "Others / Lain-lain"].map((item) => <label key={item}><input type="radio" name="race" checked={values.race === item} onChange={() => update("race", item)} />{item}</label>)}
          <LabeledInput label="Please specify / Sila nyatakan" name="raceOther" value={values.raceOther ?? ""} onChange={update} required={values.race === "Others / Lain-lain"} />
        </div></div>
        <div className="employment-form__option-block" data-invalid={showMissingReligion || undefined}><strong><Bi en="Religion" ms="Agama" /></strong><div>
          {["Buddha", "Christian", "Hindu", "Islam", "Others / Lain-lain"].map((item) => <label key={item}><input type="radio" name="religion" checked={values.religion === item} onChange={() => update("religion", item)} />{item}</label>)}
          <LabeledInput label="Please specify / Sila nyatakan" name="religionOther" value={values.religionOther ?? ""} onChange={update} required={values.religion === "Others / Lain-lain"} />
        </div></div>
        <div className="employment-form__option-block" data-invalid={showMissingMaritalStatus || undefined}><strong><Bi en="Marital Status" ms="Status Perkahwinan" /></strong><div className="employment-form__radio-options">
          {["Married / Berkahwin", "Single / Bujang", "Divorced / Bercerai", "Widow / Widower / Janda / Duda"].map((item, index) => <label key={item}><input type="radio" name="maritalStatus" required={index === 0} checked={values.maritalStatus === item} onChange={() => update("maritalStatus", item)} />{item}</label>)}
        </div></div>
      </section>
      </fieldset>

      <div className="employment-form__grid employment-form__grid--two">
        <LabeledInput label={<Bi en="EPF No." ms="No. KWSP" />} name="epfNo" value={values.epfNo ?? ""} onChange={update} disabled={lockCandidateFields && !canHrFillBlankCandidateField("epfNo")} />
        <LabeledInput label={<Bi en="Income Tax No." ms="No. Cukai Pendapatan" />} name="incomeTaxNo" value={values.incomeTaxNo ?? ""} onChange={update} disabled={lockCandidateFields && !canHrFillBlankCandidateField("incomeTaxNo")} />
        <LabeledInput label={<Bi en="Bank Name" ms="Nama Bank" />} name="bankName" value={values.bankName ?? ""} onChange={update} disabled={lockCandidateFields && !canHrFillBlankCandidateField("bankName")} />
        <LabeledInput label={<Bi en="Bank Acc. No." ms="No. Akaun Bank" />} name="bankAccount" value={values.bankAccount ?? ""} onChange={update} disabled={lockCandidateFields && !canHrFillBlankCandidateField("bankAccount")} />
      </div>

      <fieldset
        className="employment-form__candidate-fields"
        data-locked={lockCandidateFields || undefined}
        disabled={lockCandidateFields}
      >
      <section>
        <SectionTitle number="2" en="LANGUAGES AND DIALECTS" ms="BAHASA DAN DIALEK" />
        <p className="employment-form__hint">
          <strong>Proficient Level / Tahap mahir:</strong> 1 - Basic / Asas &nbsp;&nbsp; 2 - Average / Sederhana &nbsp;&nbsp; 3 - Fluent / Lancar
        </p>
        <RepeatableTable ariaLabel="Languages and dialects" columns={languageColumns} rows={languages} onChange={setLanguages} required />
      </section>
      <section>
        <SectionTitle number="3" en="EMPLOYMENT HISTORY" ms="PENGALAMAN KERJA" />
        <p className="employment-form__hint">
          Start with your present (or last) employer / <em>Bermula dari majikan semasa atau majikan terakhir</em>
        </p>
        <RepeatableTable ariaLabel="Employment history" columns={employmentColumns} rows={employment} onChange={setEmployment} />
      </section>
      <section>
        <SectionTitle number="4" en="QUALIFICATION OR OTHER TRAINING CERTIFICATION" ms="KELULUSAN AKADEMIK ATAU SIJIL LATIHAN" />
        <RepeatableTable ariaLabel="Qualifications and training" columns={qualificationColumns} rows={qualifications} onChange={setQualifications} />
      </section>
      <section>
        <SectionTitle number="5" en="PERSONAL REFERENCES" ms="RUJUKAN PERIBADI" />
        <p className="employment-form__hint">
          (Those acquainted with your work are preferred eg. present / past / immediate superiors)
          <br />
          <em>(Orang-orang yang mengetahui tentang latar belakang pekerjaan anda)</em>
        </p>
        <RepeatableTable ariaLabel="Personal references" columns={referenceColumns} rows={references} onChange={setReferences} />
      </section>
      <section>
        <SectionTitle number="6" en="FAMILY INFORMATION" ms="MAKLUMAT KELUARGA" />
        <div className="employment-form__family-note">
          <span>
            <strong>MARRIED:</strong> Details of spouse and child(ren)
            <br />
            <em><strong>BERKAHWIN:</strong> Maklumat pasangan dan anak-anak</em>
          </span>
          <span>
            <strong>SINGLE:</strong> Details of parents and sibling(s)
            <br />
            <em><strong>BUJANG:</strong> Maklumat ibubapa dan adik-beradik</em>
          </span>
        </div>
        <RepeatableTable ariaLabel="Family information" columns={familyColumns} rows={family} onChange={setFamily} />
      </section>
      <section className="employment-form__print-page-start">
        <SectionTitle number="7" en="LEISURE INTEREST" ms="MINAT" />
          <textarea
            className="employment-form__wide-textarea"
          value={values.leisureInterest ?? ""}
          onChange={(event) => update("leisureInterest", event.target.value)}
        />
        <div className="employment-form__grid employment-form__grid--two employment-form__spaced-grid">
          <LabeledInput label={<Bi en="Expected Salary" ms="Jangkaan Gaji" />} name="expectedSalary" value={values.expectedSalary ?? ""} onChange={update} type="number" />
          <LabeledInput label={<Bi en="Earliest available Date" ms="Tarikh paling awal boleh bermula bekerja" />} name="availableDate" value={values.availableDate ?? ""} onChange={update} type="date" />
        </div>
      </section>

      <section className="employment-form__others-section">
        <SectionTitle number="8" en="OTHERS INFORMATION" ms="KETERANGAN-KETERANGAN LAIN" />
        <p className="employment-form__hint">
          (Please tick appropriate box / <em>Tanda kotak yang bersesuaian</em>)
        </p>
        <h3 className="employment-form__subheading">1) Person to contact during emergency / <em>Orang yang perlu dihubungi semasa kecemasan</em></h3>
        <RepeatableTable ariaLabel="Emergency contacts" columns={emergencyColumns} rows={emergency} onChange={setEmergency} />
        <div className="employment-form__disclosures">
          {disclosureQuestions.map((question) => (
            <fieldset key={question.id} className="employment-form__disclosure" data-invalid={showValidation && !values[question.id] ? true : undefined}>
              <legend>
                {question.number}) {question.en}
                <em>{question.ms}</em>
              </legend>
              <YesNo name={question.id} value={values[question.id] ?? ""} onChange={update} />
              {question.fields.length > 0 && (
                <div className="employment-form__detail-fields">
                  {question.detailIntro && <p>{question.detailIntro}</p>}
                  {question.fields.map((field) => (
                    <LabeledInput
                      key={field.key}
                      label={field.label}
                      name={field.key}
                      value={values[field.key] ?? ""}
                      onChange={update}
                      type={field.type}
                      required={values[question.id] === "yes"}
                    />
                  ))}
                </div>
              )}
            </fieldset>
          ))}
        </div>
      </section>

      <section className="employment-form__declaration employment-form__print-page-start">
        <h2>Declaration / Pengesahan</h2>
        <p>
          I declare that the information provided above is true and complete in all aspects. I understand that any
          misrepresentation or omission of information may be considered sufficient for withdrawal of an offer or
          subsequent dismissal from employment.
        </p>
        <p>
          <em>
            Saya mengakui bahawa maklumat yang diberikan di atas oleh saya adalah benar dan lengkap dalam semua aspek.
            Saya faham bahawa jika memberi sebarang gambaran yang salah atau maklumat yang tidak lengkap ianya boleh
            dianggap mencukupi untuk penarikan balik tawaran kerja atau pemecatan daripada pekerjaan.
          </em>
        </p>
        <label className="employment-form__declaration-check" data-invalid={showMissingDeclaration || undefined}>
          <input type="checkbox" required checked={checked("declaration", "accepted")} onChange={() => toggle("declaration", "accepted")} /> I confirm this declaration / <em>Saya mengesahkan pengakuan ini</em>
        </label>
        <div className="employment-form__grid employment-form__grid--two">
          <SignatureField
            value={values.candidateSignature ?? ""}
            onChange={(signature) => update("candidateSignature", signature)}
            invalid={showMissingCandidateSignature}
          />
          <LabeledInput label={<Bi en="Date" ms="Tarikh" />} name="declarationDate" value={values.declarationDate ?? ""} onChange={update} type="date" />
        </div>
      </section>
      </fieldset>

      {!showInternalSections && (
        <div className="employment-form__candidate-submit">
          <button type="button" onClick={submitCandidateForm} disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit Employment Form"}
          </button>
        </div>
      )}

      {showInternalSections && (
        <>
          <div className="employment-form__internal-divider" role="separator">
            HR / Internal Use Section
          </div>
          <section className="employment-form__internal">
            <h2 className="employment-form__blue-header">FOR HIRING DEPARTMENT USE ONLY</h2>
            <fieldset className="employment-form__interview-status">
              <legend>Interview Status:</legend>
              <label className="employment-form__status-hire"><input type="checkbox" checked={checked("interviewStatus", "Hire")} onChange={() => toggle("interviewStatus", "Hire")} />Hire</label>
              <label className="employment-form__status-kiv"><input type="checkbox" checked={checked("interviewStatus", "KIV")} onChange={() => toggle("interviewStatus", "KIV")} />KIV</label>
              <label className="employment-form__status-reject"><input type="checkbox" checked={checked("interviewStatus", "Reject")} onChange={() => toggle("interviewStatus", "Reject")} />Reject</label>
              <label className="employment-form__status-second"><input type="checkbox" checked={checked("interviewStatus", "2nd Interview")} onChange={() => toggle("interviewStatus", "2nd Interview")} />2nd Interview</label>
              <label className="employment-form__status-other"><input type="checkbox" checked={checked("interviewStatus", "Suitable for other department")} onChange={() => toggle("interviewStatus", "Suitable for other department")} />Suitable for other department</label>
              <input className="employment-form__suitable-department-input" aria-label="Suitable for other department details" value={values.suitableDepartment ?? ""} onChange={(event) => update("suitableDepartment", event.target.value)} />
            </fieldset>
            <label className="employment-form__field employment-form__comments">
              <span>
                <strong>Interviewer's Comments:</strong>
                <br />
                Remarks:
              </span>
              <textarea value={values.interviewerComments ?? ""} onChange={(event) => update("interviewerComments", event.target.value)} />
            </label>
            <h3 className="employment-form__blue-header">HIRING DETAILS:</h3>
            <div className="employment-form__grid employment-form__grid--two">
              <LabeledInput label="Position" name="hiringPosition" value={values.hiringPosition ?? ""} onChange={update} />
              <LabeledInput label="Starting Basic Salary" name="startingSalary" value={values.startingSalary ?? ""} onChange={update} type="number" />
              <label className="employment-form__field">
                <span>Job Level</span>
                <select value={values.jobLevel ?? ""} onChange={(event) => update("jobLevel", event.target.value)}>
                  <option value="">Select</option>
                  {["Non-Executive", "Executive", "Senior Executive", "Manager", "Senior Manager"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <LabeledInput label="Daily Transport Claim" name="dailyTransportClaim" value={values.dailyTransportClaim ?? ""} onChange={update} type="number" />
              <LabeledInput label="Department" name="hiringDepartment" value={values.hiringDepartment ?? ""} onChange={update} />
              <LabeledInput label="Maximum Transport Claim" name="maximumTransportClaim" value={values.maximumTransportClaim ?? ""} onChange={update} type="number" />
              <LabeledInput label="Shift Group" name="shiftGroup" value={values.shiftGroup ?? ""} onChange={update} />
              <LabeledInput label="Fuel Claim" name="fuelClaim" value={values.fuelClaim ?? ""} onChange={update} type="number" />
              <LabeledInput label="Supervisor" name="supervisor" value={values.supervisor ?? ""} onChange={update} />
              <label className="employment-form__field">
                <span>Monthly OT Claim</span>
                <YesNo name="monthlyOtClaim" value={values.monthlyOtClaim ?? ""} onChange={update} required={false} />
              </label>
              <LabeledInput label="Mentor" name="mentor" value={values.mentor ?? ""} onChange={update} />
              <LabeledInput label="1st Approver (MyWave)" name="firstApprover" value={values.firstApprover ?? ""} onChange={update} />
              <span aria-hidden="true" />
              <LabeledInput label="2nd Approver (MyWave)" name="secondApprover" value={values.secondApprover ?? ""} onChange={update} />
            </div>
            <ApprovalBlock title="Interviewer Acknowledgement" prefix="interviewer" values={values} update={update} /><ApprovalBlock title="Department's Manager Approval" prefix="departmentManager" values={values} update={update} /><ApprovalBlock title="Head of Operation / General Manager / Director Approval" prefix="headApproval" values={values} update={update} />
          </section>

          <section className="employment-form__internal">
            <h2 className="employment-form__blue-header">FOR HUMAN RESOURCES ONLY:</h2>
            <div className="employment-form__grid employment-form__grid--three">
              <LabeledInput label="Date of Joining" name="hrJoiningDate" value={values.hrJoiningDate ?? ""} onChange={update} type="date" />
              <LabeledInput label="Date of Offer" name="hrOfferDate" value={values.hrOfferDate ?? ""} onChange={update} type="date" />
              <LabeledInput label="Date LOA Issued" name="loaIssuedDate" value={values.loaIssuedDate ?? ""} onChange={update} type="date" />
              <LabeledInput label="Employee No." name="hrEmployeeNo" value={values.hrEmployeeNo ?? ""} onChange={update} />
              <LabeledInput label="Badge No." name="badgeNo" value={values.badgeNo ?? ""} onChange={update} />
            </div>
            <ApprovalBlock title="Senior Human Resource Manager Approval" prefix="seniorHrManager" values={values} update={update} />
          </section>
          {submissionId && (
            <div className="employment-form__internal-save">
              {internalSaveMessage && <p role="status">{internalSaveMessage}</p>}
              <button type="button" onClick={saveInternalSections} disabled={isSavingInternal}>
                {isSavingInternal ? "Saving..." : "Save HR Section"}
              </button>
            </div>
          )}
        </>
      )}
        <footer className="employment-form__footer"><span>UWC-FR-238-02</span><span>Employment form submissions are stored securely for HR processing.</span></footer>
      </form>
    </div>
  </main>;
}
