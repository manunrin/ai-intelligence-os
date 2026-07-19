"use client";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { KnowledgeItem } from "@/types";

interface KnowledgePanelProps {
  items: KnowledgeItem[];
  onNew: () => void;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: string) => void;
}

const KIND_ICONS: Record<string, string> = {
  concept: "💡",
  person: "👤",
  event: "📅",
  organization: "🏢",
  place: "📍",
  default: "📋",
};

const KIND_LABELS: Record<string, string> = {
  concept: "Concept",
  person: "Person",
  event: "Event",
  organization: "Organization",
  place: "Place",
  default: "Knowledge",
};

export function KnowledgePanel({ items, onNew, onEdit, onDelete }: KnowledgePanelProps) {
  const kinds = [...new Set(items.map((i) => i.kind))];

  return (
    <>
      <div className="flex items-center justify-between">
        <p className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{items.length} item{items.length !== 1 ? 's' : ''}</p>
        <Button onClick={onNew}>New Item</Button>
      </div>

      {/* Tag cloud */}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {kinds.map((kind) => (
            <Badge key={kind} variant="muted" className="text-[10px] px-2 py-0.5">
              {KIND_LABELS[kind] ?? kind} ({items.filter((i) => i.kind === kind).length})
            </Badge>
          ))}
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="No knowledge extracted yet"
          description="Knowledge items are created when agents analyze articles and extract facts, concepts, and relationships."
          action={<Button size="sm" onClick={onNew}>Add knowledge manually</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {items.slice().reverse().map((item) => (
            <KnowledgeCard key={item.id} item={item} onEdit={onEdit} onDelete={onDelete} />
          ))}
        </div>
      )}
    </>
  );
}

function KnowledgeCard({
  item,
  onEdit,
  onDelete,
}: {
  item: KnowledgeItem;
  onEdit: (i: KnowledgeItem) => void;
  onDelete: (id: string) => void;
}) {
  const icon = KIND_ICONS[item.kind] ?? KIND_ICONS.default;
  const kindLabel = KIND_LABELS[item.kind] ?? item.kind;

  return (
    <div className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-150 ease-out hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start gap-3">
        <span className="text-lg flex-shrink-0 mt-0.5">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 leading-relaxed">
              {item.title}
            </p>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <Badge variant="default" className="text-[10px] px-1.5 py-0">{kindLabel}</Badge>
            {item.tags?.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="muted" className="text-[10px] px-1.5 py-0">{tag}</Badge>
            ))}
            {item.tags && item.tags.length > 3 && (
              <span className="text-[10px] text-slate-400">+{item.tags.length - 3}</span>
            )}
          </div>
          <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500">
            {new Date(item.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </p>
        </div>
        <div className="flex gap-1 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => onEdit(item)}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
            </svg>
          </Button>
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30" onClick={() => onDelete(item.id)}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </Button>
        </div>
      </div>
    </div>
  );
}
