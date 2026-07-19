"use client";

import { AppShell } from "@/components/layout/AppShell";
import { AgentsPanel } from "@/components/panels/AgentExecutionPanel";

export default function AgentsPage() {
  return (
    <AppShell>
      <AgentsPanel />
    </AppShell>
  );
}
