import { AlertCircle, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

export function ActionFeedback({
  variant,
  message,
  action,
  className,
}: {
  variant: "success" | "error";
  message: string;
  action?: React.ReactNode;
  className?: string;
}) {
  const successful = variant === "success";

  return (
    <div
      role={successful ? "status" : "alert"}
      className={cn(
        "flex items-start gap-2 rounded-xl border px-3.5 py-3 text-sm leading-5",
        successful
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-rose-200 bg-rose-50 text-rose-700",
        className,
      )}
    >
      {successful ? (
        <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      ) : (
        <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        <p className="break-words">{message}</p>
        {action ? <div className="mt-2">{action}</div> : null}
      </div>
    </div>
  );
}
