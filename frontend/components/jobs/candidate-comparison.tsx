"use client";

import { gql } from "@apollo/client";
import { useApolloClient, useMutation } from "@apollo/client/react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FitScore } from "@/components/shared/fit-score-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatEvaluationRecommendation,
  type ApplicationStatus,
  type EvaluationFinding,
} from "@/lib/graphql/applications";
import {
  COMPARE_CANDIDATES,
  type CandidateComparisonPayload,
  type CandidateComparisonSummary,
  type CompareCandidatesData,
  type ComparedCandidate,
  type CompareCandidatesVariables,
} from "@/lib/graphql/comparison";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import {
  comparisonScoreAvailable,
  gapEvidenceLabel,
} from "@/lib/comparison-presentation";
import {
  buildApplicantsUrl,
  buildCandidateComparisonInput,
  storeComparisonSelection,
} from "@/lib/comparison-selection";
import { cn } from "@/lib/utils";

const APPLICATION_STATUS_FRAGMENT = gql`
  fragment ComparisonApplicationStatus on ApplicationType {
    id
    status
  }
`;

interface CandidateComparisonProps {
  jobId: string;
  applicationIds: string[];
  inputError: string | null;
}

interface ComparisonRequestState {
  key: string | null;
  loading: boolean;
  data: CompareCandidatesData | null;
  error: unknown;
}

function titleCase(value: string): string {
  const normalized = value.replaceAll("_", " ").trim().toLowerCase();
  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ComparisonLoading({ count }: { count: number }) {
  return (
    <div
      className="space-y-6"
      aria-busy="true"
      aria-label="Comparing candidate evaluations"
    >
      <Card className="border-[#d7e8e3] bg-[#f5f9f8]">
        <CardContent className="flex items-center gap-4 p-5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-primary shadow-sm ring-1 ring-[#d7e8e3]">
            <LoaderCircle className="size-5 animate-spin" />
          </span>
          <div>
            <p className="text-sm font-semibold">Comparing candidate evaluations…</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Building a grounded comparison from {count} persisted evaluation reports.
            </p>
          </div>
        </CardContent>
      </Card>
      <div className="overflow-x-auto pb-1">
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${Math.max(2, count)}, minmax(220px, 1fr))`,
            minWidth: `${Math.max(2, count) * 220}px`,
          }}
        >
          {Array.from({ length: Math.max(2, count) }, (_, index) => (
            <Card key={index} className="p-5">
              <Skeleton className="h-5 w-36" />
              <Skeleton className="mt-5 h-10 w-24" />
              <Skeleton className="mt-4 h-6 w-28" />
            </Card>
          ))}
        </div>
      </div>
      <Card className="p-5">
        <Skeleton className="h-5 w-44" />
        <div className="mt-5 space-y-3">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      </Card>
    </div>
  );
}

function ComparisonError({
  message,
  backHref,
  onSelectDifferent,
  onRetry,
}: {
  message: string;
  backHref: string;
  onSelectDifferent: () => void;
  onRetry?: () => void;
}) {
  return (
    <Card className="border-rose-200">
      <CardContent className="flex min-h-72 flex-col items-center justify-center p-8 text-center">
        <span className="rounded-xl bg-rose-50 p-3 text-rose-600">
          <CircleAlert className="size-6" />
        </span>
        <h2 className="mt-4 text-lg font-semibold">Unable to compare candidates</h2>
        <p className="mt-2 max-w-lg break-words text-sm leading-6 text-muted-foreground">
          {message}
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Link
            href={backHref}
            onClick={onSelectDifferent}
            className={buttonVariants({ variant: "outline" })}
          >
            <ArrowLeft /> Select different candidates
          </Link>
          {onRetry ? (
            <Button onClick={onRetry}>
              <RefreshCw /> Retry comparison
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

function CandidateSummaryCards({
  jobId,
  candidates,
  statuses,
}: {
  jobId: string;
  candidates: ComparedCandidate[];
  statuses: Record<string, ApplicationStatus | undefined>;
}) {
  return (
    <section aria-labelledby="candidate-summaries-heading">
      <h2 id="candidate-summaries-heading" className="sr-only">
        Candidate summaries
      </h2>
      <div className="overflow-x-auto pb-2">
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${candidates.length}, minmax(220px, 1fr))`,
            minWidth: `${candidates.length * 220}px`,
          }}
        >
          {candidates.map((candidate) => {
            const status = statuses[candidate.applicationId];
            const detailHref = `/jobs/${encodeURIComponent(jobId)}/applications/${encodeURIComponent(candidate.applicationId)}`;

            return (
              <Card key={candidate.applicationId} className="min-w-0">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        href={detailHref}
                        className="break-words text-base font-semibold leading-6 transition-colors hover:text-primary focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                      >
                        {candidate.name}
                      </Link>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Application {candidate.applicationId}
                      </p>
                    </div>
                    {status ? <StatusBadge status={status} /> : null}
                  </div>
                  <div className="mt-5">
                    <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Overall fit
                    </p>
                    <FitScore
                      score={candidate.overallScore}
                      processingState="COMPLETED"
                      className="min-w-16 px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge
                      variant="outline"
                      className="border-sky-200 bg-sky-50 text-sky-700"
                    >
                      <ShieldCheck className="size-3.5" />
                      {titleCase(candidate.confidence)} confidence
                    </Badge>
                  </div>
                  <p className="mt-4 break-words text-sm font-medium leading-6">
                    {formatEvaluationRecommendation(candidate.recommendation)}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ComparisonTable({
  jobId,
  result,
}: {
  jobId: string;
  result: CandidateComparisonPayload;
}) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle>Evaluation score comparison</CardTitle>
        <p className="text-xs leading-5 text-muted-foreground">
          Stored scores from each job-specific evaluation. Expand a score to inspect its recorded
          rationale.
        </p>
      </CardHeader>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse text-left"
          style={{ minWidth: `${220 + result.candidates.length * 190}px` }}
        >
          <thead className="border-b bg-muted/55 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
            <tr>
              <th className="sticky left-0 z-10 w-52 bg-muted px-5 py-3.5">Category</th>
              {result.candidates.map((candidate) => (
                <th key={candidate.applicationId} className="min-w-48 px-4 py-3.5">
                  <Link
                    href={`/jobs/${encodeURIComponent(jobId)}/applications/${encodeURIComponent(candidate.applicationId)}`}
                    className="block max-w-48 break-words transition-colors hover:text-primary focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                  >
                    {candidate.name}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            <tr className="bg-[#f7faf9]">
              <th className="sticky left-0 z-10 bg-[#f7faf9] px-5 py-4 text-sm font-semibold">
                Overall fit
              </th>
              {result.candidates.map((candidate) => (
                <td key={candidate.applicationId} className="px-4 py-4">
                  <FitScore
                    score={candidate.overallScore}
                    processingState="COMPLETED"
                  />
                </td>
              ))}
            </tr>
            {result.categories.map((category) => (
              <tr key={category.name} className="align-top">
                <th className="sticky left-0 z-10 bg-card px-5 py-4">
                  <p className="break-words text-sm font-semibold">{category.name}</p>
                  <p className="mt-1 text-[11px] font-normal text-muted-foreground">
                    Weight {category.weight}%
                  </p>
                </th>
                {result.candidates.map((candidate) => {
                  const categoryResult = category.candidates.find(
                    (item) => item.applicationId === candidate.applicationId,
                  );
                  const available = comparisonScoreAvailable(
                    categoryResult?.available ?? false,
                    categoryResult?.score ?? null,
                  );

                  return (
                    <td key={candidate.applicationId} className="px-4 py-4">
                      {available ? (
                        <FitScore
                          score={categoryResult?.score ?? null}
                          processingState="COMPLETED"
                        />
                      ) : (
                        <p className="text-sm font-medium text-muted-foreground">
                          Not available
                        </p>
                      )}
                      {categoryResult?.summary ? (
                        <details className="group mt-2 max-w-64 text-xs">
                          <summary className="cursor-pointer font-medium text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring/30">
                            View details
                          </summary>
                          <p className="mt-2 break-words leading-5 text-muted-foreground">
                            {categoryResult.summary}
                          </p>
                        </details>
                      ) : null}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function FindingGroup({
  title,
  findings,
  tone,
}: {
  title: string;
  findings: EvaluationFinding[];
  tone: "strength" | "gap";
}) {
  const strength = tone === "strength";

  return (
    <div>
      <h4 className="flex items-center gap-2 text-sm font-semibold">
        {strength ? (
          <CheckCircle2 className="size-4 text-emerald-600" />
        ) : (
          <CircleAlert className="size-4 text-amber-600" />
        )}
        {title}
      </h4>
      {findings.length ? (
        <div className="mt-3 space-y-3">
          {findings.map((finding, index) => (
            <div key={`${finding.summary}-${index}`} className="rounded-lg border p-3.5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="min-w-0 flex-1 break-words text-sm font-medium leading-5">
                  {finding.summary}
                </p>
                {!strength ? (
                  <Badge
                    variant="outline"
                    className={cn(
                      finding.evidence.length
                        ? "border-rose-200 bg-rose-50 text-rose-700"
                        : "border-amber-200 bg-amber-50 text-amber-700",
                    )}
                  >
                    {gapEvidenceLabel(finding.evidence)}
                  </Badge>
                ) : null}
              </div>
              {finding.evidence.length ? (
                <div className="mt-2 space-y-1.5">
                  {finding.evidence.slice(0, 3).map((evidence, evidenceIndex) => (
                    <blockquote
                      key={`${evidence}-${evidenceIndex}`}
                      className="break-words border-l-2 border-border pl-3 text-xs italic leading-5 text-muted-foreground"
                    >
                      “{evidence}”
                    </blockquote>
                  ))}
                </div>
              ) : !strength ? (
                <p className="mt-2 text-xs leading-5 text-amber-700">
                  This was not found in the stored resume evidence. Treat it as unverified, not as
                  a confirmed lack of experience.
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          No {strength ? "strengths" : "potential gaps"} were recorded.
        </p>
      )}
    </div>
  );
}

function CandidateEvidence({
  jobId,
  candidates,
}: {
  jobId: string;
  candidates: ComparedCandidate[];
}) {
  return (
    <section aria-labelledby="candidate-evidence-heading">
      <div>
        <h2 id="candidate-evidence-heading" className="text-lg font-semibold">
          Candidate evidence
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Existing evaluation strengths and potential gaps, shown without changing their meaning.
        </p>
      </div>
      <div className="mt-4 overflow-x-auto pb-2">
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${candidates.length}, minmax(260px, 1fr))`,
            minWidth: `${candidates.length * 260}px`,
          }}
        >
          {candidates.map((candidate) => (
            <Card key={candidate.applicationId} className="min-w-0">
              <CardHeader className="border-b">
                <CardTitle className="break-words leading-6">
                  <Link
                    href={`/jobs/${encodeURIComponent(jobId)}/applications/${encodeURIComponent(candidate.applicationId)}`}
                    className="transition-colors hover:text-primary focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                  >
                    {candidate.name}
                  </Link>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6 pt-5">
                <FindingGroup title="Strengths" findings={candidate.strengths} tone="strength" />
                <FindingGroup title="Potential gaps" findings={candidate.gaps} tone="gap" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

const summaryGroups: Array<{
  key: keyof Omit<CandidateComparisonSummary, "overview">;
  label: string;
}> = [
  { key: "relativeStrengths", label: "Relative strengths" },
  { key: "tradeoffs", label: "Meaningful tradeoffs" },
  { key: "differentiatingExperience", label: "Differentiating experience" },
  { key: "notableGaps", label: "Notable gaps" },
  { key: "comparableAreas", label: "Comparable areas" },
];

function TradeoffSummary({ summary }: { summary: CandidateComparisonSummary }) {
  return (
    <Card className="border-[#cfe1dc]">
      <CardHeader className="border-b bg-[#f7faf9]">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-[#e8f3f0] p-2 text-primary">
            <Sparkles className="size-4.5" />
          </span>
          <div>
            <CardTitle>AI comparison summary</CardTitle>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Grounded tradeoffs from the selected resumes and persisted job evaluations.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-5">
        <p className="whitespace-pre-wrap break-words text-base font-medium leading-7">
          {summary.overview}
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {summaryGroups.map(({ key, label }) => {
            const statements = summary[key];
            if (!statements.length) return null;

            return (
              <section key={key} className="rounded-xl border bg-card p-4">
                <h3 className="text-sm font-semibold">{label}</h3>
                <ul className="mt-3 space-y-2.5">
                  {statements.map((statement, index) => (
                    <li
                      key={`${statement}-${index}`}
                      className="flex gap-2.5 break-words text-sm leading-6 text-muted-foreground"
                    >
                      <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary/60" />
                      <span>{statement}</span>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
        <p className="mt-5 flex items-start gap-2 rounded-lg bg-muted/60 px-3.5 py-3 text-xs leading-5 text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
          This comparison supports recruiter review and does not select, hire, or reject a
          candidate.
        </p>
      </CardContent>
    </Card>
  );
}

export function CandidateComparison({
  jobId,
  applicationIds,
  inputError,
}: CandidateComparisonProps) {
  const client = useApolloClient();
  const requestedKey = `${jobId}:${applicationIds.join(",")}`;
  const completedRequestRef = useRef<string | null>(null);
  const requestSequenceRef = useRef(0);
  const [requestState, setRequestState] = useState<ComparisonRequestState>({
    key: null,
    loading: false,
    data: null,
    error: null,
  });
  const [compareCandidates] = useMutation<
    CompareCandidatesData,
    CompareCandidatesVariables
  >(COMPARE_CANDIDATES, { fetchPolicy: "no-cache" });

  const runComparison = useCallback(async () => {
    if (inputError) return;
    const sequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = sequence;
    completedRequestRef.current = requestedKey;
    setRequestState({
      key: requestedKey,
      loading: true,
      data: null,
      error: null,
    });
    try {
      const response = await compareCandidates({
        variables: {
          input: buildCandidateComparisonInput(jobId, applicationIds),
        },
      });
      if (requestSequenceRef.current !== sequence) return;
      setRequestState({
        key: requestedKey,
        loading: false,
        data: response.data ?? null,
        error: null,
      });
    } catch (caughtError) {
      if (requestSequenceRef.current !== sequence) return;
      setRequestState({
        key: requestedKey,
        loading: false,
        data: null,
        error: caughtError,
      });
    }
  }, [applicationIds, compareCandidates, inputError, jobId, requestedKey]);

  useEffect(() => {
    if (inputError || completedRequestRef.current === requestedKey) return;
    void runComparison();
  }, [inputError, requestedKey, runComparison]);

  const result = requestState.data?.compareCandidates;
  const requestMatchesRoute = requestState.key === requestedKey;
  const statuses = useMemo(() => {
    const values: Record<string, ApplicationStatus | undefined> = {};
    for (const applicationId of applicationIds) {
      const cacheId = client.cache.identify({ __typename: "ApplicationType", id: applicationId });
      if (!cacheId) continue;
      const cached = client.cache.readFragment<{
        id: string;
        status: ApplicationStatus;
      }>({ id: cacheId, fragment: APPLICATION_STATUS_FRAGMENT });
      values[applicationId] = cached?.status;
    }
    return values;
  }, [applicationIds, client]);

  const backHref = buildApplicantsUrl(jobId);
  const selectDifferentCandidates = () => {
    storeComparisonSelection(jobId, []);
  };
  const backLink = (
    <Link
      href={backHref}
      className={cn(
        buttonVariants({ variant: "ghost", size: "sm" }),
        "-ml-3 text-muted-foreground",
      )}
    >
      <ArrowLeft /> Back to applicants
    </Link>
  );

  if (inputError) {
    return (
      <div className="space-y-5">
        {backLink}
        <ComparisonError
          message={inputError}
          backHref={backHref}
          onSelectDifferent={selectDifferentCandidates}
        />
      </div>
    );
  }

  if (requestState.loading || !requestMatchesRoute) {
    return (
      <div className="space-y-6">
        {backLink}
        <div>
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Candidate Comparison
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Comparing {applicationIds.length} evaluated applicants.
          </p>
        </div>
        <ComparisonLoading count={applicationIds.length} />
      </div>
    );
  }

  const failureMessage = requestState.error
    ? graphQLErrorMessage(
        requestState.error,
        "The comparison request failed. Please try again.",
      )
    : !result?.success
      ? result?.errors[0]?.message ?? "The comparison could not be generated."
      : !result.job || !result.summary
        ? "The backend returned an incomplete comparison result."
        : null;

  if (failureMessage || !result?.job || !result.summary) {
    return (
      <div className="space-y-5">
        {backLink}
        <ComparisonError
          message={failureMessage ?? "The comparison could not be generated."}
          backHref={backHref}
          onSelectDifferent={selectDifferentCandidates}
          onRetry={() => {
            completedRequestRef.current = null;
            void runComparison();
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {backLink}

      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
            <Scale className="size-4" /> Decision support
          </div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Candidate Comparison
          </h2>
          <p className="mt-2 break-words text-sm text-muted-foreground">
            {result.job.title} · {result.candidates.length} candidates compared
          </p>
        </div>
        <Badge variant="outline" className="border-[#d7e8e3] bg-[#eef7f4] text-primary">
          <ShieldCheck className="size-3.5" /> Existing evaluations only
        </Badge>
      </header>

      <CandidateSummaryCards
        jobId={jobId}
        candidates={result.candidates}
        statuses={statuses}
      />
      <ComparisonTable jobId={jobId} result={result} />
      <TradeoffSummary summary={result.summary} />
      <CandidateEvidence jobId={jobId} candidates={result.candidates} />
    </div>
  );
}
