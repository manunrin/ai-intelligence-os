"use client";

import { DataTable } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { AgentRun } from "@/types";

interface AgentsPanelProps {
  runs: AgentRun[];
}

export function AgentsPanel({ runs }: AgentsPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Agent Runs</h2>
      </div>
      {runs.length === 0 ? (
        <Card title="No agent runs recorded">
          <p className="text-sm text-slate-500">Run an agent to see execution history here.</p>
        </Card>
      ) : (
        <DataTable
          columns={[{ key: "agent_id", label: "Agent" }, { key: "status", label: "Status" }, { key: "started_at", label: "Started" }]}
          data={runs}
          rowKey="id"
          renderCell={(key: string, value: unknown) => {
            if (key === "status") {
              const colors: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
                pending: "muted", running: "default", completed: "success", failed: "danger",
              };
              return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
            }
            if (key === "started_at" && typeof value === "string") return new Date(value).toLocaleString();
            return String(value ?? "");
          }}
        />
      )}
    </>
  );
}
