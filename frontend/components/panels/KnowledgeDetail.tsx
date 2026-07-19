"use client";

import { Badge } from "@/components/ui/Badge";
import type { KnowledgeItem } from "@/types";

interface KnowledgeDetailProps {
  item: KnowledgeItem;
  onClose: () => void;
}

const KIND_CONFIG: Record<string, { icon: string; label: string }> = {
  concept: { icon: "💡", label: "Concept" },
  person: { icon: "👤", label: "Person" },
  event: { icon: "📅", label: "Event" },
  organization: { icon: "🏢", label: "Organization" },
  place: { icon: "📍", label: "Place" },
};

export function KnowledgeDetail({ item, onClose }: KnowledgeDetailProps) {
  const config = KIND_CONFIG[item.kind] ?? { icon: "📋", label: item.kind };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end" role="dialog">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" style={{ animation: "fadeIn 200ms ease-out" }} onClick={onClose} />

      {/* Sheet */}
      <div
        className="relative ml-auto flex h-full w-full max-w-lg flex-col border-l border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
        style={{ animation: "slideIn 200ms var(--ease-out)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <span className="text-lg">{config.icon}</span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</h2>
              <Badge variant="default" className="mt-0.5 text-[10px] px-1.5 py-0">{config.label}</Badge>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300 transition-colors duration-150"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Content body */}
          {item.content && (
            <dl>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Content</dt>
              <dd className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{item.content}</dd>
            </dl>
          )}

          {/* Tags */}
          {item.tags && item.tags.length > 0 && (
            <dl>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Tags</dt>
              <dd className="mt-2 flex flex-wrap gap-1.5">
                {item.tags.map((tag) => (
                  <Badge key={tag} variant="muted" className="text-[10px] px-2 py-0.5">{tag}</Badge>
                ))}
              </dd>
            </dl>
          )}

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <dl>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</dt>
              <dd className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                {new Date(item.created_at).toLocaleString()}
              </dd>
            </dl>
            {item.article_id && (
              <dl>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Source</dt>
                <dd className="mt-1 text-sm text-blue-600 dark:text-blue-400">Article #{item.article_id.slice(0, 8)}</dd>
              </dl>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
