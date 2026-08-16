"use client";

import { useQuery } from "@apollo/client/react";
import { ArrowLeft, CalendarDays, CheckCircle2, Clock3, Sparkles, UserCheck, Users } from "lucide-react";
import Link from "next/link";

import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GET_JOB, type JobQueryData, formatDate, stringList } from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

export function JobDetail({ jobId }: { jobId: string }) {
  const { data, loading, error, refetch } = useQuery<JobQueryData>(GET_JOB, {
    variables: { input: { id: jobId } },
  });

  if (loading) return <LoadingState />;
  if (error) return <ErrorState description={error.message} onRetry={() => void refetch()} />;
  if (!data?.job.success || !data.job.job) {
    return <ErrorState title="Job not found" description={data?.job.errors[0]?.message ?? "This role may no longer exist."} />;
  }

  const job = data.job.job;
  const requiredSkills = stringList(job.requiredSkills);
  const preferredSkills = stringList(job.preferredSkills);

  return (
    <div className="space-y-6">
      <Link href="/jobs" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3 text-muted-foreground")}>
        <ArrowLeft /> Back to jobs
      </Link>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{job.title}</h2>
            <StatusBadge status={job.status} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-4" />Created {formatDate(job.createdAt)}</span>
            <span className="inline-flex items-center gap-1.5"><Clock3 className="size-4" />Updated {formatDate(job.updatedAt)}</span>
          </div>
        </div>
        <Badge variant="outline" className="border-[#d7e8e3] bg-[#eef7f4] text-primary">
          <Sparkles className="size-3.5" /> AI criteria: {job.criteriaProcessingState.replaceAll("_", " ").toLowerCase()}
        </Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Applicants" value={job.applicantCount} detail="Total applications" icon={Users} />
        <StatCard label="Shortlisted" value={job.shortlistedCount} detail="Ready for review" icon={UserCheck} />
        <StatCard label="Interviews" value={job.interviewCount} detail="In interview stage" icon={CalendarDays} />
        <StatCard label="Hired" value={job.hiredCount} detail="Successful hires" icon={CheckCircle2} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(300px,0.8fr)]">
        <Card>
          <CardHeader><CardTitle>About this role</CardTitle></CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-7 text-muted-foreground">{job.description}</p>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Role requirements</CardTitle></CardHeader>
            <CardContent className="space-y-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Experience</p>
                <p className="mt-2 text-sm">{job.experienceRequirement || "Not specified"}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Required skills</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {requiredSkills.length ? requiredSkills.map((skill) => <Badge key={skill} variant="secondary">{skill}</Badge>) : <span className="text-sm text-muted-foreground">None listed</span>}
                </div>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Preferred skills</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {preferredSkills.length ? preferredSkills.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>) : <span className="text-sm text-muted-foreground">None listed</span>}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
