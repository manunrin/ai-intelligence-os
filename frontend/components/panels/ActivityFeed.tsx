"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import type { Article, KnowledgeItem, Task, AgentRun } from "@/types";

export interface NormalizedActivityItem {
  id: string;
  type: "article" | "knowledge" | "task" | "agent";
  title: string;
  subtitle?: string;
  timestamp: string;
  badge?: string;
  badgeVariant?: "default" | "success" | "warning" | "danger" | "muted";
  href?: string;
}

const STATUS_COLORS: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  raw: "warning", analyzed: "default", translated: "success", error: "danger",
  todo: "muted", in_progress: "default", done: "success", blocked: "danger", pending: "muted",
  running: "default", completed: "success", failed: "danger", cancelling: "warning",
};

const PRIORITY_COLORS: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  low: "muted", medium: "default", high: "warning", urgent: "danger",
};

/**
 * Normalize heterogeneous data sources into a single typed activity stream.
 * Called once at the page level — never inside JSX.
 */
export function normalizeActivityItems(
  articles: Article[],
  knowledge: KnowledgeItem[],
  tasks: Task[],
  runs: AgentRun[],
): NormalizedActivityItem[] {
  const items: NormalizedActivityItem[] = [];

  for (const a of articles.slice(-5)) {
    items.push({
      id: a.id,
      type: "article",
      title: a.title,
      subtitle: `${a.source} · ${a.status}`,
      timestamp: a.fetched_at,
      badge: a.status,
      badgeVariant: STATUS_COLORS[a.status] ?? "default",
      href: "/articles",
    });
  }

  for (const k of knowledge.slice(-5)) {
    items.push({
      id: k.id,
      type: "knowledge",
      title: k.title,
      subtitle: k.kind,
      timestamp: k.created_at,
      badge: k.kind,
      badgeVariant: "muted",
      href: "/knowledge",
    });
  }

  for (const t of tasks.filter((t) => t.status !== "done").slice(-5)) {
    items.push({
      id: t.id,
      type: "task",
      title: t.title,
      subtitle: t.priority,
      timestamp: t.created_at,
      badge: t.status.replace("_", " "),
      badgeVariant: STATUS_COLORS[t.status] ?? "default",
      href: "/tasks",
    });
  }

  for (const r of runs.slice(-5)) {
    items.push({
      id: r.id,
      type: "agent",
      title: r.agent_id,
      subtitle: r.stage ? `Stage: ${r.stage}` : undefined,
      timestamp: r.started_at,
      badge: r.status,
      badgeVariant: STATUS_COLORS[r.status] ?? "default",
      href: "/agents",
    });
  }

  // Sort descending by timestamp
  return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

interface ActivityFeedProps {
  items: NormalizedActivityItem[];
}

const TYPE_ICONS: Record<string, ReactNode> = {
  article: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  ),
  knowledge: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
    </svg>
  ),
  task: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  ),
  agent: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456 1.875 1.875 0 1 0-2.652 2.652 1.875 1.875 0 0 0 2.652-2.652Zm-2.652 10.544a1.875 1.875 0 1 0 2.652-2.653 3.375 3.375 0 0 0 2.455-2.456 1.875 1.875 0 1 0-2.652-2.652L10.5 18.75l-.813 2.846Z" />
    </svg>
  ),
};

export function ActivityFeed({ items }: ActivityFeedProps) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-400 dark:text-slate-500">No recent activity.</p>;
  }

  return (
    <div className="space-y-1">
      {items.map((item) => (
        <ActivityRow key={item.id} item={item} />
      ))}
    </div>
  );
}

function ActivityRow({ item }: { item: NormalizedActivityItem }) {
  const badgeVariant = item.badgeVariant ?? "muted";

  return (
    <Link href={item.href ?? "#"} className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors duration-150 ease-out hover:bg-slate-50 dark:hover:bg-slate-800/60">
      <span className="flex-shrink-0 text-slate-400 dark:text-slate-500">
        {TYPE_ICONS[item.type]}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{item.title}</p>
        {item.subtitle && (
          <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{item.subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {item.badge && (
          <Badge variant={badgeVariant} className="text-[10px] px-1.5 py-0">{item.badge}</Badge>
        )}
        <span className="text-[11px] text-slate-400 dark:text-slate-500 tabular-nums whitespace-nowrap">
          {formatTimeAgo(item.timestamp)}
        </span>
      </div>
    </Link>
  );
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `${days}d`;
}
