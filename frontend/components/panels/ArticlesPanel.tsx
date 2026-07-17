"use client";

import { DataTable } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { Article } from "@/types";

interface ArticlesPanelProps {
  articles: Article[];
  onNew: () => void;
  onEdit: (article: Article) => void;
  onDelete: (id: string) => void;
}

export function ArticlesPanel({ articles, onNew, onEdit, onDelete }: ArticlesPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Articles</h2>
        <Button onClick={onNew}>New Article</Button>
      </div>
      {articles.length === 0 ? (
        <Card title="No articles yet">
          <p className="text-sm text-slate-500">Create an article or wait for ingestion.</p>
        </Card>
      ) : (
        <DataTable
          columns={[
            { key: "title", label: "Title" },
            { key: "source", label: "Source" },
            { key: "status", label: "Status" },
            { key: "fetched_at", label: "Fetched" },
          ]}
          data={articles}
          rowKey="id"
          renderCell={(key: string, value: unknown, row: unknown) => {
            if (key === "status") {
              const colors: Record<string, "default" | "success" | "warning" | "danger"> = {
                raw: "warning", analyzed: "default", translated: "success", error: "danger",
              };
              return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
            }
            if (key === "fetched_at" && typeof value === "string") return new Date(value).toLocaleDateString();
            if (key === "actions") {
              const r = row as Record<string, unknown>;
              return (
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => onEdit(r as unknown as Article)}>Edit</Button>
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
