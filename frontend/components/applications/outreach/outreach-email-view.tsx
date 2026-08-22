"use client";

import { CheckCircle2, Clock3, LoaderCircle, MailCheck, Send } from "lucide-react";
import { useState } from "react";

import { OutreachConfirmationDialog } from "@/components/applications/outreach/outreach-dialog";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import type { OutreachEmail } from "@/lib/graphql/outreach";
import { formatDateTime } from "@/lib/graphql/jobs";

export function OutreachEmailView({
  email,
  candidateEmail,
  sending,
  onSend,
}: {
  email: OutreachEmail;
  candidateEmail: string;
  sending: boolean;
  onSend: () => Promise<boolean>;
}) {
  const [confirmSend, setConfirmSend] = useState(false);
  const approved = email.status === "APPROVED";
  const sent = email.status === "SENT";
  const hasRecipient = Boolean(candidateEmail.trim());

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-xl border bg-muted/25 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span
            className={
              sent
                ? "rounded-xl bg-emerald-50 p-2.5 text-emerald-700"
                : "rounded-xl bg-blue-50 p-2.5 text-blue-700"
            }
          >
            {sent ? (
              <CheckCircle2 className="size-5" aria-hidden="true" />
            ) : (
              <MailCheck className="size-5" aria-hidden="true" />
            )}
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">
                {sent ? "Email sent" : "Approved and ready to send"}
              </p>
              <StatusBadge status={email.status} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {sent && email.sentAt
                ? `Sent ${formatDateTime(email.sentAt)}`
                : email.approvedAt
                  ? `Approved ${formatDateTime(email.approvedAt)}`
                  : "Approval recorded"}
            </p>
          </div>
        </div>
        {approved ? (
          <Button
            onClick={() => setConfirmSend(true)}
            disabled={sending || !hasRecipient}
          >
            {sending ? <LoaderCircle className="animate-spin" /> : <Send />}
            {sending ? "Sending…" : "Send email"}
          </Button>
        ) : null}
      </div>

      {!hasRecipient && approved ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          This candidate has no email address, so the approved outreach cannot be sent.
        </p>
      ) : null}

      <div className="overflow-hidden rounded-xl border bg-card">
        <div className="border-b bg-muted/30 px-4 py-3 sm:px-5">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
            Subject
          </p>
          <p className="mt-1 break-words text-sm font-semibold">{email.subject}</p>
        </div>
        <div className="px-4 py-4 sm:px-5 sm:py-5">
          <p className="whitespace-pre-wrap break-words text-sm leading-7 text-foreground">
            {email.body}
          </p>
        </div>
      </div>

      {approved ? (
        <div className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
          <Clock3 className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <p>
            Review the exact subject and body above before sending. Delivery is simulated in this
            MVP; the backend will record the message as sent and may move the application to
            Contacted.
          </p>
        </div>
      ) : null}

      <OutreachConfirmationDialog
        open={confirmSend}
        title="Send this outreach?"
        description={`Send this exact email to ${candidateEmail}? This action cannot be undone.`}
        confirmLabel="Send email"
        loading={sending}
        onCancel={() => setConfirmSend(false)}
        onConfirm={() => {
          void onSend().then((success) => {
            if (success) setConfirmSend(false);
          });
        }}
      />
    </div>
  );
}

export function OutreachHistory({ emails }: { emails: OutreachEmail[] }) {
  if (emails.length < 2) return null;

  return (
    <div className="border-t pt-5">
      <h4 className="text-sm font-semibold">Previous outreach</h4>
      <p className="mt-1 text-xs text-muted-foreground">
        Earlier drafts and sent messages for this application.
      </p>
      <div className="mt-3 divide-y rounded-xl border">
        {emails.slice(1).map((email) => (
          <div key={email.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{email.subject}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Generated {formatDateTime(email.generatedAt)}
                {email.approvedAt ? ` · Approved ${formatDateTime(email.approvedAt)}` : ""}
                {email.sentAt ? ` · Sent ${formatDateTime(email.sentAt)}` : ""}
              </p>
            </div>
            <StatusBadge status={email.status} className="w-fit" />
          </div>
        ))}
      </div>
    </div>
  );
}
