"use client";

import { DataTable } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { Task } from "@/types";

interface TasksPanelProps {
  tasks: Task[];
  onNew: () => void;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
}

export function TasksPanel({ tasks, onNew, onEdit, onDelete }: TasksPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Tasks</h2>
        <Button onClick={onNew}>New Task</Button>
      </div>
      {tasks.length === 0 ? (
        <Card title="No tasks yet">
          <p className="text-sm text-slate-500">Create a task or wait for the agent to generate one.</p>
        </Card>
      ) : (
        <DataTable
          columns={[
            { key: "title", label: "Task" },
            { key: "priority", label: "Priority" },
            { key: "status", label: "Status" },
          ]}
          data={tasks}
          rowKey="id"
          renderCell={(key: string, value: unknown, row: unknown) => {
            if (key === "priority" || key === "status") {
              const colors: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
                low: "muted", medium: "default", high: "warning", urgent: "danger",
                todo: "muted", in_progress: "default", done: "success", blocked: "danger", pending: "muted",
              };
              return <Badge variant={colors[value as string] || "default"}>{String(value)}</Badge>;
            }
            if (key === "actions") {
              const r = row as Record<string, unknown>;
              return (
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => onEdit(r as unknown as Task)}>Edit</Button>
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
