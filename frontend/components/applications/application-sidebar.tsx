import { FileClock, MessageSquareText, PencilLine, UserRoundCog } from "lucide-react";

import { ApplicationActivity } from "@/components/applications/application-activity";
import { ApplicationNotes } from "@/components/applications/application-notes";
import { ApplicationStatusControl } from "@/components/applications/application-status-control";
import { FitScore } from "@/components/shared/fit-score-badge";
import {
  ProcessingStateBadge,
  evaluationStateLabel,
} from "@/components/shared/processing-state-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationDetail } from "@/lib/graphql/applications";
import { formatDate } from "@/lib/graphql/jobs";

export function ApplicationSidebar({
  application,
  onApplicationUpdated,
}: {
  application: ApplicationDetail;
  onApplicationUpdated: () => Promise<unknown> | void;
}) {
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
            <ProcessingStateBadge
              state={application.evaluationProcessingState}
              label={evaluationStateLabel(application.evaluationProcessingState)}
            />
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
        <CardContent>
          <ApplicationStatusControl
            applicationId={application.id}
            jobId={application.job.id}
            currentStatus={application.status}
            onStatusUpdated={onApplicationUpdated}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <MessageSquareText className="size-4 text-muted-foreground" />
          <CardTitle>Recruiter notes</CardTitle>
        </CardHeader>
        <CardContent>
          <ApplicationNotes
            applicationId={application.id}
            notes={application.notes}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <FileClock className="size-4 text-muted-foreground" />
          <CardTitle>Application activity</CardTitle>
        </CardHeader>
        <CardContent>
          <ApplicationActivity application={application} />
        </CardContent>
      </Card>
    </aside>
  );
}
