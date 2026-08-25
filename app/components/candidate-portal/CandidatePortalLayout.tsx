// Provides the candidate portal layout.
import { Link, useLocation } from "react-router";
import { BriefcaseBusiness, FileText, LogOut, Menu, UserRound } from "lucide-react";

import image_a7e321551d78150f830b1e4870452ab5d2dd7d7e from "../../assets/uwc-berhad-logo.png";
import type { CandidateAccount } from "../../lib/api";
import { Button } from "../ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../ui/sheet";

type CandidatePortalHeaderProps = {
  candidate: CandidateAccount | null;
  onLogin: () => void;
  onLogout?: () => void;
  sticky?: boolean;
};

// Renders the Candidate Portal Header component.
export function CandidatePortalHeader({
  candidate,
  onLogin,
  onLogout,
  sticky = true,
}: CandidatePortalHeaderProps) {
  const location = useLocation();
  const navigationItems = [
    {
      label: "Careers",
      path: "/careers",
      icon: BriefcaseBusiness,
      active: location.pathname.startsWith("/careers") || location.pathname.startsWith("/apply"),
    },
    {
      label: "My Applications",
      path: "/candidate/applications",
      icon: FileText,
      active: location.pathname.startsWith("/candidate/applications"),
    },
    {
      label: "Profile",
      path: "/candidate/profile",
      icon: UserRound,
      active: location.pathname === "/candidate/profile",
    },
  ];

  return (
    <header
      className={`z-30 border-b border-slate-200 bg-white/95 backdrop-blur ${
        sticky ? "sticky top-0" : ""
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/careers" className="flex items-center gap-3">
          <img
            src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e}
            alt="UWC"
            className="h-8 w-auto"
          />
          <div>
            <p className="font-semibold text-slate-950">UWC Careers</p>
            <p className="text-xs text-slate-500">Candidate Portal</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-2 text-sm lg:flex">
          {navigationItems.slice(0, candidate ? undefined : 1).map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors ${
                  item.active
                    ? "bg-blue-50 text-[#003B7A]"
                    : "text-slate-600 hover:bg-slate-50 hover:text-[#003B7A]"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
          {candidate ? (
            <>
              {onLogout && (
                <Button variant="ghost" size="sm" onClick={onLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </Button>
              )}
            </>
          ) : (
            <Button variant="ghost" size="sm" onClick={onLogin}>
              Login
            </Button>
          )}
        </nav>

        <Sheet>
          <SheetTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 lg:hidden"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[82vw] max-w-xs gap-0 bg-white p-0">
            <SheetHeader className="border-b border-slate-200 px-5 py-5 text-left">
              {candidate ? (
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#0052CC] text-sm font-semibold text-white">
                    {candidate.fullName?.trim().charAt(0).toUpperCase() || "C"}
                  </div>
                  <SheetTitle className="min-w-0 truncate text-base">
                    {candidate.fullName || "Candidate"}
                  </SheetTitle>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <img
                    src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e}
                    alt="UWC"
                    className="h-8 w-auto"
                  />
                  <SheetTitle className="text-base">UWC Careers</SheetTitle>
                </div>
              )}
            </SheetHeader>
            <nav className="flex flex-col gap-1 p-3">
              {navigationItems.slice(0, candidate ? undefined : 1).map((item) => {
                const Icon = item.icon;
                return (
                  <SheetClose key={item.path} asChild>
                    <Link
                      to={item.path}
                      className={`inline-flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors ${
                        item.active
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
              {candidate ? (
                <>
                  {onLogout && (
                    <SheetClose asChild>
                      <Button
                        variant="ghost"
                        className="h-11 justify-start px-3"
                        onClick={onLogout}
                      >
                        <LogOut className="mr-2 h-4 w-4" />
                        Logout
                      </Button>
                    </SheetClose>
                  )}
                </>
              ) : (
                <SheetClose asChild>
                  <Button
                    variant="ghost"
                    className="h-11 justify-start px-3"
                    onClick={onLogin}
                  >
                    Login
                  </Button>
                </SheetClose>
              )}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}

// Renders the Candidate Portal Footer component.
export function CandidatePortalFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-6 py-6 lg:px-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <img
              src={image_a7e321551d78150f830b1e4870452ab5d2dd7d7e}
              alt="UWC Logo"
              className="h-7 w-auto"
            />
            <div>
              <p className="text-sm font-semibold text-slate-900">
                UWC Berhad Recruitment
              </p>
              <p className="text-sm text-slate-500">
                Submit your application securely through this page.
              </p>
            </div>
          </div>
          <p className="text-sm text-slate-500">
            © 2026 UWC Berhad. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
