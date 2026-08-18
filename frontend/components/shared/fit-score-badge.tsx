import { cn } from "@/lib/utils";

type EvaluationState = "NOT_STARTED" | "PROCESSING" | "COMPLETED" | "FAILED";

const stateLabels: Record<Exclude<EvaluationState, "COMPLETED">, string> = {
  NOT_STARTED: "Not evaluated",
  PROCESSING: "Processing",
  FAILED: "Failed",
};

export function FitScore({
  score,
  processingState = "COMPLETED",
  className,
}: {
  score: number | string | null;
  processingState?: EvaluationState;
  className?: string;
}) {
  const numericScore = score === null ? null : Number(score);

  if (numericScore === null || !Number.isFinite(numericScore)) {
    const state = processingState === "COMPLETED" ? "NOT_STARTED" : processingState;
    const stateColor =
      state === "PROCESSING"
        ? "bg-sky-50 text-sky-700"
        : state === "FAILED"
          ? "bg-rose-50 text-rose-700"
          : "bg-slate-100 text-slate-500";

    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
          stateColor,
          className,
        )}
      >
        <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
        {stateLabels[state]}
      </span>
    );
  }

  const color =
    numericScore >= 80
      ? "bg-emerald-100 text-emerald-700"
      : numericScore >= 60
        ? "bg-amber-100 text-amber-700"
        : "bg-rose-100 text-rose-700";

  return (
    <span className={cn("inline-flex min-w-12 items-center justify-center rounded-full px-2.5 py-1 text-xs font-bold", color, className)}>
      {Math.round(numericScore)}%
    </span>
  );
}

export function FitScoreBadge(props: React.ComponentProps<typeof FitScore>) {
  return <FitScore {...props} />;
}
