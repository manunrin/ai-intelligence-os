"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAgentRuns, useSubmitAgentRun, useCancelAgentRun, useRefreshAgentRuns } from "@/hooks/useAgentRuns";
import { useAgentStream } from "@/hooks/useAgentStream";
import type { AgentRun } from "@/types";
import type { AgentStreamEvent } from "@/hooks/useAgentStream";

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

function getQualityVariant(score: number): "success" | "warning" | "danger" {
  if (score >= 0.7) return "success";
  if (score >= 0.4) return "warning";
  return "danger";
}

function formatScore(score: number | null | undefined): string {
  if (score == null) return "—";
  return `${Math.round(score * 100)}%`;
}

const STAGE_ORDER = [
  "ingest",
  "research",
  "analyze",
  "translate",
  "knowledge",
  "report",
  "notify",
  "complete",
];

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

function formatElapsed(startedAt: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const elapsed = Date.now() - start;
  return formatDuration(elapsed);
}

/* ─── Pipeline Stage Dot ─── */

function PipelineStage({
  name,
  status,
  index,
  total,
}: {
  name: string;
  status: "done" | "active" | "pending";
  index: number;
  total: number;
}) {
  const isLast = index === total - 1;

  const dotColors: Record<string, string> = {
    done: "bg-green-500 dark:bg-green-400",
    active: "bg-blue-500 dark:bg-blue-400",
    pending: "bg-slate-300 dark:bg-slate-600",
  };

  const iconColors: Record<string, string> = {
    done: "text-white",
    active: "text-blue-500 dark:text-blue-400",
    pending: "text-slate-400 dark:text-slate-500",
  };

  return (
    <div className="flex items-center flex-1 min-w-0">
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <div
          className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors duration-200 ease-out ${dotColors[status]}`}
        >
          {status === "done" && (
            <svg className={`w-3 h-3 ${iconColors.done}`} fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          )}
          {status === "active" && (
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400 animate-pulse" />
          )}
        </div>
        <span className={`text-xs font-medium truncate hidden sm:block ${
          status === "done" ? "text-green-600 dark:text-green-400" :
          status === "active" ? "text-blue-600 dark:text-blue-400" :
          "text-slate-400 dark:text-slate-500"
        }`}>
          {name}
        </span>
      </div>
      {!isLast && (
        <div className={`flex-1 h-[2px] mx-1 rounded-full transition-colors duration-200 ease-out ${
          status === "done" ? "bg-green-300 dark:bg-green-800" : "bg-slate-200 dark:bg-slate-700"
        }`} />
      )}
    </div>
  );
}

/* ─── Live Pipeline Card ─── */

function LivePipelineCard({ run }: { run: AgentRun }) {
  const cancelMutation = useCancelAgentRun();
  const [streamEvents, setStreamEvents] = useState<AgentStreamEvent[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Auto-start SSE streaming
  useAgentStream({
    runId: run.id,
    enabled: true,
    onEvent: (event: AgentStreamEvent) => {
      setStreamEvents((prev) => [...prev.slice(-50), event]);
      queryClient.invalidateQueries({ queryKey: ["agentRuns"] });
    },
  });

  // Auto-scroll event log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [streamEvents.length]);

  const stageStatuses = getStageStatuses(run, streamEvents);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {run.agent_id}
          </span>
          <Badge variant="default" className="text-[10px] px-1.5 py-0">Running</Badge>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400 tabular-nums">
          {formatElapsed(run.started_at)} elapsed
        </span>
      </div>

      {/* Pipeline stages */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-1">
          {stageStatuses.map(({ name, status }, i) => (
            <PipelineStage
              key={name}
              name={name}
              status={status}
              index={i}
              total={stageStatuses.length}
            />
          ))}
        </div>
      </div>

      {/* Event log (collapsible) */}
      {streamEvents.length > 0 && (
        <div ref={logRef} className="mx-4 mb-3 max-h-32 overflow-y-auto rounded-lg bg-slate-50 p-2 text-xs font-mono dark:bg-slate-900/50">
          {streamEvents.map((event, i) => (
            <div key={i} className="flex gap-2 text-slate-600 dark:text-slate-400 leading-relaxed">
              <span className="text-slate-400 dark:text-slate-500 flex-shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span className={`${
                event.type.includes("fail") ? "text-red-600 dark:text-red-400" :
                event.type.includes("complete") ? "text-green-600 dark:text-green-400" :
                ""
              }`}>
                {event.type.replace(/_/g, " ")}
                {event.stage_name ? ` · ${event.stage_name}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700">
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Current: {run.stage || "Initializing"}
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-950/30"
          onClick={() => cancelMutation.mutate(run.id)}
          disabled={cancelMutation.isPending}
        >
          {cancelMutation.isPending ? "Cancelling…" : "Cancel"}
        </Button>
      </div>
    </div>
  );
}

/* ─── Determine stage statuses from run + stream events ─── */

function getStageStatuses(
  run: AgentRun,
  events: AgentStreamEvent[],
): Array<{ name: string; status: "done" | "active" | "pending" }> {
  const completedStages = new Set<string>();
  let activeStage = "";

  for (const event of events) {
    if (event.type === "stage_complete" && event.stage_name) {
      completedStages.add(event.stage_name);
    }
    if (event.type === "stage_start" && event.stage_name) {
      activeStage = event.stage_name;
    }
    if (event.type === "run_complete" || event.type === "run_failed" || event.type === "run_cancelled") {
      // All stages are effectively done or cancelled
    }
  }

  // Also infer from run stage
  if (run.stage) {
    // Find the matching stage name in our ordered list
    const matchIndex = STAGE_ORDER.findIndex((s) => run.stage!.toLowerCase().includes(s));
    if (matchIndex >= 0) {
      activeStage = STAGE_ORDER[matchIndex];
    } else {
      activeStage = run.stage;
    }
  }

  // Build ordered stages — use what we have
  const allStages: string[] = [];
  for (const s of STAGE_ORDER) {
    if (!allStages.some((a) => a.toLowerCase() === s)) {
      allStages.push(s);
    }
  }

  // Add any stage from events that's not in our list
  for (const event of events) {
    if (event.stage_name && !allStages.some((a) => a.toLowerCase() === event.stage_name!.toLowerCase())) {
      allStages.push(event.stage_name);
    }
  }

  return allStages.map((name) => {
    const normalized = name.toLowerCase();
    if (completedStages.has(name) || completedStages.has(normalized)) return { name, status: "done" as const };
    if (activeStage && activeStage.toLowerCase() === normalized) return { name, status: "active" as const };
    return { name, status: "pending" as const };
  });
}

/* ─── Historical Run Card ─── */

function RunHistoryCard({ run, onViewDetails }: { run: AgentRun; onViewDetails: (run: AgentRun) => void }) {
  const variant = STATUS_VARIANTS[run.status] || "default";
  const isTerminal = run.status === "completed" || run.status === "failed" || run.status === "cancelled";
  const isFailed = run.status === "failed";
  const score = (run as any).evaluation_score as number | null | undefined;
  const criteria = (run as any).evaluation_criteria as Record<string, number> | null | undefined;
  const confidence = (run as any).evaluation_confidence as number | null | undefined;
  const hasEvaluation = score != null && isTerminal;

  return (
    <div className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-150 ease-out hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
              {run.agent_id}
            </span>
            <Badge variant={variant}>{run.status}</Badge>
            {hasEvaluation && (
              <Badge variant={getQualityVariant(score)}>
                {formatScore(score)}
              </Badge>
            )}
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span className="tabular-nums">{formatDuration(run.duration_ms)}</span>
            {run.started_at && (
              <span>{new Date(run.started_at).toLocaleString()}</span>
            )}
            {(run as any).retry_count > 0 && (
              <span className="text-red-500 dark:text-red-400">retry {(run as any).retry_count}</span>
            )}
            {run.stage && (
              <span className="truncate">Stage: {run.stage}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
          {isTerminal && (
            <>
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => onViewDetails(run)}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </Button>
              {(run.status === "completed" || isFailed) && (
                <RunRetryButton run={run} />
              )}
            </>
          )}
        </div>
      </div>
      {isFailed && run.error_message && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400 truncate">
          {run.error_message}
        </p>
      )}
    </div>
  );
}

function RunRetryButton({ run }: { run: AgentRun }) {
  const submitMutation = useSubmitAgentRun();
  const queryClient = useQueryClient();

  return (
    <Button
      size="sm"
      variant="ghost"
      className="h-7 w-7 p-0 text-blue-600 hover:text-blue-700 dark:text-blue-400"
      onClick={async () => {
        try {
          await submitMutation.mutateAsync({
            agent_type: ((run.input_payload as Record<string, unknown>)?._agent_type as string) ?? "intelligence",
            input_payload: run.input_payload,
          });
          queryClient.invalidateQueries({ queryKey: ["agentRuns"] });
        } catch { /* handled by mutation */ }
      }}
      disabled={submitMutation.isPending}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
      </svg>
    </Button>
  );
}

/* ─── Run Details Slide-over ─── */

function RunDetailsSheet({
  run,
  onClose,
}: {
  run: AgentRun | null;
  onClose: () => void;
}) {
  if (!run) return null;

  const score = (run as any).evaluation_score as number | null | undefined;
  const criteria = (run as any).evaluation_criteria as Record<string, number> | null | undefined;
  const confidence = (run as any).evaluation_confidence as number | null | undefined;
  const hasEvaluation = score != null && criteria != null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end" role="dialog">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        style={{ animation: "fadeIn 200ms ease-out" }}
        onClick={onClose}
      />
      {/* Sheet */}
      <div
        className="relative ml-auto flex h-full w-full max-w-lg flex-col border-l border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
        style={{ animation: "slideIn 200ms var(--ease-out)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{run.agent_id}</h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Run ID: <span className="font-mono">{run.id}</span></p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300 transition-colors duration-150"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Status row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</dt>
              <dd className="mt-1"><Badge variant={STATUS_VARIANTS[run.status] || "default"}>{run.status}</Badge></dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Duration</dt>
              <dd className="mt-1 text-sm tabular-nums">{formatDuration(run.duration_ms)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Started</dt>
              <dd className="mt-1 text-sm">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Finished</dt>
              <dd className="mt-1 text-sm">{run.finished_at ? new Date(run.finished_at).toLocaleString() : "—"}</dd>
            </div>
          </div>

          {/* Evaluation */}
          {hasEvaluation && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Quality Evaluation</dt>
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant={getQualityVariant(score)} className="text-sm px-3 py-1">
                    {formatScore(score)}
                  </Badge>
                  {confidence != null && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      置信度: {Math.round(confidence * 100)}%
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(criteria).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1.5 text-xs dark:bg-slate-800">
                      <span className="text-slate-500 dark:text-slate-400 capitalize">{key}</span>
                      <span className="font-medium tabular-nums text-slate-700 dark:text-slate-300">
                        {Math.round((val as number) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {run.error_message && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Error</dt>
              <pre className="mt-1.5 max-h-32 overflow-auto rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400 whitespace-pre-wrap">
                {run.error_message}
              </pre>
            </div>
          )}

          {/* Output */}
          {run.output_payload && Object.keys(run.output_payload).length > 0 && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Output</dt>
              <pre className="mt-1.5 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 whitespace-pre-wrap font-mono">
                {JSON.stringify(run.output_payload, null, 2)}
              </pre>
            </div>
          )}

          {/* Input */}
          {run.input_payload && Object.keys(run.input_payload).length > 0 && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Input</dt>
              <pre className="mt-1.5 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 whitespace-pre-wrap font-mono">
                {JSON.stringify(run.input_payload, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Agents Panel ─── */

export function AgentsPanel() {
  const { data: runs = [], isLoading } = useAgentRuns();
  const [showRunModal, setShowRunModal] = useState(false);
  const [detailRun, setDetailRun] = useState<AgentRun | null>(null);
  const [topic, setTopic] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [agentType, setAgentType] = useState("intelligence");
  const [error, setError] = useState<string | null>(null);

  const submitMutation = useSubmitAgentRun();
  const refreshMutation = useRefreshAgentRuns();

  const runningRuns = runs.filter((r: AgentRun) => r.status === "running" || r.status === "cancelling");
  const historicalRuns = runs.filter((r: AgentRun) => !(r.status === "running" || r.status === "cancelling"));

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
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
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">Agent Runs</h2>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowRunModal(true)}>
            New Run
          </Button>
        </div>
      </div>

      {/* Live pipeline */}
      {runningRuns.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Active Runs ({runningRuns.length})
          </h3>
          <div className="space-y-3">
            {runningRuns.map((run: AgentRun) => (
              <LivePipelineCard key={run.id} run={run} />
            ))}
          </div>
        </div>
      )}

      {/* Historical runs */}
      <div>
        {historicalRuns.length === 0 && !isLoading ? (
          <EmptyState
            title={runningRuns.length > 0 ? "No completed runs yet" : "No agent runs recorded"}
            description={
              runningRuns.length > 0
                ? "Completed runs will appear here."
                : "Start an agent to see execution history here."
            }
            action={
              <Button size="sm" onClick={() => setShowRunModal(true)}>
                Start your first run
              </Button>
            }
          />
        ) : (
          <div className="space-y-2">
            {historicalRuns.map((run: AgentRun) => (
              <RunHistoryCard key={run.id} run={run} onViewDetails={setDetailRun} />
            ))}
          </div>
        )}
      </div>

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
            <Button onClick={(e) => { (e.target as HTMLElement).closest("form")?.requestSubmit(); }} disabled={submitMutation.isPending}>
              {submitMutation.isPending ? "Starting…" : "Start Run"}
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

      {/* Details slide-over */}
      <RunDetailsSheet run={detailRun} onClose={() => setDetailRun(null)} />
    </div>
  );
}
