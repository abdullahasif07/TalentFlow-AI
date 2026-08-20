"use client";

import { useDroppable } from "@dnd-kit/core";

import { PipelineCard } from "@/components/pipeline/pipeline-card";
import type {
  ApplicantListItem,
  ApplicationStatus,
} from "@/lib/graphql/applications";
import { formatApplicationStatus } from "@/lib/graphql/applications";
import { cn } from "@/lib/utils";

interface PipelineColumnProps {
  status: ApplicationStatus;
  applications: ApplicantListItem[];
  jobId: string;
  pendingIds: Set<string>;
  draggable?: boolean;
}

export function PipelineColumn({
  status,
  applications,
  jobId,
  pendingIds,
  draggable = true,
}: PipelineColumnProps) {
  const { isOver, setNodeRef } = useDroppable({ id: status });

  return (
    <section
      ref={setNodeRef}
      aria-label={`${formatApplicationStatus(status)} applications`}
      className={cn(
        "flex w-[310px] shrink-0 flex-col rounded-2xl border bg-muted/25 transition-colors",
        isOver && "border-primary/40 bg-primary/[0.04]",
      )}
    >
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3.5">
        <h3 className="text-xs font-bold uppercase tracking-[0.08em] text-foreground">
          {formatApplicationStatus(status)}
        </h3>
        <span className="inline-flex min-w-6 items-center justify-center rounded-full border bg-card px-1.5 py-0.5 text-[11px] font-bold text-muted-foreground">
          {applications.length}
        </span>
      </header>

      <div className="min-h-40 flex-1 space-y-3 p-3">
        {applications.length ? (
          applications.map((application) => (
            <PipelineCard
              key={application.id}
              application={application}
              jobId={jobId}
              pending={pendingIds.has(application.id)}
              draggable={draggable}
            />
          ))
        ) : (
          <div
            className={cn(
              "flex min-h-28 items-center justify-center rounded-xl border border-dashed bg-card/50 px-4 text-center text-xs leading-5 text-muted-foreground",
              isOver && "border-primary/40 bg-card text-primary",
            )}
          >
            {isOver ? "Drop candidate here" : "No candidates in this stage"}
          </div>
        )}
      </div>
    </section>
  );
}
