"use client";

import { useState, useCallback } from "react";
import { Sidebar } from "@/components/layout/Sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapse = useCallback(() => {
    setSidebarCollapsed((c) => !c);
  }, []);

  const sidebarWidth = sidebarCollapsed ? 64 : 240;

  return (
    <div className="flex h-screen bg-[var(--background)]">
      {/* Mobile hamburger trigger */}
      <button
        type="button"
        className="fixed top-3 left-3 z-50 flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition-colors hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 md:hidden dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
        </svg>
      </button>

      {/* Desktop collapse toggle — positioned inline with sidebar edge */}
      <button
        type="button"
        className={`hidden top-3 z-40 flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 shadow-sm transition-all duration-200 ease-out hover:bg-slate-50 hover:text-slate-600 focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 md:flex md:absolute`}
        style={{ left: `calc(${sidebarWidth}px + 8px)` }}
        onClick={toggleCollapse}
        aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <svg
          className={`w-4 h-4 transition-transform duration-200 ease-out ${sidebarCollapsed ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
      </button>

      <Sidebar collapsed={sidebarCollapsed} onToggleCollapse={toggleCollapse} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto" style={{ marginLeft: `${sidebarWidth}px` }}>
        <div className="p-4 sm:p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
