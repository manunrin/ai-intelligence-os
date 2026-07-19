import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

const DEFAULT_ICONS: Record<string, ReactNode> = {
  default: (
    <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.113H6.622a2.25 2.25 0 01-2.247-2.113L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  ),
};

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 py-12 px-4 text-center dark:border-slate-700 dark:bg-slate-800/30">
      <div className="mb-3 text-slate-300 dark:text-slate-600">
        {icon ?? DEFAULT_ICONS.default}
      </div>
      <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
