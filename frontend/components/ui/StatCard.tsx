import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: string;
  variant?: "default" | "success" | "warning" | "danger";
}

const variants: Record<string, string> = {
  default: "border-l-blue-500",
  success: "border-l-green-500",
  warning: "border-l-amber-500",
  danger: "border-l-red-500",
};

export function StatCard({ title, value, icon, trend, variant = "default" }: StatCardProps) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 border-l-4 ${variants[variant]}`}>
      <div className="px-5 py-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
          {icon && <span className="text-slate-400">{icon}</span>}
        </div>
        <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
        {trend && <p className="mt-1 text-xs text-slate-400">{trend}</p>}
      </div>
    </div>
  );
}
