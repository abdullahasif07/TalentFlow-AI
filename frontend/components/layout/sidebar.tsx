"use client";

import {
  BriefcaseBusiness,
  Columns3,
  LayoutDashboard,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigation = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Jobs", href: "/jobs", icon: BriefcaseBusiness },
  { label: "Candidates", href: "/candidates", icon: Users },
  { label: "Pipeline", href: "/pipeline", icon: Columns3 },
  { label: "AI Activity", href: "/ai-activity", icon: Sparkles },
];

interface SidebarProps {
  mobile?: boolean;
  onClose?: () => void;
}

export function Sidebar({ mobile = false, onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "flex h-full w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground",
        !mobile && "fixed inset-y-0 left-0 z-30 hidden lg:flex",
      )}
    >
      <div className="flex h-18 items-center justify-between px-5">
        <Link href="/dashboard" className="flex items-center gap-3" onClick={onClose}>
          <span className="flex size-9 items-center justify-center rounded-xl bg-[#2b8277] text-white shadow-sm">
            <Sparkles className="size-4.5" aria-hidden="true" />
          </span>
          <span>
            <span className="block text-[15px] font-bold tracking-tight text-white">TalentFlow AI</span>
            <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-sidebar-muted">Recruiting OS</span>
          </span>
        </Link>
        {mobile ? (
          <Button
            size="icon"
            variant="ghost"
            className="text-sidebar-muted hover:bg-sidebar-accent hover:text-white"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X />
          </Button>
        ) : null}
      </div>

      <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Main navigation">
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-sidebar-muted">Workspace</p>
        {navigation.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));

          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                "flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-white"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-white",
              )}
            >
              <Icon className={cn("size-[18px]", active ? "text-[#6fc4b6]" : "text-sidebar-muted")} aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <button className="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-sidebar-accent">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#dbe9e6] text-xs font-bold text-[#205f57]">AM</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-white">Alex Morgan</span>
            <span className="block truncate text-xs text-sidebar-muted">Northstar Labs</span>
          </span>
          <span className="text-sidebar-muted" aria-hidden="true">•••</span>
        </button>
      </div>
    </aside>
  );
}
