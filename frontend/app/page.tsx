"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, type User } from "@/lib/auth-context";
import { api, unwrap } from "@/lib/api";
import { useToast } from "@/lib/toast";
import type { Article, AgentRun, Task, KnowledgeItem, IntelligenceReport } from "@/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/Table";
import { StatCard } from "@/components/ui/StatCard";
import { Modal } from "@/components/ui/Modal";
import { ArticleFormBody } from "@/components/articles/ArticleForm";
import { TaskFormBody } from "@/components/tasks/TaskForm";
import { KnowledgeFormBody } from "@/components/knowledge/KnowledgeForm";
import { ReportFormBody } from "@/components/reports/ReportForm";

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
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center dark:bg-slate-950">
        <div className="text-center space-y-3">
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading...</p>
        </div>
      </main>
    );
  }

  return <DashboardContent user={user!} onLogout={() => { logout(); router.push("/login"); }} toast={toast} />;
}

function DashboardContent({ user, onLogout, toast }: { user: User; onLogout: () => void; toast: (msg: string, type?: "success" | "error" | "info") => void }) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [articles, setArticles] = useState<Article[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [reports, setReports] = useState<IntelligenceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [articles, knowledge, tasks, agents, reports] = await Promise.all([
        unwrap<Article>(api.get<unknown>("/api/v1/articles")),
        unwrap<KnowledgeItem>(api.get<unknown>("/api/v1/knowledge")),
        unwrap<Task>(api.get<unknown>("/api/v1/tasks")),
        unwrap<AgentRun>(api.get<unknown>("/api/v1/agents/runs")),
        unwrap<IntelligenceReport>(api.get<unknown>("/api/v1/reports")),
      ]);
      setArticles(articles);
      setKnowledgeItems(knowledge);
      setTasks(tasks);
      setAgentRuns(agents);
      setReports(reports);
    } catch (err) {
      if (err instanceof Error && err.message.includes("fetch")) {
        setError("Backend not available. Start with `make start`.");
      } else {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Article modal state
  const [articleModalOpen, setArticleModalOpen] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [articleFormError, setArticleFormError] = useState<string | null>(null);

  // Task modal state
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [taskFormError, setTaskFormError] = useState<string | null>(null);

  // Knowledge modal state
  const [knowledgeModalOpen, setKnowledgeModalOpen] = useState(false);
  const [editingKnowledge, setEditingKnowledge] = useState<KnowledgeItem | null>(null);
  const [knowledgeFormError, setKnowledgeFormError] = useState<string | null>(null);

  // Report modal state
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportFormError, setReportFormError] = useState<string | null>(null);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: string; id: string } | null>(null);

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    const { type, id } = deleteConfirm;
    try {
      const endpoints: Record<string, string> = {
        article: `/api/v1/articles/${id}`,
        task: `/api/v1/tasks/${id}`,
        knowledge: `/api/v1/knowledge/${id}`,
      };
      await api.delete(endpoints[type]);
      toast(`${type.charAt(0).toUpperCase() + type.slice(1)} deleted`, "success");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Delete failed", "error");
    }
    setDeleteConfirm(null);
  };

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
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">AI Intelligence OS</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Monitor your autonomous intelligence pipeline</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={error ? "danger" : "success"}>{error ? "Offline" : "Connected"}</Badge>
            <span className="text-sm text-slate-600 dark:text-slate-300">{user.username}</span>
            <Button variant="ghost" size="sm" onClick={onLogout}>Logout</Button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Articles" value={articles.length} variant="default" />
          <StatCard title="Knowledge Items" value={knowledgeItems.length} variant="success" />
          <StatCard title="Active Tasks" value={tasks.filter((t) => t.status !== "done").length} variant="warning" />
          <StatCard title="Agent Runs" value={agentRuns.length} variant="default" />
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

        <ErrorBanner error={error} />

        {/* Dashboard Tab */}
        {activeTab === "dashboard" && (
          <DashboardView articles={articles} knowledgeItems={knowledgeItems} tasks={tasks} agentRuns={agentRuns} />
        )}

        {/* Articles Tab */}
        {activeTab === "articles" && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Articles</h2>
              <Button onClick={() => { setEditingArticle(null); setArticleModalOpen(true); }}>New Article</Button>
            </div>
            {articles.length === 0 ? (
              <Card title="No articles yet">
                <p className="text-sm text-slate-500">Create an article or wait for ingestion.</p>
              </Card>
            ) : (
              <DataTable
                columns={[
                  { key: "title", label: "Title" },
                  { key: "source", label: "Source" },
                  { key: "status", label: "Status" },
                  { key: "fetched_at", label: "Fetched" },
                ]}
                data={articles}
                rowKey="id"
                renderCell={(key: string, value: unknown, row: unknown) => {
                  if (key === "status") {
                    const colors: Record<string, "default" | "success" | "warning" | "danger"> = { raw: "warning", analyzed: "default", translated: "success", error: "danger" };
                    return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
                  }
                  if (key === "fetched_at" && typeof value === "string") return new Date(value).toLocaleDateString();
                  if (key === "actions") {
                    const r = row as Record<string, unknown>;
                    return (
                      <div className="flex gap-2">
                        <Button size="sm" variant="ghost" onClick={() => { setEditingArticle(r as unknown as Article); setArticleModalOpen(true); }}>Edit</Button>
                        <Button size="sm" variant="destructive" onClick={() => setDeleteConfirm({ type: "article", id: String(r.id) })}>Delete</Button>
                      </div>
                    );
                  }
                  return String(value ?? "");
                }}
              />
            )}
          </>
        )}

        {/* Knowledge Tab */}
        {activeTab === "knowledge" && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Knowledge Items</h2>
              <Button onClick={() => { setEditingKnowledge(null); setKnowledgeModalOpen(true); }}>New Item</Button>
            </div>
            {knowledgeItems.length === 0 ? (
              <Card title="No knowledge items yet">
                <p className="text-sm text-slate-500">Create a knowledge item to start building your knowledge base.</p>
              </Card>
            ) : (
              <DataTable
                columns={[
                  { key: "title", label: "Title" },
                  { key: "kind", label: "Type" },
                  { key: "tags", label: "Tags" },
                  { key: "created_at", label: "Created" },
                ]}
                data={knowledgeItems}
                rowKey="id"
                renderCell={(key: string, value: unknown, row: unknown) => {
                  if (key === "tags" && Array.isArray(value)) {
                    return <div className="flex flex-wrap gap-1">{value.slice(0, 3).map((tag: string) => <Badge key={tag} variant="muted">{tag}</Badge>)}</div>;
                  }
                  if (key === "created_at" && typeof value === "string") return new Date(value).toLocaleDateString();
                  if (key === "actions") {
                    const r = row as Record<string, unknown>;
                    return (
                      <div className="flex gap-2">
                        <Button size="sm" variant="ghost" onClick={() => { setEditingKnowledge(r as unknown as KnowledgeItem); setKnowledgeModalOpen(true); }}>Edit</Button>
                        <Button size="sm" variant="destructive" onClick={() => setDeleteConfirm({ type: "knowledge", id: String(r.id) })}>Delete</Button>
                      </div>
                    );
                  }
                  return String(value ?? "");
                }}
              />
            )}
          </>
        )}

        {/* Tasks Tab */}
        {activeTab === "tasks" && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Tasks</h2>
              <Button onClick={() => { setEditingTask(null); setTaskModalOpen(true); }}>New Task</Button>
            </div>
            {tasks.length === 0 ? (
              <Card title="No tasks yet">
                <p className="text-sm text-slate-500">Create a task or wait for the agent to generate one.</p>
              </Card>
            ) : (
              <DataTable
                columns={[
                  { key: "title", label: "Task" },
                  { key: "priority", label: "Priority" },
                  { key: "status", label: "Status" },
                ]}
                data={tasks}
                rowKey="id"
                renderCell={(key: string, value: unknown, row: unknown) => {
                  if (key === "priority" || key === "status") {
                    const colors: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = { low: "muted", medium: "default", high: "warning", urgent: "danger", todo: "muted", in_progress: "default", done: "success", blocked: "danger", pending: "muted" };
                    return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
                  }
                  if (key === "actions") {
                    const r = row as Record<string, unknown>;
                    return (
                      <div className="flex gap-2">
                        <Button size="sm" variant="ghost" onClick={() => { setEditingTask(r as unknown as Task); setTaskModalOpen(true); }}>Edit</Button>
                        <Button size="sm" variant="destructive" onClick={() => setDeleteConfirm({ type: "task", id: String(r.id) })}>Delete</Button>
                      </div>
                    );
                  }
                  return String(value ?? "");
                }}
              />
            )}
          </>
        )}

        {/* Agents Tab */}
        {activeTab === "agents" && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Agent Runs</h2>
            </div>
            {agentRuns.length === 0 ? (
              <Card title="No agent runs recorded">
                <p className="text-sm text-slate-500">Run an agent to see execution history here.</p>
              </Card>
            ) : (
              <DataTable
                columns={[{ key: "agent_id", label: "Agent" }, { key: "status", label: "Status" }, { key: "started_at", label: "Started" }]}
                data={agentRuns}
                rowKey="id"
                renderCell={(key: string, value: unknown) => {
                  if (key === "status") {
                    const colors: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = { pending: "muted", running: "default", completed: "success", failed: "danger" };
                    return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
                  }
                  if (key === "started_at" && typeof value === "string") return new Date(value).toLocaleString();
                  return String(value ?? "");
                }}
              />
            )}
          </>
        )}

        {/* Reports Tab */}
        {activeTab === "reports" && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Intelligence Reports</h2>
              <Button onClick={() => setReportModalOpen(true)}>New Report</Button>
            </div>
            {reports.length === 0 ? (
              <Card title="No reports generated yet">
                <p className="text-sm text-slate-500">Create a report or run the daily intelligence workflow.</p>
              </Card>
            ) : (
              <div className="space-y-4">
                {reports.map((report) => (
                  <Card
                    key={report.id}
                    title={report.topic}
                    footer={<div className="text-xs text-slate-400">Created: {new Date(report.created_at).toLocaleString()}</div>}
                  >
                    <div className="space-y-2 text-sm">
                      {report.research_result && (
                        <div><span className="font-medium text-slate-700 dark:text-slate-300">Research: </span><span className="text-slate-500">{typeof report.research_result === "object" ? JSON.stringify(report.research_result).slice(0, 200) : String(report.research_result)}</span></div>
                      )}
                      {report.analysis_result && (
                        <div><span className="font-medium text-slate-700 dark:text-slate-300">Analysis: </span><span className="text-slate-500">{typeof report.analysis_result === "object" ? JSON.stringify(report.analysis_result).slice(0, 200) : String(report.analysis_result)}</span></div>
                      )}
                      {report.knowledge_items.length > 0 && (
                        <div><span className="font-medium text-slate-700 dark:text-slate-300">Knowledge: {report.knowledge_items.length} items</span></div>
                      )}
                      {report.tasks.length > 0 && (
                        <div><span className="font-medium text-slate-700 dark:text-slate-300">Tasks: {report.tasks.length} generated</span></div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Modals */}
      <Modal open={articleModalOpen} onClose={() => { setArticleModalOpen(false); setEditingArticle(null); }} title={editingArticle ? "Edit Article" : "New Article"}
        footer={<Button variant="outline" onClick={() => { setArticleModalOpen(false); setEditingArticle(null); }}>Cancel</Button>}
      >
        <ArticleFormBody onSubmit={load} initialData={editingArticle} error={articleFormError} onError={setArticleFormError} />
      </Modal>

      <Modal open={taskModalOpen} onClose={() => { setTaskModalOpen(false); setEditingTask(null); }} title={editingTask ? "Edit Task" : "New Task"}
        footer={<Button variant="outline" onClick={() => { setTaskModalOpen(false); setEditingTask(null); }}>Cancel</Button>}
      >
        <TaskFormBody onSubmit={load} initialData={editingTask} error={taskFormError} onError={setTaskFormError} />
      </Modal>

      <Modal open={knowledgeModalOpen} onClose={() => { setKnowledgeModalOpen(false); setEditingKnowledge(null); }} title={editingKnowledge ? "Edit Knowledge Item" : "New Knowledge Item"}
        footer={<Button variant="outline" onClick={() => { setKnowledgeModalOpen(false); setEditingKnowledge(null); }}>Cancel</Button>}
      >
        <KnowledgeFormBody onSubmit={load} initialData={editingKnowledge} error={knowledgeFormError} onError={setKnowledgeFormError} />
      </Modal>

      <Modal open={reportModalOpen} onClose={() => setReportModalOpen(false)} title="New Report"
        footer={<Button variant="outline" onClick={() => setReportModalOpen(false)}>Cancel</Button>}
      >
        <ReportFormBody onSubmit={load} error={reportFormError} onError={setReportFormError} />
      </Modal>

      {/* Delete Confirmation */}
      <Modal open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} title={`Delete ${deleteConfirm?.type}?`}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-300">Are you sure you want to delete this {deleteConfirm?.type}? This action cannot be undone.</p>
      </Modal>
    </main>
  );
}

function DashboardView({ articles, knowledgeItems, tasks, agentRuns }: { articles: Article[]; knowledgeItems: KnowledgeItem[]; tasks: Task[]; agentRuns: AgentRun[] }) {
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
                <div className="mt-1 flex items-center gap-2"><Badge variant="muted">{a.source}</Badge><Badge variant={a.status === "translated" ? "success" : a.status === "analyzed" ? "default" : a.status === "error" ? "danger" : "warning"}>{a.status}</Badge></div>
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
                  <Badge variant={t.priority === "urgent" ? "danger" : t.priority === "high" ? "warning" : "muted"}>{t.priority}</Badge>
                  <Badge variant={t.status === "done" ? "success" : t.status === "in_progress" ? "default" : "muted"}>{t.status}</Badge>
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
                <Badge variant={r.status === "completed" ? "success" : r.status === "failed" ? "danger" : r.status === "running" ? "default" : "muted"}>{r.status}</Badge>
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
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">{error}</div>
  );
}
