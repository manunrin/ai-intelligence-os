"use client";

import { Badge } from "@/components/ui/Badge";
import type { AgentRun } from "@/types";
import { PipelineStages } from "./PipelineStages";

interface ActiveAgentsCardProps {
  runs: AgentRun[];
}

export function ActiveAgentsCard({ runs }: ActiveAgentsCardProps) {
  const activeRuns = runs.filter((r) => r.status === "running" || r.status === "cancelling");

  if (activeRuns.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Active Agents</h3>
          </div>
          <p className="text-sm text-slate-400 dark:text-slate-500">No agents currently running.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="px-5 py-4 space-y-4">
        {activeRuns.map((run) => (
          <div key={run.id}>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{run.agent_id}</span>
              <Badge variant="default" className="text-[10px] px-1.5 py-0">Running</Badge>
              {run.stage && (
                <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">Stage: {run.stage}</span>
              )}
            </div>
            <PipelineStages run={run} />
          </div>
        ))}
      </div>
    </div>
  );
}
