import { FileClock, MessageSquareText, PencilLine, Plus, UserRoundCog } from "lucide-react";

import { FitScore } from "@/components/shared/fit-score-badge";
import { ProcessingStateBadge } from "@/components/shared/processing-state-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationDetail } from "@/lib/graphql/applications";
import { formatDate } from "@/lib/graphql/jobs";

export function ApplicationSidebar({ application }: { application: ApplicationDetail }) {
  return (
    <aside className="space-y-5">
      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <div className="rounded-lg bg-muted p-2 text-muted-foreground">
            <UserRoundCog className="size-4.5" />
          </div>
          <CardTitle>Application status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-muted-foreground">Current stage</span>
            <StatusBadge status={application.status} />
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-muted-foreground">Fit score</span>
            <FitScore
              score={application.fitScore}
              processingState={application.evaluationProcessingState}
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-muted-foreground">AI evaluation</span>
            <ProcessingStateBadge state={application.evaluationProcessingState} />
          </div>
          <div className="border-t pt-4">
            <p className="text-xs text-muted-foreground">Applied {formatDate(application.appliedAt)}</p>
            <p className="mt-1 text-xs text-muted-foreground">Updated {formatDate(application.updatedAt)}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <PencilLine className="size-4 text-muted-foreground" />
          <CardTitle>Recruiter actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Button className="w-full" disabled title="Application actions are planned for Day 5">
            Update status
          </Button>
          <Button className="w-full" variant="outline" disabled title="Recruiter notes are planned for Day 5">
            <Plus /> Add note
          </Button>
          <p className="pt-1 text-center text-[11px] leading-4 text-muted-foreground">
            Application actions will be enabled in the next workflow step.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <FileClock className="size-4 text-muted-foreground" />
          <CardTitle>Status history</CardTitle>
        </CardHeader>
        <CardContent>
          {application.statusHistory.length ? (
            <div className="space-y-0 border-l-2 pl-4">
              {application.statusHistory.map((history) => (
                <div key={history.id} className="relative pb-5 last:pb-0">
                  <span className="absolute -left-[21px] top-1 size-2.5 rounded-full border-2 border-primary bg-card" />
                  <StatusBadge status={history.newStatus} />
                  <p className="mt-2 break-words text-xs text-muted-foreground">
                    {history.previousStatus
                      ? `Moved from ${history.previousStatus.replaceAll("_", " ").toLowerCase()}`
                      : "Application submitted"}
                  </p>
                  <p className="mt-1 break-words text-[11px] text-muted-foreground">
                    {formatDate(history.createdAt)} · {history.changedBy}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No status changes have been recorded.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <MessageSquareText className="size-4 text-muted-foreground" />
          <CardTitle>Recruiter notes</CardTitle>
        </CardHeader>
        <CardContent>
          {application.notes.length ? (
            <div className="space-y-3">
              {application.notes.map((note) => (
                <article key={note.id} className="rounded-lg border bg-muted/20 p-3.5">
                  <p className="break-words text-sm leading-6 text-foreground">{note.content}</p>
                  <div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
                    <span className="truncate">{note.recruiter?.name || "Recruiter"}</span>
                    <span className="shrink-0">{formatDate(note.createdAt)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-4 text-center">
              <p className="text-sm font-medium">No recruiter notes</p>
              <p className="mt-1 text-xs text-muted-foreground">Notes added to this application will appear here.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </aside>
  );
}
