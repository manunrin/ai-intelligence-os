"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DashboardPanel } from "@/components/panels/DashboardPanel";
import { useArticles } from "@/hooks/useArticles";
import { useKnowledgeItems } from "@/hooks/useKnowledge";
import { useTasks } from "@/hooks/useTasks";
import { useAgentRuns } from "@/hooks/useAgentRuns";

export default function DashboardPage() {
  const { data: articles = [], isLoading: loadingArticles } = useArticles();
  const { data: knowledgeItems = [], isLoading: loadingKnowledge } = useKnowledgeItems();
  const { data: tasks = [], isLoading: loadingTasks } = useTasks();
  const { data: agentRuns = [], isLoading: loadingAgents } = useAgentRuns();

  return (
    <AppShell>
      <DashboardPanel
        articles={articles}
        knowledgeItems={knowledgeItems}
        tasks={tasks}
        agentRuns={agentRuns}
      />
    </AppShell>
  );
}
