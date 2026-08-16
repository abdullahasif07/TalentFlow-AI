"use client";

import { useQuery } from "@apollo/client/react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarCheck2,
  CircleCheckBig,
  Clock3,
  Plus,
  Trophy,
  UserCheck,
  Users,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { SectionHeader } from "@/components/shared/section-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GET_RECENT_APPLICATIONS,
  type RecentApplicationsQueryData,
} from "@/lib/graphql/applications";
import { GET_JOBS, type JobsQueryData, formatDate } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

function RecentActivity({ jobId, jobTitle }: { jobId: string; jobTitle: string }) {
  const { data, loading, error, refetch } = useQuery<RecentApplicationsQueryData>(
    GET_RECENT_APPLICATIONS,
    {
      variables: {
        input: {
          jobId,
          sort: "NEWEST",
          pagination: { limit: 5, offset: 0 },
        },
      },
      fetchPolicy: "cache-and-network",
    },
  );

  if (loading && !data) {
    return (
      <Card className="space-y-4 p-5" aria-busy="true" aria-label="Loading recent applications">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="flex items-center gap-3">
            <Skeleton className="size-9 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3.5 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </Card>
    );
  }

  if (error || (data && !data.applications.success)) {
    return (
      <ErrorState
        title="Recent activity is unavailable"
        description={error?.message ?? data?.applications.errors[0]?.message}
        onRetry={() => void refetch()}
      />
    );
  }

  const applications = data?.applications.items ?? [];

  if (!applications.length) {
    return (
      <EmptyState
        icon={Clock3}
        title="No recent applications"
        description={`Applications for ${jobTitle} will appear here as candidates apply.`}
      />
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="divide-y">
        {applications.map((application) => (
          <Link
            key={application.id}
            href={`/jobs/${application.job.id}`}
            className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-muted/40 sm:px-5"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#e8f3f0] text-xs font-bold text-primary">
              {application.candidate.name
                .split(" ")
                .slice(0, 2)
                .map((part) => part[0])
                .join("")
                .toUpperCase()}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">
                {application.candidate.name}
              </span>
              <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                Applied to {application.job.title}
              </span>
            </span>
            <StatusBadge status={application.status} className="hidden sm:inline-flex" />
            <span className="shrink-0 text-right text-xs text-muted-foreground">
              {formatDate(application.appliedAt)}
            </span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

export function DashboardOverview() {
  const { data, loading, error, refetch } = useQuery<JobsQueryData>(GET_JOBS, {
    variables: { input: null },
    fetchPolicy: "cache-and-network",
  });

  if (loading && !data) return <LoadingState cards={5} />;
  if (error) return <ErrorState description={error.message} onRetry={() => void refetch()} />;
  if (data && !data.jobs.success) {
    return <ErrorState description={data.jobs.errors[0]?.message} onRetry={() => void refetch()} />;
  }

  const jobs = data?.jobs.items ?? [];
  const activeJobs = jobs.filter((job) => job.status === "OPEN");
  const applicants = jobs.reduce((sum, job) => sum + job.applicantCount, 0);
  const shortlisted = jobs.reduce((sum, job) => sum + job.shortlistedCount, 0);
  const interviews = jobs.reduce((sum, job) => sum + job.interviewCount, 0);
  const hired = jobs.reduce((sum, job) => sum + job.hiredCount, 0);
  const recentActiveJobs = activeJobs.slice(0, 6);
  const activityJob =
    activeJobs.find((job) => job.applicantCount > 0) ??
    jobs.find((job) => job.applicantCount > 0) ??
    activeJobs[0] ??
    jobs[0];

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Recruitment Overview
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Monitor active roles and candidate progress across your hiring pipeline.
            </p>
          </div>
          <Button disabled title="Job creation will be available soon">
            <Plus /> Create Job
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <StatCard
            label="Active Jobs"
            value={activeJobs.length}
            detail={`${jobs.length} total roles`}
            icon={BriefcaseBusiness}
          />
          <StatCard
            label="Total Applicants"
            value={applicants}
            detail="Across all roles"
            icon={Users}
          />
          <StatCard
            label="Shortlisted"
            value={shortlisted}
            detail="Selected for review"
            icon={UserCheck}
          />
          <StatCard
            label="Interviews"
            value={interviews}
            detail="Currently interviewing"
            icon={CalendarCheck2}
          />
          <StatCard
            label="Hired"
            value={hired}
            detail="Successful hires"
            icon={Trophy}
          />
        </div>
      </section>

      {!jobs.length ? (
        <EmptyState
          icon={BriefcaseBusiness}
          title="No jobs yet"
          description="Once your first role is created, hiring statistics and activity will appear here."
        />
      ) : (
        <>
          <section>
            <SectionHeader
              title="Active Jobs"
              description="Open positions and their current hiring progress."
              action={
                <Link
                  href="/jobs"
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "sm" }),
                    "text-primary",
                  )}
                >
                  View all jobs <ArrowRight />
                </Link>
              }
              className="mb-4"
            />

            {recentActiveJobs.length ? (
              <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[940px] text-left">
                    <thead className="border-b bg-muted/55 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      <tr>
                        <th className="px-5 py-3.5">Role</th>
                        <th className="px-4 py-3.5">Status</th>
                        <th className="px-4 py-3.5 text-center">Applicants</th>
                        <th className="px-4 py-3.5 text-center">Recommended</th>
                        <th className="px-4 py-3.5 text-center">Shortlisted</th>
                        <th className="px-4 py-3.5 text-center">Interviews</th>
                        <th className="px-5 py-3.5">Created</th>
                        <th className="px-5 py-3.5"><span className="sr-only">Open</span></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {recentActiveJobs.map((job) => (
                        <tr key={job.id} className="transition-colors hover:bg-muted/35">
                          <td className="px-5 py-4">
                            <Link
                              href={`/jobs/${job.id}`}
                              className="font-semibold text-foreground hover:text-primary"
                            >
                              {job.title}
                            </Link>
                          </td>
                          <td className="px-4 py-4"><StatusBadge status={job.status} /></td>
                          <td className="px-4 py-4 text-center text-sm font-semibold">{job.applicantCount}</td>
                          <td className="px-4 py-4 text-center text-sm font-semibold">{job.recommendedCandidateCount}</td>
                          <td className="px-4 py-4 text-center text-sm font-semibold">{job.shortlistedCount}</td>
                          <td className="px-4 py-4 text-center text-sm font-semibold">{job.interviewCount}</td>
                          <td className="px-5 py-4 text-sm text-muted-foreground">{formatDate(job.createdAt)}</td>
                          <td className="px-5 py-4 text-right">
                            <Link
                              href={`/jobs/${job.id}`}
                              className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                              aria-label={`Open ${job.title}`}
                            >
                              <ArrowRight className="size-4" />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <EmptyState
                icon={CircleCheckBig}
                title="No active jobs"
                description="Your existing roles are currently draft or closed."
              />
            )}
          </section>

          {activityJob ? (
            <section>
              <SectionHeader
                title="Recent Activity"
                description={`Latest applications for ${activityJob.title}.`}
                className="mb-4"
              />
              <RecentActivity jobId={activityJob.id} jobTitle={activityJob.title} />
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
