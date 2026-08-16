"use client";

import { useQuery } from "@apollo/client/react";
import { ArrowUpRight, BriefcaseBusiness, Search, Users } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { GET_JOBS, type JobsQueryData, type JobStatus, formatDate } from "@/lib/graphql/jobs";

type StatusFilter = "ALL" | JobStatus;

export function JobList() {
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [search, setSearch] = useState("");
  const { data, loading, error, refetch } = useQuery<JobsQueryData>(GET_JOBS, {
    variables: { input: status === "ALL" ? null : { status } },
    fetchPolicy: "cache-and-network",
  });

  const jobs = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = data?.jobs.items ?? [];
    if (!query) return items;
    return items.filter((job) =>
      `${job.title} ${job.description}`.toLowerCase().includes(query),
    );
  }, [data?.jobs.items, search]);

  if (loading && !data) return <LoadingState cards={3} />;
  if (error) return <ErrorState description={error.message} onRetry={() => void refetch()} />;
  if (data && !data.jobs.success) {
    return <ErrorState description={data.jobs.errors[0]?.message} onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search roles…"
            aria-label="Search jobs"
          />
        </div>
        <div className="flex flex-wrap gap-2" aria-label="Filter jobs by status">
          {(["ALL", "OPEN", "DRAFT", "CLOSED"] as const).map((value) => (
            <Button
              key={value}
              variant={status === value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatus(value)}
              className={status === value ? "bg-accent text-accent-foreground hover:bg-accent" : "text-muted-foreground"}
            >
              {value === "ALL" ? "All roles" : value.charAt(0) + value.slice(1).toLowerCase()}
            </Button>
          ))}
        </div>
      </div>

      {jobs.length === 0 ? (
        <EmptyState
          icon={BriefcaseBusiness}
          title="No jobs found"
          description={search ? "Try a different search or status filter." : "New roles will appear here once they are created."}
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left">
              <thead className="border-b bg-muted/55 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-3.5">Role</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Applicants</th>
                  <th className="px-4 py-3.5">Shortlisted</th>
                  <th className="px-4 py-3.5">Created</th>
                  <th className="px-5 py-3.5 text-right"><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {jobs.map((job) => (
                  <tr key={job.id} className="group transition-colors hover:bg-muted/35">
                    <td className="px-5 py-4">
                      <Link href={`/jobs/${job.id}`} className="font-semibold text-foreground hover:text-primary">
                        {job.title}
                      </Link>
                      <p className="mt-1 max-w-md truncate text-xs text-muted-foreground">{job.experienceRequirement || "Experience level not specified"}</p>
                    </td>
                    <td className="px-4 py-4"><StatusBadge status={job.status} /></td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1.5 text-sm font-medium"><Users className="size-4 text-muted-foreground" />{job.applicantCount}</span>
                    </td>
                    <td className="px-4 py-4 text-sm font-medium">{job.shortlistedCount}</td>
                    <td className="px-4 py-4 text-sm text-muted-foreground">{formatDate(job.createdAt)}</td>
                    <td className="px-5 py-4 text-right">
                      <Link href={`/jobs/${job.id}`} className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground" aria-label={`Open ${job.title}`}>
                        <ArrowUpRight className="size-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      <p className="text-xs text-muted-foreground">Showing {jobs.length} of {data?.jobs.totalCount ?? 0} roles</p>
    </div>
  );
}
