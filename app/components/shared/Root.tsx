// Provides the shared Root.
import { Outlet } from "react-router";

// Renders the Root component.
export function Root() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Outlet />
    </div>
  );
}
