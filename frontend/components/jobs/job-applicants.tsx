"use client";

import { useQuery } from "@apollo/client/react";
import {
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  UserRoundSearch,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { FitScore } from "@/components/shared/fit-score-badge";
import {
  ProcessingStateBadge,
  evaluationStateLabel,
} from "@/components/shared/processing-state-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  APPLICATION_STATUSES,
  GET_JOB_APPLICATIONS,
  type ApplicationSort,
  type JobApplicationsQueryData,
  formatApplicationStatus,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { formatDate } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

function ApplicantsLoading() {
  return (
    <Card className="space-y-4 p-5" aria-busy="true" aria-label="Loading applicants">
      {Array.from({ length: 6 }, (_, index) => (
        <div key={index} className="flex items-center gap-4">
          <Skeleton className="size-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-56" />
          </div>
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-16" />
        </div>
      ))}
    </Card>
  );
}

export function JobApplicants({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState("ALL");
  const [sort, setSort] = useState<ApplicationSort>("NEWEST");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
      setOffset(0);
    }, 300);

    return () => window.clearTimeout(timeout);
  }, [search]);

  const { data, loading, error, refetch } = useQuery<JobApplicationsQueryData>(
    GET_JOB_APPLICATIONS,
    {
      variables: {
        input: {
          jobId,
          filters: {
            status: status === "ALL" ? null : status,
            candidateSearch: debouncedSearch || null,
          },
          sort,
          pagination: { limit: PAGE_SIZE, offset },
        },
      },
      fetchPolicy: "cache-and-network",
    },
  );

  const clearControls = () => {
    setSearch("");
    setDebouncedSearch("");
    setStatus("ALL");
    setSort("NEWEST");
    setOffset(0);
  };

  if (loading && !data) return <ApplicantsLoading />;
  if (error) {
    return <ErrorState description={graphQLErrorMessage(error)} onRetry={() => void refetch()} />;
  }
  if (data && !data.applications.success) {
    return (
      <ErrorState
        description={data.applications.errors[0]?.message}
        onRetry={() => void refetch()}
      />
    );
  }

  const result = data?.applications;
  const applications = result?.items ?? [];
  const pageInfo = result?.pageInfo;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil((result?.totalCount ?? 0) / PAGE_SIZE));
  const controlsActive = Boolean(search || status !== "ALL" || sort !== "NEWEST");

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-card p-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="relative w-full xl:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-9"
              placeholder="Search candidate name or email…"
              aria-label="Search applicants"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-48">
              <select
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setOffset(0);
                }}
                className="h-10 w-full appearance-none rounded-lg border border-input bg-card px-3 pr-9 text-sm font-medium outline-none focus:border-primary focus:ring-2 focus:ring-ring/15"
                aria-label="Filter applicants by status"
              >
                <option value="ALL">All statuses</option>
                {APPLICATION_STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {formatApplicationStatus(value)}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>

            <div className="relative min-w-48">
              <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <select
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value as ApplicationSort);
                  setOffset(0);
                }}
                className="h-10 w-full appearance-none rounded-lg border border-input bg-card pl-9 pr-9 text-sm font-medium outline-none focus:border-primary focus:ring-2 focus:ring-ring/15"
                aria-label="Sort applicants"
              >
                <option value="NEWEST">Newest first</option>
                <option value="OLDEST">Oldest first</option>
                <option value="FIT_SCORE_DESC">Fit score: high to low</option>
                <option value="FIT_SCORE_ASC">Fit score: low to high</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>
        </div>
      </div>

      {!applications.length ? (
        <EmptyState
          icon={UserRoundSearch}
          title={controlsActive ? "No matching applicants" : "No applicants yet"}
          description={
            controlsActive
              ? "Try changing the search, status, or sorting controls."
              : "Applications will appear here as candidates apply to this role."
          }
          action={
            controlsActive ? (
              <Button variant="outline" onClick={clearControls}>Clear controls</Button>
            ) : undefined
          }
        />
      ) : (
        <Card className={cn("overflow-hidden", loading && "opacity-70")}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left" aria-busy={loading}>
              <thead className="border-b bg-muted/55 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-3.5">Candidate</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Fit score</th>
                  <th className="px-4 py-3.5">Applied</th>
                  <th className="px-4 py-3.5">AI evaluation</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {applications.map((application) => {
                  const detailUrl = `/jobs/${jobId}/applications/${application.id}`;

                  return (
                    <tr
                      key={application.id}
                      role="link"
                      tabIndex={0}
                      onClick={() => router.push(detailUrl)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") router.push(detailUrl);
                      }}
                      className="cursor-pointer transition-colors hover:bg-muted/35 focus:bg-muted/35 focus:outline-none"
                    >
                      <td className="px-5 py-4">
                        <Link
                          href={detailUrl}
                          onClick={(event) => event.stopPropagation()}
                          className="font-semibold hover:text-primary"
                        >
                          {application.candidate.name}
                        </Link>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {application.candidate.email}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge status={application.status} />
                      </td>
                      <td className="px-4 py-4">
                        <FitScore
                          score={application.fitScore}
                          processingState={application.evaluationProcessingState}
                        />
                      </td>
                      <td className="px-4 py-4 text-sm text-muted-foreground">
                        {formatDate(application.appliedAt)}
                      </td>
                      <td className="px-4 py-4">
                        <ProcessingStateBadge
                          state={application.evaluationProcessingState}
                          label={evaluationStateLabel(application.evaluationProcessingState)}
                        />
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link
                          href={detailUrl}
                          onClick={(event) => event.stopPropagation()}
                          className={buttonVariants({ variant: "outline", size: "sm" })}
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-3 border-t px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              Showing {offset + 1}–{Math.min(offset + applications.length, result?.totalCount ?? 0)} of {result?.totalCount ?? 0} applicants
            </p>
            <div className="flex items-center gap-2">
              <span className="mr-2 text-xs font-medium text-muted-foreground">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                size="icon"
                variant="outline"
                className="size-8"
                disabled={!pageInfo?.hasPreviousPage || loading}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                aria-label="Previous page"
              >
                <ChevronLeft />
              </Button>
              <Button
                size="icon"
                variant="outline"
                className="size-8"
                disabled={!pageInfo?.hasNextPage || loading}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                aria-label="Next page"
              >
                <ChevronRight />
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
