import type { ReactNode } from "react";

interface TableProps {
  columns: { key: string; label: string }[];
  data: unknown[];
  rowKey?: string;
  renderCell?: (key: string, value: unknown, row: unknown) => ReactNode;
}

export function DataTable({ columns, data, rowKey = "id", renderCell }: TableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">
                No data available
              </td>
            </tr>
          ) : (
            data.map((row, i) => {
              const r = row as Record<string, unknown>;
              return (
                <tr key={(r[rowKey] as string) || i} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      {renderCell
                        ? renderCell(col.key, r[col.key], row)
                        : String(r[col.key] ?? "")}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
