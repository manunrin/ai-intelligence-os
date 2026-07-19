"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { KnowledgePanel } from "@/components/panels/KnowledgePanel";
import { KnowledgeDetail } from "@/components/panels/KnowledgeDetail";
import type { KnowledgeItem } from "@/types";

interface KnowledgePageProps {
  items: KnowledgeItem[];
  onNew: () => void;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: string) => void;
}

export function KnowledgePage({ items, onNew, onEdit, onDelete }: KnowledgePageProps) {
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
  const [filterKind, setFilterKind] = useState<string | null>(null);

  const kinds = [...new Set(items.map((i) => i.kind))];
  const filteredItems = filterKind ? items.filter((i) => i.kind === filterKind) : items;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Knowledge Base</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {filteredItems.length} item{filteredItems.length !== 1 ? 's' : ''}
            {filteredItems.length !== items.length && ` of ${items.length} total`}
          </p>
        </div>
        <Button onClick={onNew}>New Item</Button>
      </div>

      {/* Tag/kind filter bar */}
      {kinds.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setFilterKind(null)}
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
              filterKind === null
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
            }`}
          >
            All ({items.length})
          </button>
          {kinds.map((kind) => (
            <button
              key={kind}
              type="button"
              onClick={() => setFilterKind(filterKind === kind ? null : kind)}
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-150 cursor-pointer ${
                filterKind === kind
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
              }`}
            >
              {kind} ({items.filter((i) => i.kind === kind).length})
            </button>
          ))}
        </div>
      )}

      {/* Content grid */}
      <KnowledgePanel items={filteredItems} onNew={onNew} onEdit={onEdit} onDelete={onDelete} />

      {/* Detail slide-over */}
      {selectedItem && (
        <KnowledgeDetail item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
}
