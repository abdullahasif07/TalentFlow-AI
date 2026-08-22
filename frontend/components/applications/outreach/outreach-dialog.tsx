"use client";

import { AlertTriangle, MailCheck, X } from "lucide-react";

import { Button } from "@/components/ui/button";

export function OutreachConfirmationDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = false,
  loading = false,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-[1px]"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !loading) onCancel();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="outreach-dialog-title"
        className="w-full max-w-md rounded-2xl border bg-card p-5 shadow-2xl sm:p-6"
      >
        <div className="flex items-start gap-3">
          <span
            className={
              destructive
                ? "rounded-xl bg-rose-50 p-2.5 text-rose-600"
                : "rounded-xl bg-[#e8f3f0] p-2.5 text-primary"
            }
          >
            {destructive ? (
              <AlertTriangle className="size-5" aria-hidden="true" />
            ) : (
              <MailCheck className="size-5" aria-hidden="true" />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <h3 id="outreach-dialog-title" className="font-semibold">
              {title}
            </h3>
            <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
              {description}
            </p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/20 disabled:opacity-50"
            aria-label="Close confirmation"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
