"use client";

import { StatCard } from "@/components/ui/StatCard";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { Article, KnowledgeItem, Task, AgentRun } from "@/types";

interface DashboardPanelProps {
  articles: Article[];
  knowledgeItems: KnowledgeItem[];
  tasks: Task[];
  agentRuns: AgentRun[];
}

export function DashboardPanel({ articles, knowledgeItems, tasks, agentRuns }: DashboardPanelProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Articles" value={articles.length} variant="default" />
        <StatCard title="Knowledge Items" value={knowledgeItems.length} variant="success" />
        <StatCard title="Active Tasks" value={tasks.filter((t) => t.status !== "done").length} variant="warning" />
        <StatCard title="Agent Runs" value={agentRuns.length} variant="default" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Recent Articles" subtitle={`${articles.length} total`}>
          {articles.length === 0 ? (
            <p className="text-sm text-slate-400">No articles ingested yet.</p>
          ) : (
            <div className="space-y-3">
              {articles.slice(-5).map((a) => (
                <div key={a.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{a.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="muted">{a.source}</Badge>
                    <Badge variant={statusColor(a.status, ["raw", "analyzed", "translated", "error"])}>
                      {a.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Knowledge Items" subtitle={`${knowledgeItems.length} extracted`}>
          {knowledgeItems.length === 0 ? (
            <p className="text-sm text-slate-400">No knowledge extracted yet.</p>
          ) : (
            <div className="space-y-3">
              {knowledgeItems.slice(-5).map((k) => (
                <div key={k.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{k.title}</p>
                  <Badge variant="muted">{k.kind}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Active Tasks" subtitle={`${tasks.filter((t) => t.status !== "done").length} remaining`}>
          {tasks.length === 0 ? (
            <p className="text-sm text-slate-400">No tasks generated yet.</p>
          ) : (
            <div className="space-y-3">
              {tasks.slice(-5).map((t) => (
                <div key={t.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{t.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant={priorityColor(t.priority)}>
                      {t.priority}
                    </Badge>
                    <Badge variant={statusColor(t.status, ["pending", "todo", "in_progress", "done", "blocked"])}>
                      {t.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Agent Runs" subtitle={`${agentRuns.length} total`}>
          {agentRuns.length === 0 ? (
            <p className="text-sm text-slate-400">No agent runs recorded.</p>
          ) : (
            <div className="space-y-3">
              {agentRuns.slice(-5).map((r) => (
                <div key={r.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{r.agent_id}</p>
                  <Badge variant={statusColor(r.status, ["pending", "running", "completed", "failed"])}>
                    {r.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function statusColor(status: string, known: string[]): "default" | "success" | "warning" | "danger" | "muted" {
  const map: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
    raw: "warning", analyzed: "default", translated: "success", error: "danger",
    todo: "muted", in_progress: "default", done: "success", blocked: "danger", pending: "muted",
    running: "default", completed: "success", failed: "danger",
  };
  if (known.includes(status)) return map[status] ?? "default";
  return "default";
}

function priorityColor(p: string): "default" | "success" | "warning" | "danger" | "muted" {
  const map: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
    low: "muted", medium: "default", high: "warning", urgent: "danger",
  };
  return map[p] ?? "default";
}
