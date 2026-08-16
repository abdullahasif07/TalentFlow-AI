import { cn } from "@/lib/utils";

export function FitScoreBadge({ score, className }: { score: number | null; className?: string }) {
  const color = score === null
    ? "bg-slate-100 text-slate-500"
    : score >= 80
      ? "bg-emerald-100 text-emerald-700"
      : score >= 60
        ? "bg-amber-100 text-amber-700"
        : "bg-rose-100 text-rose-700";

  return (
    <span className={cn("inline-flex min-w-12 items-center justify-center rounded-full px-2.5 py-1 text-xs font-bold", color, className)}>
      {score === null ? "N/A" : `${Math.round(score)}%`}
    </span>
  );
}
