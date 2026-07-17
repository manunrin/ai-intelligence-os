"use client";

import { DataTable } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { KnowledgeItem } from "@/types";

interface KnowledgePanelProps {
  items: KnowledgeItem[];
  onNew: () => void;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: string) => void;
}

export function KnowledgePanel({ items, onNew, onEdit, onDelete }: KnowledgePanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Knowledge Items</h2>
        <Button onClick={onNew}>New Item</Button>
      </div>
      {items.length === 0 ? (
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
          data={items}
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
                  <Button size="sm" variant="ghost" onClick={() => onEdit(r as unknown as KnowledgeItem)}>Edit</Button>
                  <Button size="sm" variant="destructive" onClick={() => onDelete(String(r.id))}>Delete</Button>
                </div>
              );
            }
            return String(value ?? "");
          }}
        />
      )}
    </>
  );
}
