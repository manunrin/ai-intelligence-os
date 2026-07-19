"use client";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Article } from "@/types";

interface ArticlesPanelProps {
  articles: Article[];
  onNew: () => void;
  onEdit: (article: Article) => void;
  onDelete: (id: string) => void;
}

const STATUS_MAP: Record<string, "default" | "success" | "warning" | "danger"> = {
  raw: "warning",
  analyzed: "default",
  translated: "success",
  error: "danger",
};

const SOURCE_COLORS: Record<string, string> = {
  "openai-blog": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  "anthropic-blog": "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  default: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export function ArticlesPanel({ articles, onNew, onEdit, onDelete }: ArticlesPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">Articles</h2>
        <Button onClick={onNew}>New Article</Button>
      </div>

      {articles.length === 0 ? (
        <EmptyState
          title="No articles ingested yet"
          description="Articles appear automatically when RSS sources are connected."
          action={<Button size="sm" onClick={onNew}>Add an article manually</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {articles.slice().reverse().map((article) => (
            <ArticleCard key={article.id} article={article} onEdit={onEdit} onDelete={onDelete} />
          ))}
        </div>
      )}
    </>
  );
}

function ArticleCard({
  article,
  onEdit,
  onDelete,
}: {
  article: Article;
  onEdit: (a: Article) => void;
  onDelete: (id: string) => void;
}) {
  const statusColor = STATUS_MAP[article.status] || "default";
  const sourceClass = SOURCE_COLORS[article.source.toLowerCase().replace(/\s+/g, "-")] ?? SOURCE_COLORS.default;

  return (
    <div className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-150 ease-out hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 leading-relaxed">
            {article.title}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant="muted" className={sourceClass}>{article.source}</Badge>
            <Badge variant={statusColor}>{article.status}</Badge>
          </div>
          <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
            {new Date(article.fetched_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
          </p>
        </div>
        <div className="flex gap-1 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => onEdit(article)}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
            </svg>
          </Button>
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30" onClick={() => onDelete(article.id)}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </Button>
        </div>
      </div>
    </div>
  );
}
