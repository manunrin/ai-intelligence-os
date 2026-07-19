import type { ButtonHTMLAttributes, DetailedHTMLProps } from "react";

export interface ButtonProps
  extends DetailedHTMLProps<
    ButtonHTMLAttributes<HTMLButtonElement>,
    HTMLButtonElement
  > {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
}

export function Button({
  children,
  variant = "default",
  size = "md",
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center font-medium rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none active:scale-[0.97] transition-colors duration-150 ease-out";

  const variants: Record<string, string> = {
    default: "bg-blue-600 text-white hover:bg-blue-700/90 dark:bg-blue-500 dark:hover:bg-blue-600 shadow-sm hover:shadow",
    outline: "border border-slate-300 bg-transparent hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800",
    ghost: "hover:bg-slate-100/80 dark:hover:bg-slate-800",
    destructive: "bg-red-600 text-white hover:bg-red-700/90 dark:bg-red-500 dark:hover:bg-red-600 shadow-sm",
  };

  const sizes: Record<string, string> = {
    sm: "text-sm px-3 py-1.5 h-8",
    md: "text-sm px-4 py-2 h-9",
    lg: "text-base px-6 py-3 h-11",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
