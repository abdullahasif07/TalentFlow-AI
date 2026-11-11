"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";

import { initials, useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/button";

const routeTitles: Record<string, { title: string; eyebrow: string }> = {
  "/dashboard": { title: "Dashboard", eyebrow: "Recruiting overview" },
  "/jobs": { title: "Jobs", eyebrow: "Open roles & hiring progress" },
  "/pipeline": { title: "Pipeline", eyebrow: "Hiring stages" },
  "/jobs/new": { title: "Create job", eyebrow: "Jobs / New role" },
};

function getRouteTitle(pathname: string) {
  if (routeTitles[pathname]) return routeTitles[pathname];
  if (/^\/jobs\/[^/]+\/compare$/.test(pathname)) {
    return { title: "Candidate comparison", eyebrow: "Jobs / Applicants / Compare" };
  }
  if (/^\/jobs\/[^/]+\/applications\/[^/]+$/.test(pathname)) {
    return { title: "Application details", eyebrow: "Jobs / Applicants / Application" };
  }
  if (pathname.startsWith("/jobs/")) {
    return { title: "Job details", eyebrow: "Jobs / Role overview" };
  }
  return routeTitles[pathname] ?? { title: "TalentFlow AI", eyebrow: "Recruiting workspace" };
}

export function TopHeader({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const pathname = usePathname();
  const route = getRouteTitle(pathname);
  const { recruiter } = useSession();

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
          <span
            className="flex size-8 items-center justify-center rounded-full bg-[#dbe9e6] text-xs font-bold text-[#205f57]"
            title={recruiter ? `${recruiter.name} · ${recruiter.email}` : undefined}
          >
            {initials(recruiter?.name ?? "")}
          </span>
        </div>
      </div>
    </header>
  );
}
