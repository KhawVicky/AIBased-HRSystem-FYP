// Shows the Admin view.
import { useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  MoreHorizontal,
  UserPlus,
  Users,
  UserCheck,
  Mail,
  KeyRound,
  Pencil,
  Ban,
  CheckCircle2,
  Briefcase,
  Filter,
} from "lucide-react";

import { PageLayout } from "../shared/PageLayout";
import { SearchClearButton } from "../shared/SearchClearButton";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Badge } from "../ui/badge";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../ui/pagination";
import { toast } from "sonner";
import { apiFetch, getStoredUser } from "../../lib/api";
import { formatDisplayDate, formatDisplayDateTime } from "../../lib/date";
import { getCompactPageItems } from "../../lib/pagination";
import { LoadingState } from "../shared/LoadingState";
import { PasswordInput } from "../shared/PasswordInput";

type UserRole = "HR Staff" | "Hiring Manager";
type UserStatus = "Active" | "Inactive";

type UserAccount = {
  numericId: number;
  id: string;
  fullName: string;
  email: string;
  avatarPath?: string | null;
  role: UserRole;
  status: UserStatus;
  createdAt: string;
};

type ApiUser = {
  id: number;
  name: string;
  email: string;
  avatarPath?: string | null;
  status: string;
  roleId: 1 | 2;
  roleKey: "hr_staff" | "hiring_manager";
  createdAt: string;
};

// Provides the map api user helper.
const mapApiUser = (user: ApiUser): UserAccount => ({
  numericId: user.id,
  id: `USR-${String(user.id).padStart(3, "0")}`,
  fullName: user.name,
  email: user.email,
  avatarPath: user.avatarPath || null,
  role: user.roleId === 2 ? "Hiring Manager" : "HR Staff",
  status: user.status === "active" ? "Active" : "Inactive",
  createdAt: user.createdAt.slice(0, 10),
});

type UserActionLog = {
  id: number;
  actionType: string;
  actionLabel: string;
  reasonType: string | null;
  reasonDetails: string | null;
  createdAt: string;
  applicationId: number | null;
  jobId: number | null;
  jobTitle: string | null;
  jobDepartment: string | null;
  candidateId: number | null;
  candidateName: string | null;
  candidateEmail: string | null;
  applicationStatus: string | null;
};

const ACTION_HISTORY_PAGE_SIZE = 20;

// Provides the role to id helper.
const roleToId = (role: UserRole) =>
  role === "Hiring Manager" ? 2 : 1;

// Provides the status to api helper.
const statusToApi = (status: UserStatus) =>
  status === "Active" ? "active" : "inactive";

// Gets role badge class.
function getRoleBadgeClass(role: UserRole) {
  if (role === "HR Staff") {
    return "bg-blue-50 text-blue-700 border-blue-200";
  }

  return "bg-amber-50 text-amber-700 border-amber-200";
}

// Gets status badge class.
function getStatusBadgeClass(status: UserStatus) {
  return status === "Active"
    ? "bg-green-50 text-green-700 border-green-200"
    : "bg-slate-100 text-slate-600 border-slate-200";
}

// Formats action date.
function formatActionDate(value: string) {
  return formatDisplayDateTime(value);
}

// Gets action badge class.
function getActionBadgeClass(actionType: string) {
  if (actionType.includes("job")) {
    if (actionType.includes("delete")) {
      return "bg-red-50 text-red-700 border-red-200";
    }

    return "bg-blue-50 text-blue-700 border-blue-200";
  }

  if (actionType.includes("hire") || actionType.includes("hired")) {
    return "bg-emerald-50 text-emerald-700 border-emerald-100";
  }

  if (actionType.includes("interviewed")) {
    return "bg-sky-50 text-sky-700 border-sky-100";
  }

  if (actionType.includes("shortlist")) {
    return "bg-amber-50 text-amber-700 border-amber-200";
  }

  if (actionType.includes("reject")) {
    return "bg-red-50 text-red-700 border-red-200";
  }

  if (actionType.includes("reason")) {
    return "bg-slate-100 text-slate-700 border-slate-200";
  }

  if (actionType.includes("email")) {
    return "bg-blue-50 text-blue-700 border-blue-200";
  }

  if (actionType.includes("review")) {
    return "bg-green-50 text-green-700 border-green-200";
  }

  return "bg-slate-100 text-slate-700 border-slate-200";
}

// Formats action type label.
function formatActionTypeLabel(actionType: string) {
  if (actionType === "update_hired_start_date") {
    return "Updated Start Date";
  }

  if (actionType === "reject_candidate") {
    return "Rejected";
  }

  if (actionType === "send_rejection_email") {
    return "Rejection Email Sent";
  }

  if (actionType === "rejection_reason") {
    return "Rejection Reason";
  }

  return actionType
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

type UserManagementPageProps = {
  embedded?: boolean;
  alignToolbarWithTabs?: boolean;
};

// Renders the User Management Page component.
export function UserManagementPage({
  embedded = false,
  alignToolbarWithTabs = false,
}: UserManagementPageProps) {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [search, setSearch] = useState("");
  const [openCreate, setOpenCreate] = useState(false);
  const currentUserEmail = useMemo(() => {
    const storedUser = getStoredUser();
    return (
      storedUser?.email?.trim().toLowerCase() ||
      localStorage.getItem("hr_user")?.trim().toLowerCase() ||
      ""
    );
  }, []);

  const [newUser, setNewUser] = useState({
    fullName: "",
    email: "",
    role: "" as "" | UserRole,
    status: "Active" as UserStatus,
    temporaryPassword: "",
  });

  // Load all HR and hiring manager accounts.
  useEffect(() => {
    setIsLoadingUsers(true);
    apiFetch<{ users: ApiUser[] }>("/users")
      .then((data) => setUsers(data.users.map(mapApiUser)))
      .catch((error) =>
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to load users",
        ),
      )
      .finally(() => setIsLoadingUsers(false));
  }, []);

  const filteredUsers = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (!keyword) return users;

    return users.filter((user) => {
      return (
        user.fullName.toLowerCase().includes(keyword) ||
        user.email.toLowerCase().includes(keyword) ||
        user.role.toLowerCase().includes(keyword) ||
        user.status.toLowerCase().includes(keyword)
      );
    });
  }, [users, search]);

  const totalUsers = users.length;
  const activeUsers = users.filter(
    (user) => user.status === "Active",
  ).length;
  const hrCount = users.filter(
    (user) => user.role === "HR Staff",
  ).length;
  const hiringManagerCount = users.filter(
    (user) => user.role === "Hiring Manager",
  ).length;

  // Resets create form.
  const resetCreateForm = () => {
    setNewUser({
      fullName: "",
      email: "",
      role: "",
      status: "Active",
      temporaryPassword: "",
    });
  };

  // Handles create user.
  const handleCreateUser = async () => {
    // Check required account fields before the API call.
    if (!newUser.fullName.trim()) {
      toast.error("Full name is required");
      return;
    }

    if (!newUser.email.trim()) {
      toast.error("Email is required");
      return;
    }

    if (!/\S+@\S+\.\S+/.test(newUser.email)) {
      toast.error("Please enter a valid email address");
      return;
    }

    if (!newUser.role) {
      toast.error("Please select a role");
      return;
    }

    if (!newUser.temporaryPassword.trim()) {
      toast.error("Temporary password is required");
      return;
    }

    if (newUser.temporaryPassword.trim().length < 8) {
      toast.error("Temporary password must be at least 8 characters");
      return;
    }

    try {
      const data = await apiFetch<{ user: ApiUser }>("/users", {
        method: "POST",
        body: JSON.stringify({
          fullName: newUser.fullName.trim(),
          email: newUser.email.trim(),
          roleId: roleToId(newUser.role),
          status: statusToApi(newUser.status),
          temporaryPassword: newUser.temporaryPassword,
          department:
            newUser.role === "Hiring Manager"
              ? "Engineering"
              : "Human Resources",
        }),
      });

      setUsers((prev) => [mapApiUser(data.user), ...prev]);
      setOpenCreate(false);
      resetCreateForm();

      toast.success("Account created successfully");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to create account",
      );
    }
  };

  const [openResetPassword, setOpenResetPassword] =
    useState(false);

  const [resetPasswordUser, setResetPasswordUser] =
    useState<UserAccount | null>(null);

  const [resetPasswordForm, setResetPasswordForm] = useState({
    temporaryPassword: "",
    requirePasswordChange: true,
  });
  const [isResettingPassword, setIsResettingPassword] = useState(false);

  // Handles reset password.
  const handleResetPassword = (user: UserAccount) => {
    setResetPasswordUser(user);
    setResetPasswordForm({
      temporaryPassword: "",
      requirePasswordChange: true,
    });
    setOpenResetPassword(true);
  };

  // Handles confirm reset password.
  const handleConfirmResetPassword = async () => {
    if (!resetPasswordUser) return;

    if (!resetPasswordForm.temporaryPassword.trim()) {
      toast.error("Temporary password is required");
      return;
    }

    if (resetPasswordForm.temporaryPassword.trim().length < 8) {
      toast.error("Temporary password must be at least 8 characters");
      return;
    }

    setIsResettingPassword(true);
    try {
      await apiFetch(`/users/${resetPasswordUser.numericId}/password`, {
        method: "PATCH",
        body: JSON.stringify({
          temporaryPassword: resetPasswordForm.temporaryPassword.trim(),
          requirePasswordChange: resetPasswordForm.requirePasswordChange,
        }),
      });

      setOpenResetPassword(false);
      setResetPasswordUser(null);
      toast.success(
        `Temporary password reset for ${resetPasswordUser.fullName}`,
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to reset password",
      );
    } finally {
      setIsResettingPassword(false);
    }
  };

  // Handles toggle status.
  const handleToggleStatus = (user: UserAccount) => {
    setUsers((prev) =>
      prev.map((item) =>
        item.id === user.id
          ? {
              ...item,
              status:
                item.status === "Active"
                  ? "Inactive"
                  : "Active",
            }
          : item,
      ),
    );

    toast.success(
      `${user.fullName} is now ${
        user.status === "Active" ? "inactive" : "active"
      }`,
    );
  };

  const [openEdit, setOpenEdit] = useState(false);

  const [editingUser, setEditingUser] =
    useState<UserAccount | null>(null);

  const [editForm, setEditForm] = useState({
    fullName: "",
    email: "",
    role: "HR Staff" as UserRole,
    status: "Active" as UserStatus,
  });

  // Handles edit.
  const handleEdit = (user: UserAccount) => {
    setEditingUser(user);
    setEditForm({
      fullName: user.fullName,
      email: user.email,
      role: user.role,
      status: user.status,
    });
    setOpenEdit(true);
  };

  // Handles save edit.
  const handleSaveEdit = () => {
    if (!editingUser) return;

    if (!editForm.fullName.trim()) {
      toast.error("Full name is required");
      return;
    }

    if (!editForm.email.trim()) {
      toast.error("Email is required");
      return;
    }

    if (!/\S+@\S+\.\S+/.test(editForm.email)) {
      toast.error("Please enter a valid email address");
      return;
    }

    setUsers((prev) =>
      prev.map((user) =>
        user.id === editingUser.id
          ? {
              ...user,
              fullName: editForm.fullName,
              email: editForm.email,
              role: editForm.role,
              status: editForm.status,
            }
          : user,
      ),
    );

    setOpenEdit(false);
    setEditingUser(null);
    toast.success("Account updated successfully");
  };

  const [openActionHistory, setOpenActionHistory] = useState(false);
  const [actionHistoryUser, setActionHistoryUser] =
    useState<UserAccount | null>(null);
  const [actionHistory, setActionHistory] = useState<UserActionLog[]>([]);
  const [isLoadingActionHistory, setIsLoadingActionHistory] =
    useState(false);
  const [actionHistorySearch, setActionHistorySearch] = useState("");
  const [actionTypeFilter, setActionTypeFilter] = useState("all");
  const [actionHistoryPage, setActionHistoryPage] = useState(1);

  // Handles view action history.
  const handleViewActionHistory = async (user: UserAccount) => {
    // Open the audit history for one user.
    setActionHistoryUser(user);
    setOpenActionHistory(true);
    setActionHistorySearch("");
    setActionTypeFilter("all");
    setActionHistoryPage(1);
    setIsLoadingActionHistory(true);

    try {
      const data = await apiFetch<{ actions: UserActionLog[] }>(
        `/users/${user.numericId}/actions`,
      );
      setActionHistory(data.actions);
    } catch (error) {
      setActionHistory([]);
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to load HR action history",
      );
    } finally {
      setIsLoadingActionHistory(false);
    }
  };

  const actionTypeOptions = useMemo(() => {
    const labelsByType = new Map<string, string>();

    actionHistory.forEach((action) => {
      if (!labelsByType.has(action.actionType)) {
        labelsByType.set(
          action.actionType,
          action.actionLabel || formatActionTypeLabel(action.actionType),
        );
      }
    });

    return Array.from(labelsByType.entries()).map(
      ([value, label]) => ({ value, label }),
    );
  }, [actionHistory]);

  const filteredActionHistory = useMemo(() => {
    const keyword = actionHistorySearch.trim().toLowerCase();

    return actionHistory.filter((action) => {
      if (
        actionTypeFilter !== "all" &&
        action.actionType !== actionTypeFilter
      ) {
        return false;
      }

      if (!keyword) return true;

      return [
        action.actionType,
        action.actionLabel,
        action.reasonType,
        action.reasonDetails,
        action.candidateName,
        action.candidateEmail,
        action.jobTitle,
        action.jobDepartment,
        action.applicationStatus,
        action.createdAt,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(keyword),
        );
    });
  }, [actionHistory, actionHistorySearch, actionTypeFilter]);

  const actionHistoryPageCount = Math.max(
    1,
    Math.ceil(filteredActionHistory.length / ACTION_HISTORY_PAGE_SIZE),
  );

  useEffect(() => {
    setActionHistoryPage(1);
  }, [actionHistorySearch, actionTypeFilter, openActionHistory]);

  useEffect(() => {
    setActionHistoryPage((currentPage) =>
      Math.min(currentPage, actionHistoryPageCount),
    );
  }, [actionHistoryPageCount]);

  const pagedActionHistory = useMemo(() => {
    const startIndex =
      (actionHistoryPage - 1) * ACTION_HISTORY_PAGE_SIZE;

    return filteredActionHistory.slice(
      startIndex,
      startIndex + ACTION_HISTORY_PAGE_SIZE,
    );
  }, [filteredActionHistory, actionHistoryPage]);

  const content = (
    <>
      {isLoadingUsers ? (
        <LoadingState title="Loading user accounts" />
      ) : (
      <div className="space-y-6">
        <div
          className={
            alignToolbarWithTabs
              ? "flex justify-end sm:absolute sm:right-0 sm:top-0 sm:z-10"
              : "flex justify-end"
          }
        >
          <Dialog
            open={openCreate}
            onOpenChange={setOpenCreate}
          >
            <DialogTrigger asChild>
              <Button className="bg-[#003B7A] text-white hover:bg-[#002f63] shadow-sm">
                <Plus className="mr-2 h-4 w-4" />
                Create Account
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-[560px]">
              <DialogHeader>
                <DialogTitle>Create New Account</DialogTitle>
                <DialogDescription>
                  Add a new internal user account for the HR
                  system.
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-5 py-2">
                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input
                    id="fullName"
                    placeholder="Enter full name"
                    value={newUser.fullName}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        fullName: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="text"
                    inputMode="email"
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder="Enter email address"
                    value={newUser.email}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        email: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select
                      value={newUser.role}
                      onValueChange={(value: UserRole) =>
                        setNewUser((prev) => ({
                          ...prev,
                          role: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="HR Staff">
                          HR Staff
                        </SelectItem>
                        <SelectItem value="Hiring Manager">
                          Hiring Manager
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={newUser.status}
                      onValueChange={(value: UserStatus) =>
                        setNewUser((prev) => ({
                          ...prev,
                          status: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Active">
                          Active
                        </SelectItem>
                        <SelectItem value="Inactive">
                          Inactive
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="temporaryPassword">
                    Temporary Password
                  </Label>
                  <PasswordInput
                    id="temporaryPassword"
                    placeholder="Enter temporary password"
                    value={newUser.temporaryPassword}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        temporaryPassword: e.target.value,
                      }))
                    }
                  />
                  <p className="text-sm text-slate-500">
                    The user can change this password after
                    first login.
                  </p>
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setOpenCreate(false);
                    resetCreateForm();
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                  onClick={handleCreateUser}
                >
                  Create Account
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <UserManagementBody
          filteredUsers={filteredUsers}
          currentUserEmail={currentUserEmail}
          totalUsers={totalUsers}
          activeUsers={activeUsers}
          hrCount={hrCount}
          hiringManagerCount={hiringManagerCount}
          search={search}
          setSearch={setSearch}
          handleEdit={handleEdit}
          handleResetPassword={handleResetPassword}
          handleToggleStatus={handleToggleStatus}
          handleViewActionHistory={handleViewActionHistory}
        />
      </div>
      )}

      <Dialog open={openEdit} onOpenChange={setOpenEdit}>
        <DialogContent
          className="sm:max-w-[560px]"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Edit Account</DialogTitle>
            <DialogDescription>
              Update the selected user account details.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-5 py-2">
            <div className="space-y-2">
              <Label htmlFor="edit-fullName">
                Full Name
              </Label>
              <Input
                id="edit-fullName"
                placeholder="Enter full name"
                value={editForm.fullName}
                onChange={(e) =>
                  setEditForm((prev) => ({
                    ...prev,
                    fullName: e.target.value,
                  }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-email">
                Email Address
              </Label>
              <Input
                id="edit-email"
                type="text"
                inputMode="email"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="Enter email address"
                value={editForm.email}
                onChange={(e) =>
                  setEditForm((prev) => ({
                    ...prev,
                    email: e.target.value,
                  }))
                }
              />
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Role</Label>
                <Select
                  value={editForm.role}
                  onValueChange={(value: UserRole) =>
                    setEditForm((prev) => ({
                      ...prev,
                      role: value,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="HR Staff">
                      HR Staff
                    </SelectItem>
                    <SelectItem value="Hiring Manager">
                      Hiring Manager
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={editForm.status}
                  onValueChange={(value: UserStatus) =>
                    setEditForm((prev) => ({
                      ...prev,
                      status: value,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Active">
                      Active
                    </SelectItem>
                    <SelectItem value="Inactive">
                      Inactive
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
              onClick={handleSaveEdit}
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={openResetPassword}
        onOpenChange={setOpenResetPassword}
      >
        <DialogContent
          className="sm:max-w-[520px]"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a new temporary password for this account.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-5 py-2">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="font-medium text-slate-900">
                {resetPasswordUser?.fullName}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {resetPasswordUser?.email}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="reset-temporaryPassword">
                New Temporary Password
              </Label>
              <PasswordInput
                id="reset-temporaryPassword"
                placeholder="Enter temporary password"
                value={resetPasswordForm.temporaryPassword}
                onChange={(e) =>
                  setResetPasswordForm((prev) => ({
                    ...prev,
                    temporaryPassword: e.target.value,
                  }))
                }
              />
              <p className="text-sm text-slate-500">
                The user will use this password for the next
                login.
              </p>
            </div>

            <div className="flex items-start gap-3 rounded-lg border border-slate-200 p-4">
              <input
                id="require-password-change"
                type="checkbox"
                checked={
                  resetPasswordForm.requirePasswordChange
                }
                onChange={(e) =>
                  setResetPasswordForm((prev) => ({
                    ...prev,
                    requirePasswordChange: e.target.checked,
                  }))
                }
                className="mt-1 h-4 w-4 rounded border-slate-300"
              />
              <div className="space-y-1">
                <Label
                  htmlFor="require-password-change"
                  className="cursor-pointer"
                >
                  Require password change on next login
                </Label>
                <p className="text-sm text-slate-500">
                  The user must create a new password after
                  signing in.
                </p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOpenResetPassword(false);
                setResetPasswordUser(null);
              }}
            >
              Cancel
            </Button>
            <Button
              className="bg-[#003B7A] text-white hover:bg-[#002f63]"
              onClick={handleConfirmResetPassword}
              disabled={isResettingPassword}
            >
              {isResettingPassword ? "Resetting..." : "Reset Password"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={openActionHistory}
        onOpenChange={setOpenActionHistory}
      >
        <DialogContent className="max-h-[88vh] w-[calc(100vw-48px)] overflow-hidden bg-slate-50 p-0 sm:max-w-[1320px]">
          <DialogHeader className="sr-only">
            <DialogTitle>HR Action History</DialogTitle>
            <DialogDescription>
              HR actions recorded for{" "}
              {actionHistoryUser?.fullName}.
            </DialogDescription>
          </DialogHeader>

          <div className="border-b border-slate-200 bg-white px-8 py-6">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#003B7A] text-lg font-bold text-white">
                {actionHistoryUser?.avatarPath ? (
                  <img
                    src={actionHistoryUser.avatarPath}
                    alt={actionHistoryUser.fullName}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  actionHistoryUser?.fullName
                    .split(" ")
                    .map((part) => part[0])
                    .join("")
                    .slice(0, 2) || "HR"
                )}
              </div>
              <div className="min-w-0">
                <h2 className="mt-1 text-lg font-semibold text-slate-900">
                  {actionHistoryUser?.fullName}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {actionHistoryUser?.id} |{" "}
                  {actionHistoryUser?.role} |{" "}
                  {actionHistoryUser?.email}
                </p>
              </div>
            </div>
          </div>

          <div className="border-b border-slate-200 bg-white px-8 py-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                HR Action History
              </h3>

              <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <div className="relative w-full md:w-[330px]">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    placeholder="Search candidate, email, job or action"
                    value={actionHistorySearch}
                    onChange={(event) =>
                      setActionHistorySearch(event.target.value)
                    }
                    className="h-10 pl-9 pr-10"
                  />
                  <SearchClearButton
                    show={Boolean(actionHistorySearch)}
                    onClear={() => setActionHistorySearch("")}
                  />
                </div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="h-10 gap-2">
                      <Filter className="h-4 w-4" />
                      Filter
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuItem
                      onClick={() => setActionTypeFilter("all")}
                    >
                      All actions
                    </DropdownMenuItem>
                    {actionTypeOptions.map((option) => (
                      <DropdownMenuItem
                        key={option.value}
                        onClick={() =>
                          setActionTypeFilter(option.value)
                        }
                      >
                        {option.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {(actionHistorySearch || actionTypeFilter !== "all") && (
              <div className="mt-4 flex items-center justify-between rounded bg-slate-100 px-4 py-2 text-sm text-slate-600">
                <span>
                  Filter Applied |{" "}
                  {actionTypeFilter === "all"
                    ? "All Actions"
                    : actionTypeOptions.find(
                        (option) =>
                          option.value === actionTypeFilter,
                      )?.label ||
                      formatActionTypeLabel(actionTypeFilter)}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setActionHistorySearch("");
                    setActionTypeFilter("all");
                  }}
                  className="font-medium text-[#003B7A] hover:underline"
                >
                  Reset
                </button>
              </div>
            )}
          </div>

          <div className="uwc-scrollbar max-h-[58vh] overflow-auto bg-white px-8 pb-8 pt-5">
            {isLoadingActionHistory ? (
              <LoadingState
                title="Loading action history"
                className="border-0 shadow-none"
              />
            ) : filteredActionHistory.length > 0 ? (
              <table className="w-full min-w-[920px] table-fixed text-sm">
                <colgroup>
                  <col className="w-[25%]" />
                  <col className="w-[30%]" />
                  <col className="w-[20%]" />
                  <col className="w-[25%]" />
                </colgroup>
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs font-semibold tracking-wide text-slate-500">
                    <th className="px-3 pb-4">Candidate</th>
                    <th className="px-3 pb-4">Job Title</th>
                    <th className="px-3 pb-4">Action Type</th>
                    <th className="px-3 pb-4">Action Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pagedActionHistory.map((action) => (
                    <tr
                      key={action.id}
                      className="align-top transition-colors hover:bg-slate-50"
                    >
                      <td className="px-3 py-5">
                        <p className="break-words text-slate-900 [overflow-wrap:anywhere]">
                          {action.candidateName || "-"}
                        </p>
                      </td>
                      <td className="px-3 py-5">
                        <p className="break-words text-slate-900">
                          {action.jobTitle || "-"}
                        </p>
                      </td>
                      <td className="px-3 py-5">
                        <Badge
                          variant="outline"
                          className={getActionBadgeClass(
                            action.actionType,
                          )}
                        >
                          {action.actionLabel}
                        </Badge>
                      </td>
                      <td className="whitespace-nowrap px-3 py-5 text-slate-700">
                        {formatActionDate(action.createdAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="rounded-lg border border-slate-200 p-10 text-center text-slate-500">
                No HR actions found.
              </div>
            )}

            {!isLoadingActionHistory &&
              filteredActionHistory.length > ACTION_HISTORY_PAGE_SIZE && (
                <Pagination className="mt-6 justify-center">
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        href="#"
                        aria-disabled={actionHistoryPage === 1}
                        className={
                          actionHistoryPage === 1
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                        onClick={(event) => {
                          event.preventDefault();
                          setActionHistoryPage((page) =>
                            Math.max(1, page - 1),
                          );
                        }}
                      />
                    </PaginationItem>

                    {getCompactPageItems(
                      actionHistoryPage,
                      actionHistoryPageCount,
                    ).map((item) => (
                      <PaginationItem key={item}>
                        {typeof item === "number" ? (
                          <PaginationLink
                            href="#"
                            isActive={item === actionHistoryPage}
                            onClick={(event) => {
                              event.preventDefault();
                              setActionHistoryPage(item);
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
                        aria-disabled={
                          actionHistoryPage === actionHistoryPageCount
                        }
                        className={
                          actionHistoryPage === actionHistoryPageCount
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                        onClick={(event) => {
                          event.preventDefault();
                          setActionHistoryPage((page) =>
                            Math.min(actionHistoryPageCount, page + 1),
                          );
                        }}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: "User Management" },
      ]}
      title="User Management"
      subtitle={
        <p className="text-slate-600">
          Create and manage internal accounts for HR staff and
          hiring managers.
        </p>
      }
      useCard={false}
    >
      {isLoadingUsers ? (
        <LoadingState title="Loading user accounts" />
      ) : (
      <div className="space-y-6">
        <div className="flex justify-end">
          <Dialog
            open={openCreate}
            onOpenChange={setOpenCreate}
          >
            <DialogTrigger asChild>
              <Button className="bg-[#003B7A] text-white hover:bg-[#002f63] shadow-sm">
                <Plus className="mr-2 h-4 w-4" />
                Create Account
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-[560px]">
              <DialogHeader>
                <DialogTitle>Create New Account</DialogTitle>
                <DialogDescription>
                  Add a new internal user account for the HR
                  system.
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-5 py-2">
                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input
                    id="fullName"
                    placeholder="Enter full name"
                    value={newUser.fullName}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        fullName: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="text"
                    inputMode="email"
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder="Enter email address"
                    value={newUser.email}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        email: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select
                      value={newUser.role}
                      onValueChange={(value: UserRole) =>
                        setNewUser((prev) => ({
                          ...prev,
                          role: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="HR Staff">
                          HR Staff
                        </SelectItem>
                        <SelectItem value="Hiring Manager">
                          Hiring Manager
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={newUser.status}
                      onValueChange={(value: UserStatus) =>
                        setNewUser((prev) => ({
                          ...prev,
                          status: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Active">
                          Active
                        </SelectItem>
                        <SelectItem value="Inactive">
                          Inactive
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="temporaryPassword">
                    Temporary Password
                  </Label>
                  <PasswordInput
                    id="temporaryPassword"
                    placeholder="Enter temporary password"
                    value={newUser.temporaryPassword}
                    onChange={(e) =>
                      setNewUser((prev) => ({
                        ...prev,
                        temporaryPassword: e.target.value,
                      }))
                    }
                  />
                  <p className="text-sm text-slate-500">
                    The user can change this password after
                    first login.
                  </p>
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setOpenCreate(false);
                    resetCreateForm();
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                  onClick={handleCreateUser}
                >
                  Create Account
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={openEdit} onOpenChange={setOpenEdit}>
            <DialogContent
              className="sm:max-w-[560px]"
              onOpenAutoFocus={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle>Edit Account</DialogTitle>
                <DialogDescription>
                  Update the selected user account details.
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-5 py-2">
                <div className="space-y-2">
                  <Label htmlFor="edit-fullName">
                    Full Name
                  </Label>
                  <Input
                    id="edit-fullName"
                    placeholder="Enter full name"
                    value={editForm.fullName}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        fullName: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-email">
                    Email Address
                  </Label>
                  <Input
                    id="edit-email"
                    type="text"
                    inputMode="email"
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    placeholder="Enter email address"
                    value={editForm.email}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        email: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select
                      value={editForm.role}
                      onValueChange={(value: UserRole) =>
                        setEditForm((prev) => ({
                          ...prev,
                          role: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="HR Staff">
                          HR Staff
                        </SelectItem>
                        <SelectItem value="Hiring Manager">
                          Hiring Manager
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={editForm.status}
                      onValueChange={(value: UserStatus) =>
                        setEditForm((prev) => ({
                          ...prev,
                          status: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Active">
                          Active
                        </SelectItem>
                        <SelectItem value="Inactive">
                          Inactive
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <DialogFooter>
                <Button
                  className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                  onClick={handleSaveEdit}
                >
                  Save Changes
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog
            open={openResetPassword}
            onOpenChange={setOpenResetPassword}
          >
            <DialogContent
              className="sm:max-w-[520px]"
              onOpenAutoFocus={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle>Reset Password</DialogTitle>
                <DialogDescription>
                  Set a new temporary password for this account.
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-5 py-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="font-medium text-slate-900">
                    {resetPasswordUser?.fullName}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {resetPasswordUser?.email}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reset-temporaryPassword">
                    New Temporary Password
                  </Label>
                  <PasswordInput
                    id="reset-temporaryPassword"
                    placeholder="Enter temporary password"
                    value={resetPasswordForm.temporaryPassword}
                    onChange={(e) =>
                      setResetPasswordForm((prev) => ({
                        ...prev,
                        temporaryPassword: e.target.value,
                      }))
                    }
                  />
                  <p className="text-sm text-slate-500">
                    The user will use this password for the next
                    login.
                  </p>
                </div>

                <div className="flex items-start gap-3 rounded-lg border border-slate-200 p-4">
                  <input
                    id="require-password-change"
                    type="checkbox"
                    checked={
                      resetPasswordForm.requirePasswordChange
                    }
                    onChange={(e) =>
                      setResetPasswordForm((prev) => ({
                        ...prev,
                        requirePasswordChange: e.target.checked,
                      }))
                    }
                    className="mt-1 h-4 w-4 rounded border-slate-300"
                  />
                  <div className="space-y-1">
                    <Label
                      htmlFor="require-password-change"
                      className="cursor-pointer"
                    >
                      Require password change on next login
                    </Label>
                    <p className="text-sm text-slate-500">
                      The user must create a new password after
                      signing in.
                    </p>
                  </div>
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setOpenResetPassword(false);
                    setResetPasswordUser(null);
                  }}
                >
                  Cancel
                </Button>
                  <Button
                    className="bg-[#003B7A] text-white hover:bg-[#002f63]"
                    onClick={handleConfirmResetPassword}
                    disabled={isResettingPassword}
                  >
                    {isResettingPassword ? "Resetting..." : "Reset Password"}
                  </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Card className="shadow-md">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <p className="text-sm text-slate-500">
                  Total Users
                </p>
                <p className="mt-1 text-3xl font-bold text-slate-900">
                  {totalUsers}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-100 p-3">
                <Users className="h-5 w-5 text-slate-700" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <p className="text-sm text-slate-500">
                  Active Users
                </p>
                <p className="mt-1 text-3xl font-bold text-slate-900">
                  {activeUsers}
                </p>
              </div>
              <div className="rounded-2xl bg-green-50 p-3">
                <UserCheck className="h-5 w-5 text-green-700" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <p className="text-sm text-slate-500">
                  HR Staff
                </p>
                <p className="mt-1 text-3xl font-bold text-slate-900">
                  {hrCount}
                </p>
              </div>
              <div className="rounded-2xl bg-blue-50 p-3">
                <UserPlus className="h-5 w-5 text-blue-700" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md">
            <CardContent className="flex items-center justify-between p-6">
              <div>
                <p className="text-sm text-slate-500">
                  Hiring Managers
                </p>
                <p className="mt-1 text-3xl font-bold text-slate-900">
                  {hiringManagerCount}
                </p>
              </div>
              <div className="rounded-2xl bg-amber-50 p-3">
                <Briefcase className="h-5 w-5 text-amber-700" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-md">
          <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>All Accounts</CardTitle>
              <p className="mt-1 text-sm text-slate-500">
                View and manage all internal system accounts.
              </p>
            </div>

            <div className="relative w-full md:w-[320px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search users"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 pr-10"
              />
              <SearchClearButton
                show={Boolean(search)}
                onClear={() => setSearch("")}
              />
            </div>
          </CardHeader>

          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created Date</TableHead>
                    <TableHead className="w-[80px] text-right">
                      Action
                    </TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {filteredUsers.length > 0 ? (
                    filteredUsers.map((user) => (
                      <TableRow
                        key={user.id}
                        className="cursor-pointer hover:bg-slate-50"
                        onClick={() => handleViewActionHistory(user)}
                      >
                        <TableCell>
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-medium text-slate-900">
                                {user.fullName}
                              </p>
                              {user.email.toLowerCase() === currentUserEmail && (
                                <Badge
                                  variant="outline"
                                  className="border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-[#003B7A]"
                                >
                                  You
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                              <Mail className="h-4 w-4" />
                              {user.email}
                            </div>
                          </div>
                        </TableCell>

                        <TableCell>
                          <Badge
                            variant="outline"
                            className={getRoleBadgeClass(
                              user.role,
                            )}
                          >
                            {user.role}
                          </Badge>
                        </TableCell>

                        <TableCell>
                          <Badge
                            variant="outline"
                            className={getStatusBadgeClass(
                              user.status,
                            )}
                          >
                            {user.status}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-slate-600">
                          {formatDisplayDate(user.createdAt)}
                        </TableCell>

                        <TableCell
                          className="text-right"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>

                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => handleEdit(user)}
                              >
                                <Pencil className="mr-2 h-4 w-4" />
                                Edit Account
                              </DropdownMenuItem>

                              <DropdownMenuItem
                                onClick={() =>
                                  handleResetPassword(user)
                                }
                              >
                                <KeyRound className="mr-2 h-4 w-4" />
                                Reset Password
                              </DropdownMenuItem>

                              <DropdownMenuItem
                                onClick={() =>
                                  handleToggleStatus(user)
                                }
                              >
                                {user.status === "Active" ? (
                                  <>
                                    <Ban className="mr-2 h-4 w-4" />
                                    Disable Account
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle2 className="mr-2 h-4 w-4" />
                                    Activate Account
                                  </>
                                )}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="py-10 text-center text-slate-500"
                      >
                        No users found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
      )}
    </PageLayout>
  );
}

type UserManagementBodyProps = {
  filteredUsers: UserAccount[];
  currentUserEmail: string;
  totalUsers: number;
  activeUsers: number;
  hrCount: number;
  hiringManagerCount: number;
  search: string;
  setSearch: (value: string) => void;
  handleEdit: (user: UserAccount) => void;
  handleResetPassword: (user: UserAccount) => void;
  handleToggleStatus: (user: UserAccount) => void;
  handleViewActionHistory: (user: UserAccount) => void;
};

// Renders the User Management Body component.
function UserManagementBody({
  filteredUsers,
  currentUserEmail,
  totalUsers,
  activeUsers,
  hrCount,
  hiringManagerCount,
  search,
  setSearch,
  handleEdit,
  handleResetPassword,
  handleToggleStatus,
  handleViewActionHistory,
}: UserManagementBodyProps) {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card className="shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-slate-500">Total Users</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {totalUsers}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-100 p-3">
              <Users className="h-5 w-5 text-slate-700" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-slate-500">Active Users</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {activeUsers}
              </p>
            </div>
            <div className="rounded-2xl bg-green-50 p-3">
              <UserCheck className="h-5 w-5 text-green-700" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-slate-500">HR Staff</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {hrCount}
              </p>
            </div>
            <div className="rounded-2xl bg-blue-50 p-3">
              <UserPlus className="h-5 w-5 text-blue-700" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-slate-500">Hiring Managers</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {hiringManagerCount}
              </p>
            </div>
            <div className="rounded-2xl bg-amber-50 p-3">
              <Briefcase className="h-5 w-5 text-amber-700" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-md">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>All Accounts</CardTitle>
            <p className="mt-1 text-sm text-slate-500">
              View and manage all internal system accounts.
            </p>
          </div>

          <div className="relative w-full md:w-[320px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search users"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-10"
            />
            <SearchClearButton
              show={Boolean(search)}
              onClear={() => setSearch("")}
            />
          </div>
        </CardHeader>

        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created Date</TableHead>
                  <TableHead className="w-[80px] text-right">
                    Action
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {filteredUsers.length > 0 ? (
                  filteredUsers.map((user) => (
                    <TableRow
                      key={user.id}
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => handleViewActionHistory(user)}
                    >
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-slate-900">
                              {user.fullName}
                            </p>
                            {user.email.toLowerCase() === currentUserEmail && (
                              <Badge
                                variant="outline"
                                className="border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-[#003B7A]"
                              >
                                You
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Mail className="h-4 w-4" />
                            {user.email}
                          </div>
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant="outline"
                          className={getRoleBadgeClass(user.role)}
                        >
                          {user.role}
                        </Badge>
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant="outline"
                          className={getStatusBadgeClass(user.status)}
                        >
                          {user.status}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-slate-600">
                        {formatDisplayDate(user.createdAt)}
                      </TableCell>

                      <TableCell
                        className="text-right"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>

                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => handleEdit(user)}
                            >
                              <Pencil className="mr-2 h-4 w-4" />
                              Edit Account
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              onClick={() => handleResetPassword(user)}
                            >
                              <KeyRound className="mr-2 h-4 w-4" />
                              Reset Password
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              onClick={() => handleToggleStatus(user)}
                            >
                              {user.status === "Active" ? (
                                <>
                                  <Ban className="mr-2 h-4 w-4" />
                                  Disable Account
                                </>
                              ) : (
                                <>
                                  <CheckCircle2 className="mr-2 h-4 w-4" />
                                  Activate Account
                                </>
                              )}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="py-10 text-center text-slate-500"
                    >
                      No users found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
