"use client";

import { AppShell } from "@/components/layout/AppShell";
import { ReportsPanel } from "@/components/panels/ReportsPanel";
import { ReportViewer } from "@/components/panels/ReportViewer";
import { useReports } from "@/hooks/useReports";
import { useCreateReport } from "@/hooks/useReports";
import { useToast } from "@/lib/toast";
import { queryClient } from "@/lib/query-client";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { IntelligenceReport } from "@/types";
import { ReportFormBody } from "@/components/reports/ReportForm";
import { useState } from "react";

export default function ReportsRoute() {
  const { toast } = useToast();
  const { data: reports = [], isLoading: loading } = useReports();
  const createMutation = useCreateReport();

  const [formOpen, setFormOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [viewingReport, setViewingReport] = useState<IntelligenceReport | null>(null);

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync({ topic: "General Intelligence" });
      toast("Report creation started", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create report", "error");
    } finally {
      setFormOpen(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {!loading && (
          <ReportsPanel
            reports={reports}
            onCreate={() => setFormOpen(true)}
            onView={(report) => setViewingReport(report)}
          />
        )}
      </div>

      {/* View Report Slide-over */}
      {viewingReport && (
        <ReportViewer
          report={viewingReport}
          onClose={() => setViewingReport(null)}
        />
      )}

      {/* Create Report Modal */}
      <Modal
        open={formOpen}
        onClose={() => { setFormOpen(false); }}
        title="New Report"
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Generate</Button>
          </>
        }
      >
        <ReportFormBody
          onSubmit={() => {
            setFormOpen(false);
            queryClient.invalidateQueries({ queryKey: [["reports"]] });
          }}
          error={formError}
          onError={setFormError}
        />
      </Modal>
    </AppShell>
  );
}
