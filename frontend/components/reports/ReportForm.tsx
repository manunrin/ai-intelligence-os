/** Report creation form body — renders inside a Modal. */

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

interface ReportFormBodyProps {
  error: string | null;
  onError: (err: string | null) => void;
  onSubmit: () => void;
}

export function ReportFormBody({ error, onError, onSubmit }: ReportFormBodyProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("");
  const [importanceScore, setImportanceScore] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setTitle("");
    setBody("");
    setCategory("");
    setImportanceScore("");
    onError(null);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);

    try {
      const bodyData: Record<string, unknown> = { title, body };
      if (category) bodyData.category = category;
      if (importanceScore) bodyData.importance_score = parseFloat(importanceScore);
      await api.post("/api/v1/reports", bodyData);
      onSubmit();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to create report");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Report title" required />
      <textarea
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500"
        rows={4} placeholder="Report body" value={body} onChange={(e) => setBody(e.target.value)} required
      />
      <div className="grid grid-cols-2 gap-4">
        <Input label="Category" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g., market-analysis" />
        <Input label="Importance Score (0-10)" value={importanceScore} onChange={(e) => setImportanceScore(e.target.value)} placeholder="7" type="number" min={0} max={10} />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onError(null)}>Cancel</Button>
        <Button type="submit" disabled={loading || !title || !body}>
          {loading ? "Creating..." : "Create Report"}
        </Button>
      </div>
    </form>
  );
}
