import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  OPEN: "border-emerald-200 bg-emerald-50 text-emerald-700",
  DRAFT: "border-slate-200 bg-slate-50 text-slate-600",
  CLOSED: "border-rose-200 bg-rose-50 text-rose-700",
  APPLIED: "border-sky-200 bg-sky-50 text-sky-700",
  SHORTLISTED: "border-violet-200 bg-violet-50 text-violet-700",
  INTERVIEW: "border-amber-200 bg-amber-50 text-amber-700",
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
