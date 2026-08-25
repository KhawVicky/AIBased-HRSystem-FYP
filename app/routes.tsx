// Defines all website routes.
import { createBrowserRouter, Navigate } from "react-router";
import { Root } from "./components/shared/Root";
import { Login } from "./components/auth/Login";
import { Dashboard } from "./components/dashboard/Dashboard";
import { JobDetails } from "./components/jobs/JobDetails";
import { CandidateList } from "./components/candidates/CandidateList";
import { CreateJob } from "./components/jobs/CreateJob";
import { ApplyJob } from "./components/candidate-portal/ApplyJob";
import { AttendanceAnalytics } from "./components/attendance/AttendanceAnalytics";
import { Reports } from "./components/reports/Reports";
import { UserProfile } from "./components/profile/UserProfile";
import { UserSettings } from "./components/profile/UserSettings";
import { NotificationsPage } from "./components/notifications/NotificationsPage";
import { HRManagement } from "./components/users/HRManagement";
import { DepartmentJobs } from "./components/jobs/DepartmentJobs";
import { JobManagement } from "./components/jobs/JobManagement";
import { ApplicationList } from "./components/candidates/ApplicationList";
import { NewCandidates } from "./components/candidates/NewCandidates";
import {
  CareersHome,
  CareerJobDetailsPage,
  CandidateApplicationDetailsPage,
  CandidateApplicationsPage,
  CandidateLogin,
  CandidateProfilePage,
  CandidateRegister,
} from "./components/candidate-portal/CandidatePortal";
import { NotFound } from "./components/shared/NotFound";
import { EmploymentForm } from "./components/uwc-employment-form";
import { canManageUsers, getStoredUser } from "./lib/api";

// Simple auth check
export const isAuthenticated = () => {
  return localStorage.getItem("hr_authenticated") === "true";
};

// Protected route wrapper
const ProtectedRoute = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

// Renders the Manager Route component.
const ManagerRoute = ({ children }: { children: React.ReactNode }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (!canManageUsers(getStoredUser())) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

const isCandidateSurface = import.meta.env.VITE_APP_SURFACE === "candidate";
const candidateSurfacePaths = new Set([
  "careers",
  "careers/:jobCode",
  "candidate/login",
  "candidate/register",
  "candidate/applications",
  "candidate/applications/:applicationId",
  "candidate/profile",
  "apply",
  "apply/:jobCode",
  "employment-form",
  "*",
]);

const applicationRoutes = [
      {
        index: true,
        element: <Navigate to={isCandidateSurface ? "/careers" : "/dashboard"} replace />,
      },
      {
        path: "login",
        Component: Login,
      },
      {
        path: "careers",
        Component: CareersHome,
      },
      {
        path: "careers/:jobCode",
        Component: CareerJobDetailsPage,
      },
      {
        path: "candidate/login",
        Component: CandidateLogin,
      },
      {
        path: "candidate/register",
        Component: CandidateRegister,
      },
      {
        path: "candidate/applications",
        Component: CandidateApplicationsPage,
      },
      {
        path: "candidate/applications/:applicationId",
        Component: CandidateApplicationDetailsPage,
      },
      {
        path: "candidate/profile",
        Component: CandidateProfilePage,
      },
      {
        path: "dashboard",
        element: (
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: "jobs",
        element: (
          <ProtectedRoute>
            <JobManagement />
          </ProtectedRoute>
        ),
      },
      {
        path: "jobs/create",
        element: (
          <ProtectedRoute>
            <CreateJob />
          </ProtectedRoute>
        ),
      },
      {
        path: "jobs/:jobId",
        element: (
          <ProtectedRoute>
            <JobDetails />
          </ProtectedRoute>
        ),
      },
      {
        path: "jobs/:jobId/edit",
        element: (
          <ProtectedRoute>
            <CreateJob />
          </ProtectedRoute>
        ),
      },
      {
        path: "jobs/:jobId/candidates",
        element: (
          <ProtectedRoute>
            <CandidateList />
          </ProtectedRoute>
        ),
      },
      {
        path: "applications",
        element: (
          <ProtectedRoute>
            <ApplicationList />
          </ProtectedRoute>
        ),
      },
      {
        path: "candidates",
        element: (
          <ProtectedRoute>
            <NewCandidates />
          </ProtectedRoute>
        ),
      },
      {
        path: "apply",
        Component: ApplyJob,
      },
      {
        path: "apply/:jobCode",
        Component: ApplyJob,
      },
      {
        path: "employment-form",
        Component: EmploymentForm,
      },
      {
        path: "attendance",
        element: (
          <ProtectedRoute>
            <AttendanceAnalytics />
          </ProtectedRoute>
        ),
      },
      {
        path: "reports",
        element: (
          <ProtectedRoute>
            <Reports />
          </ProtectedRoute>
        ),
      },
      {
        path: "profile",
        element: (
          <ProtectedRoute>
            <UserProfile />
          </ProtectedRoute>
        ),
      },
      {
        path: "settings",
        element: (
          <ProtectedRoute>
            <UserSettings />
          </ProtectedRoute>
        ),
      },
      {
        path: "notifications",
        element: (
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin",
        element: (
          <ManagerRoute>
            <HRManagement />
          </ManagerRoute>
        ),
      },
      {
        path: "hr-efficiency",
        element: (
          <ManagerRoute>
            <HRManagement />
          </ManagerRoute>
        ),
      },
      {
        path: "departments/:department",
        element: (
          <ProtectedRoute>
            <DepartmentJobs />
          </ProtectedRoute>
        ),
      },
      {
        path: "*",
        Component: NotFound,
      },
    ];

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: applicationRoutes.filter(
      (route) =>
        !isCandidateSurface ||
        "index" in route ||
        ("path" in route && candidateSurfacePaths.has(route.path)),
    ),
  },
]);
