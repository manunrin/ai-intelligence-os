"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Article, AgentRun, Task, KnowledgeItem, IntelligenceReport } from "@/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/Table";
import { StatCard } from "@/components/ui/StatCard";

type TabKey = "dashboard" | "articles" | "knowledge" | "tasks" | "agents" | "reports";

const tabs: { key: TabKey; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "articles", label: "Articles" },
  { key: "knowledge", label: "Knowledge" },
  { key: "tasks", label: "Tasks" },
  { key: "agents", label: "Agents" },
  { key: "reports", label: "Reports" },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [articles, setArticles] = useState<Article[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [reports, setReports] = useState<IntelligenceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [articlesRes, knowledgeRes, tasksRes, agentsRes, reportsRes] =
          await Promise.all([
            api.get<Article[]>("/api/articles"),
            api.get<KnowledgeItem[]>("/api/knowledge"),
            api.get<Task[]>("/api/tasks"),
            api.get<AgentRun[]>("/api/agents/runs"),
            api.get<IntelligenceReport[]>("/api/reports"),
          ]);
        setArticles(articlesRes);
        setKnowledgeItems(knowledgeRes);
        setTasks(tasksRes);
        setAgentRuns(agentsRes);
        setReports(reportsRes);
      } catch (err) {
        // Backend not running yet — show empty state
        if (err instanceof Error && err.message.includes("fetch")) {
          setError("Backend not available. Start with `make start`.");
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 dark:bg-slate-950">
        <div className="mx-auto max-w-6xl">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 rounded-xl bg-slate-200 dark:bg-slate-800" />
              ))}
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              AI Intelligence OS
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Monitor your autonomous intelligence pipeline
            </p>
          </div>
          <Badge variant={error ? "danger" : "success"}>
            {error ? "Offline" : "Connected"}
          </Badge>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Articles"
            value={articles.length}
            variant="default"
          />
          <StatCard
            title="Knowledge Items"
            value={knowledgeItems.length}
            variant="success"
          />
          <StatCard
            title="Active Tasks"
            value={tasks.filter((t) => t.status !== "done").length}
            variant="warning"
          />
          <StatCard
            title="Agent Runs"
            value={agentRuns.length}
            variant="default"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto rounded-lg bg-white p-1 dark:bg-slate-900">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <ErrorBanner error={error} />

        {activeTab === "dashboard" && (
          <DashboardView
            articles={articles}
            knowledgeItems={knowledgeItems}
            tasks={tasks}
            agentRuns={agentRuns}
          />
        )}
        {activeTab === "articles" && (
          <DataTable
            columns={[
              { key: "title", label: "Title" },
              { key: "source", label: "Source" },
              { key: "status", label: "Status" },
              { key: "fetched_at", label: "Fetched" },
            ]}
            data={articles}
            rowKey="id"
            renderCell={(key, value) => {
              if (key === "status") {
                const statusColors: Record<string, "default" | "success" | "warning" | "danger"> = {
                  raw: "warning",
                  analyzed: "default",
                  translated: "success",
                  error: "danger",
                };
                return (
                  <Badge variant={(statusColors[value as string] || "default") as "default" | "success" | "warning" | "danger" | "muted"}>
                    {String(value)}
                  </Badge>
                );
              }
              if (key === "fetched_at" && typeof value === "string") {
                return new Date(value).toLocaleDateString();
              }
              return String(value ?? "");
            }}
          />
        )}
        {activeTab === "knowledge" && (
          <DataTable
            columns={[
              { key: "title", label: "Title" },
              { key: "kind", label: "Type" },
              { key: "tags", label: "Tags" },
              { key: "created_at", label: "Created" },
            ]}
            data={knowledgeItems}
            rowKey="id"
            renderCell={(key, value) => {
              if (key === "tags" && Array.isArray(value)) {
                return (
                  <div className="flex flex-wrap gap-1">
                    {value.slice(0, 3).map((tag: string) => (
                      <Badge key={tag} variant="muted">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                );
              }
              if (key === "created_at" && typeof value === "string") {
                return new Date(value).toLocaleDateString();
              }
              return String(value ?? "");
            }}
          />
        )}
        {activeTab === "tasks" && (
          <DataTable
            columns={[
              { key: "title", label: "Task" },
              { key: "priority", label: "Priority" },
              { key: "status", label: "Status" },
            ]}
            data={tasks}
            rowKey="id"
            renderCell={(key, value) => {
              if (key === "priority" || key === "status") {
                const colors: Record<string, "default" | "success" | "warning" | "danger"> = {
                  low: "muted",
                  medium: "default",
                  high: "warning",
                  urgent: "danger",
                  todo: "muted",
                  in_progress: "default",
                  done: "success",
                  blocked: "danger",
                };
                return (
                  <Badge variant={colors[value as string] || "muted"}>
                    {String(value)}
                  </Badge>
                );
              }
              return String(value ?? "");
            }}
          />
        )}
        {activeTab === "agents" && (
          <DataTable
            columns={[
              { key: "agent_id", label: "Agent" },
              { key: "status", label: "Status" },
              { key: "started_at", label: "Started" },
            ]}
            data={agentRuns}
            rowKey="id"
            renderCell={(key, value) => {
              if (key === "status") {
                const colors: Record<string, "default" | "success" | "warning" | "danger"> = {
                  pending: "muted",
                  running: "default",
                  completed: "success",
                  failed: "danger",
                };
                return (
                  <Badge variant={colors[value as string] || "muted"}>
                    {String(value)}
                  </Badge>
                );
              }
              if (key === "started_at" && typeof value === "string") {
                return new Date(value).toLocaleString();
              }
              return String(value ?? "");
            }}
          />
        )}
        {activeTab === "reports" && (
          <div className="space-y-4">
            {reports.length === 0 && (
              <Card title="Intelligence Reports" subtitle="No reports generated yet">
                <p className="text-sm text-slate-500">
                  Run the daily intelligence workflow to generate reports.
                </p>
              </Card>
            )}
            {reports.map((report) => (
              <Card
                key={report.id}
                title={report.topic}
                footer={
                  <div className="text-xs text-slate-400">
                    Created: {new Date(report.created_at).toLocaleString()}
                  </div>
                }
              >
                <div className="space-y-2 text-sm">
                  {report.research_result && (
                    <div>
                      <span className="font-medium text-slate-700 dark:text-slate-300">Research: </span>
                      <span className="text-slate-500">
                        {typeof report.research_result === "object"
                          ? JSON.stringify(report.research_result).slice(0, 200)
                          : String(report.research_result)}
                      </span>
                    </div>
                  )}
                  {report.analysis_result && (
                    <div>
                      <span className="font-medium text-slate-700 dark:text-slate-300">Analysis: </span>
                      <span className="text-slate-500">
                        {typeof report.analysis_result === "object"
                          ? JSON.stringify(report.analysis_result).slice(0, 200)
                          : String(report.analysis_result)}
                      </span>
                    </div>
                  )}
                  {report.knowledge_items.length > 0 && (
                    <div>
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        Knowledge: {report.knowledge_items.length} items
                      </span>
                    </div>
                  )}
                  {report.tasks.length > 0 && (
                    <div>
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        Tasks: {report.tasks.length} generated
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function DashboardView({
  articles,
  knowledgeItems,
  tasks,
  agentRuns,
}: {
  articles: Article[];
  knowledgeItems: KnowledgeItem[];
  tasks: Task[];
  agentRuns: AgentRun[];
}) {
  return (
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
                  <Badge
                    variant={
                      a.status === "translated"
                        ? "success"
                        : a.status === "analyzed"
                          ? "default"
                          : a.status === "error"
                            ? "danger"
                            : "warning"
                    }
                  >
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
                  <Badge
                    variant={
                      t.priority === "urgent"
                        ? "danger"
                        : t.priority === "high"
                          ? "warning"
                          : "muted"
                    }
                  >
                    {t.priority}
                  </Badge>
                  <Badge
                    variant={t.status === "done" ? "success" : t.status === "in_progress" ? "default" : "muted"}
                  >
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
                <Badge
                  variant={
                    r.status === "completed"
                      ? "success"
                      : r.status === "failed"
                        ? "danger"
                        : r.status === "running"
                          ? "default"
                          : "muted"
                  }
                >
                  {r.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function ErrorBanner({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
      {error}
    </div>
  );
}
