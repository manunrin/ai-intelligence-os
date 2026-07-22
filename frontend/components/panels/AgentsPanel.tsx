"use client";

import { useState } from "react";
import { useAgentRuns, useSubmitAgentRun, useCancelAgentRun, useRefreshAgentRuns } from "@/hooks/useAgentRuns";
import { useAgentStream } from "@/hooks/useAgentStream";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { DataTable } from "@/components/ui/Table";
import type { AgentRun } from "@/types";

interface AgentsPanelProps {
  runs: AgentRun[];
  isLoading: boolean;
}

const AGENT_OPTIONS = [
  { value: "intelligence", label: "Daily Intelligence" },
  { value: "autonomous", label: "Autonomous Intelligence" },
];

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  pending: "muted",
  initializing: "muted",
  running: "default",
  completed: "success",
  failed: "danger",
  cancelled: "muted",
  cancelling: "warning",
  timeout: "danger",
  interrupted: "warning",
  recovered: "warning",
};

function formatDuration(ms: number | null): string {
  if (ms == null || ms <= 0) return "—";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  if (m < 60) return `${m}m ${sec}s`;
  const h = Math.floor(m / 60);
  const min = m % 60;
  return `${h}h ${min}m`;
}

function formatElapsed(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  return formatDuration(end - start);
}

export function AgentsPanel({ runs, isLoading }: AgentsPanelProps) {
  const [showRunModal, setShowRunModal] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [agentType, setAgentType] = useState("intelligence");
  const [topic, setTopic] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitMutation = useSubmitAgentRun();
  const cancelMutation = useCancelAgentRun();
  const refreshMutation = useRefreshAgentRuns();

  // Track active streaming run
  const [streamingRunId, setStreamingRunId] = useState<string | null>(null);

  // Find any currently running run for auto-streaming
  const runningRun = runs.find((r) => r.status === "running");
  const activeStreamId = runningRun?.id ?? null;

  // Auto-start SSE when a run is active
  useAgentStream({
    runId: activeStreamId,
    enabled: !isLoading && !!activeStreamId,
    onEvent: () => {
      // Events received — the query invalidation in mutations handles UI updates
      // This callback exists for future extensibility (e.g., logging)
    },
  });

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await submitMutation.mutateAsync({
        agent_type: agentType,
        input_payload: { ...(topic ? { topic } : {}), ...(sourceId ? { source_id: sourceId } : {}) },
        topic: topic || undefined,
        source_id: sourceId || undefined,
      });
      setShowRunModal(false);
      setTopic("");
      setSourceId("");
      setAgentType("intelligence");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit agent run");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (runId: string) => {
    try {
      await cancelMutation.mutateAsync(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel run");
    }
  };

  const handleRetry = async (run: AgentRun) => {
    try {
      await submitMutation.mutateAsync({
        agent_type: ((run.input_payload as Record<string, unknown>)?._agent_type as string) ?? "intelligence",
        input_payload: run.input_payload,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to retry run");
    }
  };

  const handleRefresh = async () => {
    await refreshMutation.mutateAsync();
  };

  const handleViewDetails = (run: AgentRun) => {
    setStreamingRunId(run.id);
    setSelectedRunId(run.id);
  };

  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null;

  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Agent Runs</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshMutation.isPending}>
            {refreshMutation.isPending ? "Refreshing…" : "Refresh"}
          </Button>
          <Button size="sm" onClick={() => setShowRunModal(true)}>
            New Run
          </Button>
        </div>
      </div>

      {runs.length === 0 ? (
        <Card title="No agent runs recorded">
          <p className="text-sm text-slate-500">Run an agent to see execution history here.</p>
        </Card>
      ) : (
        <DataTable
          columns={[
            { key: "agent_id", label: "Agent" },
            { key: "status", label: "Status" },
            { key: "stage", label: "Stage" },
            { key: "started_at", label: "Started" },
            { key: "duration", label: "Elapsed" },
            { key: "_actions", label: "Actions" },
          ]}
          data={runs}
          rowKey="id"
          renderCell={(key: string, value: unknown, row: unknown) => {
            const r = row as AgentRun;

            if (key === "status") {
              const variant = STATUS_VARIANTS[value as string] || "default";
              return <Badge variant={variant}>{String(value)}</Badge>;
            }

            if (key === "stage") {
              return <span className="text-slate-600 dark:text-slate-400">{value as string}</span>;
            }

            if (key === "started_at" && typeof value === "string") {
              return <span>{new Date(value).toLocaleString()}</span>;
            }

            if (key === "duration") {
              return <span className="text-slate-600 dark:text-slate-400">{formatElapsed(r.started_at, r.finished_at)}</span>;
            }

            if (key === "_actions") {
              const isRunning = r.status === "running" || r.status === "cancelling";
              const isTerminal = r.status === "completed" || r.status === "failed" || r.status === "cancelled" || r.status === "interrupted";
              return (
                <div className="flex items-center gap-1">
                  {isRunning && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                      onClick={() => handleCancel(r.id)}
                      disabled={cancelMutation.isPending}
                    >
                      Cancel
                    </Button>
                  )}
                  {r.status === "failed" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                      onClick={() => handleRetry(r)}
                      disabled={submitMutation.isPending}
                    >
                      Retry
                    </Button>
                  )}
                  {isTerminal && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-600 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
                      onClick={() => handleViewDetails(r)}
                    >
                      Details
                    </Button>
                  )}
                  {(r.status === "completed" || r.status === "interrupted") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                      onClick={() => handleRetry(r)}
                      disabled={submitMutation.isPending}
                    >
                      Re-run
                    </Button>
                  )}
                </div>
              );
            }

            return String(value ?? "");
          }}
        />
      )}

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* New Run Modal */}
      <Modal
        open={showRunModal}
        onClose={() => { setShowRunModal(false); setError(null); }}
        title="New Agent Run"
        footer={
          <>
            <Button variant="outline" onClick={() => { setShowRunModal(false); setError(null); }}>Cancel</Button>
            <Button onClick={handleRun} disabled={submitting}>
              {submitting ? "Starting…" : "Start Run"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleRun} className="space-y-4">
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <Select
            label="Agent Type"
            value={agentType}
            onChange={(e) => setAgentType(e.target.value)}
            options={AGENT_OPTIONS}
          />
          <Input
            label="Topic (optional)"
            placeholder="e.g., AI regulation trends in EU"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <Input
            label="Source Article ID (optional)"
            placeholder="Link a specific article as context"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          />
        </form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        open={!!selectedRun}
        onClose={() => { setSelectedRunId(null); setStreamingRunId(null); }}
        title={`Run Details — ${selectedRun?.agent_id ?? ""}`}
        footer={
          <Button variant="outline" onClick={() => { setSelectedRunId(null); setStreamingRunId(null); }}>Close</Button>
        }
      >
        {selectedRun && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Status</dt>
                <dd className="mt-1">
                  <Badge variant={STATUS_VARIANTS[selectedRun.status] || "default"}>{selectedRun.status}</Badge>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Stage</dt>
                <dd className="mt-1 text-sm text-slate-900 dark:text-slate-100">{selectedRun.stage}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Started</dt>
                <dd className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                  {new Date(selectedRun.started_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Finished</dt>
                <dd className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                  {selectedRun.finished_at ? new Date(selectedRun.finished_at).toLocaleString() : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Duration</dt>
                <dd className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                  {formatDuration(selectedRun.duration_ms)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Run ID</dt>
                <dd className="mt-1 text-xs font-mono text-slate-600 dark:text-slate-400">{selectedRun.id}</dd>
              </div>
            </div>

            {selectedRun.error_message && (
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Error</dt>
                <pre className="mt-1 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
                  {selectedRun.error_message}
                </pre>
              </div>
            )}

            {selectedRun.output_payload && Object.keys(selectedRun.output_payload).length > 0 && (
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Output</dt>
                <pre className="mt-1 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {JSON.stringify(selectedRun.output_payload, null, 2)}
                </pre>
              </div>
            )}

            {selectedRun.input_payload && Object.keys(selectedRun.input_payload).length > 0 && (
              <div>
                <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Input</dt>
                <pre className="mt-1 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {JSON.stringify(selectedRun.input_payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </>
  );
}
