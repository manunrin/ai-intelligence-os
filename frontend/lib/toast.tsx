/** Shared toast notification system with polished animations. */

"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastContextValue {
  toast: (message: string, type?: Toast["type"]) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DURATIONS: Record<Toast["type"], number> = {
  success: 3000,
  error: 5000,
  info: 4000,
};

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, DURATIONS[type]);
  }, []);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const icons: Record<string, React.ReactNode> = {
    success: (
      <svg className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
    ),
    info: (
      <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
      </svg>
    ),
  };

  const borderColors: Record<string, string> = {
    success: "border-green-200 dark:border-green-900/50",
    error: "border-red-200 dark:border-red-900/50",
    info: "border-blue-200 dark:border-blue-900/50",
  };

  const bgColors: Record<string, string> = {
    success: "bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-300",
    error: "bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-300",
    info: "bg-blue-50 text-blue-800 dark:bg-blue-950/30 dark:text-blue-300",
  };

  return (
    <div
      className={`pointer-events-auto flex items-center gap-3 rounded-xl border ${borderColors[t.type]} ${bgColors[t.type]} px-4 py-3 shadow-lg min-w-[280px] max-w-sm`}
      style={{ animation: "slideIn 200ms var(--ease-out)" }}
    >
      {icons[t.type]}
      <p className="flex-1 text-sm leading-relaxed">{t.message}</p>
      <button
        onClick={() => onDismiss(t.id)}
        className="flex-shrink-0 p-0.5 rounded-md text-current opacity-50 hover:opacity-100 transition-opacity duration-150"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
