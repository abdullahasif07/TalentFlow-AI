"use client";

import { Check, LoaderCircle, RefreshCw, Save } from "lucide-react";
import { useState } from "react";

import { OutreachConfirmationDialog } from "@/components/applications/outreach/outreach-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { OutreachEmail } from "@/lib/graphql/outreach";

const instructionSuggestions = [
  "Make it shorter",
  "More formal",
  "Focus on AI experience",
];

export function OutreachDraftEditor({
  email,
  busyAction,
  onSave,
  onRegenerate,
  onApprove,
}: {
  email: OutreachEmail;
  busyAction: string | null;
  onSave: (subject: string, body: string) => Promise<boolean>;
  onRegenerate: (instruction: string | null) => Promise<boolean>;
  onApprove: (subject: string, body: string, hasUnsavedChanges: boolean) => Promise<boolean>;
}) {
  const [subject, setSubject] = useState(email.subject);
  const [body, setBody] = useState(email.body);
  const [instruction, setInstruction] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirmRegeneration, setConfirmRegeneration] = useState(false);
  const dirty = subject !== email.subject || body !== email.body;
  const busy = busyAction !== null;

  function validateDraft() {
    if (!subject.trim()) {
      setLocalError("Add a subject before saving or approving this draft.");
      return false;
    }
    if (!body.trim()) {
      setLocalError("Add an email body before saving or approving this draft.");
      return false;
    }
    setLocalError(null);
    return true;
  }

  async function regenerate() {
    setConfirmRegeneration(false);
    const regenerated = await onRegenerate(instruction.trim() || null);
    if (regenerated) setInstruction("");
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4">
        <div>
          <label htmlFor={`outreach-subject-${email.id}`} className="text-sm font-semibold">
            Subject
          </label>
          <Input
            id={`outreach-subject-${email.id}`}
            value={subject}
            maxLength={500}
            disabled={busy}
            onChange={(event) => {
              setSubject(event.target.value);
              setLocalError(null);
            }}
            className="mt-1.5"
          />
        </div>
        <div>
          <div className="flex items-center justify-between gap-3">
            <label htmlFor={`outreach-body-${email.id}`} className="text-sm font-semibold">
              Email body
            </label>
            <span className="text-[11px] text-muted-foreground">
              {body.length}/10,000
            </span>
          </div>
          <textarea
            id={`outreach-body-${email.id}`}
            value={body}
            maxLength={10_000}
            disabled={busy}
            onChange={(event) => {
              setBody(event.target.value);
              setLocalError(null);
            }}
            rows={12}
            className="mt-1.5 min-h-64 w-full resize-y rounded-xl border border-input bg-card px-3.5 py-3 text-sm leading-7 outline-none transition-shadow placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/15 disabled:cursor-not-allowed disabled:opacity-60"
          />
        </div>
      </div>

      {localError ? (
        <p className="text-sm text-rose-700" role="alert">
          {localError}
        </p>
      ) : null}

      <div className="rounded-xl border bg-muted/25 p-4">
        <label htmlFor={`regenerate-instruction-${email.id}`} className="text-sm font-semibold">
          Regeneration instruction
        </label>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Optional. Regeneration replaces this current draft after confirmation.
        </p>
        <Input
          id={`regenerate-instruction-${email.id}`}
          value={instruction}
          maxLength={500}
          disabled={busy}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder="Make it shorter"
          className="mt-3"
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {instructionSuggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setInstruction(suggestion)}
              disabled={busy}
              className="rounded-full border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground outline-none transition-colors hover:border-primary/30 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/20 disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            variant="outline"
            disabled={busy || !dirty}
            onClick={() => {
              if (validateDraft()) void onSave(subject.trim(), body.trim());
            }}
          >
            {busyAction === "save" ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Save />
            )}
            {busyAction === "save" ? "Saving…" : "Save draft"}
          </Button>
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => {
              if (dirty) setConfirmRegeneration(true);
              else void regenerate();
            }}
          >
            {busyAction === "generate" ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <RefreshCw />
            )}
            {busyAction === "generate" ? "Regenerating…" : "Regenerate"}
          </Button>
        </div>
        <Button
          disabled={busy}
          onClick={() => {
            if (validateDraft()) void onApprove(subject.trim(), body.trim(), dirty);
          }}
        >
          {busyAction === "approve" ? (
            <LoaderCircle className="animate-spin" />
          ) : (
            <Check />
          )}
          {busyAction === "approve" ? "Approving…" : "Approve draft"}
        </Button>
      </div>

      <OutreachConfirmationDialog
        open={confirmRegeneration}
        title="Replace unsaved edits?"
        description="Regenerating will replace this draft. Your unsaved subject and body changes will be lost."
        confirmLabel="Replace and regenerate"
        destructive
        loading={busyAction === "generate"}
        onCancel={() => setConfirmRegeneration(false)}
        onConfirm={() => void regenerate()}
      />
    </div>
  );
}
