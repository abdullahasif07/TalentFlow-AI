"use client";

import { FlaskConical } from "lucide-react";

import { useSession } from "@/components/providers/session-provider";

export function DemoBanner() {
  const { recruiter } = useSession();
  if (!recruiter?.isDemo) return null;
  return (
    <div className="flex items-center justify-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
      <FlaskConical className="size-3.5 shrink-0" aria-hidden="true" />
      <p>
        <span className="font-semibold">Demo mode</span> - fictional sample data that resets
        nightly. AI usage is capped per day, so some AI actions may pause.
      </p>
    </div>
  );
}
