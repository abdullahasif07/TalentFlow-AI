"use client";

import { useQuery } from "@apollo/client/react";
import Link from "next/link";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  CircleAlert,
  Clock3,
  ShieldCheck,
} from "lucide-react";

import { ApplicationForm } from "@/components/public-application/application-form";
import { useDemoMode } from "@/components/public-application/use-demo-mode";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import {
  GET_PUBLIC_JOB,
  type PublicJobQueryData,
} from "@/lib/graphql/public-jobs";
import { stringList } from "@/lib/graphql/jobs";

function safeWebsite(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function PublicHeader() {
  return (
    <header className="border-b bg-white/95">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <BriefcaseBusiness className="size-4.5" aria-hidden="true" />
          </span>
          <span className="font-semibold tracking-tight">TalentFlow AI</span>
        </Link>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Secure candidate application
        </span>
      </div>
    </header>
  );
}

function PublicPageLoading() {
  return (
    <div className="min-h-screen bg-[#f7f9f8]">
      <PublicHeader />
      <main className="mx-auto grid max-w-6xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)] lg:px-8 lg:py-12">
        <div className="space-y-5">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-11 w-4/5" />
          <Skeleton className="h-5 w-52" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <div className="rounded-2xl border bg-card p-7 shadow-sm">
          <Skeleton className="h-6 w-48" />
          <div className="mt-8 grid gap-5 sm:grid-cols-2">
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} className="h-16 w-full" />
            ))}
          </div>
          <Skeleton className="mt-6 h-32 w-full" />
          <Skeleton className="mt-6 h-40 w-full" />
        </div>
      </main>
    </div>
  );
}

function UnavailableJob({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="min-h-screen bg-[#f7f9f8]">
      <PublicHeader />
      <main className="mx-auto flex max-w-3xl px-4 py-16 sm:px-6 sm:py-24">
        <section className="w-full rounded-2xl border bg-card px-6 py-14 text-center shadow-sm sm:px-10">
          <span className="mx-auto flex size-12 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
            <CircleAlert className="size-6" aria-hidden="true" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight">Job unavailable</h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
            {message}
          </p>
          {onRetry ? (
            <Button className="mt-6" variant="outline" onClick={onRetry}>
              Try again
            </Button>
          ) : null}
        </section>
      </main>
    </div>
  );
}

export function PublicApplicationPage({ jobId }: { jobId: string }) {
  const demoMode = useDemoMode();
  const validJobId = /^\d+$/.test(jobId) && Number(jobId) > 0;
  const { data, loading, error, refetch } = useQuery<PublicJobQueryData>(GET_PUBLIC_JOB, {
    variables: { input: { id: jobId } },
    skip: !validJobId,
    fetchPolicy: "network-only",
  });

  if (!validJobId) {
    return <UnavailableJob message="This job link is invalid or may no longer be available." />;
  }
  if (loading && !data) return <PublicPageLoading />;
  if (error) {
    return (
      <UnavailableJob
        message={graphQLErrorMessage(
          error,
          "We couldn’t load this job. Please check your connection and try again.",
        )}
        onRetry={() => void refetch()}
      />
    );
  }
  if (!data?.publicJob.success || !data.publicJob.job) {
    return (
      <UnavailableJob
        message={
          data?.publicJob.errors[0]?.message ??
          "This role may have closed or is no longer accepting applications."
        }
      />
    );
  }

  const job = data.publicJob.job;
  const requiredSkills = stringList(job.requiredSkills);
  const preferredSkills = stringList(job.preferredSkills);
  const companyWebsite = safeWebsite(job.company.website);

  return (
    <div className="min-h-screen bg-[#f7f9f8]">
      <PublicHeader />
      <main className="mx-auto grid max-w-6xl items-start gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)] lg:gap-12 lg:px-8 lg:py-12">
        <section className="lg:sticky lg:top-8">
          <div className="flex items-center gap-2 text-sm font-semibold text-primary">
            <Building2 className="size-4" aria-hidden="true" />
            {companyWebsite ? (
              <a
                href={companyWebsite}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-sm outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring/30"
              >
                {job.company.name} <ArrowUpRight className="size-3.5" />
              </a>
            ) : (
              job.company.name
            )}
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
            {job.title}
          </h1>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge className="border-[#d7e8e3] bg-[#eef7f4] text-primary" variant="outline">
              <BriefcaseBusiness className="size-3.5" /> Open role
            </Badge>
            {job.experienceRequirement ? (
              <Badge variant="outline">
                <Clock3 className="size-3.5" /> {job.experienceRequirement}
              </Badge>
            ) : null}
          </div>

          <div className="mt-8 border-t pt-7">
            <h2 className="text-sm font-semibold">About the role</h2>
            <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-muted-foreground">
              {job.description}
            </p>
          </div>

          <div className="mt-7 grid gap-6 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <div>
              <h2 className="text-sm font-semibold">Required skills</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {requiredSkills.length ? (
                  requiredSkills.map((skill) => (
                    <Badge key={skill} variant="secondary">{skill}</Badge>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No specific skills listed.</p>
                )}
              </div>
            </div>
            <div>
              <h2 className="text-sm font-semibold">Preferred skills</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {preferredSkills.length ? (
                  preferredSkills.map((skill) => (
                    <Badge key={skill} variant="outline">{skill}</Badge>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No preferences listed.</p>
                )}
              </div>
            </div>
          </div>

          <div className="mt-8 flex gap-3 rounded-xl border bg-white/70 p-4 text-xs leading-5 text-muted-foreground">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <p>Your information is submitted directly to {job.company.name} for this role.</p>
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border bg-card shadow-[0_16px_45px_rgba(23,32,51,0.06)]">
          <ApplicationForm jobId={job.id} demoMode={demoMode} />
        </section>
      </main>
      <footer className="border-t bg-white/60">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center text-xs text-muted-foreground sm:px-6 lg:px-8">
          Applications powered by TalentFlow AI
        </div>
      </footer>
    </div>
  );
}
