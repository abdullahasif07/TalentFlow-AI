"use client";

import { Check, Copy, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  publicApplicationPath,
  publicApplicationUrl,
} from "@/lib/application-link";
import { cn } from "@/lib/utils";

type CopyState = "idle" | "copied" | "failed";

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Clipboard unavailable");
}

export function ApplicationLinkActions({ jobId }: { jobId: string }) {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const applicationPath = publicApplicationPath(jobId);

  useEffect(
    () => () => {
      if (resetTimer.current) clearTimeout(resetTimer.current);
    },
    [],
  );

  async function handleCopy() {
    if (resetTimer.current) clearTimeout(resetTimer.current);
    try {
      await copyText(publicApplicationUrl(window.location.origin, jobId));
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    resetTimer.current = setTimeout(() => setCopyState("idle"), 3000);
  }

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <div className="flex flex-wrap gap-2 sm:justify-end">
        <Button type="button" size="sm" variant="outline" onClick={() => void handleCopy()}>
          {copyState === "copied" ? <Check /> : <Copy />}
          Copy application link
        </Button>
        <Link
          href={applicationPath}
          target="_blank"
          rel="noreferrer"
          className={cn(buttonVariants({ size: "sm" }), "no-underline")}
        >
          <ExternalLink /> Open application page
        </Link>
      </div>
      <p
        role={copyState === "failed" ? "alert" : "status"}
        aria-live="polite"
        className={cn(
          "min-h-4 text-xs font-medium",
          copyState === "copied" && "text-emerald-700",
          copyState === "failed" && "text-rose-700",
          copyState === "idle" && "text-muted-foreground",
        )}
      >
        {copyState === "copied"
          ? "Application link copied"
          : copyState === "failed"
            ? "Could not copy the link. Open the page and copy its address."
            : <span aria-hidden="true">&nbsp;</span>}
      </p>
    </div>
  );
}
