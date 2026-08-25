// Provides the shared Page Layout.
import { ChevronRight } from "lucide-react";
import { Link } from "react-router";
import { HrHeader } from "./HrHeader";

interface BreadcrumbItem {
  label: string;
  href?: string;
}
interface PageLayoutProps {
  breadcrumbs: BreadcrumbItem[];
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  useCard?: boolean;
}
// Renders the Page Layout component.
export function PageLayout({
  breadcrumbs,
  title,
  subtitle,
  children,
  useCard = true,
}: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-100">
      <HrHeader />
      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-8">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-sm mb-6">
          {breadcrumbs.map((crumb, index) => (
            <div
              key={index}
              className="flex items-center gap-2"
            >
              {index > 0 && (
                <ChevronRight className="w-4 h-4 text-slate-400" />
              )}
              <Link
                to={crumb.href || "#"}
                className={
                  index === breadcrumbs.length - 1
                    ? "text-slate-900 font-medium hover:text-[#003B7A] transition-colors"
                    : "text-slate-500 hover:text-[#003B7A] transition-colors"
                }
              >
                {crumb.label}
              </Link>
            </div>
          ))}
        </div>
        {/* Page Title */}
        {title && (
        <div className="mb-6">
          {typeof title === "string" ? (
            <h1 className="text-3xl font-bold text-slate-900 mb-2">
              {title}
            </h1>
          ) : (
            title
          )}
          {subtitle && (
            <div className="text-slate-600">{subtitle}</div>
          )}
        </div>
        )}
        {/* Page Content */}
        {useCard ? (
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-8">
            {children}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
