// Defines the employment form data.
export type FormValues = Record<string, string>;

export type TableRow = Record<string, string> & { id: string };

export interface TableColumn {
  key: string;
  label: React.ReactNode;
  inputType?: "text" | "date" | "number" | "select";
  options?: string[];
  width?: string;
}
