"use client";

import { useState } from "react";
import {
  useSchedulerJobs,
  useCreateScheduledJob,
  useUpdateScheduledJob,
  useDeleteScheduledJob,
  useTriggerScheduledJob,
} from "@/hooks/useScheduler";
import { formatCronExpression } from "@/lib/cron-helpers";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { ScheduledJob } from "@/types";

const JOB_OPTIONS = [
  { value: "intelligence", label: "Daily Intelligence" },
  { value: "autonomous", label: "Autonomous Intelligence" },
];

export function SchedulerPanel() {
  const { data: jobs = [], isLoading } = useSchedulerJobs();
  const createMutation = useCreateScheduledJob();
  const updateMutation = useUpdateScheduledJob();
  const deleteMutation = useDeleteScheduledJob();
  const triggerMutation = useTriggerScheduledJob();

  const [showNewModal, setShowNewModal] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [triggeredId, setTriggeredId] = useState<string | null>(null);

  // Form state for new/edit
  const [formName, setFormName] = useState("");
  const [formCron, setFormCron] = useState("0 8 * * *");
  const [formType, setFormType] = useState("intelligence");
  const [formPayload, setFormPayload] = useState("");

  const openNewModal = () => {
    setEditingJob(null);
    setFormName("");
    setFormCron("0 8 * * *");
    setFormType("intelligence");
    setFormPayload("{}");
    setShowNewModal(true);
    setError(null);
  };

  const openEditModal = (job: ScheduledJob) => {
    setEditingJob(job);
    setFormName(job.name);
    setFormCron(job.cron_expression);
    setFormType(job.job_type);
    setFormPayload(JSON.stringify(job.input_payload || {}, null, 2));
    setShowNewModal(true);
    setError(null);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = formPayload.trim() ? JSON.parse(formPayload) : {};
      if (editingJob) {
        await updateMutation.mutateAsync({
          jobId: editingJob.id,
          name: formName,
          cron_expression: formCron,
          job_type: formType,
          input_payload: Object.keys(payload).length > 0 ? payload : undefined,
        });
      } else {
        await createMutation.mutateAsync({
          name: formName,
          cron_expression: formCron,
          job_type: formType,
          enabled: true,
          input_payload: Object.keys(payload).length > 0 ? payload : undefined,
        });
      }
      setShowNewModal(false);
      setEditingJob(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save schedule");
    }
  };

  const handleToggle = async (job: ScheduledJob) => {
    try {
      await updateMutation.mutateAsync({
        jobId: job.id,
        enabled: !job.enabled,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle");
    }
  };

  const handleDelete = async (job: ScheduledJob) => {
    if (!confirm(`Delete schedule "${job.name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const handleTrigger = async (job: ScheduledJob) => {
    try {
      await triggerMutation.mutateAsync(job.id);
      setTriggeredId(job.id);
      setTimeout(() => setTriggeredId(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger");
    }
  };

  const statusBadge = (status?: string | null) => {
    if (!status) return null;
    const variant: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
      submitted: "default",
      completed: "success",
      failed: "danger",
      cancelled: "muted",
      running: "warning",
    };
    return <Badge variant={variant[status] || "default"}>{status}</Badge>;
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Scheduler</h2>
        <Button size="sm" onClick={openNewModal}>
          New Schedule
        </Button>
      </div>

      {isLoading ? (
        <Card title="Loading…">
          <p className="text-sm text-slate-500">Fetching schedules…</p>
        </Card>
      ) : jobs.length === 0 ? (
        <Card title="No scheduled jobs">
          <p className="text-sm text-slate-500">
            Create a schedule to run agent pipelines automatically.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <Card key={job.id} title={job.name} className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="default">{JOB_OPTIONS.find((o) => o.value === job.job_type)?.label || job.job_type}</Badge>
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{job.cron_expression}</span>
                  <span className="text-xs text-slate-400 dark:text-slate-500">— {formatCronExpression(job.cron_expression)}</span>
                </div>

                <div className="flex items-center gap-3">
                  {/* Toggle switch */}
                  <button
                    type="button"
                    onClick={() => handleToggle(job)}
                    disabled={updateMutation.isPending}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
                      job.enabled
                        ? "bg-blue-600"
                        : "bg-slate-300 dark:bg-slate-600"
                    }`}
                    aria-label={job.enabled ? "Disable" : "Enable"}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                        job.enabled ? "translate-x-4" : "translate-x-0"
                      }`}
                    />
                  </button>
                  <span className="text-xs text-slate-600 dark:text-slate-400">
                    {job.enabled ? "Enabled" : "Disabled"}
                  </span>

                  {/* Last run info */}
                  {job.last_run_at && (
                    <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
                      Last run: {new Date(job.last_run_at).toLocaleString()}
                      {job.last_run_status && (
                        <span className="ml-2">{statusBadge(job.last_run_status)}</span>
                      )}
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                    onClick={() => openEditModal(job)}
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
                    onClick={() => handleTrigger(job)}
                    disabled={triggerMutation.isPending}
                  >
                    {triggeredId === job.id ? "Triggered!" : "Trigger Now"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    onClick={() => handleDelete(job)}
                    disabled={deleteMutation.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* New/Edit Modal */}
      <Modal
        open={showNewModal}
        onClose={() => { setShowNewModal(false); setEditingJob(null); setError(null); }}
        title={editingJob ? `Edit: ${editingJob.name}` : "New Schedule"}
        footer={
          <>
            <Button variant="outline" onClick={() => { setShowNewModal(false); setEditingJob(null); setError(null); }}>Cancel</Button>
            <Button onClick={handleSave} disabled={createMutation.isPending || updateMutation.isPending}>
              {(createMutation.isPending || updateMutation.isPending) ? "Saving…" : "Save"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSave} className="space-y-4">
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <Input
            label="Name"
            placeholder="e.g., daily intelligence"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />
          <Select
            label="Agent Type"
            value={formType}
            onChange={(e) => setFormType(e.target.value)}
            options={JOB_OPTIONS}
          />
          <Input
            label="Cron Expression"
            placeholder="0 8 * * *"
            value={formCron}
            onChange={(e) => setFormCron(e.target.value)}
          />
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Format: minute hour day-of-month month day-of-week
          </p>
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Input Payload (JSON)</label>
            <textarea
              className="w-full min-h-[80px] rounded-lg border border-slate-300 bg-white p-2 text-sm font-mono dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              value={formPayload}
              onChange={(e) => setFormPayload(e.target.value)}
              placeholder='{"topic": "AI trends"}'
            />
          </div>
        </form>
      </Modal>
    </>
  );
}
