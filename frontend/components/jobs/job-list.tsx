"use client";

import { useQuery } from "@apollo/client/react";
import {
  ArrowUpDown,
  ArrowUpRight,
  BriefcaseBusiness,
  ChevronDown,
  Search,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { GET_JOBS, type JobsQueryData, type JobStatus, formatDate } from "@/lib/graphql/jobs";
import { graphQLErrorMessage } from "@/lib/graphql/errors";

type StatusFilter = "ALL" | JobStatus;
type SortOrder = "NEWEST" | "OLDEST";

export function JobList() {
  const router = useRouter();
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOrder>("NEWEST");
  const { data, loading, error, refetch } = useQuery<JobsQueryData>(GET_JOBS, {
    variables: { input: status === "ALL" ? null : { status } },
    fetchPolicy: "cache-and-network",
  });

  const jobs = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = [...(data?.jobs.items ?? [])];
    const filtered = query
      ? items.filter((job) => job.title.toLowerCase().includes(query))
      : items;

    return filtered.sort((first, second) => {
      const difference =
        new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime();
      return sort === "NEWEST" ? difference : -difference;
    });
  }, [data?.jobs.items, search, sort]);

  const clearControls = () => {
    setSearch("");
    setStatus("ALL");
    setSort("NEWEST");
  };

  if (loading && !data) return <LoadingState cards={3} />;
  if (error) {
    return <ErrorState description={graphQLErrorMessage(error)} onRetry={() => void refetch()} />;
  }
  if (data && !data.jobs.success) {
    return <ErrorState description={data.jobs.errors[0]?.message} onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border bg-card p-3 shadow-[0_1px_2px_rgba(23,32,51,0.03)]">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="relative w-full xl:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            className="pl-9"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search roles…"
            aria-label="Search jobs"
          />
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between xl:justify-end">
            <div className="flex flex-wrap gap-1.5" aria-label="Filter jobs by status">
              {(["ALL", "OPEN", "DRAFT", "CLOSED"] as const).map((value) => (
                <Button
                  key={value}
                  variant={status === value ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => setStatus(value)}
                  className={
                    status === value
                      ? "bg-accent text-accent-foreground hover:bg-accent"
                      : "text-muted-foreground"
                  }
                >
                  {value === "ALL"
                    ? "All"
                    : value.charAt(0) + value.slice(1).toLowerCase()}
                </Button>
              ))}
            </div>

            <div className="relative min-w-42">
              <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as SortOrder)}
                className="h-9 w-full appearance-none rounded-lg border border-input bg-card pl-9 pr-8 text-xs font-semibold text-foreground outline-none transition-shadow focus:border-primary focus:ring-2 focus:ring-ring/15"
                aria-label="Sort jobs"
              >
                <option value="NEWEST">Newest first</option>
                <option value="OLDEST">Oldest first</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            </div>
          </div>
        </div>
      </div>

      {jobs.length === 0 ? (
        <EmptyState
          icon={BriefcaseBusiness}
          title="No jobs found"
          description={search ? "Try a different search or status filter." : "New roles will appear here once they are created."}
          action={
            search || status !== "ALL" || sort !== "NEWEST" ? (
              <Button variant="outline" onClick={clearControls}>Clear filters</Button>
            ) : undefined
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left">
              <thead className="border-b bg-muted/55 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-3.5">Role</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5 text-center">Applicants</th>
                  <th className="px-4 py-3.5 text-center">Recommended</th>
                  <th className="px-4 py-3.5 text-center">Shortlisted</th>
                  <th className="px-4 py-3.5 text-center">Interviews</th>
                  <th className="px-4 py-3.5 text-center">Hired</th>
                  <th className="px-4 py-3.5">Created</th>
                  <th className="px-5 py-3.5 text-right"><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    role="link"
                    tabIndex={0}
                    className="group cursor-pointer transition-colors hover:bg-muted/35 focus-within:bg-muted/35"
                    onClick={() => router.push(`/jobs/${job.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") router.push(`/jobs/${job.id}`);
                    }}
                  >
                    <td className="px-5 py-4">
                      <Link
                        href={`/jobs/${job.id}`}
                        className="font-semibold text-foreground outline-none hover:text-primary focus-visible:text-primary"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {job.title}
                      </Link>
                      <p className="mt-1 max-w-md truncate text-xs text-muted-foreground">{job.experienceRequirement || "Experience level not specified"}</p>
                    </td>
                    <td className="px-4 py-4"><StatusBadge status={job.status} /></td>
                    <td className="px-4 py-4 text-center">
                      <span className="inline-flex items-center gap-1.5 text-sm font-semibold"><Users className="size-4 text-muted-foreground" />{job.applicantCount}</span>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span className="inline-flex items-center gap-1.5 text-sm font-semibold"><Sparkles className="size-3.5 text-primary" />{job.recommendedCandidateCount}</span>
                    </td>
                    <td className="px-4 py-4 text-center text-sm font-semibold">{job.shortlistedCount}</td>
                    <td className="px-4 py-4 text-center text-sm font-semibold">{job.interviewCount}</td>
                    <td className="px-4 py-4 text-center text-sm font-semibold">{job.hiredCount}</td>
                    <td className="px-4 py-4 text-sm text-muted-foreground">{formatDate(job.createdAt)}</td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/jobs/${job.id}`}
                        onClick={(event) => event.stopPropagation()}
                        className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                        aria-label={`Open ${job.title}`}
                      >
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
      <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <p>Showing {jobs.length} of {data?.jobs.totalCount ?? 0} jobs</p>
        {(search || status !== "ALL" || sort !== "NEWEST") && (
          <button className="font-semibold text-primary hover:underline" onClick={clearControls}>
            Reset controls
          </button>
        )}
      </div>
    </div>
  );
}
