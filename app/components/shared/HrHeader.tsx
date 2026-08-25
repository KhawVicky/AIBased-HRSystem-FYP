// Provides the shared HR header.
import image_a7e321551d78150f830b1e4870452ab5d2dd7d7e from "../../assets/uwc-berhad-logo.png";
import { useRef, useState } from "react";
import { CalendarCheck, LayoutDashboard, LogOut, Menu, Settings, ShieldCheck, User, Users } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router";
import { toast } from "sonner";
import { canManageUsers, getStoredUser } from "../../lib/api";
import { HeaderNotifications } from "../notifications/HeaderNotifications";
import { Button } from "../ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../ui/sheet";

interface HrHeaderProps {
  sticky?: boolean;
  horizontalPaddingClassName?: string;
}

// Renders the Hr Header component.
export function HrHeader({
  sticky = false,
  horizontalPaddingClassName = "px-6 lg:px-8",
}: HrHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuCloseTimer = useRef<number | null>(null);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const navigationItems = [
    { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, visible: true },
    { label: "Candidates", path: "/candidates", icon: Users, visible: true },
    { label: "Attendance", path: "/attendance", icon: CalendarCheck, visible: true },
    {
      label: "HR Management",
      path: "/hr-efficiency",
      icon: ShieldCheck,
      visible: canManageUsers(user),
      activePaths: ["/hr-efficiency", "/users"],
    },
  ].filter((item) => item.visible);

  const isNavigationItemActive = (item: (typeof navigationItems)[number]) =>
    location.pathname === item.path ||
    item.activePaths?.some((path) => location.pathname.startsWith(path));

  // Opens user menu.
  const openUserMenu = () => {
    if (userMenuCloseTimer.current !== null) {
      window.clearTimeout(userMenuCloseTimer.current);
      userMenuCloseTimer.current = null;
    }
    setIsUserMenuOpen(true);
  };

  // Closes user menu.
  const closeUserMenu = () => {
    if (userMenuCloseTimer.current !== null) {
      window.clearTimeout(userMenuCloseTimer.current);
    }
    userMenuCloseTimer.current = window.setTimeout(() => {
      setIsUserMenuOpen(false);
      userMenuCloseTimer.current = null;
    }, 120);
  };

  // Handles logout.
  const handleLogout = () => {
    localStorage.removeItem("hr_authenticated");
    localStorage.removeItem("hr_user");
    localStorage.removeItem("hr_user_data");
    toast.success("Logged out successfully");
    navigate("/login");
  };

  // Closes user menu now.
  const closeUserMenuNow = () => {
    if (userMenuCloseTimer.current !== null) {
      window.clearTimeout(userMenuCloseTimer.current);
      userMenuCloseTimer.current = null;
    }
    setIsUserMenuOpen(false);
  };

  // Handles user menu blur.
  const handleUserMenuBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    if (!userMenuRef.current?.contains(event.relatedTarget as Node | null)) {
      closeUserMenu();
    }
  };

  return (
    <nav
      className={`border-b border-slate-200 bg-white ${
        sticky ? "sticky top-0 z-10" : ""
      }`}
    >
      <div className={`mx-auto max-w-7xl ${horizontalPaddingClassName}`}>
        <div className="flex h-16 items-center justify-between">
          <Link
            to="/dashboard"
            className="flex items-center gap-3 rounded-md transition-opacity hover:opacity-80"
            aria-label="Go to HR Dashboard"
          >
            <img
              src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e}
              alt="UWC Logo"
              className="h-8 w-auto"
            />
            <span className="text-lg font-semibold text-slate-900">
              HR Dashboard
            </span>
          </Link>

          <div className="hidden items-center gap-1 lg:flex">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const active = isNavigationItemActive(item);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors ${
                    active
                      ? "bg-blue-50 text-[#003B7A]"
                      : "text-slate-600 hover:bg-slate-50 hover:text-[#003B7A]"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}

            <HeaderNotifications />

            <div className="flex items-center gap-2 border-l border-slate-200 pl-4">
              <div
                ref={userMenuRef}
                className="relative"
                onMouseEnter={openUserMenu}
                onMouseLeave={closeUserMenu}
                onFocus={openUserMenu}
                onBlur={handleUserMenuBlur}
              >
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex items-center gap-2"
                  aria-haspopup="menu"
                  aria-expanded={isUserMenuOpen}
                >
                  <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-sm font-bold text-white">
                    {user?.avatarPath ? (
                      <img
                        src={user.avatarPath}
                        alt="Profile"
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      user?.name?.charAt(0).toUpperCase() ||
                      localStorage.getItem("hr_user")?.charAt(0).toUpperCase() ||
                      "H"
                    )}
                  </div>
                  <span className="text-sm text-slate-600">
                    {user?.name || localStorage.getItem("hr_user")}
                  </span>
                </Button>

                {isUserMenuOpen && (
                  <div
                    role="menu"
                    className="absolute right-0 top-full z-50 mt-2 w-52 rounded-md border border-slate-200 bg-white p-1 shadow-lg"
                  >
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        closeUserMenuNow();
                        navigate("/profile");
                      }}
                      className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"
                    >
                      <User className="h-4 w-4 text-slate-500" />
                      User Profile
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        closeUserMenuNow();
                        navigate("/settings");
                      }}
                      className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"
                    >
                      <Settings className="h-4 w-4 text-slate-500" />
                      Setting
                    </button>
                    <div className="-mx-1 my-1 h-px bg-slate-200" />
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        closeUserMenuNow();
                        handleLogout();
                      }}
                      className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4" />
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 lg:hidden">
            <HeaderNotifications />
            <Sheet>
              <SheetTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10"
                  aria-label="Open navigation menu"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[82vw] max-w-xs gap-0 bg-white p-0">
                <SheetHeader className="border-b border-slate-200 px-5 py-5 text-left">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#0052CC] text-sm font-semibold text-white">
                      {user?.avatarPath ? (
                        <img
                          src={user.avatarPath}
                          alt="Profile"
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        user?.name?.charAt(0).toUpperCase() ||
                        localStorage.getItem("hr_user")?.charAt(0).toUpperCase() ||
                        "H"
                      )}
                    </div>
                    <SheetTitle className="min-w-0 truncate text-base">
                      {user?.name || localStorage.getItem("hr_user") || "HR User"}
                    </SheetTitle>
                  </div>
                </SheetHeader>

                <nav className="flex flex-col gap-1 p-3">
                  {navigationItems.map((item) => {
                    const Icon = item.icon;
                    const active = isNavigationItemActive(item);
                    return (
                      <SheetClose key={item.path} asChild>
                        <Link
                          to={item.path}
                          className={`inline-flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors ${
                            active
                              ? "bg-blue-50 text-[#003B7A]"
                              : "text-slate-600 hover:bg-slate-50 hover:text-[#003B7A]"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                          {item.label}
                        </Link>
                      </SheetClose>
                    );
                  })}

                  <div className="my-2 h-px bg-slate-200" />

                  <SheetClose asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-11 justify-start px-3 text-slate-600"
                      onClick={() => navigate("/profile")}
                    >
                      <User className="mr-2 h-4 w-4" />
                      User Profile
                    </Button>
                  </SheetClose>
                  <SheetClose asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-11 justify-start px-3 text-slate-600"
                      onClick={() => navigate("/settings")}
                    >
                      <Settings className="mr-2 h-4 w-4" />
                      Setting
                    </Button>
                  </SheetClose>
                  <SheetClose asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-11 justify-start px-3 text-red-600 hover:bg-red-50 hover:text-red-600"
                      onClick={handleLogout}
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      Logout
                    </Button>
                  </SheetClose>
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </nav>
  );
}
