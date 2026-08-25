// Shows the Login view.
import image_a7e321551d78150f830b1e4870452ab5d2dd7d7e from "../../assets/uwc-berhad-logo.png";
import { useState } from "react";
import { useNavigate } from "react-router";
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
import { toast } from "sonner";
import { apiFetch, type AuthUser } from "../../lib/api";
import { Eye, EyeOff } from "lucide-react";
import { PasswordInput } from "../shared/PasswordInput";

// Renders the Login component.
export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {},
  );
  const [forcedPasswordUser, setForcedPasswordUser] =
    useState<AuthUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [passwordChangeErrors, setPasswordChangeErrors] = useState<{
    newPassword?: string;
    confirmPassword?: string;
  }>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const storeAuthenticatedUser = (user: AuthUser) => {
    localStorage.setItem("hr_authenticated", "true");
    localStorage.setItem("hr_user", user.email);
    localStorage.setItem("hr_user_data", JSON.stringify(user));
  };

  // Validates form.
  const validateForm = () => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handles login.
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error("Please fix the errors in the form");
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await apiFetch<{ user: AuthUser }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (data.user.mustChangePassword) {
        setForcedPasswordUser(data.user);
        setPasswordChangeErrors({});
        toast.info("Please set a new password before continuing");
        return;
      }

      storeAuthenticatedUser(data.user);
      toast.success(`Welcome, ${data.user.name}`);
      navigate("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForcedPasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forcedPasswordUser) return;

    const nextErrors: {
      newPassword?: string;
      confirmPassword?: string;
    } = {};

    if (newPassword.length < 8) {
      nextErrors.newPassword = "Password must be at least 8 characters";
    }

    if (newPassword !== confirmNewPassword) {
      nextErrors.confirmPassword = "Passwords do not match";
    }

    setPasswordChangeErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      toast.error("Please fix the errors in the form");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch("/auth/password", {
        method: "PATCH",
        body: JSON.stringify({
          userId: forcedPasswordUser.id,
          currentPassword: password,
          newPassword,
        }),
      });

      const authenticatedUser = {
        ...forcedPasswordUser,
        mustChangePassword: false,
      };
      storeAuthenticatedUser(authenticatedUser);
      toast.success("Password updated successfully");
      navigate("/dashboard");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update password",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-md">
        <CardHeader className="space-y-4 text-center">
          <img src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e} alt="UWC Logo" className="mx-auto h-16 w-auto" />
          <CardTitle className="text-2xl">
            {forcedPasswordUser ? "Set a New Password" : "HR Recruitment System"}
          </CardTitle>
          <CardDescription>
            {forcedPasswordUser
              ? "Your administrator requires a password change before you continue."
              : "Sign in to access your dashboard and manage candidates"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {forcedPasswordUser ? (
            <form
              onSubmit={handleForcedPasswordChange}
              noValidate
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label htmlFor="forced-new-password">New Password</Label>
                <PasswordInput
                  id="forced-new-password"
                  autoComplete="new-password"
                  placeholder="Enter a new password"
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    if (passwordChangeErrors.newPassword) {
                      setPasswordChangeErrors((current) => ({
                        ...current,
                        newPassword: undefined,
                      }));
                    }
                  }}
                  className={
                    passwordChangeErrors.newPassword ? "border-red-500" : ""
                  }
                />
                {passwordChangeErrors.newPassword && (
                  <p className="text-sm text-red-500">
                    {passwordChangeErrors.newPassword}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="forced-confirm-password">
                  Confirm New Password
                </Label>
                <PasswordInput
                  id="forced-confirm-password"
                  autoComplete="new-password"
                  placeholder="Re-enter the new password"
                  value={confirmNewPassword}
                  onChange={(e) => {
                    setConfirmNewPassword(e.target.value);
                    if (passwordChangeErrors.confirmPassword) {
                      setPasswordChangeErrors((current) => ({
                        ...current,
                        confirmPassword: undefined,
                      }));
                    }
                  }}
                  className={
                    passwordChangeErrors.confirmPassword
                      ? "border-red-500"
                      : ""
                  }
                />
                {passwordChangeErrors.confirmPassword && (
                  <p className="text-sm text-red-500">
                    {passwordChangeErrors.confirmPassword}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[#003B7A] text-white shadow-sm hover:bg-[#002f63]"
              >
                {isSubmitting ? "Updating..." : "Update Password"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleLogin} noValidate className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="text"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="hr@uwc.com.my"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email)
                      setErrors({ ...errors, email: undefined });
                  }}
                  className={errors.email ? "border-red-500" : ""}
                />
                {errors.email && (
                  <p className="text-sm text-red-500">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Minimum 8 characters"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password)
                        setErrors({ ...errors, password: undefined });
                    }}
                    className={`${errors.password ? "border-red-500" : ""} pr-10`}
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-700"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-red-500">{errors.password}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[#003B7A] text-white shadow-sm hover:bg-[#002f63]"
              >
                {isSubmitting ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
