import { CheckCircle2, CircleX, Clock3, LoaderCircle } from "lucide-react";

import { cn } from "@/lib/utils";

export type ProcessingState = "NOT_STARTED" | "PROCESSING" | "COMPLETED" | "FAILED";

const evaluationStateLabels: Record<ProcessingState, string> = {
  NOT_STARTED: "Not evaluated",
  PROCESSING: "Evaluating",
  COMPLETED: "Evaluated",
  FAILED: "Evaluation failed",
};

export function evaluationStateLabel(state: ProcessingState) {
  return evaluationStateLabels[state];
}

const statePresentation = {
  NOT_STARTED: {
    label: "Not started",
    icon: Clock3,
    className: "border-slate-200 bg-slate-50 text-slate-600",
  },
  PROCESSING: {
    label: "Processing",
    icon: LoaderCircle,
    className: "border-sky-200 bg-sky-50 text-sky-700",
  },
  COMPLETED: {
    label: "Completed",
    icon: CheckCircle2,
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  FAILED: {
    label: "Failed",
    icon: CircleX,
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
} satisfies Record<
  ProcessingState,
  { label: string; icon: typeof Clock3; className: string }
>;

export function ProcessingStateBadge({
  state,
  label,
  className,
}: {
  state: ProcessingState;
  label?: string;
  className?: string;
}) {
  const presentation = statePresentation[state];
  const Icon = presentation.icon;

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        presentation.className,
        className,
      )}
    >
      <Icon
        className={cn("size-3.5", state === "PROCESSING" && "animate-spin")}
        aria-hidden="true"
      />
      {label ?? presentation.label}
    </span>
  );
}
