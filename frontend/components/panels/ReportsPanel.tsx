"use client";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { IntelligenceReport } from "@/types";

interface ReportsPanelProps {
  reports: IntelligenceReport[];
  onCreate: () => void;
  onView?: (report: IntelligenceReport) => void;
}

export function ReportsPanel({ reports, onCreate, onView }: ReportsPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Intelligence Reports</h2>
        <Button onClick={onCreate}>New Report</Button>
      </div>

      {reports.length === 0 ? (
        <EmptyState
          title="No reports generated yet"
          description="Reports synthesize insights from your knowledge base into structured intelligence briefings."
          action={<Button size="sm" onClick={onCreate}>Generate first report</Button>}
        />
      ) : (
        <div className="space-y-2">
          {reports.slice().reverse().map((report) => (
            <ReportRow key={report.id} report={report} onView={onView} />
          ))}
        </div>
      )}
    </>
  );
}

function ReportRow({ report, onView }: { report: IntelligenceReport; onView?: (report: IntelligenceReport) => void }) {
  return (
    <div className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition-all duration-150 ease-out hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
      {/* Icon */}
      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-gradient-to-br from-violet-100 to-indigo-100 flex items-center justify-center dark:from-violet-900/30 dark:to-indigo-900/30">
        <svg className="w-4 h-4 text-violet-600 dark:text-violet-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{report.topic}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          {new Date(report.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
        {onView ? (
          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => onView(report)}>View</Button>
        ) : (
          <span className="h-8" />
        )}
      </div>
    </div>
  );
}
