// Provides the shared Loading State.
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "../ui/card";

type LoadingStateProps = {
  title?: string;
  message?: string;
  className?: string;
  delayMs?: number;
};

// Renders the Loading State component.
export function LoadingState({
  title = "Loading data",
  message = "Please wait while the latest database records are loaded.",
  className = "",
  delayMs = 200,
}: LoadingStateProps) {
  const [isVisible, setIsVisible] = useState(delayMs <= 0);

  useEffect(() => {
    if (delayMs <= 0) {
      setIsVisible(true);
      return;
    }

    const timer = window.setTimeout(() => {
      setIsVisible(true);
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [delayMs]);

  if (!isVisible) return null;

  return (
    <Card className={`shadow-sm ${className}`}>
      <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-12 text-center">
        <Loader2 className="h-9 w-9 animate-spin text-[#003B7A]" />
        <div>
          <p className="text-base font-semibold text-slate-900">
            {title}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {message}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
