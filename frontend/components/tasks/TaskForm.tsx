/** Task creation/edit form body — renders inside a Modal. */

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import type { Task } from "@/types";
import { api } from "@/lib/api";

interface TaskFormBodyProps {
  initialData?: Task | null;
  error: string | null;
  onError: (err: string | null) => void;
  onSubmit: () => void;
}

export function TaskFormBody({ initialData, error, onError, onSubmit }: TaskFormBodyProps) {
  const isEdit = !!initialData;
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [status, setStatus] = useState("pending");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit && initialData) {
      setTitle(initialData.title || "");
      setDescription(initialData.description || "");
      setPriority(initialData.priority || "medium");
      setStatus(initialData.status || "pending");
    } else {
      setTitle("");
      setDescription("");
      setPriority("medium");
      setStatus("pending");
    }
    onError(null);
  }, [isEdit, initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);

    try {
      const body = { title, description: description || null, priority, status };
      if (isEdit && initialData?.id) {
        await api.put(`/api/v1/tasks/${initialData.id}`, body);
      } else {
        await api.post("/api/v1/tasks", body);
      }
      onSubmit();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Task title" required />
      <textarea
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500"
        rows={3} placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)}
      />
      <div className="grid grid-cols-2 gap-4">
        <select
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          value={priority} onChange={(e) => setPriority(e.target.value)}
        >
          <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option>
        </select>
        <select
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          value={status} onChange={(e) => setStatus(e.target.value)}
        >
          <option value="pending">Pending</option><option value="todo">Todo</option><option value="in_progress">In Progress</option><option value="done">Done</option><option value="blocked">Blocked</option>
        </select>
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => onError(null)}>Cancel</Button>
        <Button type="submit" disabled={loading || !title}>
          {loading ? "Saving..." : isEdit ? "Update" : "Create"}
        </Button>
      </div>
    </form>
  );
}
