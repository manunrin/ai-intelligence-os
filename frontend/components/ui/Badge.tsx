interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "muted";
  className?: string;
}

const variants: Record<string, string> = {
  default: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  danger: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  muted: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
