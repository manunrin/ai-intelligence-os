"use client";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Task } from "@/types";

interface TasksPanelProps {
  tasks: Task[];
  onNew: () => void;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
}

const PRIORITY_CONFIG: Record<string, { color: "default" | "success" | "warning" | "danger" | "muted"; dot: string }> = {
  low: { color: "muted", dot: "bg-slate-400" },
  medium: { color: "default", dot: "bg-blue-500" },
  high: { color: "warning", dot: "bg-amber-500" },
  urgent: { color: "danger", dot: "bg-red-500" },
};

const STATUS_CONFIG: Record<string, { color: "default" | "success" | "warning" | "danger" | "muted" }> = {
  pending: { color: "muted" },
  todo: { color: "muted" },
  in_progress: { color: "default" },
  done: { color: "success" },
  blocked: { color: "danger" },
};

export function TasksPanel({ tasks, onNew, onEdit, onDelete }: TasksPanelProps) {
  const activeTasks = tasks.filter((t) => t.status !== "done");
  const doneTasks = tasks.filter((t) => t.status === "done");

  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">Tasks</h2>
        <Button onClick={onNew}>New Task</Button>
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          title="No tasks generated yet"
          description="Tasks are created by the Project Manager agent or manually."
          action={<Button size="sm" onClick={onNew}>Create a task</Button>}
        />
      ) : (
        <div className="space-y-4">
          {activeTasks.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Active ({activeTasks.length})
              </h3>
              <div className="space-y-2">
                {activeTasks.map((task) => (
                  <TaskRow key={task.id} task={task} onEdit={onEdit} onDelete={onDelete} />
                ))}
              </div>
            </section>
          )}

          {doneTasks.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Completed ({doneTasks.length})
              </h3>
              <div className="space-y-2">
                {doneTasks.map((task) => (
                  <TaskRow key={task.id} task={task} onEdit={onEdit} onDelete={onDelete} completed />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}

function TaskRow({
  task,
  onEdit,
  onDelete,
  completed = false,
}: {
  task: Task;
  onEdit: (t: Task) => void;
  onDelete: (id: string) => void;
  completed?: boolean;
}) {
  const priority = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium;
  const status = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.todo;

  return (
    <div className={`group flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm transition-all duration-150 ease-out hover:shadow-md dark:border-slate-700 dark:bg-slate-800 ${
      completed ? "opacity-60" : ""
    }`}>
      {/* Priority dot */}
      <div className={`flex-shrink-0 w-2 h-2 rounded-full ${priority.dot}`} />

      {/* Title */}
      <div className="min-w-0 flex-1">
        <p className={`text-sm leading-relaxed ${completed ? "line-through text-slate-400 dark:text-slate-500" : "text-slate-900 dark:text-slate-100"}`}>
          {task.title}
        </p>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <Badge variant={status.color} className="text-[10px] px-1.5 py-0">
          {task.status.replace("_", " ")}
        </Badge>
        <div className="flex gap-0.5 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
          <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => onEdit(task)}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
            </svg>
          </Button>
          <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30" onClick={() => onDelete(task.id)}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </Button>
        </div>
      </div>
    </div>
  );
}
