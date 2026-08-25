// Shows the Repeatable Table view.
import type { TableColumn, TableRow } from "./types";

interface RepeatableTableProps {
  ariaLabel: string;
  columns: TableColumn[];
  rows: TableRow[];
  onChange: (rows: TableRow[]) => void;
  minimumRows?: number;
  required?: boolean;
}

// Creates row.
const makeRow = (columns: TableColumn[]): TableRow => ({
  id: crypto.randomUUID(),
  ...Object.fromEntries(columns.map((column) => [column.key, ""])),
});

// Creates rows.
export function createRows(columns: TableColumn[], count: number) {
  return Array.from({ length: count }, () => makeRow(columns));
}

// Renders the Repeatable Table component.
export function RepeatableTable({
  ariaLabel,
  columns,
  rows,
  onChange,
  minimumRows = 1,
  required = false,
}: RepeatableTableProps) {
  // Updates cell.
  const updateCell = (rowId: string, key: string, value: string) => {
    onChange(
      rows.map((row) => (row.id === rowId ? { ...row, [key]: value } : row)),
    );
  };

  return (
    <div className="employment-form__repeatable">
      <div className="employment-form__table-scroll">
        <table className="employment-form__table" aria-label={ariaLabel}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} style={{ width: column.width }}>
                  {column.label}
                </th>
              ))}
              <th className="employment-form__action-column">Row</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={row.id}>
                {columns.map((column) => (
                  <td key={column.key}>
                    {column.inputType === "select" ? (
                      <select
                        aria-label={`${ariaLabel}, row ${rowIndex + 1}, ${column.key}`}
                        required={required}
                        value={row[column.key]}
                        onChange={(event) =>
                          updateCell(row.id, column.key, event.target.value)
                        }
                      >
                        <option value="">Select</option>
                        {column.options?.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        aria-label={`${ariaLabel}, row ${rowIndex + 1}, ${column.key}`}
                        required={required}
                        type={column.inputType ?? "text"}
                        value={row[column.key]}
                        onChange={(event) =>
                          updateCell(row.id, column.key, event.target.value)
                        }
                      />
                    )}
                  </td>
                ))}
                <td className="employment-form__row-action">
                  <button
                    type="button"
                    onClick={() => onChange(rows.filter((item) => item.id !== row.id))}
                    disabled={rows.length <= minimumRows}
                    aria-label={`Delete row ${rowIndex + 1} from ${ariaLabel}`}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        className="employment-form__add-row"
        type="button"
        onClick={() => onChange([...rows, makeRow(columns)])}
      >
        + Add row
      </button>
    </div>
  );
}
