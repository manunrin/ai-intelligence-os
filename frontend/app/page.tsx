"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { useArticles } from "@/hooks/useArticles";
import { useKnowledgeItems } from "@/hooks/useKnowledge";
import { useTasks } from "@/hooks/useTasks";
import { useReports } from "@/hooks/useReports";
import { useAgentRuns } from "@/hooks/useAgentRuns";
import { useDeleteArticle, useDeleteTask, useDeleteKnowledge } from "@/hooks/useDelete";
import { useToast } from "@/lib/toast";
import { queryClient } from "@/lib/query-client";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import type { Article, AgentRun, Task, KnowledgeItem, IntelligenceReport } from "@/types";
import { ArticleFormBody } from "@/components/articles/ArticleForm";
import { TaskFormBody } from "@/components/tasks/TaskForm";
import { KnowledgeFormBody } from "@/components/knowledge/KnowledgeForm";
import { ReportFormBody } from "@/components/reports/ReportForm";
import { DashboardPanel } from "@/components/panels/DashboardPanel";
import { ArticlesPanel } from "@/components/panels/ArticlesPanel";
import { TasksPanel } from "@/components/panels/TasksPanel";
import { KnowledgePanel } from "@/components/panels/KnowledgePanel";
import { AgentsPanel } from "@/components/panels/AgentExecutionPanel";
import { ReportsPanel } from "@/components/panels/ReportsPanel";

type TabKey = "dashboard" | "articles" | "knowledge" | "tasks" | "agents" | "reports";

const tabs: { key: TabKey; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "articles", label: "Articles" },
  { key: "knowledge", label: "Knowledge" },
  { key: "tasks", label: "Tasks" },
  { key: "agents", label: "Agents" },
  { key: "reports", label: "Reports" },
];

export default function HomePage() {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  // Data fetching via React Query
  const { data: articles = [], isLoading: loadingArticles } = useArticles();
  const { data: knowledgeItems = [], isLoading: loadingKnowledge } = useKnowledgeItems();
  const { data: tasks = [], isLoading: loadingTasks } = useTasks();
  const { data: agentRuns = [], isLoading: loadingAgents } = useAgentRuns();
  const { data: reports = [], isLoading: loadingReports } = useReports();

  const allLoading = loadingArticles || loadingKnowledge || loadingTasks || loadingAgents || loadingReports;

  // Mutations
  const deleteArticle = useDeleteArticle();
  const deleteTask = useDeleteTask();
  const deleteKnowledge = useDeleteKnowledge();

  // Tab state
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: string; id: string } | null>(null);

  // Article modal
  const [articleModalOpen, setArticleModalOpen] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [articleFormError, setArticleFormError] = useState<string | null>(null);

  // Task modal
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [taskFormError, setTaskFormError] = useState<string | null>(null);

  // Knowledge modal
  const [knowledgeModalOpen, setKnowledgeModalOpen] = useState(false);
  const [editingKnowledge, setEditingKnowledge] = useState<KnowledgeItem | null>(null);
  const [knowledgeFormError, setKnowledgeFormError] = useState<string | null>(null);

  // Report modal
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportFormError, setReportFormError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    const { type, id } = deleteConfirm;
    try {
      if (type === "article") await deleteArticle.mutateAsync(id);
      else if (type === "task") await deleteTask.mutateAsync(id);
      else if (type === "knowledge") await deleteKnowledge.mutateAsync(id);
      toast(`${type.charAt(0).toUpperCase() + type.slice(1)} deleted`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Delete failed", "error");
    } finally {
      setDeleteConfirm(null);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">AI Intelligence OS</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Monitor your autonomous intelligence pipeline</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={error ? "danger" : "success"}>{error ? "Offline" : "Connected"}</Badge>
          </div>
        </div>

        <ErrorBanner error={error} />

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

        {/* Loading state */}
        {allLoading && (
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 rounded-xl bg-slate-200 dark:bg-slate-800" />
              ))}
            </div>
          </div>
        )}

        {/* Tab content */}
        {!allLoading && (
          <>
            {activeTab === "dashboard" && (
              <DashboardPanel
                articles={articles}
                knowledgeItems={knowledgeItems}
                tasks={tasks}
                agentRuns={agentRuns}
              />
            )}

            {activeTab === "articles" && (
              <ArticlesPanel
                articles={articles}
                onNew={() => { setEditingArticle(null); setArticleModalOpen(true); }}
                onEdit={(article) => { setEditingArticle(article); setArticleModalOpen(true); }}
                onDelete={(id) => setDeleteConfirm({ type: "article", id })}
              />
            )}

            {activeTab === "knowledge" && (
              <KnowledgePanel
                items={knowledgeItems}
                onNew={() => { setEditingKnowledge(null); setKnowledgeModalOpen(true); }}
                onEdit={(item) => { setEditingKnowledge(item); setKnowledgeModalOpen(true); }}
                onDelete={(id) => setDeleteConfirm({ type: "knowledge", id })}
              />
            )}

            {activeTab === "tasks" && (
              <TasksPanel
                tasks={tasks}
                onNew={() => { setEditingTask(null); setTaskModalOpen(true); }}
                onEdit={(task) => { setEditingTask(task); setTaskModalOpen(true); }}
                onDelete={(id) => setDeleteConfirm({ type: "task", id })}
              />
            )}

            {activeTab === "agents" && (
              <AgentsPanel runs={agentRuns} isLoading={loadingAgents} />
            )}

            {activeTab === "reports" && (
              <ReportsPanel
                reports={reports}
                onCreate={() => setReportModalOpen(true)}
              />
            )}
          </>
        )}
      </div>

      {/* Article Modal */}
      <Modal
        open={articleModalOpen}
        onClose={() => { setArticleModalOpen(false); setEditingArticle(null); }}
        title={editingArticle ? "Edit Article" : "New Article"}
        footer={<Button variant="outline" onClick={() => { setArticleModalOpen(false); setEditingArticle(null); }}>Cancel</Button>}
      >
        <ArticleFormBody
          onSubmit={() => {
            setArticleModalOpen(false);
            setEditingArticle(null);
            queryClient.invalidateQueries({ queryKey: [["articles"]] });
          }}
          initialData={editingArticle}
          error={articleFormError}
          onError={setArticleFormError}
        />
      </Modal>

      {/* Task Modal */}
      <Modal
        open={taskModalOpen}
        onClose={() => { setTaskModalOpen(false); setEditingTask(null); }}
        title={editingTask ? "Edit Task" : "New Task"}
        footer={<Button variant="outline" onClick={() => { setTaskModalOpen(false); setEditingTask(null); }}>Cancel</Button>}
      >
        <TaskFormBody
          onSubmit={() => {
            setTaskModalOpen(false);
            setEditingTask(null);
            queryClient.invalidateQueries({ queryKey: [["tasks"]] });
          }}
          initialData={editingTask}
          error={taskFormError}
          onError={setTaskFormError}
        />
      </Modal>

      {/* Knowledge Modal */}
      <Modal
        open={knowledgeModalOpen}
        onClose={() => { setKnowledgeModalOpen(false); setEditingKnowledge(null); }}
        title={editingKnowledge ? "Edit Knowledge Item" : "New Knowledge Item"}
        footer={<Button variant="outline" onClick={() => { setKnowledgeModalOpen(false); setEditingKnowledge(null); }}>Cancel</Button>}
      >
        <KnowledgeFormBody
          onSubmit={() => {
            setKnowledgeModalOpen(false);
            setEditingKnowledge(null);
            queryClient.invalidateQueries({ queryKey: [["knowledge"]] });
          }}
          initialData={editingKnowledge}
          error={knowledgeFormError}
          onError={setKnowledgeFormError}
        />
      </Modal>

      {/* Report Modal */}
      <Modal
        open={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        title="New Report"
        footer={<Button variant="outline" onClick={() => setReportModalOpen(false)}>Cancel</Button>}
      >
        <ReportFormBody
          onSubmit={() => {
            setReportModalOpen(false);
            queryClient.invalidateQueries({ queryKey: [["reports"]] });
          }}
          error={reportFormError}
          onError={setReportFormError}
        />
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
    </AppShell>
  );
}

function ErrorBanner({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">{error}</div>
  );
}
