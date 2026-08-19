"use client";

import { useMutation } from "@apollo/client/react";
import { CheckCircle2, LoaderCircle, MessageSquarePlus, Send } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  ADD_APPLICATION_NOTE,
  GET_APPLICATION_DETAIL,
  type AddApplicationNoteData,
  type ApplicationDetailQueryData,
  type ApplicationNote,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { formatDateTime } from "@/lib/graphql/jobs";

const MAX_NOTE_LENGTH = 5_000;

interface ApplicationNotesProps {
  applicationId: string;
  notes: ApplicationNote[];
}

export function ApplicationNotes({
  applicationId,
  notes,
}: ApplicationNotesProps) {
  const [content, setContent] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [addNote, { loading }] = useMutation<
    AddApplicationNoteData,
    { input: { applicationId: string; content: string } }
  >(ADD_APPLICATION_NOTE);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 4_000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedContent = content.trim();
    if (!normalizedContent) {
      setActionError("Enter a note before submitting.");
      return;
    }

    setActionError(null);
    setSuccessMessage(null);

    try {
      const result = await addNote({
        variables: {
          input: { applicationId, content: normalizedContent },
        },
        update(cache, mutationResult) {
          const payload = mutationResult.data?.addApplicationNote;
          if (!payload?.success || !payload.note) return;
          const newNote = payload.note;

          cache.updateQuery<ApplicationDetailQueryData>(
            {
              query: GET_APPLICATION_DETAIL,
              variables: { input: { id: applicationId } },
            },
            (cached) => {
              if (!cached?.application.application) return cached;
              const existingNotes = cached.application.application.notes;
              if (existingNotes.some((note) => note.id === newNote.id)) {
                return cached;
              }
              return {
                ...cached,
                application: {
                  ...cached.application,
                  application: {
                    ...cached.application.application,
                    notes: [...existingNotes, newNote],
                  },
                },
              };
            },
          );
        },
      });
      const payload = result.data?.addApplicationNote;

      if (!payload?.success || !payload.note) {
        setActionError(payload?.errors[0]?.message ?? "The note could not be added.");
        return;
      }

      setContent("");
      setSuccessMessage("Note added.");
    } catch (error) {
      setActionError(graphQLErrorMessage(error, "The note could not be added."));
    }
  }

  const newestNotes = [...notes].sort(
    (first, second) =>
      new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime(),
  );
  const remainingCharacters = MAX_NOTE_LENGTH - content.length;

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-2.5">
        <label htmlFor="recruiter-note" className="sr-only">
          Add recruiter note
        </label>
        <textarea
          id="recruiter-note"
          value={content}
          onChange={(event) => {
            setContent(event.target.value);
            setActionError(null);
          }}
          rows={3}
          maxLength={MAX_NOTE_LENGTH}
          disabled={loading}
          placeholder="Add private context for the recruiting team…"
          className="min-h-24 w-full resize-y rounded-lg border border-input bg-card px-3 py-2.5 text-sm leading-6 outline-none transition-shadow placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/15 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-3">
          <span
            className={
              remainingCharacters < 250
                ? "text-[11px] text-amber-700"
                : "text-[11px] text-muted-foreground"
            }
          >
            {remainingCharacters.toLocaleString()} characters remaining
          </span>
          <Button size="sm" type="submit" disabled={loading || !content.trim()}>
            {loading ? <LoaderCircle className="animate-spin" /> : <Send />}
            {loading ? "Adding…" : "Add Note"}
          </Button>
        </div>
        {successMessage ? (
          <p role="status" className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
            <CheckCircle2 className="size-3.5" /> {successMessage}
          </p>
        ) : null}
        {actionError ? (
          <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs font-medium leading-5 text-rose-800">
            {actionError}
          </p>
        ) : null}
      </form>

      <div className="border-t pt-4">
        {newestNotes.length ? (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {newestNotes.map((note) => (
              <article key={note.id} className="rounded-lg border bg-muted/20 p-3.5">
                <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">
                  {note.content}
                </p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                  <span className="min-w-0 truncate font-medium">
                    {note.recruiter?.name || "Recruiter"}
                  </span>
                  <time className="shrink-0" dateTime={note.createdAt}>
                    {formatDateTime(note.createdAt)}
                  </time>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-4 text-center">
            <MessageSquarePlus className="mx-auto size-5 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">No recruiter notes</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Add the first note to share context with the recruiting team.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
