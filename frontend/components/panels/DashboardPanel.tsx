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
  const activeTasks = tasks.filter((t) => t.status !== "done").length;
  const runningAgents = agentRuns.filter((r) => r.status === "running" || r.status === "cancelling");

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">AI Intelligence OS</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Monitor your autonomous intelligence pipeline</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Connected
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Articles" value={articles.length} variant="default" />
        <StatCard title="Knowledge Items" value={knowledgeItems.length} variant="success" />
        <StatCard title="Active Tasks" value={activeTasks} variant="warning" />
        <StatCard title="Agent Runs" value={agentRuns.length} variant="default" />
      </div>

      {/* Active agents (if any) */}
      {runningAgents.length > 0 && (
        <section>
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Active Agents ({runningAgents.length})
          </h3>
          <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-900/50 dark:bg-blue-950/20">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
                {runningAgents[0].agent_id} — {runningAgents[0].stage || "Running"}
              </span>
              <Badge variant="default" className="ml-auto text-[10px] px-1.5 py-0">Running</Badge>
            </div>
          </div>
        </section>
      )}

      {/* Recent activity cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentList title="Recent Articles" subtitle={`${articles.length} total`} items={articles.slice(-5)} type="article" />
        <RecentList title="Knowledge Items" subtitle={`${knowledgeItems.length} extracted`} items={knowledgeItems.slice(-5)} type="knowledge" />
        <RecentList title="Active Tasks" subtitle={`${activeTasks} remaining`} items={tasks.slice(-5)} type="task" />
        <RecentList title="Agent Runs" subtitle={`${agentRuns.length} total`} items={agentRuns.slice(-5)} type="agent" />
      </div>
    </div>
  );
}

function RecentList({
  title,
  subtitle,
  items,
  type,
}: {
  title: string;
  subtitle: string;
  items: unknown[];
  type: "article" | "knowledge" | "task" | "agent";
}) {
  return (
    <Card title={title} subtitle={subtitle}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">
          {type === "article" && "No articles ingested yet."}
          {type === "knowledge" && "No knowledge extracted yet."}
          {type === "task" && "No tasks generated yet."}
          {type === "agent" && "No agent runs recorded."}
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item, i) => {
            const it = item as Record<string, unknown>;
            if (type === "article") {
              const a = it as Article;
              return (
                <div key={a.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{a.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="muted">{a.source}</Badge>
                    <Badge variant={statusColor(a.status, ["raw", "analyzed", "translated", "error"])}>
                      {a.status}
                    </Badge>
                  </div>
                </div>
              );
            }
            if (type === "knowledge") {
              const k = it as KnowledgeItem;
              return (
                <div key={k.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{k.title}</p>
                  <Badge variant="muted">{k.kind}</Badge>
                </div>
              );
            }
            if (type === "task") {
              const t = it as Task;
              return (
                <div key={t.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                  <p className={`text-sm ${t.status === "done" ? "line-through text-slate-400" : "font-medium text-slate-900 dark:text-slate-100"}`}>
                    {t.title}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant={priorityColor(t.priority)}>{t.priority}</Badge>
                    <Badge variant={statusColor(t.status, ["pending", "todo", "in_progress", "done", "blocked"])}>
                      {t.status.replace("_", " ")}
                    </Badge>
                  </div>
                </div>
              );
            }
            // agent
            const r = it as AgentRun;
            return (
              <div key={r.id} className="border-b border-slate-100 pb-2 last:border-0 dark:border-slate-800">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{r.agent_id}</p>
                <Badge variant={statusColor(r.status, ["pending", "running", "completed", "failed"])}>
                  {r.status}
                </Badge>
              </div>
            );
          })}
        </div>
      )}
    </Card>
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
