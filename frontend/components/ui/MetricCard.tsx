"use client";

import type { ReactNode } from "react";

interface MetricCardProps {
  title: string;
  value: number;
  icon: ReactNode;
  href: string;
  color: "blue" | "green" | "amber" | "violet";
}

const colorMap: Record<MetricCardProps["color"], { bg: string; text: string; darkBg: string; darkText: string }> = {
  blue: { bg: "bg-blue-100", text: "text-blue-700", darkBg: "dark:bg-blue-900/30", darkText: "dark:text-blue-400" },
  green: { bg: "bg-green-100", text: "text-green-700", darkBg: "dark:bg-green-900/30", darkText: "dark:text-green-400" },
  amber: { bg: "bg-amber-100", text: "text-amber-700", darkBg: "dark:bg-amber-900/30", darkText: "dark:text-amber-400" },
  violet: { bg: "bg-violet-100", text: "text-violet-700", darkBg: "dark:bg-violet-900/30", darkText: "dark:text-violet-400" },
};

export function MetricCard({ title, value, icon, href, color }: MetricCardProps) {
  const c = colorMap[color];

  return (
    <a href={href} className="group relative rounded-xl border border-slate-200 bg-white shadow-sm hover:shadow-md hover:-translate-y-0.5 dark:border-slate-700 dark:bg-slate-900 transition-all duration-150 ease-out active:scale-[0.98]">
      <div className="px-5 py-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
          <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg ${c.bg} ${c.text} ${c.darkBg} ${c.darkText} transition-transform duration-150 ease-out group-hover:scale-105`}>
            {icon}
          </span>
        </div>
        <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{value}</p>
      </div>
    </a>
  );
}
