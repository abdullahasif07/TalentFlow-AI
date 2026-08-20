"use client";

import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery } from "@apollo/client/react";
import {
  ArchiveX,
  CheckCircle2,
  ChevronDown,
  Columns3,
  FilterX,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PipelineCard } from "@/components/pipeline/pipeline-card";
import { PipelineColumn } from "@/components/pipeline/pipeline-column";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GET_JOB_APPLICATIONS,
  UPDATE_APPLICATION_STATUS,
  formatApplicationStatus,
  type ApplicantListItem,
  type ApplicationStatus,
  type JobApplicationsQueryData,
  type UpdateApplicationStatusData,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { GET_JOBS, type JobsQueryData } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

const PIPELINE_STATUSES: ApplicationStatus[] = [
  "APPLIED",
  "AI_REVIEWED",
  "HUMAN_REVIEW",
  "SHORTLISTED",
  "CONTACTED",
  "REPLIED",
  "INTERVIEW",
  "OFFER",
  "HIRED",
];
const CURRENT_RECRUITER = "Alex Morgan";
const PIPELINE_PAGE_SIZE = 100;

type EvaluationFilter = "ALL" | "EVALUATED" | "NOT_EVALUATED";
type BoardView = "ACTIVE" | "REJECTED";

interface PipelineQueryVariables {
  input: {
    jobId: string;
    filters: {
      candidateSearch: string | null;
      minimumFitScore: number | null;
    };
    sort: "NEWEST";
    pagination: {
      limit: number;
      offset: number;
    };
  };
}

interface StatusMutationVariables {
  input: {
    applicationId: string;
    status: ApplicationStatus;
    changedBy: string;
    automated: false;
  };
}

function PipelineLoading() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading hiring pipeline">
      <div className="flex items-end justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-80 max-w-full" />
        </div>
        <Skeleton className="h-10 w-64" />
      </div>
      <Skeleton className="h-16 w-full rounded-xl" />
      <div className="flex gap-4 overflow-hidden">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-[460px] w-[310px] shrink-0 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

function PipelineColumnsLoading() {
  return (
    <div
      className="flex gap-4 overflow-hidden pb-4"
      aria-busy="true"
      aria-label="Loading candidates"
    >
      {Array.from({ length: 4 }, (_, index) => (
        <Skeleton key={index} className="h-[460px] w-[310px] shrink-0 rounded-2xl" />
      ))}
    </div>
  );
}

function isPipelineStatus(value: string): value is ApplicationStatus {
  return PIPELINE_STATUSES.includes(value as ApplicationStatus);
}

export function HiringPipelineBoard() {
  const [requestedJobId, setRequestedJobId] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [minimumScore, setMinimumScore] = useState("");
  const [evaluationFilter, setEvaluationFilter] = useState<EvaluationFilter>("ALL");
  const [boardView, setBoardView] = useState<BoardView>("ACTIVE");
  const [statusOverrides, setStatusOverrides] = useState<
    Record<string, ApplicationStatus>
  >({});
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [activeApplicationId, setActiveApplicationId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor),
  );

  const jobsQuery = useQuery<JobsQueryData>(GET_JOBS, {
    variables: { input: null },
    fetchPolicy: "cache-and-network",
  });
  const jobs = useMemo(() => {
    const items = [...(jobsQuery.data?.jobs.items ?? [])];
    return items.sort((first, second) => {
      if (first.status === "OPEN" && second.status !== "OPEN") return -1;
      if (first.status !== "OPEN" && second.status === "OPEN") return 1;
      return new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime();
    });
  }, [jobsQuery.data?.jobs.items]);
  const selectedJobId = jobs.some((job) => job.id === requestedJobId)
    ? requestedJobId
    : (jobs.find((job) => job.status === "OPEN")?.id ?? jobs[0]?.id ?? "");

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 3_500);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  const parsedMinimumScore = minimumScore === "" ? null : Number(minimumScore);
  const queryVariables = useMemo<PipelineQueryVariables>(
    () => ({
      input: {
        jobId: selectedJobId,
        filters: {
          candidateSearch: debouncedSearch || null,
          minimumFitScore:
            parsedMinimumScore !== null && Number.isFinite(parsedMinimumScore)
              ? parsedMinimumScore
              : null,
        },
        sort: "NEWEST",
        pagination: { limit: PIPELINE_PAGE_SIZE, offset: 0 },
      },
    }),
    [debouncedSearch, parsedMinimumScore, selectedJobId],
  );
  const applicationsQuery = useQuery<
    JobApplicationsQueryData,
    PipelineQueryVariables
  >(GET_JOB_APPLICATIONS, {
    variables: queryVariables,
    skip: !selectedJobId,
    fetchPolicy: "cache-and-network",
  });
  const applicationResult = applicationsQuery.data?.applications;
  const [updateStatus] = useMutation<
    UpdateApplicationStatusData,
    StatusMutationVariables
  >(UPDATE_APPLICATION_STATUS);

  const applications = useMemo(() => {
    const items = (applicationsQuery.data?.applications.items ?? []).map(
      (application) => ({
        ...application,
        status: statusOverrides[application.id] ?? application.status,
      }),
    );
    if (evaluationFilter === "EVALUATED") {
      return items.filter(
        (application) => application.evaluationProcessingState === "COMPLETED",
      );
    }
    if (evaluationFilter === "NOT_EVALUATED") {
      return items.filter(
        (application) => application.evaluationProcessingState !== "COMPLETED",
      );
    }
    return items;
  }, [applicationsQuery.data?.applications.items, evaluationFilter, statusOverrides]);

  const activeApplication = applications.find(
    (application) => application.id === activeApplicationId,
  );
  const rejectedApplications = applications.filter(
    (application) => application.status === "REJECTED",
  );
  const pipelineApplications = applications.filter(
    (application) => application.status !== "REJECTED",
  );
  const selectedJob = jobs.find((job) => job.id === selectedJobId);
  const filtersActive = Boolean(
    search || minimumScore || evaluationFilter !== "ALL",
  );
  const filteredNoResults = Boolean(
    applicationResult?.totalCount && !applications.length && filtersActive,
  );

  function clearFilters() {
    setSearch("");
    setDebouncedSearch("");
    setMinimumScore("");
    setEvaluationFilter("ALL");
  }

  function handleDragStart(event: DragStartEvent) {
    setActiveApplicationId(String(event.active.id));
    setActionError(null);
  }

  async function handleDragEnd(event: DragEndEvent) {
    setActiveApplicationId(null);
    const applicationId = String(event.active.id);
    const destination = event.over ? String(event.over.id) : "";
    const application = applications.find((item) => item.id === applicationId);
    if (!application || !isPipelineStatus(destination)) return;

    const previousStatus = application.status;
    if (previousStatus === destination || pendingIds.has(applicationId)) return;

    setStatusOverrides((current) => ({ ...current, [applicationId]: destination }));
    setPendingIds((current) => new Set(current).add(applicationId));
    setActionError(null);
    setSuccessMessage(null);

    try {
      const result = await updateStatus({
        variables: {
          input: {
            applicationId,
            status: destination,
            changedBy: CURRENT_RECRUITER,
            automated: false,
          },
        },
        optimisticResponse: {
          updateApplicationStatus: {
            success: true,
            application: {
              id: applicationId,
              status: destination,
              updatedAt: new Date().toISOString(),
            },
            errors: [],
          },
        },
        update(cache, mutationResult) {
          const payload = mutationResult.data?.updateApplicationStatus;
          if (!payload?.success || !payload.application) return;
          const updatedStatus = payload.application.status;

          cache.updateQuery<JobApplicationsQueryData, PipelineQueryVariables>(
            { query: GET_JOB_APPLICATIONS, variables: queryVariables },
            (cached) => {
              if (!cached) return cached;
              return {
                ...cached,
                applications: {
                  ...cached.applications,
                  items: cached.applications.items.map((item) =>
                    item.id === applicationId
                      ? { ...item, status: updatedStatus }
                      : item,
                  ),
                },
              };
            },
          );

          for (const typename of ["ApplicationListItemType", "ApplicationDetailType"]) {
            const cacheId = cache.identify({ __typename: typename, id: applicationId });
            if (cacheId) {
              cache.modify({
                id: cacheId,
                fields: { status: () => updatedStatus },
              });
            }
          }

          const jobCacheId = cache.identify({ __typename: "JobType", id: selectedJobId });
          if (jobCacheId) {
            const countDelta = (status: ApplicationStatus) =>
              Number(updatedStatus === status) - Number(previousStatus === status);
            cache.modify({
              id: jobCacheId,
              fields: {
                shortlistedCount(existing: number = 0) {
                  return Math.max(0, existing + countDelta("SHORTLISTED"));
                },
                contactedCount(existing: number = 0) {
                  return Math.max(0, existing + countDelta("CONTACTED"));
                },
                interviewCount(existing: number = 0) {
                  return Math.max(0, existing + countDelta("INTERVIEW"));
                },
                hiredCount(existing: number = 0) {
                  return Math.max(0, existing + countDelta("HIRED"));
                },
              },
            });
          }
          cache.evict({ id: "ROOT_QUERY", fieldName: "application" });
          cache.evict({ id: "ROOT_QUERY", fieldName: "recommendedCandidates" });
        },
      });
      const payload = result.data?.updateApplicationStatus;
      if (!payload?.success || !payload.application) {
        throw new Error(
          payload?.errors[0]?.message ?? "The application could not be moved.",
        );
      }

      setStatusOverrides((current) => {
        const next = { ...current };
        delete next[applicationId];
        return next;
      });
      setSuccessMessage(
        `${application.candidate.name} moved to ${formatApplicationStatus(destination)}.`,
      );
    } catch (error) {
      setStatusOverrides((current) => {
        const next = { ...current };
        delete next[applicationId];
        return next;
      });
      setActionError(
        graphQLErrorMessage(error, "The application could not be moved. Try again."),
      );
    } finally {
      setPendingIds((current) => {
        const next = new Set(current);
        next.delete(applicationId);
        return next;
      });
    }
  }

  if (jobsQuery.loading && !jobsQuery.data) return <PipelineLoading />;
  if (jobsQuery.error) {
    return (
      <ErrorState
        title="Jobs could not be loaded"
        description={graphQLErrorMessage(jobsQuery.error)}
        onRetry={() => void jobsQuery.refetch()}
      />
    );
  }
  if (jobsQuery.data && !jobsQuery.data.jobs.success) {
    return (
      <ErrorState
        title="Jobs could not be loaded"
        description={jobsQuery.data.jobs.errors[0]?.message}
        onRetry={() => void jobsQuery.refetch()}
      />
    );
  }
  if (!jobs.length) {
    return (
      <EmptyState
        icon={Columns3}
        title="No jobs available"
        description="Create a job before organizing candidates in the hiring pipeline."
      />
    );
  }

  const applicationsFailed = applicationResult && !applicationResult.success;
  const initialApplicationsLoading = applicationsQuery.loading && !applicationsQuery.data;

  return (
    <div className="min-w-0 space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Pipeline</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Move applicants through each stage while keeping every decision recruiter-controlled.
          </p>
        </div>

        <div className="w-full lg:w-80">
          <label
            htmlFor="pipeline-job"
            className="mb-1.5 block text-xs font-semibold text-muted-foreground"
          >
            Hiring pipeline for
          </label>
          <div className="relative">
            <select
              id="pipeline-job"
              value={selectedJobId}
              onChange={(event) => {
                setRequestedJobId(event.target.value);
                setStatusOverrides({});
                setPendingIds(new Set());
                setActionError(null);
                setSuccessMessage(null);
                setActiveApplicationId(null);
              }}
              className="h-10 w-full appearance-none rounded-lg border border-input bg-card px-3 pr-9 text-sm font-semibold outline-none transition-shadow focus:border-primary focus:ring-2 focus:ring-ring/15"
            >
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}{job.status === "OPEN" ? "" : ` · ${job.status.toLowerCase()}`}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          </div>
        </div>
      </header>

      <Card className="p-3 shadow-[0_1px_2px_rgba(23,32,51,0.03)]">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="relative w-full xl:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-9"
              placeholder="Search candidate name or email…"
              aria-label="Search pipeline candidates"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="relative sm:w-40">
              <Input
                type="number"
                min="0"
                max="100"
                value={minimumScore}
                onChange={(event) => {
                  const value = event.target.value;
                  if (value === "" || (Number(value) >= 0 && Number(value) <= 100)) {
                    setMinimumScore(value);
                  }
                }}
                className="pl-9"
                placeholder="Min fit score"
                aria-label="Minimum fit score"
              />
              <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>

            <div className="relative sm:w-44">
              <select
                value={evaluationFilter}
                onChange={(event) =>
                  setEvaluationFilter(event.target.value as EvaluationFilter)
                }
                className="h-10 w-full appearance-none rounded-lg border border-input bg-card px-3 pr-9 text-sm font-medium outline-none focus:border-primary focus:ring-2 focus:ring-ring/15"
                aria-label="Filter by evaluation state"
              >
                <option value="ALL">All evaluations</option>
                <option value="EVALUATED">Evaluated</option>
                <option value="NOT_EVALUATED">Not evaluated</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>

            {filtersActive ? (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <FilterX /> Clear filters
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="inline-flex w-fit rounded-lg border bg-card p-1" aria-label="Pipeline view">
          <button
            type="button"
            onClick={() => setBoardView("ACTIVE")}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/20",
              boardView === "ACTIVE"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Active pipeline
          </button>
          <button
            type="button"
            onClick={() => setBoardView("REJECTED")}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/20",
              boardView === "REJECTED"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Rejected ({rejectedApplications.length})
          </button>
        </div>
        <p className="text-xs text-muted-foreground">
          {selectedJob?.title} · {applicationResult?.totalCount ?? 0} matching applicants
        </p>
      </div>

      {actionError ? (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          {actionError}
        </div>
      ) : null}
      {successMessage ? (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          <CheckCircle2 className="size-4" /> {successMessage}
        </div>
      ) : null}

      {initialApplicationsLoading ? <PipelineColumnsLoading /> : null}
      {!initialApplicationsLoading && (applicationsQuery.error || applicationsFailed) ? (
        <ErrorState
          title="The pipeline could not be loaded"
          description={
            applicationsQuery.error
              ? graphQLErrorMessage(applicationsQuery.error)
              : applicationResult?.errors[0]?.message
          }
          onRetry={() => void applicationsQuery.refetch()}
        />
      ) : null}

      {!initialApplicationsLoading &&
      !applicationsQuery.error &&
      !applicationsFailed &&
      applicationResult?.totalCount === 0 ? (
        <EmptyState
          icon={filtersActive ? FilterX : Columns3}
          title={filtersActive ? "No matching candidates" : "No applicants yet"}
          description={
            filtersActive
              ? "Try changing or clearing the pipeline filters."
              : `Applications for ${selectedJob?.title ?? "this job"} will appear here.`
          }
          action={
            filtersActive ? (
              <Button variant="outline" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      ) : null}

      {!initialApplicationsLoading &&
      !applicationsQuery.error &&
      !applicationsFailed &&
      filteredNoResults ? (
        <EmptyState
          icon={FilterX}
          title="No matching candidates"
          description="Try changing or clearing the evaluation filter."
          action={
            <Button variant="outline" onClick={clearFilters}>
              Clear filters
            </Button>
          }
        />
      ) : null}

      {!initialApplicationsLoading &&
      !applicationsQuery.error &&
      !applicationsFailed &&
      !filteredNoResults &&
      applicationResult &&
      applicationResult.totalCount > 0 ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragCancel={() => setActiveApplicationId(null)}
          onDragEnd={(event) => void handleDragEnd(event)}
        >
          {boardView === "ACTIVE" ? (
            <div
              className="overflow-x-auto pb-4 [scrollbar-color:var(--border)_transparent]"
              aria-label="Hiring pipeline board"
            >
              <div className="flex min-w-max items-stretch gap-4">
                {PIPELINE_STATUSES.map((status) => (
                  <PipelineColumn
                    key={status}
                    status={status}
                    applications={pipelineApplications.filter(
                      (application) => application.status === status,
                    )}
                    jobId={selectedJobId}
                    pendingIds={pendingIds}
                  />
                ))}
              </div>
            </div>
          ) : rejectedApplications.length ? (
            <div className="max-w-[640px]">
              <PipelineColumn
                status="REJECTED"
                applications={rejectedApplications}
                jobId={selectedJobId}
                pendingIds={pendingIds}
                draggable={false}
              />
            </div>
          ) : (
            <EmptyState
              icon={ArchiveX}
              title="No rejected candidates"
              description="Rejected applications for this job will be kept here, separate from the active pipeline."
            />
          )}

          <DragOverlay dropAnimation={null}>
            {activeApplication ? (
              <PipelineCard
                application={activeApplication}
                jobId={selectedJobId}
                overlay
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      ) : null}

      {applicationResult && applicationResult.totalCount > PIPELINE_PAGE_SIZE ? (
        <p className="text-xs text-muted-foreground">
          Showing the first {PIPELINE_PAGE_SIZE} applicants. Refine the filters to manage the
          remaining candidates.
        </p>
      ) : null}
    </div>
  );
}
