// Shows the User Profile view.
import { useState } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Camera, Pencil, Save, Upload } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, getStoredUser, type AuthUser } from "../../lib/api";

// Renders the User Profile component.
export function UserProfile() {
  const storedUser = getStoredUser();
  const userEmail = storedUser?.email || localStorage.getItem("hr_user") || "";
  const userName = storedUser?.name || userEmail.split("@")[0] || "HR User";
  const userRole =
    storedUser?.roleName ||
    (storedUser?.roleKey === "hiring_manager" ? "Hiring Manager" : "HR Staff");

  const [profileData, setProfileData] = useState({
    fullName: userName,
    email: userEmail,
    phone: storedUser?.phone || "",
    department: storedUser?.department || "Human Resources",
    jobTitle: userRole,
  });
  const [avatarPreview, setAvatarPreview] = useState<string | null>(
    storedUser?.avatarPath || null,
  );
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);

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
      setProfileData((current) => ({
        ...current,
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
      toast.error(
        error instanceof Error ? error.message : "Failed to update profile",
      );
      return false;
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handles avatar upload.
  const handleAvatarUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!storedUser?.id) {
      toast.error("Unable to identify the current user");
      event.target.value = "";
      return;
    }

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload an image file");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("File size must be less than 5MB");
      event.target.value = "";
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
      setProfileData((current) => ({
        ...current,
        fullName: data.user.name,
        email: data.user.email,
        phone: data.user.phone || "",
        department: data.user.department || "Human Resources",
        jobTitle: data.user.roleName,
      }));
      toast.success("Avatar uploaded successfully!");
    } catch (error) {
      setAvatarPreview(storedUser.avatarPath || null);
      toast.error(
        error instanceof Error ? error.message : "Failed to upload avatar",
      );
    } finally {
      setIsUploadingAvatar(false);
      event.target.value = "";
    }
  };

  return (
    <PageLayout
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "User Profile" },
      ]}
      title="User Profile"
      subtitle="Manage your profile details and contact information"
      useCard={false}
    >
      <Card className="border border-slate-200 shadow-md rounded-2xl">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-semibold">
            Employee Profile Settings
          </CardTitle>
          <CardDescription className="text-base">
            Review and update your profile details, contact information, and
            professional role.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
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
                  <span>{profileData.fullName.charAt(0)}</span>
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
                  onClick={() => setIsEditingProfile((current) => !current)}
                  className="inline-flex items-center justify-center text-slate-500 hover:text-slate-700 transition-colors"
                  aria-label="Edit profile"
                >
                  <Pencil className="w-4 h-4" />
                </button>
              </div>

              <p className="text-base text-slate-600 mb-1">
                {profileData.department} | {profileData.jobTitle}
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

          {isEditingProfile && (
            <>
              <div className="border-t border-slate-200 pt-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full Name</Label>
                    <Input
                      id="fullName"
                      value={profileData.fullName}
                      onChange={(event) =>
                        setProfileData({
                          ...profileData,
                          fullName: event.target.value,
                        })
                      }
                      className="h-12"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="department">Department</Label>
                    <Select
                      value={profileData.department}
                      onValueChange={(value) =>
                        setProfileData({
                          ...profileData,
                          department: value,
                        })
                      }
                    >
                      <SelectTrigger id="department" className="h-12">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Human Resources">
                          Human Resources
                        </SelectItem>
                        <SelectItem value="Engineering">Engineering</SelectItem>
                        <SelectItem value="Product">Product</SelectItem>
                        <SelectItem value="Marketing">Marketing</SelectItem>
                        <SelectItem value="Sales">Sales</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={profileData.phone}
                      onChange={(event) =>
                        setProfileData({
                          ...profileData,
                          phone: event.target.value,
                        })
                      }
                      placeholder="+60 12-345 6789"
                      className="h-12"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="jobTitle">Job Title</Label>
                    <Input
                      id="jobTitle"
                      value={profileData.jobTitle}
                      onChange={(event) =>
                        setProfileData({
                          ...profileData,
                          jobTitle: event.target.value,
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
                    if (saved) setIsEditingProfile(false);
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
    </PageLayout>
  );
}
