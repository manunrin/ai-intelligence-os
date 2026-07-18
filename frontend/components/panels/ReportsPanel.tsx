"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { IntelligenceReport } from "@/types";

interface ReportsPanelProps {
  reports: IntelligenceReport[];
  onCreate: () => void;
}

export function ReportsPanel({ reports, onCreate }: ReportsPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Intelligence Reports</h2>
        <Button onClick={onCreate}>New Report</Button>
      </div>
      {reports.length === 0 ? (
        <Card title="No reports generated yet">
          <p className="text-sm text-slate-500">Create a report or run the daily intelligence workflow.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <Card
              key={report.id}
              title={report.topic}
              footer={<div className="text-xs text-slate-400">Created: {new Date(report.created_at).toLocaleString()}</div>}
            >
              <div className="space-y-2 text-sm">
                <p className="text-slate-500">Report created successfully.</p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
