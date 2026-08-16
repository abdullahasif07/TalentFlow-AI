"use client";

import { useEffect, useState } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { TopHeader } from "@/components/layout/top-header";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const [navigationOpen, setNavigationOpen] = useState(false);

  useEffect(() => {
    if (!navigationOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavigationOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [navigationOpen]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      {navigationOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-slate-950/45 backdrop-blur-[1px]"
            onClick={() => setNavigationOpen(false)}
            aria-label="Close navigation"
          />
          <div className="relative h-full w-64 shadow-2xl">
            <Sidebar mobile onClose={() => setNavigationOpen(false)} />
          </div>
        </div>
      ) : null}
      <div className="min-h-screen lg:pl-64">
        <TopHeader onOpenNavigation={() => setNavigationOpen(true)} />
        {children}
      </div>
    </div>
  );
}
