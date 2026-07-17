/** Article creation/edit form body — renders inside a Modal. */

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import type { Article } from "@/types";
import { api } from "@/lib/api";

interface ArticleFormBodyProps {
  initialData?: Article | null;
  error: string | null;
  onError: (err: string | null) => void;
  onSubmit: () => void;
}

const languageOptions = [
  { value: "en" },
  { value: "zh" },
  { value: "ja" },
  { value: "ko" },
];

const statusOptions = [
  { value: "raw" },
  { value: "analyzed" },
  { value: "translated" },
];

export function ArticleFormBody({ initialData, error, onError, onSubmit }: ArticleFormBodyProps) {
  const isEdit = !!initialData;
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [status, setStatus] = useState("raw");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit && initialData) {
      setTitle(initialData.title || "");
      setSummary(initialData.summary || "");
      setContent(initialData.content || "");
      setStatus(initialData.status || "raw");
      setLanguage(initialData.language || "en");
      setSourceId("");
    } else {
      setTitle("");
      setSummary("");
      setContent("");
      setSourceId("");
      setStatus("raw");
      setLanguage("en");
    }
    onError(null);
  }, [isEdit, initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);

    try {
      const body = { title, summary: summary || null, content: content || null, language, status };
      if (isEdit && initialData?.id) {
        await api.put(`/api/v1/articles/${initialData.id}`, body);
      } else {
        if (!sourceId) { onError("Source ID is required"); setLoading(false); return; }
        await api.post("/api/v1/articles", { ...body, source_id: sourceId });
      }
      onSubmit();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save article");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Article title" required />
      <Input label="Source ID (UUID)" value={sourceId} onChange={(e) => setSourceId(e.target.value)} placeholder={isEdit ? "Not required for edits" : "UUID of the source"} required={!isEdit} />
      <Input label="Summary" value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Brief summary" />
      <Textarea rows={4} placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} />
      <div className="grid grid-cols-2 gap-4">
        <Select label="Language" value={language} onChange={(e) => setLanguage(e.target.value)} options={languageOptions} />
        <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value)} options={statusOptions} />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onError(null)}>Cancel</Button>
        <Button type="submit" disabled={loading || !title || !sourceId}>
          {loading ? "Saving..." : isEdit ? "Update" : "Create"}
        </Button>
      </div>
    </form>
  );
}
