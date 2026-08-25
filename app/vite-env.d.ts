/// <reference types="vite/client" />
// Adds Vite types to the app.

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_HR_API_BASE_URL?: string;
  readonly VITE_CANDIDATE_API_BASE_URL?: string;
  readonly VITE_APP_SURFACE?: "full" | "candidate";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
