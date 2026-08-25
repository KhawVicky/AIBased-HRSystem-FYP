// Shows the User Settings view.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { PageLayout } from "../shared/PageLayout";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../ui/tabs";
import { Switch } from "../ui/switch";
import { Textarea } from "../ui/textarea";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../ui/pagination";
import {
  ArrowLeft,
  User,
  Mail,
  Phone,
  Building2,
  MapPin,
  Upload,
  Camera,
  Save,
  Shield,
  Bell,
  Lock,
  Pencil,
  FileText,
  ChevronDown,
  Filter,
  LoaderCircle,
  Plus,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, getStoredUser, type AuthUser } from "../../lib/api";
import { getCompactPageItems } from "../../lib/pagination";
import { LoadingState } from "../shared/LoadingState";
import { PasswordInput } from "../shared/PasswordInput";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../ui/collapsible";

interface EligibilityFilterDefinition {
  id: number;
  filterKey: string;
  filterName: string;
  filterType: "dropdown" | "text" | "number";
  options: string[];
  isSystem: boolean;
  sortOrder: number;
}

const ELIGIBILITY_FILTERS_PER_PAGE = 10;

const EMAIL_ASSET_NAME_KEYS = {
  interview_invitation: {
    attachment: "candidateInterviewAttachmentName",
    logo: "candidateInterviewLogoAttachmentName",
  },
  reject_application: {
    attachment: "candidateRejectedAttachmentName",
    logo: "candidateRejectedLogoAttachmentName",
  },
  application_confirmation: {
    attachment: "candidateApplicationAttachmentName",
    logo: "candidateApplicationLogoAttachmentName",
  },
} as const;

type EmailTemplateKey = keyof typeof EMAIL_ASSET_NAME_KEYS;
type EmailAssetType = keyof typeof EMAIL_ASSET_NAME_KEYS[EmailTemplateKey];
type EmailAssetUploadKey = `${EmailTemplateKey}:${EmailAssetType}`;

interface EmailAssetFieldsProps {
  templateKey: EmailTemplateKey;
  templateLabel: string;
  attachmentName: string;
  logoName: string;
  canEdit: boolean;
  uploadingAsset: EmailAssetUploadKey | null;
  removingAsset: EmailAssetUploadKey | null;
  onUpload: (
    event: React.ChangeEvent<HTMLInputElement>,
    templateKey: EmailTemplateKey,
    asset: EmailAssetType,
  ) => void;
  onRemove: (templateKey: EmailTemplateKey, asset: EmailAssetType) => void;
}

function EmailAssetFields({
  templateKey,
  templateLabel,
  attachmentName,
  logoName,
  canEdit,
  uploadingAsset,
  removingAsset,
  onUpload,
  onRemove,
}: EmailAssetFieldsProps) {
  const attachmentKey = `${templateKey}:attachment` as EmailAssetUploadKey;
  const logoKey = `${templateKey}:logo` as EmailAssetUploadKey;
  const attachmentInputId = `email-${templateKey}-attachment`;
  const logoInputId = `email-${templateKey}-logo`;
  const isBusy = uploadingAsset !== null || removingAsset !== null;

  return (
    <div className="space-y-3">
      <div>
        <p className="font-medium text-slate-900">Email Attachments</p>
        <p className="text-sm text-slate-500">
          Manage files included with {templateLabel} emails.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={attachmentInputId}>Attachment for Candidate</Label>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <input
              id={attachmentInputId}
              type="file"
              accept=".pdf,.doc,.docx"
              className="hidden"
              onChange={(event) => onUpload(event, templateKey, "attachment")}
              disabled={!canEdit || isBusy}
            />

            <Button
              type="button"
              variant="outline"
              className="h-10"
              disabled={!canEdit || isBusy}
              onClick={() => document.getElementById(attachmentInputId)?.click()}
            >
              {uploadingAsset === attachmentKey ? (
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {uploadingAsset === attachmentKey ? "Uploading..." : "Upload File"}
            </Button>

            {attachmentName ? (
              <div className="flex min-w-0 items-center gap-2 text-sm text-slate-600">
                <FileText className="h-4 w-4 shrink-0 text-[#003B7A]" />
                <span className="truncate">{attachmentName}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 text-slate-500 hover:bg-transparent hover:text-red-600"
                  disabled={!canEdit || isBusy}
                  onClick={() => onRemove(templateKey, "attachment")}
                  aria-label="Remove candidate attachment"
                  title="Remove attachment"
                >
                  {removingAsset === attachmentKey ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <X className="h-4 w-4" />
                  )}
                </Button>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No file uploaded</p>
            )}
          </div>

          <p className="mt-3 text-xs text-slate-500">
            This file will be attached to the {templateLabel} email.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor={logoInputId}>Email Logo</Label>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <input
              id={logoInputId}
              type="file"
              accept=".png,.jpg,.jpeg,.gif,.webp"
              className="hidden"
              onChange={(event) => onUpload(event, templateKey, "logo")}
              disabled={!canEdit || isBusy}
            />

            <Button
              type="button"
              variant="outline"
              className="h-10"
              disabled={!canEdit || isBusy}
              onClick={() => document.getElementById(logoInputId)?.click()}
            >
              {uploadingAsset === logoKey ? (
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {uploadingAsset === logoKey ? "Uploading..." : "Upload Logo"}
            </Button>

            {logoName ? (
              <div className="flex min-w-0 items-center gap-2 text-sm text-slate-600">
                <span className="truncate">{logoName}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 text-slate-500 hover:bg-transparent hover:text-red-600"
                  disabled={!canEdit || isBusy}
                  onClick={() => onRemove(templateKey, "logo")}
                  aria-label="Remove email logo"
                  title="Remove logo"
                >
                  {removingAsset === logoKey ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <X className="h-4 w-4" />
                  )}
                </Button>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No logo uploaded</p>
            )}
          </div>

          <p className="mt-3 text-xs text-slate-500">
            This logo image will be displayed inside the {templateLabel} email.
          </p>
        </div>
      </div>
    </div>
  );
}

// Renders the User Settings component.
export function UserSettings() {
  const navigate = useNavigate();

  const storedUser = getStoredUser();
  const userEmail = storedUser?.email || localStorage.getItem("hr_user") || "";
  const userName = storedUser?.name || userEmail.split("@")[0] || "HR User";
  const userRole = storedUser?.roleName || (storedUser?.roleKey === "hiring_manager" ? "Hiring Manager" : "HR Staff");
  const canEditEmailTemplates =
    storedUser?.roleId === 2 ||
    storedUser?.roleKey === "hiring_manager";

  // Profile state
  const [profileData, setProfileData] = useState({
    fullName: userName,
    email: userEmail,
    phone: storedUser?.phone || "",
    department: storedUser?.department || "Human Resources",
    jobTitle: userRole,
  });
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Password state
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  // Notification settings
  const [notifications, setNotifications] = useState({
    candidateInterviewEnabled: true,
    candidateInterviewSubject:
      "Interview invitation for {jobTitle}",
    candidateInterviewMessage:
      "Dear {candidateName},\n\nWe would like to invite you for an interview for the {jobTitle} position on {interviewDate}.\n\nPlease complete the attached file and reply to this email before attending the interview.\n\nRegards,\n{companyName}",
    candidateInterviewAttachmentName: "",
    candidateInterviewLogoAttachmentName: "",

    candidateRejectedEnabled: true,
    candidateRejectedSubject: "Update on your job application",
    candidateRejectedMessage:
      "Dear {candidateName},\n\nThank you for your interest in {jobTitle}. After careful review, we regret to inform you that you have not been selected for this role.\n\nWe appreciate your time and interest in {companyName}.\n\nRegards,\n{companyName}",
    candidateRejectedAttachmentName: "",
    candidateRejectedLogoAttachmentName: "",

    candidateApplicationEnabled: true,
    candidateApplicationSubject: "Application received for {jobTitle}",
    candidateApplicationMessage:
      "Dear {candidateName},\n\nThank you for applying for the {jobTitle} position at {companyName}.\n\nWe have received your application successfully. Our HR team will review your application and contact you if you are shortlisted.\n\nPlease keep this email for your records.\n\nRegards,\n{companyName}",
    candidateApplicationAttachmentName: "",
    candidateApplicationLogoAttachmentName: "",

    pushNewApplicant: true,
    pushInterviewReminder: true,
  });
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);
  const [uploadingEmailAsset, setUploadingEmailAsset] = useState<
    EmailAssetUploadKey | null
  >(null);
  const [removingEmailAsset, setRemovingEmailAsset] = useState<
    EmailAssetUploadKey | null
  >(null);
  const [openInterviewTemplate, setOpenInterviewTemplate] =
    useState(false);
  const [openRejectTemplate, setOpenRejectTemplate] =
    useState(false);
  const [openApplicationTemplate, setOpenApplicationTemplate] =
    useState(false);
  const [eligibilityFilters, setEligibilityFilters] = useState<
    EligibilityFilterDefinition[]
  >([]);
  const [isLoadingEligibilityFilters, setIsLoadingEligibilityFilters] =
    useState(true);
  const [isEligibilityDialogOpen, setIsEligibilityDialogOpen] =
    useState(false);
  const [editingEligibilityFilter, setEditingEligibilityFilter] =
    useState<EligibilityFilterDefinition | null>(null);
  const [eligibilityDraftName, setEligibilityDraftName] =
    useState("");
  const [eligibilityDraftType, setEligibilityDraftType] =
    useState<EligibilityFilterDefinition["filterType"]>("dropdown");
  const [eligibilityDraftOptions, setEligibilityDraftOptions] =
    useState<string[]>([""]);
  const [deleteEligibilityTarget, setDeleteEligibilityTarget] =
    useState<EligibilityFilterDefinition | null>(null);
  const [eligibilityFilterPage, setEligibilityFilterPage] = useState(1);
  // Avatar state
  const [avatarPreview, setAvatarPreview] = useState<
    string | null
  >(storedUser?.avatarPath || null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);

  const eligibilityFilterPageCount = Math.max(
    1,
    Math.ceil(eligibilityFilters.length / ELIGIBILITY_FILTERS_PER_PAGE),
  );
  const pagedEligibilityFilters = eligibilityFilters.slice(
    (eligibilityFilterPage - 1) * ELIGIBILITY_FILTERS_PER_PAGE,
    eligibilityFilterPage * ELIGIBILITY_FILTERS_PER_PAGE,
  );

  useEffect(() => {
    setEligibilityFilterPage((currentPage) =>
      Math.min(currentPage, eligibilityFilterPageCount),
    );
  }, [eligibilityFilterPageCount]);

  // Handles profile update.
  const handleProfileUpdate = async () => {
    if (!storedUser?.id) {
      toast.error("Unable to identify the current user");
      return false;
    }

    setIsSavingProfile(true);
    try {
      const data = await apiFetch<{ user: AuthUser }>("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({
          userId: storedUser.id,
          fullName: profileData.fullName,
          department: profileData.department,
          phone: profileData.phone,
        }),
      });

      localStorage.setItem("hr_user", data.user.email);
      localStorage.setItem("hr_user_data", JSON.stringify(data.user));
      setProfileData((prev) => ({
        ...prev,
        fullName: data.user.name,
        email: data.user.email,
        phone: data.user.phone || "",
        department: data.user.department || "Human Resources",
        jobTitle: data.user.roleName,
      }));
      toast.success("Profile updated successfully!", {
        description: "Your changes have been saved.",
      });
      return true;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update profile");
      return false;
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handles password change.
  const handlePasswordChange = async () => {
    if (!storedUser?.id) {
      toast.error("Unable to identify the current user");
      return;
    }

    if (!passwordData.currentPassword) {
      toast.error("Current password is required");
      return;
    }

    if (
      passwordData.newPassword !== passwordData.confirmPassword
    ) {
      toast.error("Passwords don't match!", {
        description:
          "Please make sure your new passwords match.",
      });
      return;
    }

    if (passwordData.newPassword.length < 8) {
      toast.error("Password too short!", {
        description:
          "Password must be at least 8 characters long.",
      });
      return;
    }

    setIsSavingPassword(true);
    try {
      await apiFetch("/auth/password", {
        method: "PATCH",
        body: JSON.stringify({
          userId: storedUser.id,
          currentPassword: passwordData.currentPassword,
          newPassword: passwordData.newPassword,
        }),
      });

      localStorage.setItem(
        "hr_user_data",
        JSON.stringify({ ...storedUser, mustChangePassword: false }),
      );
      toast.success("Password changed successfully!", {
        description: "Your password has been updated.",
      });
      setPasswordData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to change password",
      );
    } finally {
      setIsSavingPassword(false);
    }
  };

  // Handles avatar upload.
  const handleAvatarUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    // Show a local preview before the upload finishes.
    const file = e.target.files?.[0];
    if (!file) return;

    if (!storedUser?.id) {
      toast.error("Unable to identify the current user");
      e.target.value = "";
      return;
    }

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload an image file");
      e.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("File size must be less than 5MB");
      e.target.value = "";
      return;
    }

    const localPreview = URL.createObjectURL(file);
    setAvatarPreview(localPreview);

    const formData = new FormData();
    formData.append("userId", String(storedUser.id));
    formData.append("fullName", profileData.fullName);
    formData.append("department", profileData.department);
    formData.append("phone", profileData.phone);
    formData.append("avatar", file);

    setIsUploadingAvatar(true);
    try {
      const data = await apiFetch<{ user: AuthUser }>("/auth/profile/avatar", {
        method: "POST",
        body: formData,
      });

      localStorage.setItem("hr_user", data.user.email);
      localStorage.setItem("hr_user_data", JSON.stringify(data.user));
      setAvatarPreview(data.user.avatarPath || localPreview);
      setProfileData((prev) => ({
        ...prev,
        fullName: data.user.name,
        email: data.user.email,
        phone: data.user.phone || "",
        department: data.user.department || "Human Resources",
        jobTitle: data.user.roleName,
      }));
      toast.success("Avatar uploaded successfully!");
    } catch (error) {
      setAvatarPreview(storedUser.avatarPath || null);
      toast.error(error instanceof Error ? error.message : "Failed to upload avatar");
    } finally {
      setIsUploadingAvatar(false);
      e.target.value = "";
    }
  };

  // Handles notification update.
  const handleNotificationUpdate = async () => {
    if (!canEditEmailTemplates) {
      toast.error("Only Hiring Manager can edit email templates");
      return;
    }

    setIsSavingNotifications(true);
    try {
      await apiFetch("/email-templates", {
        method: "POST",
        body: JSON.stringify({
          interview: {
            enabled: notifications.candidateInterviewEnabled,
            subject: notifications.candidateInterviewSubject,
            body: notifications.candidateInterviewMessage,
          },
          reject: {
            enabled: notifications.candidateRejectedEnabled,
            subject: notifications.candidateRejectedSubject,
            body: notifications.candidateRejectedMessage,
          },
          application: {
            enabled: notifications.candidateApplicationEnabled,
            subject: notifications.candidateApplicationSubject,
            body: notifications.candidateApplicationMessage,
          },
        }),
      });

      toast.success("Notification settings updated!", {
        description: "Your preferences have been saved.",
      });
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to save notification settings",
      );
    } finally {
      setIsSavingNotifications(false);
    }
  };

  // Loads eligibility filters.
  const loadEligibilityFilters = async () => {
    // These filter definitions are used by Create Job.
    setIsLoadingEligibilityFilters(true);
    try {
      const data = await apiFetch<{ filters: EligibilityFilterDefinition[] }>(
        "/eligibility-filter-definitions",
      );
      setEligibilityFilters(data.filters || []);
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to load eligibility filters",
      );
    } finally {
      setIsLoadingEligibilityFilters(false);
    }
  };

  // Opens add eligibility filter.
  const openAddEligibilityFilter = () => {
    setEditingEligibilityFilter(null);
    setEligibilityDraftName("");
    setEligibilityDraftType("dropdown");
    setEligibilityDraftOptions([""]);
    setIsEligibilityDialogOpen(true);
  };

  // Opens edit eligibility filter.
  const openEditEligibilityFilter = (filter: EligibilityFilterDefinition) => {
    setEditingEligibilityFilter(filter);
    setEligibilityDraftName(filter.filterName);
    setEligibilityDraftType(filter.filterType || "dropdown");
    setEligibilityDraftOptions(filter.options.length > 0 ? filter.options : [""]);
    setIsEligibilityDialogOpen(true);
  };

  // Updates eligibility draft option.
  const updateEligibilityDraftOption = (index: number, value: string) => {
    setEligibilityDraftOptions((current) =>
      current.map((option, optionIndex) =>
        optionIndex === index ? value : option,
      ),
    );
  };

  // Removes eligibility draft option.
  const removeEligibilityDraftOption = (index: number) => {
    setEligibilityDraftOptions((current) =>
      current.length === 1
        ? [""]
        : current.filter((_, optionIndex) => optionIndex !== index),
    );
  };

  // Saves eligibility filter.
  const saveEligibilityFilter = async () => {
    // Text and number filters do not need option values.
    const filterName = eligibilityDraftName.trim();
    const options =
      eligibilityDraftType === "dropdown"
        ? eligibilityDraftOptions
            .map((option) => option.trim())
            .filter(Boolean)
        : [];

    if (!filterName) {
      toast.error("Filter name is required");
      return;
    }

    try {
      const path = editingEligibilityFilter
        ? `/eligibility-filter-definitions/${editingEligibilityFilter.id}`
        : "/eligibility-filter-definitions";
      const method = editingEligibilityFilter ? "PATCH" : "POST";
      const data = await apiFetch<{ filters: EligibilityFilterDefinition[] }>(
        path,
        {
          method,
          body: JSON.stringify({
            filterName,
            filterType: eligibilityDraftType,
            options,
          }),
        },
      );

      setEligibilityFilters(data.filters || []);
      setIsEligibilityDialogOpen(false);
      toast.success(
        editingEligibilityFilter
          ? "Eligibility filter updated"
          : "Eligibility filter added",
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to save eligibility filter",
      );
    }
  };

  // Provides the confirm delete eligibility filter helper.
  const confirmDeleteEligibilityFilter = async () => {
    if (!deleteEligibilityTarget) return;

    try {
      const data = await apiFetch<{ filters: EligibilityFilterDefinition[] }>(
        `/eligibility-filter-definitions/${deleteEligibilityTarget.id}`,
        { method: "DELETE" },
      );
      setEligibilityFilters(data.filters || []);
      setDeleteEligibilityTarget(null);
      toast.success("Eligibility filter deleted");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to delete eligibility filter",
      );
    }
  };

  useEffect(() => {
    setIsLoadingTemplates(true);
    apiFetch<{
      templates: {
        interview_invitation?: {
          subject?: string;
          body?: string;
          isActive?: boolean | number | string;
          attachmentFileName?: string | null;
          logoAttachmentFileName?: string | null;
        };
        reject_application?: {
          subject?: string;
          body?: string;
          isActive?: boolean | number | string;
          attachmentFileName?: string | null;
          logoAttachmentFileName?: string | null;
        };
        application_confirmation?: {
          subject?: string;
          body?: string;
          isActive?: boolean | number | string;
          attachmentFileName?: string | null;
          logoAttachmentFileName?: string | null;
        };
      };
    }>("/email-templates")
      .then((data) => {
        const interview = data.templates?.interview_invitation;
        const reject = data.templates?.reject_application;
        const application = data.templates?.application_confirmation;

        setNotifications((current) => ({
          ...current,
          candidateInterviewEnabled:
            interview?.isActive === undefined
              ? current.candidateInterviewEnabled
              : interview.isActive === true ||
                interview.isActive === 1 ||
                interview.isActive === "1",
          candidateInterviewSubject:
            interview?.subject ||
            current.candidateInterviewSubject,
          candidateInterviewMessage:
            interview?.body ||
            current.candidateInterviewMessage,
          candidateInterviewAttachmentName:
            interview?.attachmentFileName ||
            current.candidateInterviewAttachmentName,
          candidateInterviewLogoAttachmentName:
            interview?.logoAttachmentFileName ||
            current.candidateInterviewLogoAttachmentName,
          candidateRejectedEnabled:
            reject?.isActive === undefined
              ? current.candidateRejectedEnabled
              : reject.isActive === true ||
                reject.isActive === 1 ||
                reject.isActive === "1",
          candidateRejectedSubject:
            reject?.subject || current.candidateRejectedSubject,
          candidateRejectedMessage:
            reject?.body || current.candidateRejectedMessage,
          candidateRejectedAttachmentName:
            reject?.attachmentFileName ||
            current.candidateRejectedAttachmentName,
          candidateRejectedLogoAttachmentName:
            reject?.logoAttachmentFileName ||
            current.candidateRejectedLogoAttachmentName,
          candidateApplicationEnabled:
            application?.isActive === undefined
              ? current.candidateApplicationEnabled
              : application.isActive === true ||
                application.isActive === 1 ||
                application.isActive === "1",
          candidateApplicationSubject:
            application?.subject || current.candidateApplicationSubject,
          candidateApplicationMessage:
            application?.body || current.candidateApplicationMessage,
          candidateApplicationAttachmentName:
            application?.attachmentFileName ||
            current.candidateApplicationAttachmentName,
          candidateApplicationLogoAttachmentName:
            application?.logoAttachmentFileName ||
            current.candidateApplicationLogoAttachmentName,
        }));
      })
      .catch(() => {
        // Keep local defaults if the template cannot be loaded.
      })
      .finally(() => setIsLoadingTemplates(false));
  }, []);

  useEffect(() => {
    loadEligibilityFilters();
  }, []);

  const handleEmailAssetUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    templateKey: EmailTemplateKey,
    asset: EmailAssetType,
  ) => {
    if (!canEditEmailTemplates) {
      toast.error("Only Hiring Manager can edit email templates");
      e.target.value = "";
      return;
    }

    const file = e.target.files?.[0];
    if (!file) return;

    const isLogo = asset === "logo";
    const maxSize = isLogo ? 5 * 1024 * 1024 : 10 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error(
        isLogo
          ? "Email logo size must be less than 5MB"
          : "Attachment size must be less than 10MB",
      );
      e.target.value = "";
      return;
    }

    const formData = new FormData();
    formData.append("attachment", file);
    const uploadKey = `${templateKey}:${asset}` as EmailAssetUploadKey;
    const endpoint = `/email-templates/${templateKey}/${isLogo ? "logo-attachment" : "attachment"}`;

    setUploadingEmailAsset(uploadKey);
    try {
      const response = await apiFetch<{ fileName: string }>(endpoint, {
        method: "POST",
        body: formData,
      });

      setNotifications((current) => ({
        ...current,
        [EMAIL_ASSET_NAME_KEYS[templateKey][asset]]: response.fileName,
      }));
      toast.success(
        `${isLogo ? "Email logo" : "Email attachment"} uploaded successfully!`,
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : `Failed to upload ${isLogo ? "email logo" : "email attachment"}`,
      );
    } finally {
      setUploadingEmailAsset(null);
      e.target.value = "";
    }
  };

  const removeEmailAsset = async (
    templateKey: EmailTemplateKey,
    asset: EmailAssetType,
  ) => {
    if (!canEditEmailTemplates || removingEmailAsset || uploadingEmailAsset) {
      return;
    }

    const isLogo = asset === "logo";
    const removeKey = `${templateKey}:${asset}` as EmailAssetUploadKey;
    const endpoint = `/email-templates/${templateKey}/${isLogo ? "logo-attachment" : "attachment"}`;
    setRemovingEmailAsset(removeKey);
    try {
      await apiFetch(endpoint, { method: "DELETE" });
      setNotifications((current) => ({
        ...current,
        [EMAIL_ASSET_NAME_KEYS[templateKey][asset]]: "",
      }));
      toast.success(
        isLogo ? "Email logo removed" : "Email attachment removed",
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to remove email attachment",
      );
    } finally {
      setRemovingEmailAsset(null);
    }
  };

  const [isEditingProfile, setIsEditingProfile] =
    useState(false);
  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Settings" },
      ]}
      title="Settings"
      subtitle="Manage security, notification email settings and eligibility filters"
      useCard={false}
    >
      <Tabs defaultValue="security" className="space-y-6">
        <TabsList>
          <TabsTrigger value="security">
            <Shield className="w-4 h-4 mr-2" />
            Security
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="w-4 h-4 mr-2" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="eligibility-filters">
            <Filter className="w-4 h-4 mr-2" />
            Eligibility Filters
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}

        <TabsContent value="profile" className="space-y-6">
          <Card className="border border-slate-200 shadow-md rounded-2xl">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl font-semibold">
                Employee Profile Settings
              </CardTitle>
              <CardDescription className="text-base">
                Review and update your profile details, contact
                information, and professional role.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Top summary */}
              <div className="flex items-start gap-5">
                <div className="relative shrink-0">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-3xl font-bold overflow-hidden">
                    {avatarPreview ? (
                      <img
                        src={avatarPreview}
                        alt="Avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span>
                        {profileData.fullName.charAt(0)}
                      </span>
                    )}
                  </div>

                  <label
                    htmlFor="avatar-upload"
                    className="absolute bottom-0 right-0 w-8 h-8 bg-white border border-slate-200 rounded-full flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-colors shadow-sm"
                  >
                    <Camera className="w-4 h-4 text-slate-600" />
                  </label>

                  <input
                    id="avatar-upload"
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                    className="hidden"
                  />
                </div>

                <div className="min-w-0 flex-1 pt-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-2xl font-semibold text-slate-900 truncate">
                      {profileData.fullName}
                    </h3>

                    <button
                      type="button"
                      onClick={() =>
                        setIsEditingProfile((prev) => !prev)
                      }
                      className="inline-flex items-center justify-center text-slate-500 hover:text-slate-700 transition-colors"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                  </div>

                  <p className="text-base text-slate-600 mb-1">
                    {profileData.department} ·{" "}
                    {profileData.jobTitle}
                  </p>

                  <p className="text-base text-slate-500 mb-4 break-all">
                    {profileData.email}
                  </p>

                  <label htmlFor="avatar-upload">
                    <Button
                      variant="outline"
                      className="h-10 px-5"
                      asChild
                      disabled={isUploadingAvatar}
                    >
                      <span className="cursor-pointer">
                        <Upload className="w-4 h-4 mr-2" />
                        {isUploadingAvatar ? "Uploading..." : "Upload New Photo"}
                      </span>
                    </Button>
                  </label>

                  <p className="text-sm text-slate-500 mt-3">
                    JPG, PNG or GIF. Max size 5MB.
                  </p>
                </div>
              </div>

              {/* Editable form */}
              {isEditingProfile && (
                <>
                  <div className="border-t border-slate-200 pt-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-6">
                      <div className="space-y-2">
                        <Label htmlFor="fullName">
                          Full Name
                        </Label>
                        <Input
                          id="fullName"
                          value={profileData.fullName}
                          onChange={(e) =>
                            setProfileData({
                              ...profileData,
                              fullName: e.target.value,
                            })
                          }
                          className="h-12"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="department">
                          Department
                        </Label>
                        <Select
                          value={profileData.department}
                          onValueChange={(value) =>
                            setProfileData({
                              ...profileData,
                              department: value,
                            })
                          }
                        >
                          <SelectTrigger
                            id="department"
                            className="h-12"
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Human Resources">
                              Human Resources
                            </SelectItem>
                            <SelectItem value="Engineering">
                              Engineering
                            </SelectItem>
                            <SelectItem value="Product">
                              Product
                            </SelectItem>
                            <SelectItem value="Marketing">
                              Marketing
                            </SelectItem>
                            <SelectItem value="Sales">
                              Sales
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="phone">
                          Phone Number
                        </Label>
                        <Input
                          id="phone"
                          type="tel"
                          value={profileData.phone}
                          onChange={(e) =>
                            setProfileData({
                              ...profileData,
                              phone: e.target.value,
                            })
                          }
                          placeholder="+60 12-345 6789"
                          className="h-12"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="jobTitle">
                          Job Title
                        </Label>
                        <Input
                          id="jobTitle"
                          value={profileData.jobTitle}
                          onChange={(e) =>
                            setProfileData({
                              ...profileData,
                              jobTitle: e.target.value,
                            })
                          }
                          className="h-12"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <Button
                      className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-6 h-11"
                      disabled={isSavingProfile}
                      onClick={async () => {
                        const saved = await handleProfileUpdate();
                        if (saved) {
                          setIsEditingProfile(false);
                        }
                      }}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      {isSavingProfile ? "Saving..." : "Save Profile Changes"}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">
                  Current Password
                </Label>
                <PasswordInput
                  id="currentPassword"
                  value={passwordData.currentPassword}
                  onChange={(e) =>
                    setPasswordData({
                      ...passwordData,
                      currentPassword: e.target.value,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">
                  New Password
                </Label>
                <PasswordInput
                  id="newPassword"
                  value={passwordData.newPassword}
                  onChange={(e) =>
                    setPasswordData({
                      ...passwordData,
                      newPassword: e.target.value,
                    })
                  }
                />
                <p className="text-xs text-slate-500">
                  Password must be at least 8 characters long
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">
                  Confirm New Password
                </Label>
                <PasswordInput
                  id="confirmPassword"
                  value={passwordData.confirmPassword}
                  onChange={(e) =>
                    setPasswordData({
                      ...passwordData,
                      confirmPassword: e.target.value,
                    })
                  }
                />
              </div>
              <div className="flex justify-end">
                <Button
                  className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5"
                  onClick={handlePasswordChange}
                  disabled={isSavingPassword}
                >
                  <Lock className="w-4 h-4 mr-2" />
                  {isSavingPassword ? "Updating..." : "Update Password"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="hidden shadow-md">
            <CardHeader>
              <CardTitle>Active Sessions</CardTitle>
              <CardDescription>
                Manage your active sessions across devices
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                <div>
                  <p className="font-medium">
                    Chrome on Windows
                  </p>
                  <p className="text-sm text-slate-500">
                    Kuala Lumpur, Malaysia • Current session
                  </p>
                </div>
                <Badge className="bg-green-600">Active</Badge>
              </div>
              <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                <div>
                  <p className="font-medium">
                    Safari on MacBook
                  </p>
                  <p className="text-sm text-slate-500">
                    Kuala Lumpur, Malaysia • Last active 2 days
                    ago
                  </p>
                </div>
                <Button variant="ghost" size="sm">
                  Revoke
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent
          value="notifications"
          className="space-y-6"
        >
          {isLoadingTemplates ? (
            <LoadingState title="Loading notification settings" />
          ) : (
            <>
          {/* Interview Email Template */}
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Interview Email Template</CardTitle>
              <CardDescription>
                Configure the email sent when HR invites a
                candidate for an interview
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="candidate-interview-enabled">
                    Enable Interview Email
                  </Label>
                  <p className="text-sm text-slate-500">
                    Send this email when a candidate is invited
                    for an interview
                  </p>
                </div>

                <Switch
                  id="candidate-interview-enabled"
                  checked={
                    notifications.candidateInterviewEnabled
                  }
                  disabled={!canEditEmailTemplates}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      candidateInterviewEnabled: checked,
                    })
                  }
                />
              </div>

              <Collapsible
                open={openInterviewTemplate}
                onOpenChange={setOpenInterviewTemplate}
                className="space-y-4"
              >
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between text-left"
                  >
                    <div>
                      <p className="font-medium text-slate-900">
                        Email content and attachments
                      </p>
                      <p className="text-sm text-slate-500">
                        {canEditEmailTemplates
                          ? "Click to edit the interview email template"
                          : "Click to view the interview email template"}
                      </p>
                    </div>
                    <ChevronDown
                      className={`h-5 w-5 text-slate-500 transition-transform ${
                        openInterviewTemplate ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="candidate-interview-subject">
                      Subject
                    </Label>
                    <Input
                      id="candidate-interview-subject"
                      value={
                        notifications.candidateInterviewSubject
                      }
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateInterviewSubject: e.target.value,
                        })
                      }
                      placeholder="Interview invitation for {jobTitle}"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="candidate-interview-message">
                      Message
                    </Label>
                    <Textarea
                      id="candidate-interview-message"
                      rows={7}
                      value={
                        notifications.candidateInterviewMessage
                      }
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateInterviewMessage: e.target.value,
                        })
                      }
                      placeholder="Dear {candidateName}, please complete the attached file and reply to this email before the interview on {interviewDate}."
                    />
                  </div>

                  <EmailAssetFields
                    templateKey="interview_invitation"
                    templateLabel="interview"
                    attachmentName={notifications.candidateInterviewAttachmentName}
                    logoName={notifications.candidateInterviewLogoAttachmentName}
                    canEdit={canEditEmailTemplates}
                    uploadingAsset={uploadingEmailAsset}
                    removingAsset={removingEmailAsset}
                    onUpload={handleEmailAssetUpload}
                    onRemove={removeEmailAsset}
                  />

                  <p className="text-xs text-slate-500">
                    Available placeholders: {"{candidateName}"},{" "}
                    {"{jobTitle}"}, {"{companyName}"},{" "}
                    {"{interviewDateOptions}"}
                  </p>
                </CollapsibleContent>
              </Collapsible>
            </CardContent>
          </Card>

          {/* Rejected Email Template */}
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Rejected Email Template</CardTitle>
              <CardDescription>
                Configure the email sent when a candidate is not
                selected
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="candidate-rejected-enabled">
                    Enable Rejected Email
                  </Label>
                  <p className="text-sm text-slate-500">
                    Send this email when a candidate is not
                    selected
                  </p>
                </div>

                <Switch
                  id="candidate-rejected-enabled"
                  checked={
                    notifications.candidateRejectedEnabled
                  }
                  disabled={!canEditEmailTemplates}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      candidateRejectedEnabled: checked,
                    })
                  }
                />
              </div>

              <Collapsible
                open={openRejectTemplate}
                onOpenChange={setOpenRejectTemplate}
                className="space-y-4"
              >
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between text-left"
                  >
                    <div>
                      <p className="font-medium text-slate-900">
                        Email content
                      </p>
                      <p className="text-sm text-slate-500">
                        {canEditEmailTemplates
                          ? "Click to edit the rejection email template"
                          : "Click to view the rejection email template"}
                      </p>
                    </div>
                    <ChevronDown
                      className={`h-5 w-5 text-slate-500 transition-transform ${
                        openRejectTemplate ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="candidate-rejected-subject">
                      Subject
                    </Label>
                    <Input
                      id="candidate-rejected-subject"
                      value={notifications.candidateRejectedSubject}
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateRejectedSubject: e.target.value,
                        })
                      }
                      placeholder="Update on your job application"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="candidate-rejected-message">
                      Message
                    </Label>
                    <Textarea
                      id="candidate-rejected-message"
                      rows={6}
                      value={notifications.candidateRejectedMessage}
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateRejectedMessage: e.target.value,
                        })
                      }
                      placeholder="Dear {candidateName}, thank you for your interest in {jobTitle}."
                    />
                  </div>

                  <EmailAssetFields
                    templateKey="reject_application"
                    templateLabel="rejection"
                    attachmentName={notifications.candidateRejectedAttachmentName}
                    logoName={notifications.candidateRejectedLogoAttachmentName}
                    canEdit={canEditEmailTemplates}
                    uploadingAsset={uploadingEmailAsset}
                    removingAsset={removingEmailAsset}
                    onUpload={handleEmailAssetUpload}
                    onRemove={removeEmailAsset}
                  />

                  <p className="text-xs text-slate-500">
                    Available placeholders: {"{candidateName}"},{" "}
                    {"{jobTitle}"}, {"{companyName}"}
                  </p>
                </CollapsibleContent>
              </Collapsible>
            </CardContent>
          </Card>

          {/* Application confirmation email template */}
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Application Confirmation Email</CardTitle>
              <CardDescription>
                Configure the email sent after a candidate submits an application
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="candidate-application-enabled">
                    Enable Application Confirmation Email
                  </Label>
                  <p className="text-sm text-slate-500">
                    Send a confirmation email after an application is received
                  </p>
                </div>

                <Switch
                  id="candidate-application-enabled"
                  checked={notifications.candidateApplicationEnabled}
                  disabled={!canEditEmailTemplates}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      candidateApplicationEnabled: checked,
                    })
                  }
                />
              </div>

              <Collapsible
                open={openApplicationTemplate}
                onOpenChange={setOpenApplicationTemplate}
                className="space-y-4"
              >
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between text-left"
                  >
                    <div>
                      <p className="font-medium text-slate-900">
                        Email content
                      </p>
                      <p className="text-sm text-slate-500">
                        {canEditEmailTemplates
                          ? "Click to edit the application confirmation email"
                          : "Click to view the application confirmation email"}
                      </p>
                    </div>
                    <ChevronDown
                      className={`h-5 w-5 text-slate-500 transition-transform ${
                        openApplicationTemplate ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="candidate-application-subject">
                      Subject
                    </Label>
                    <Input
                      id="candidate-application-subject"
                      value={notifications.candidateApplicationSubject}
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateApplicationSubject: e.target.value,
                        })
                      }
                      placeholder="Application received for {jobTitle}"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="candidate-application-message">
                      Message
                    </Label>
                    <Textarea
                      id="candidate-application-message"
                      rows={7}
                      value={notifications.candidateApplicationMessage}
                      disabled={!canEditEmailTemplates}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          candidateApplicationMessage: e.target.value,
                        })
                      }
                      placeholder="Dear {candidateName}, thank you for applying for the {jobTitle} position."
                    />
                  </div>

                  <EmailAssetFields
                    templateKey="application_confirmation"
                    templateLabel="application confirmation"
                    attachmentName={notifications.candidateApplicationAttachmentName}
                    logoName={notifications.candidateApplicationLogoAttachmentName}
                    canEdit={canEditEmailTemplates}
                    uploadingAsset={uploadingEmailAsset}
                    removingAsset={removingEmailAsset}
                    onUpload={handleEmailAssetUpload}
                    onRemove={removeEmailAsset}
                  />

                  <p className="text-xs text-slate-500">
                    Available placeholders: {"{candidateName}"},{" "}
                    {"{jobTitle}"},{" "}
                    {"{companyName}"}
                  </p>
                </CollapsibleContent>
              </Collapsible>
            </CardContent>
          </Card>

          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Push Notifications</CardTitle>
              <CardDescription>
                Manage browser notifications for internal
                updates
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="push-new-applicant">
                    New Applicant
                  </Label>
                  <p className="text-sm text-slate-500">
                    Get notified instantly when someone applies
                  </p>
                </div>
                <Switch
                  id="push-new-applicant"
                  checked={notifications.pushNewApplicant}
                  disabled={!canEditEmailTemplates}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      pushNewApplicant: checked,
                    })
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="push-interview">
                    Interview Reminders
                  </Label>
                  <p className="text-sm text-slate-500">
                    Get push notifications for interview
                    reminders
                  </p>
                </div>
                <Switch
                  id="push-interview"
                  checked={notifications.pushInterviewReminder}
                  disabled={!canEditEmailTemplates}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      pushInterviewReminder: checked,
                    })
                  }
                />
              </div>
            </CardContent>
          </Card>

          {canEditEmailTemplates && (
            <div className="flex justify-end">
              <Button
                type="button"
                className="bg-[#003B7A] hover:bg-[#002f63] text-white shadow-sm px-5"
                onClick={handleNotificationUpdate}
                disabled={isSavingNotifications}
              >
                {isSavingNotifications ? (
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                {isSavingNotifications ? "Saving..." : "Save Preferences"}
              </Button>
            </div>
          )}
            </>
          )}
        </TabsContent>
        
        <TabsContent value="eligibility-filters" className="space-y-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-xl font-semibold text-slate-950">
              Eligibility Filters
            </h2>
            <Button
              type="button"
              onClick={openAddEligibilityFilter}
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Filter
            </Button>
          </div>

              {isLoadingEligibilityFilters ? (
                <LoadingState title="Loading eligibility filters" />
              ) : eligibilityFilters.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">
                  No eligibility filters found.
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg border border-slate-200">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-slate-600">
                          Filter Name
                        </TableHead>
                        <TableHead className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-slate-600">
                          Type
                        </TableHead>
                        <TableHead className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-slate-600">
                          Options
                        </TableHead>
                        <TableHead className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wide text-slate-600">
                          Actions
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pagedEligibilityFilters.map((filter) => (
                        <TableRow key={filter.id} className="bg-white">
                          <TableCell className="px-6 py-4 font-medium text-slate-950">
                            {filter.filterName}
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            <Badge
                              variant="outline"
                              className="border-blue-100 bg-blue-50 text-[#003B7A]"
                            >
                              {filter.filterType === "number"
                                ? "Number"
                                : filter.filterType === "text"
                                  ? "Text"
                                  : "Dropdown"}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            {filter.options.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {filter.options.map((option) => (
                                  <Badge
                                    key={option}
                                    variant="outline"
                                    className="border-slate-200 bg-slate-50 text-slate-700"
                                  >
                                    {option}
                                  </Badge>
                                ))}
                              </div>
                            ) : (
                              <span className="text-sm text-slate-400">No options</span>
                            )}
                          </TableCell>
                          <TableCell className="px-6 py-4">
                            <div className="flex justify-end gap-2">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => openEditEligibilityFilter(filter)}
                                className="border-slate-300 text-slate-700 hover:bg-slate-50"
                              >
                                Edit
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setDeleteEligibilityTarget(filter)}
                                className="border-red-200 text-red-600 hover:bg-red-50"
                              >
                                Delete
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {eligibilityFilters.length > ELIGIBILITY_FILTERS_PER_PAGE && (
                <Pagination className="pt-4">
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        href="#"
                        className={
                          eligibilityFilterPage === 1
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                        onClick={(event) => {
                          event.preventDefault();
                          setEligibilityFilterPage((page) =>
                            Math.max(1, page - 1),
                          );
                        }}
                      />
                    </PaginationItem>
                    {getCompactPageItems(
                      eligibilityFilterPage,
                      eligibilityFilterPageCount,
                    ).map((item) => (
                      <PaginationItem key={item}>
                        {typeof item === "number" ? (
                          <PaginationLink
                            href="#"
                            isActive={item === eligibilityFilterPage}
                            onClick={(event) => {
                              event.preventDefault();
                              setEligibilityFilterPage(item);
                            }}
                          >
                            {item}
                          </PaginationLink>
                        ) : (
                          <PaginationEllipsis />
                        )}
                      </PaginationItem>
                    ))}
                    <PaginationItem>
                      <PaginationNext
                        href="#"
                        className={
                          eligibilityFilterPage === eligibilityFilterPageCount
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                        onClick={(event) => {
                          event.preventDefault();
                          setEligibilityFilterPage((page) =>
                            Math.min(eligibilityFilterPageCount, page + 1),
                          );
                        }}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              )}
        </TabsContent>

        <Dialog
          open={isEligibilityDialogOpen}
          onOpenChange={setIsEligibilityDialogOpen}
        >
          <DialogContent
            className="max-h-[90vh] overflow-hidden sm:max-w-2xl"
            onOpenAutoFocus={(event) => event.preventDefault()}
          >
            <DialogHeader>
              <DialogTitle>
                {editingEligibilityFilter ? "Edit Filter" : "Add Filter"}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="eligibility-filter-name">Filter Name</Label>
                  <Input
                    id="eligibility-filter-name"
                    value={eligibilityDraftName}
                    onChange={(event) =>
                      setEligibilityDraftName(event.target.value)
                    }
                    placeholder="Enter filter name"
                    className="!h-11 min-h-11 bg-slate-50 px-4"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="eligibility-filter-type">Field Type</Label>
                  <Select
                    value={eligibilityDraftType}
                    onValueChange={(value) =>
                      setEligibilityDraftType(
                        value as EligibilityFilterDefinition["filterType"],
                      )
                    }
                  >
                    <SelectTrigger
                      id="eligibility-filter-type"
                      className="!h-11 min-h-11 border-slate-200 bg-slate-50 px-4 text-slate-700"
                    >
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dropdown">Dropdown</SelectItem>
                      <SelectItem value="text">Text</SelectItem>
                      <SelectItem value="number">Number</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {eligibilityDraftType === "dropdown" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Filter Options</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setEligibilityDraftOptions((current) => [...current, ""])
                    }
                    className="border-[#003B7A] text-[#003B7A] hover:bg-blue-50"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add Option
                  </Button>
                </div>

                <div className="uwc-scrollbar max-h-72 space-y-2 overflow-y-auto pr-2">
                  {eligibilityDraftOptions.map((option, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Input
                        value={option}
                        onChange={(event) =>
                          updateEligibilityDraftOption(index, event.target.value)
                        }
                        placeholder="Enter option"
                        className="!h-11 min-h-11 bg-slate-50 px-4"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeEligibilityDraftOption(index)}
                        className="h-11 w-11 shrink-0 text-slate-500 hover:bg-red-50 hover:text-red-600"
                        aria-label="Remove option"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                onClick={saveEligibilityFilter}
                className="bg-[#003B7A] text-white hover:bg-[#002f63]"
              >
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <AlertDialog
          open={Boolean(deleteEligibilityTarget)}
          onOpenChange={(open) => {
            if (!open) setDeleteEligibilityTarget(null);
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete eligibility filter?</AlertDialogTitle>
              <AlertDialogDescription>
                This filter will be removed from the Create Job eligibility filter list.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction
                onClick={confirmDeleteEligibilityFilter}
                className="bg-red-600 text-white hover:bg-red-700"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Tabs>
    </PageLayout>
  );
}
