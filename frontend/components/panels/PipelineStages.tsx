"use client";

import { useState } from "react";

import type { AgentRun } from "@/types";
import { useAgentStream } from "@/hooks/useAgentStream";
import type { AgentStreamEvent } from "@/hooks/useAgentStream";

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

function getStageStatuses(
  run: AgentRun | null,
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
  }

  if (run?.stage) {
    const matchIndex = STAGE_ORDER.findIndex((s) => run.stage!.toLowerCase().includes(s));
    if (matchIndex >= 0) {
      activeStage = STAGE_ORDER[matchIndex];
    } else {
      activeStage = run.stage;
    }
  }

  const allStages: string[] = [];
  for (const s of STAGE_ORDER) {
    if (!allStages.some((a) => a.toLowerCase() === s)) {
      allStages.push(s);
    }
  }
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

interface PipelineStagesProps {
  run: AgentRun | null;
}

export function PipelineStages({ run }: PipelineStagesProps) {
  const [streamEvents, setStreamEvents] = useState<AgentStreamEvent[]>([]);

  useAgentStream({
    runId: run?.id ?? null,
    enabled: !!run,
    onEvent: (event: AgentStreamEvent) => {
      setStreamEvents((prev) => [...prev.slice(-50), event]);
    },
  });

  const stages = getStageStatuses(run, streamEvents);

  return (
    <div className="flex items-center gap-1">
      {stages.map(({ name, status }, i) => (
        <PipelineStageDot key={name} name={name} status={status} index={i} total={stages.length} />
      ))}
    </div>
  );
}

function PipelineStageDot({
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

  return (
    <div className="flex items-center flex-1 min-w-0">
      <div className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors duration-200 ease-out ${dotColors[status]}`}>
        {status === "done" && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
        {status === "active" && (
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400 animate-pulse" />
        )}
      </div>
      {!isLast && (
        <div className={`flex-1 h-[2px] mx-1 rounded-full transition-colors duration-200 ease-out ${
          status === "done" ? "bg-green-300 dark:bg-green-800" : "bg-slate-200 dark:bg-slate-700"
        }`} />
      )}
    </div>
  );
}
