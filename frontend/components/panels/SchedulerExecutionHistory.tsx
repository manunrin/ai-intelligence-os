import { Badge } from "@/components/ui/Badge";
import type { ExecutionHistoryItem } from "@/types";

const STATUS_VARIANTS: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  pending: "muted",
  running: "default",
  completed: "success",
  failed: "danger",
  cancelled: "muted",
  timeout: "danger",
  interrupted: "warning",
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

interface SchedulerExecutionHistoryProps {
  history: ExecutionHistoryItem[];
  isLoading: boolean;
}

export function SchedulerExecutionHistory({ history, isLoading }: SchedulerExecutionHistoryProps) {
  if (isLoading) {
    return (
      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <p className="text-xs text-slate-400">Loading execution history…</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <p className="text-xs text-slate-400">No executions recorded.</p>
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      {history.map((run) => (
        <div
          key={run.id}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {new Date(run.started_at).toLocaleString()}
            </span>
            <Badge variant={STATUS_VARIANTS[run.status] || "default"}>{run.status}</Badge>
            <span className="ml-auto text-xs text-slate-400">{formatDuration(run.duration_ms)}</span>
          </div>
          {run.error_message && (
            <p className="mt-1 truncate text-[11px] text-red-600 dark:text-red-400" title={run.error_message}>
              {run.error_message}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
