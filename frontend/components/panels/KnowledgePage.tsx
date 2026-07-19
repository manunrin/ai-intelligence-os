"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
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

  const kinds = [...new Set(items.map((i) => i.kind))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Knowledge Base</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {items.length} items across {kinds.length} types
          </p>
        </div>
        <Button onClick={onNew}>New Item</Button>
      </div>

      {/* Tag/kind filter bar */}
      {kinds.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="muted" className="text-[10px] px-2 py-0.5 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors duration-150">
            All ({items.length})
          </Badge>
          {kinds.map((kind) => (
            <Badge
              key={kind}
              variant="muted"
              className="text-[10px] px-2 py-0.5 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors duration-150"
            >
              {kind} ({items.filter((i) => i.kind === kind).length})
            </Badge>
          ))}
        </div>
      )}

      {/* Content grid */}
      <KnowledgePanel items={items} onNew={onNew} onEdit={onEdit} onDelete={onDelete} />

      {/* Detail slide-over */}
      {selectedItem && (
        <KnowledgeDetail item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
}
