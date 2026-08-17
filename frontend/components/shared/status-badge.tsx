import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  OPEN: "border-emerald-200 bg-emerald-50 text-emerald-700",
  DRAFT: "border-slate-200 bg-slate-50 text-slate-600",
  CLOSED: "border-rose-200 bg-rose-50 text-rose-700",
  APPLIED: "border-sky-200 bg-sky-50 text-sky-700",
  AI_REVIEWED: "border-cyan-200 bg-cyan-50 text-cyan-700",
  HUMAN_REVIEW: "border-indigo-200 bg-indigo-50 text-indigo-700",
  SHORTLISTED: "border-violet-200 bg-violet-50 text-violet-700",
  CONTACTED: "border-blue-200 bg-blue-50 text-blue-700",
  REPLIED: "border-teal-200 bg-teal-50 text-teal-700",
  INTERVIEW: "border-amber-200 bg-amber-50 text-amber-700",
  OFFER: "border-lime-200 bg-lime-50 text-lime-700",
  HIRED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  REJECTED: "border-rose-200 bg-rose-50 text-rose-700",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const label = status.replaceAll("_", " ").toLowerCase();

  return (
    <Badge variant="outline" className={cn("capitalize", statusStyles[status], className)}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {label}
    </Badge>
  );
}
