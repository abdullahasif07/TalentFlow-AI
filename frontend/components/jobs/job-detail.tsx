"use client";

import { useQuery } from "@apollo/client/react";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  MailCheck,
  Sparkles,
  UserCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { JobApplicants } from "@/components/jobs/job-applicants";
import { JobInformation } from "@/components/jobs/job-information";
import { RecommendedCandidates } from "@/components/jobs/recommended-candidates";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { GET_JOB, type JobQueryData, formatDate, stringList } from "@/lib/graphql/jobs";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { cn } from "@/lib/utils";

type JobTab = "APPLICANTS" | "RECOMMENDED" | "DETAILS";

export function JobDetail({ jobId }: { jobId: string }) {
  const [activeTab, setActiveTab] = useState<JobTab>("APPLICANTS");
  const { data, loading, error, refetch } = useQuery<JobQueryData>(GET_JOB, {
    variables: { input: { id: jobId } },
    fetchPolicy: "cache-and-network",
  });

  const backLink = (
    <Link
      href="/jobs"
      className={cn(
        buttonVariants({ variant: "ghost", size: "sm" }),
        "-ml-3 text-muted-foreground",
      )}
    >
      <ArrowLeft /> Back to jobs
    </Link>
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        {backLink}
        <LoadingState cards={5} />
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
  if (!data?.job.success || !data.job.job) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState
          title="Job not found"
          description={data?.job.errors[0]?.message ?? "This role may no longer exist."}
        />
      </div>
    );
  }

  const job = data.job.job;
  const requiredSkills = stringList(job.requiredSkills);
  const preferredSkills = stringList(job.preferredSkills);
  const tabs: Array<{ id: JobTab; label: string; count?: number }> = [
    { id: "APPLICANTS", label: "Applicants", count: job.applicantCount },
    {
      id: "RECOMMENDED",
      label: "Recommended",
      count: job.recommendedCandidateCount,
    },
    { id: "DETAILS", label: "Job Details" },
  ];

  return (
    <div className="space-y-7">
      {backLink}

      <section>
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-4xl">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{job.title}</h2>
              <StatusBadge status={job.status} />
            </div>
            <p className="mt-3 line-clamp-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {job.description}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="size-4" /> Created {formatDate(job.createdAt)}
              </span>
              <span className="font-medium text-foreground">
                {job.experienceRequirement || "Experience requirement not specified"}
              </span>
            </div>
          </div>
          <Badge variant="outline" className="border-[#d7e8e3] bg-[#eef7f4] text-primary">
            <Sparkles className="size-3.5" /> AI criteria: {job.criteriaProcessingState.replaceAll("_", " ").toLowerCase()}
          </Badge>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">Required skills</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {requiredSkills.length
                ? requiredSkills.map((skill) => <Badge key={skill} variant="secondary">{skill}</Badge>)
                : <span className="text-sm text-muted-foreground">None listed</span>}
            </div>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">Preferred skills</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {preferredSkills.length
                ? preferredSkills.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)
                : <span className="text-sm text-muted-foreground">None listed</span>}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        <StatCard label="Applicants" value={job.applicantCount} detail="Total applications" icon={Users} />
        <StatCard label="Recommended" value={job.recommendedCandidateCount} detail="AI recommended" icon={Sparkles} />
        <StatCard label="Shortlisted" value={job.shortlistedCount} detail="Selected for review" icon={UserCheck} />
        <StatCard label="Contacted" value={job.contactedCount} detail="Outreach started" icon={MailCheck} />
        <StatCard label="Interviews" value={job.interviewCount} detail="Interview stage" icon={CalendarDays} />
        <StatCard label="Hired" value={job.hiredCount} detail="Successful hires" icon={CheckCircle2} />
      </section>

      <section>
        <div className="mb-6 border-b">
          <div className="flex gap-6 overflow-x-auto" role="tablist" aria-label="Job sections">
            {tabs.map((tab) => {
              const selected = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={selected}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "relative flex h-11 shrink-0 items-center gap-2 text-sm font-semibold transition-colors",
                    selected ? "text-primary" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {tab.label}
                  {tab.count !== undefined ? (
                    <span className={cn(
                      "rounded-full px-2 py-0.5 text-[10px]",
                      selected ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground",
                    )}>
                      {tab.count}
                    </span>
                  ) : null}
                  {selected ? <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-primary" /> : null}
                </button>
              );
            })}
          </div>
        </div>

        <div role="tabpanel">
          {activeTab === "APPLICANTS" ? <JobApplicants jobId={jobId} /> : null}
          {activeTab === "RECOMMENDED" ? <RecommendedCandidates jobId={jobId} /> : null}
          {activeTab === "DETAILS" ? <JobInformation job={job} /> : null}
        </div>
      </section>
    </div>
  );
}
