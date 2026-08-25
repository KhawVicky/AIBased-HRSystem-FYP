// Provides the shared Not Found.
import { Link } from "react-router";
import { Button } from "../ui/button";
import { FileQuestion } from "lucide-react";

// Renders the Not Found component.
export function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <FileQuestion className="w-16 h-16 text-slate-400 mx-auto mb-4" />
        <h1 className="text-4xl font-bold mb-2">404</h1>
        <p className="text-slate-600 mb-6">Page not found</p>
        <Button asChild>
          <Link to="/dashboard">Go to Dashboard</Link>
        </Button>
      </div>
    </div>
  );
}
