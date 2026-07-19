"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  )},
  { href: "/agents", label: "Agents", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
    </svg>
  )},
  { href: "/knowledge", label: "Knowledge", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  )},
  { href: "/articles", label: "Articles", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  )},
  { href: "/tasks", label: "Tasks", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )},
  { href: "/reports", label: "Reports", icon: (
    <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  )},
];

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ collapsed = false, onToggleCollapse, mobileOpen = false, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobile, setMobile] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  // Track mobile open state
  useEffect(() => {
    setMobile(mobileOpen);
  }, [mobileOpen]);

  const closeMobile = useCallback(() => {
    setMobile(false);
    onMobileClose?.();
  }, [onMobileClose]);

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/" || pathname === "/dashboard";
    return pathname === href;
  };

  const navLinkClass = (href: string) => {
    const active = isActive(href);
    return `group flex items-center gap-3 rounded-lg transition-colors duration-150 ease-out ${
      active
        ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-200"
    }`;
  };

  return (
    <>
      {/* Mobile overlay */}
      {mobile && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-md md:hidden"
          style={{ animation: "fadeIn 200ms ease-out" }}
          onClick={closeMobile}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 left-0 z-50 flex flex-col bg-white dark:bg-slate-900 border-r border-slate-200/80 dark:border-white/[0.06] transition-all duration-200 ease-in-out md:relative md:z-auto ${
          mobile ? "translate-x-0 shadow-xl" : "-translate-x-full md:translate-x-0"
        } ${
          collapsed ? "md:w-[64px]" : "md:w-[240px]"
        }`}
        style={{ height: "100dvh" }}
      >
        {/* Logo / Header */}
        <div className={`flex items-center h-14 border-b border-slate-200/80 dark:border-white/[0.06] ${collapsed ? "justify-center px-2" : "px-4"}`}>
          <svg className="w-7 h-7 text-blue-600 dark:text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
          {!collapsed && (
            <span className="ml-3 text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
              AI Intelligence OS
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <div key={item.href} className="relative">
                <Link
                  href={item.href}
                  className={navLinkClass(item.href)}
                  onClick={closeMobile}
                  onMouseEnter={() => setHoveredItem(item.href)}
                  onMouseLeave={() => setHoveredItem(null)}
                  title={collapsed ? item.label : undefined}
                >
                  <span className={`flex-shrink-0 transition-transform duration-150 ease-out ${active ? "text-blue-600 dark:text-blue-400" : ""}`}>
                    {item.icon}
                  </span>
                  <span className={`transition-opacity duration-150 ${collapsed ? "opacity-0 w-0 overflow-hidden" : "opacity-100"}`}>
                    {item.label}
                  </span>
                </Link>
                {/* Tooltip for collapsed mode */}
                {collapsed && hoveredItem === item.href && (
                  <div
                    className="absolute left-full top-1/2 -translate-y-1/2 ml-2 rounded-md bg-slate-900 px-2.5 py-1 text-xs font-medium text-white shadow-lg whitespace-nowrap z-50"
                    style={{ animation: "fadeIn 150ms ease-out" }}
                  >
                    {item.label}
                  </div>
                )}
                {/* Active indicator — subtle left accent bar */}
                {active && !collapsed && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-blue-500 dark:bg-blue-400" />
                )}
              </div>
            );
          })}
        </nav>

        {/* User section */}
        <div className={`border-t border-slate-200/80 dark:border-white/[0.06] ${collapsed ? "px-2 py-3" : "px-4 py-3"}`}>
          <div className={`flex items-center ${collapsed ? "justify-center" : ""}`}>
            <div className="flex items-center gap-3 w-full">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center ring-1 ring-blue-200/50 dark:ring-blue-800/50">
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-400">
                  {user?.username?.charAt(0).toUpperCase() ?? "U"}
                </span>
              </div>
              {!collapsed && (
                <>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {user?.username}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" onClick={() => { logout(); }}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                    </svg>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
