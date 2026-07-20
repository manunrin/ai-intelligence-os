"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { IntelligenceReport, Task } from "@/types";

interface RecentSectionProps {
  title: string;
  items: Array<{ id: string; title: string; timestamp: string; badge?: string; badgeVariant?: string; href?: string }>;
  emptyTitle: string;
  emptyDescription: string;
  viewAllHref: string;
}

export function RecentSection({ title, items, emptyTitle, emptyDescription, viewAllHref }: RecentSectionProps) {
  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</h3>
        <Link href={viewAllHref} className="text-xs text-blue-600 hover:underline dark:text-blue-400 transition-colors duration-150">
          View all
        </Link>
      </div>
      {items.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <div className="space-y-1">
          {items.slice(0, 5).map((item) => (
            <RecentRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

function RecentRow({ item }: { item: { id: string; title: string; timestamp: string; badge?: string; badgeVariant?: string; href?: string } }) {
  return (
    <Link href={item.href ?? "#"} className="group flex items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 transition-all duration-150 ease-out hover:border-slate-200 hover:bg-white hover:shadow-sm dark:hover:border-slate-700 dark:hover:bg-slate-800">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors duration-150">
          {item.title}
        </p>
        <p className="text-[11px] text-slate-400 dark:text-slate-500 tabular-nums">
          {formatTimeAgo(item.timestamp)}
        </p>
      </div>
      {item.badge && (
        <Badge variant={item.badgeVariant as any || "muted"} className="text-[10px] px-1.5 py-0 flex-shrink-0">
          {item.badge}
        </Badge>
      )}
    </Link>
  );
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
