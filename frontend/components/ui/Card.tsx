import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  subtitle?: string;
  footer?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Card({ title, subtitle, footer, className = "", children }: CardProps) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 ${className}`}>
      {(title || subtitle) && (
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          {title && <h3 className="font-semibold text-slate-900 dark:text-slate-100">{title}</h3>}
          {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
          {footer}
        </div>
      )}
    </div>
  );
}
