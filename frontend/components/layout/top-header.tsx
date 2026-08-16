"use client";

import { Bell, ChevronDown, Menu, Search } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const routeTitles: Record<string, { title: string; eyebrow: string }> = {
  "/dashboard": { title: "Dashboard", eyebrow: "Recruiting overview" },
  "/jobs": { title: "Jobs", eyebrow: "Open roles & hiring progress" },
  "/candidates": { title: "Candidates", eyebrow: "Talent database" },
  "/pipeline": { title: "Pipeline", eyebrow: "Hiring stages" },
  "/ai-activity": { title: "AI Activity", eyebrow: "Automation workspace" },
};

function getRouteTitle(pathname: string) {
  if (pathname.startsWith("/jobs/")) {
    return { title: "Job details", eyebrow: "Jobs / Role overview" };
  }
  return routeTitles[pathname] ?? { title: "TalentFlow AI", eyebrow: "Recruiting workspace" };
}

export function TopHeader({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const pathname = usePathname();
  const route = getRouteTitle(pathname);

  return (
    <header className="sticky top-0 z-20 flex h-18 items-center border-b bg-card/95 px-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex w-full items-center gap-3">
        <Button
          size="icon"
          variant="ghost"
          className="lg:hidden"
          onClick={onOpenNavigation}
          aria-label="Open navigation"
        >
          <Menu />
        </Button>

        <div className="min-w-0">
          <p className="hidden text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground sm:block">{route.eyebrow}</p>
          <h1 className="truncate text-lg font-semibold tracking-tight sm:text-xl">{route.title}</h1>
        </div>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <div className="relative hidden w-52 md:block xl:w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input className="border-transparent bg-muted pl-9 focus-visible:bg-card" placeholder="Search jobs or candidates…" aria-label="Search" />
          </div>
          <Button size="icon" variant="ghost" className="relative text-muted-foreground" aria-label="Notifications">
            <Bell />
            <span className="absolute right-2 top-2 size-1.5 rounded-full bg-rose-500 ring-2 ring-card" />
          </Button>
          <button className="flex items-center gap-2 rounded-lg p-1 pr-0 outline-none focus-visible:ring-2 focus-visible:ring-ring/30" aria-label="Open recruiter menu">
            <span className="flex size-8 items-center justify-center rounded-full bg-[#dbe9e6] text-xs font-bold text-[#205f57]">AM</span>
            <ChevronDown className="hidden size-4 text-muted-foreground sm:block" aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>
  );
}
