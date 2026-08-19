"use client";

import { useQuery } from "@apollo/client/react";
import { CircleAlert, Sparkles, Star, UserCheck } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { FitScore } from "@/components/shared/fit-score-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GET_RECOMMENDED_CANDIDATES,
  formatEvaluationRecommendation,
  type RecommendedCandidatesQueryData,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";

function RecommendedLoading() {
  return (
    <div className="grid gap-4 lg:grid-cols-2" aria-busy="true" aria-label="Loading recommendations">
      {Array.from({ length: 4 }, (_, index) => (
        <Card key={index} className="p-5">
          <div className="flex items-center gap-3">
            <Skeleton className="size-10 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-48" />
            </div>
            <Skeleton className="h-7 w-14" />
          </div>
          <Skeleton className="mt-5 h-12 w-full" />
        </Card>
      ))}
    </div>
  );
}

export function RecommendedCandidates({ jobId }: { jobId: string }) {
  const { data, loading, error, refetch } = useQuery<RecommendedCandidatesQueryData>(
    GET_RECOMMENDED_CANDIDATES,
    {
      variables: { input: { jobId, limit: 5 } },
      fetchPolicy: "cache-and-network",
    },
  );

  if (loading && !data) return <RecommendedLoading />;
  if (error) {
    return <ErrorState description={graphQLErrorMessage(error)} onRetry={() => void refetch()} />;
  }
  if (data && !data.recommendedCandidates.success) {
    return (
      <ErrorState
        description={data.recommendedCandidates.errors[0]?.message}
        onRetry={() => void refetch()}
      />
    );
  }

  const candidates = data?.recommendedCandidates.items ?? [];

  if (!candidates.length) {
    return (
      <EmptyState
        icon={Sparkles}
        title="No evaluated candidates yet"
        description="Recommended candidates will appear after resume parsing and AI evaluation are completed."
      />
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {candidates.map(({ candidate, application, evaluation }, index) => (
        <Card key={application.id} className="overflow-hidden transition-shadow hover:shadow-md">
          <CardContent className="p-5">
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#e8f3f0] text-xs font-bold text-primary">
                {candidate.name
                  .split(" ")
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join("")
                  .toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    href={`/jobs/${jobId}/applications/${application.id}`}
                    className="truncate font-semibold hover:text-primary"
                  >
                    {candidate.name}
                  </Link>
                  {index === 0 ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700">
                      <Star className="size-3 fill-current" /> Top match
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">{candidate.email}</p>
              </div>
              <FitScore score={application.fitScore} processingState="COMPLETED" />
            </div>

            <div className="mt-4 flex items-center justify-between gap-3 border-y py-3">
              <StatusBadge status={application.status} />
              <span className="text-xs font-medium capitalize text-muted-foreground">
                {evaluation.confidence.toLowerCase()} confidence
              </span>
            </div>

            <p className="mt-4 line-clamp-2 text-sm leading-6 text-muted-foreground">
              {formatEvaluationRecommendation(evaluation.recommendation)}
            </p>

            <div className="mt-4 space-y-2.5 text-xs">
              <div className="flex gap-2">
                <UserCheck className="mt-0.5 size-3.5 shrink-0 text-emerald-600" />
                <p className="line-clamp-2">
                  <span className="font-semibold text-foreground">Strength: </span>
                  <span className="text-muted-foreground">
                    {evaluation.strengths[0]?.summary ?? "No primary strength recorded."}
                  </span>
                </p>
              </div>
              <div className="flex gap-2">
                <CircleAlert className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
                <p className="line-clamp-2">
                  <span className="font-semibold text-foreground">Gap: </span>
                  <span className="text-muted-foreground">
                    {evaluation.gaps[0]?.summary ?? "No primary gap recorded."}
                  </span>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
