import { FileCheck2, MessageSquareText } from "lucide-react";

import { StatusBadge } from "@/components/shared/status-badge";
import type { ApplicationDetail } from "@/lib/graphql/applications";
import { formatApplicationStatus } from "@/lib/graphql/applications";
import { formatDateTime } from "@/lib/graphql/jobs";

interface ActivityEvent {
  id: string;
  type: "STATUS" | "NOTE";
  title: string;
  description: string | null;
  actor: string | null;
  createdAt: string;
  status?: string;
}

export function ApplicationActivity({ application }: { application: ApplicationDetail }) {
  const statusEvents: ActivityEvent[] = application.statusHistory.map((history) => ({
    id: `status-${history.id}`,
    type: "STATUS",
    title: history.previousStatus
      ? `Moved to ${formatApplicationStatus(history.newStatus)}`
      : "Application submitted",
    description: history.previousStatus
      ? `Previous stage: ${formatApplicationStatus(history.previousStatus)}`
      : null,
    actor: history.changedBy || null,
    createdAt: history.createdAt,
    status: history.newStatus,
  }));

  if (!application.statusHistory.some((history) => history.previousStatus === null)) {
    statusEvents.push({
      id: `application-${application.id}`,
      type: "STATUS",
      title: "Application submitted",
      description: null,
      actor: application.candidate.email,
      createdAt: application.appliedAt,
      status: "APPLIED",
    });
  }

  const noteEvents: ActivityEvent[] = application.notes.map((note) => ({
    id: `note-${note.id}`,
    type: "NOTE",
    title: "Recruiter note added",
    description: note.content,
    actor: note.recruiter?.name || null,
    createdAt: note.createdAt,
  }));

  const events = [...statusEvents, ...noteEvents].sort(
    (first, second) =>
      new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime(),
  );

  if (!events.length) {
    return (
      <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        No application activity has been recorded.
      </p>
    );
  }

  return (
    <div className="space-y-0 border-l-2 pl-4">
      {events.map((event) => (
        <article key={event.id} className="relative pb-5 last:pb-0">
          <span className="absolute -left-[22px] top-1 flex size-3 items-center justify-center rounded-full border-2 border-primary bg-card" />
          <div className="flex min-w-0 items-start gap-2.5">
            <div className="mt-0.5 rounded-md bg-muted p-1.5 text-muted-foreground">
              {event.type === "NOTE" ? (
                <MessageSquareText className="size-3.5" />
              ) : (
                <FileCheck2 className="size-3.5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="break-words text-xs font-semibold leading-5">{event.title}</p>
                {event.status ? <StatusBadge status={event.status} className="px-2 py-0.5 text-[10px]" /> : null}
              </div>
              {event.description ? (
                <p className="mt-1 line-clamp-3 whitespace-pre-line break-words text-xs leading-5 text-muted-foreground">
                  {event.description}
                </p>
              ) : null}
              <p className="mt-1.5 break-words text-[11px] leading-4 text-muted-foreground">
                <time dateTime={event.createdAt}>{formatDateTime(event.createdAt)}</time>
                {event.actor ? ` · ${event.actor}` : ""}
              </p>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
