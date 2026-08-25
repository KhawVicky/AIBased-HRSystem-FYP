// Provides the shared Search Clear Button.
import { X } from "lucide-react";

type SearchClearButtonProps = {
  show: boolean;
  onClear: () => void;
};

// Renders the Search Clear Button component.
export function SearchClearButton({ show, onClear }: SearchClearButtonProps) {
  if (!show) return null;

  return (
    <button
      type="button"
      aria-label="Clear search"
      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 transition-colors hover:text-slate-600"
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClear}
    >
      <X className="h-4 w-4" />
    </button>
  );
}
