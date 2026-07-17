/** Knowledge item creation/edit form body — renders inside a Modal. */

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import type { KnowledgeItem } from "@/types";
import { api } from "@/lib/api";

interface KnowledgeFormBodyProps {
  initialData?: KnowledgeItem | null;
  error: string | null;
  onError: (err: string | null) => void;
  onSubmit: () => void;
}

export function KnowledgeFormBody({ initialData, error, onError, onSubmit }: KnowledgeFormBodyProps) {
  const isEdit = !!initialData;
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("article");
  const [tagsStr, setTagsStr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit && initialData) {
      setTitle(initialData.title || "");
      setContent(initialData.content || "");
      setKind(initialData.kind || "article");
      setTagsStr((initialData.tags || []).join(", "));
    } else {
      setTitle("");
      setContent("");
      setKind("article");
      setTagsStr("");
    }
    onError(null);
  }, [isEdit, initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);

    try {
      const tags = tagsStr.split(",").map((t) => t.trim()).filter(Boolean);
      const body = { title, content, kind, tags };
      if (isEdit && initialData?.id) {
        await api.put(`/api/v1/knowledge/${initialData.id}`, body);
      } else {
        await api.post("/api/v1/knowledge", body);
      }
      onSubmit();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save knowledge item");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Knowledge title" required />
      <textarea
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500"
        rows={4} placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} required
      />
      <div className="grid grid-cols-2 gap-4">
        <select
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          value={kind} onChange={(e) => setKind(e.target.value)}
        >
          <option value="article">Article</option><option value="research">Research</option><option value="analysis">Analysis</option><option value="translation">Translation</option>
        </select>
        <Input label="Tags (comma-separated)" value={tagsStr} onChange={(e) => setTagsStr(e.target.value)} placeholder="tag1, tag2" />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onError(null)}>Cancel</Button>
        <Button type="submit" disabled={loading || !title || !content}>
          {loading ? "Saving..." : isEdit ? "Update" : "Create"}
        </Button>
      </div>
    </form>
  );
}
