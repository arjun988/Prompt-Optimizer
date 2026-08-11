"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  DollarSign,
  FlaskConical,
  FileStack,
  Layers,
  LayoutDashboard,
  Minimize2,
  ScanSearch,
  Settings,
  Sparkles,
  Terminal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/types";

const ICONS = {
  LayoutDashboard,
  ScanSearch,
  FlaskConical,
  FileStack,
  Sparkles,
  Minimize2,
  BarChart3,
  Layers,
  DollarSign,
  Settings,
} as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background">
          <Terminal className="h-4 w-4 text-foreground" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-tight text-foreground">
            OpenPrompt
          </p>
          <p className="truncate text-[10px] uppercase tracking-widest text-muted-foreground">
            Dashboard
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon];
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-active font-medium text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-active hover:text-foreground",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-foreground" : "text-muted-foreground group-hover:text-foreground",
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Connects to the OpenPrompt REST API. Start the backend with{" "}
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-[10px] text-foreground">
            openprompt serve
          </code>
        </p>
      </div>
    </aside>
  );
}
