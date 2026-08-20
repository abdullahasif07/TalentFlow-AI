"use client";

import { useDraggable } from "@dnd-kit/core";
import { GripVertical, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { FitScore } from "@/components/shared/fit-score-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import type { ApplicantListItem } from "@/lib/graphql/applications";
import { formatDate } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

interface PipelineCardProps {
  application: ApplicantListItem;
  jobId: string;
  pending?: boolean;
  overlay?: boolean;
  draggable?: boolean;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function CardContent({
  application,
  pending,
  dragHandle,
}: {
  application: ApplicantListItem;
  pending: boolean;
  dragHandle?: React.ReactNode;
}) {
  const strength = application.evaluation?.strengths[0]?.summary;

  return (
    <>
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#e8f3f0] text-[11px] font-bold text-primary">
          {initials(application.candidate.name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">
            {application.candidate.name}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {application.candidate.email}
          </p>
        </div>
        {dragHandle}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <FitScore
          score={application.fitScore}
          processingState={application.evaluationProcessingState}
          className="px-2 py-0.5 text-[11px]"
        />
        <StatusBadge status={application.status} className="px-2 py-0.5 text-[10px]" />
      </div>

      {strength ? (
        <div className="mt-3 flex items-start gap-1.5 rounded-lg bg-muted/55 px-2.5 py-2 text-xs leading-5 text-muted-foreground">
          <Sparkles className="mt-0.5 size-3 shrink-0 text-primary" aria-hidden="true" />
          <span className="line-clamp-2">{strength}</span>
        </div>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-3 border-t pt-2.5 text-[11px] text-muted-foreground">
        <span>Applied {formatDate(application.appliedAt)}</span>
        {pending ? <span className="font-medium text-primary">Updating…</span> : null}
      </div>
    </>
  );
}

export function PipelineCard({
  application,
  jobId,
  pending = false,
  overlay = false,
  draggable = true,
}: PipelineCardProps) {
  const router = useRouter();
  const detailUrl = `/jobs/${jobId}/applications/${application.id}`;
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: overlay ? `overlay-${application.id}` : application.id,
    disabled: pending || overlay || !draggable,
    data: { application },
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <article
      ref={setNodeRef}
      style={style}
      role="link"
      tabIndex={overlay ? -1 : 0}
      aria-label={`Open ${application.candidate.name}'s application`}
      onClick={() => {
        if (!isDragging && !overlay) router.push(detailUrl);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !overlay) router.push(detailUrl);
      }}
      className={cn(
        "rounded-xl border bg-card p-3.5 shadow-[0_1px_2px_rgba(23,32,51,0.04)] outline-none transition-[border-color,box-shadow,opacity]",
        !overlay && "cursor-pointer hover:border-primary/30 hover:shadow-sm focus-visible:ring-2 focus-visible:ring-ring/20",
        isDragging && "opacity-30",
        pending && "opacity-70",
        overlay && "w-[286px] rotate-1 border-primary/30 shadow-xl",
      )}
    >
      <CardContent
        application={application}
        pending={pending}
        dragHandle={
          !overlay && draggable ? (
            <button
              type="button"
              {...listeners}
              {...attributes}
              onClick={(event) => event.stopPropagation()}
              className="-mr-1 -mt-1 inline-flex size-8 shrink-0 cursor-grab items-center justify-center rounded-lg text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/25 active:cursor-grabbing disabled:cursor-not-allowed"
              aria-label={`Move ${application.candidate.name} to another stage`}
              disabled={pending}
            >
              <GripVertical className="size-4" aria-hidden="true" />
            </button>
          ) : undefined
        }
      />
    </article>
  );
}
