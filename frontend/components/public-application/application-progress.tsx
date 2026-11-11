"use client";

import { useQuery } from "@apollo/client/react";
import { Check, CheckCircle2, CircleAlert, LoaderCircle } from "lucide-react";
import { useEffect } from "react";

import {
  type ApplicationProgressStage,
  GET_PUBLIC_APPLICATION_STATUS,
  type PublicApplicationStatusData,
} from "@/lib/graphql/public-jobs";
import type { PublicApplicationReceipt } from "@/lib/public-application-submission";
import { cn } from "@/lib/utils";

const STEPS: Array<{ stage: ApplicationProgressStage; label: string }> = [
  { stage: "RECEIVED", label: "Application received" },
  { stage: "READING_RESUME", label: "Reading your resume" },
  { stage: "SCORING", label: "Matching against the role" },
  { stage: "COMPLETE", label: "Sent to the hiring team" },
];
const STEP_INDEX: Record<ApplicationProgressStage, number> = {
  RECEIVED: 0,
  READING_RESUME: 1,
  SCORING: 2,
  COMPLETE: 3,
  NEEDS_MANUAL_REVIEW: 3,
};
const POLL_INTERVAL_MS = 2_500;
// Stop polling after a few minutes; the worker may not be running locally.
const MAX_POLL_MS = 4 * 60 * 1_000;

export function ApplicationProgress({ receipt }: { receipt: PublicApplicationReceipt }) {
  const { data, startPolling, stopPolling } = useQuery<PublicApplicationStatusData>(
    GET_PUBLIC_APPLICATION_STATUS,
    {
      variables: { input: { token: receipt.statusToken } },
      fetchPolicy: "network-only",
      notifyOnNetworkStatusChange: false,
    },
  );
  const progress = data?.publicApplicationStatus.progress ?? null;
  const finished = progress?.finished ?? false;

  useEffect(() => {
    if (finished) return;
    startPolling(POLL_INTERVAL_MS);
    const timeout = window.setTimeout(stopPolling, MAX_POLL_MS);
    return () => {
      window.clearTimeout(timeout);
      stopPolling();
    };
  }, [finished, startPolling, stopPolling]);

  const stage = progress?.stage ?? "RECEIVED";
  const activeIndex = STEP_INDEX[stage];
  const needsReview = stage === "NEEDS_MANUAL_REVIEW";

  return (
    <div className="flex min-h-[520px] flex-col items-center justify-center px-5 py-12 text-center sm:px-10">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
        <CheckCircle2 className="size-7" aria-hidden="true" />
      </span>
      <h2 className="mt-5 text-2xl font-semibold tracking-tight">Application submitted</h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
        Thanks, {receipt.candidateName}. Your application for{" "}
        <span className="font-semibold text-foreground">{receipt.jobTitle}</span> is in.
      </p>

      <ol className="mt-8 w-full max-w-sm space-y-3 text-left" aria-label="Application progress">
        {STEPS.map((step, index) => {
          const done = index < activeIndex || (index === activeIndex && finished);
          const active = index === activeIndex && !finished;
          return (
            <li key={step.stage} className="flex items-center gap-3">
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs",
                  done && "border-emerald-200 bg-emerald-50 text-emerald-700",
                  active && "border-primary/30 bg-[#eef7f4] text-primary",
                  !done && !active && "text-muted-foreground",
                )}
              >
                {done ? (
                  <Check className="size-3.5" aria-hidden="true" />
                ) : active ? (
                  <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "text-sm",
                  done || active ? "font-medium text-foreground" : "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>

      <p
        className={cn(
          "mt-6 flex max-w-md items-start gap-2 text-left text-xs leading-5",
          needsReview ? "text-amber-800" : "text-muted-foreground",
        )}
        aria-live="polite"
      >
        {needsReview ? <CircleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" /> : null}
        {progress?.message ?? receipt.processingMessage}
      </p>
      <p className="mt-6 text-xs text-muted-foreground">
        Reference: application #{receipt.id}. You can close this page at any time.
      </p>
    </div>
  );
}
