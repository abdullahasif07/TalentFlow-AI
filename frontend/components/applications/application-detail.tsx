"use client";

import { useQuery } from "@apollo/client/react";
import { ArrowLeft, CalendarDays, FileText } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { ApplicationSidebar } from "@/components/applications/application-sidebar";
import { CandidateInformation } from "@/components/applications/candidate-information";
import { EvaluationPreview } from "@/components/applications/evaluation-preview";
import { ResumeOverview } from "@/components/applications/resume-overview";
import { ErrorState } from "@/components/shared/error-state";
import { FitScore } from "@/components/shared/fit-score-badge";
import {
  ProcessingStateBadge,
  evaluationStateLabel,
} from "@/components/shared/processing-state-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GET_APPLICATION_DETAIL,
  type ApplicationDetailQueryData,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { formatDate } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

export function ApplicationDetailPage({
  jobId,
  applicationId,
}: {
  jobId: string;
  applicationId: string;
}) {
  const { data, loading, error, refetch, startPolling, stopPolling } =
    useQuery<ApplicationDetailQueryData>(
      GET_APPLICATION_DETAIL,
      {
        variables: { input: { id: applicationId } },
        fetchPolicy: "cache-and-network",
      },
    );
  const evaluationProcessingState =
    data?.application.application?.evaluationProcessingState;

  useEffect(() => {
    if (evaluationProcessingState === "PROCESSING") {
      startPolling(4_000);
    } else {
      stopPolling();
    }

    return () => stopPolling();
  }, [evaluationProcessingState, startPolling, stopPolling]);

  const backLink = (
    <Link
      href={`/jobs/${jobId}`}
      className={cn(
        buttonVariants({ variant: "ghost", size: "sm" }),
        "-ml-3 text-muted-foreground",
      )}
    >
      <ArrowLeft /> Back to applicants
    </Link>
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        {backLink}
        <div className="flex items-start gap-4" aria-busy="true" aria-label="Loading application">
          <Skeleton className="size-13 shrink-0 rounded-xl" />
          <div className="min-w-0 flex-1 space-y-2.5">
            <Skeleton className="h-8 w-64 max-w-full" />
            <Skeleton className="h-4 w-52 max-w-full" />
            <Skeleton className="h-6 w-36" />
          </div>
          <Skeleton className="hidden h-8 w-20 sm:block" />
        </div>
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-6">
            <Card className="p-5">
              <Skeleton className="h-5 w-44" />
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {Array.from({ length: 5 }, (_, index) => (
                  <Skeleton key={index} className="h-16 w-full" />
                ))}
              </div>
            </Card>
            <Card className="p-5">
              <Skeleton className="h-5 w-28" />
              <Skeleton className="mt-5 h-32 w-full" />
              <Skeleton className="mt-4 h-24 w-full" />
            </Card>
          </div>
          <div className="space-y-5">
            {Array.from({ length: 3 }, (_, index) => (
              <Card key={index} className="p-5">
                <Skeleton className="h-5 w-36" />
                <Skeleton className="mt-5 h-24 w-full" />
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState description={graphQLErrorMessage(error)} onRetry={() => void refetch()} />
      </div>
    );
  }

  const result = data?.application;
  const application = result?.application;

  if (!result?.success || !application) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState
          title="Application not found"
          description={result?.errors[0]?.message ?? "This application may no longer exist."}
        />
      </div>
    );
  }

  if (application.job.id !== jobId) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState
          title="Application does not belong to this job"
          description="Return to the applicant list and select an application from this role."
        />
      </div>
    );
  }

  const initials = application.candidate.name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <div className="space-y-7">
      {backLink}

      <header className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <div className="flex size-13 shrink-0 items-center justify-center rounded-xl bg-[#dbe9e6] text-sm font-bold text-[#205f57]">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="break-words text-2xl font-semibold tracking-tight sm:text-3xl">
                {application.candidate.name}
              </h2>
              <StatusBadge status={application.status} />
            </div>
            <p className="mt-1 text-sm font-medium text-muted-foreground">
              Application for <span className="text-foreground">{application.job.title}</span>
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="size-3.5" /> Applied {formatDate(application.appliedAt)}
              </span>
              <ProcessingStateBadge
                state={application.evaluationProcessingState}
                label={`AI: ${evaluationStateLabel(application.evaluationProcessingState)}`}
              />
            </div>
          </div>
        </div>
        <FitScore
          score={application.fitScore}
          processingState={application.evaluationProcessingState}
          className="text-sm"
        />
      </header>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <main className="min-w-0 space-y-6">
          <CandidateInformation candidate={application.candidate} />

          {application.coverLetter ? (
            <Card>
              <CardHeader className="flex-row items-center gap-3">
                <div className="rounded-lg bg-muted p-2 text-muted-foreground">
                  <FileText className="size-4.5" />
                </div>
                <CardTitle>Cover letter</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-line break-words text-sm leading-7 text-muted-foreground">
                  {application.coverLetter}
                </p>
              </CardContent>
            </Card>
          ) : null}

          <ResumeOverview
            resume={application.resume}
            fallbackFileUrl={application.resumeUrl}
          />
          <EvaluationPreview
            application={application}
            onEvaluationQueued={() => refetch()}
          />
        </main>

        <ApplicationSidebar
          application={application}
          onApplicationUpdated={() => refetch()}
        />
      </div>
    </div>
  );
}
