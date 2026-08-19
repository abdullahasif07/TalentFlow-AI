"use client";

import { useMutation } from "@apollo/client/react";
import {
  AlertCircle,
  CheckCircle2,
  CircleAlert,
  FileSearch,
  LoaderCircle,
  Quote,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useState } from "react";

import {
  ProcessingStateBadge,
  evaluationStateLabel,
} from "@/components/shared/processing-state-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  GENERATE_CANDIDATE_EVALUATION,
  formatEvaluationRecommendation,
  type ApplicationDetail,
  type EvaluationFinding,
  type EvaluationRequirement,
  type GenerateCandidateEvaluationData,
  type RequirementMatchStatus,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import { cn } from "@/lib/utils";

interface EvaluationPreviewProps {
  application: ApplicationDetail;
  onEvaluationQueued?: () => Promise<unknown> | void;
}

const requirementPresentation: Record<
  RequirementMatchStatus,
  { label: string; className: string; description: string }
> = {
  MATCH: {
    label: "Strong match",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    description: "Supported by evidence in the resume.",
  },
  PARTIAL_MATCH: {
    label: "Partial match",
    className: "border-sky-200 bg-sky-50 text-sky-700",
    description: "Some relevant evidence is present, but the requirement is not fully demonstrated.",
  },
  MISSING_EVIDENCE: {
    label: "Not found in resume",
    className: "border-amber-200 bg-amber-50 text-amber-700",
    description: "This is unverified, not a confirmed lack of the skill or experience.",
  },
  NOT_MET: {
    label: "Confirmed mismatch",
    className: "border-rose-200 bg-rose-50 text-rose-700",
    description: "The available resume information conflicts with this requirement.",
  },
};

function titleCase(value: string) {
  const normalized = value.replaceAll("_", " ").trim().toLowerCase();
  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function numericScore(value: number | string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed)) : 0;
}

function RequirementCard({ item }: { item: EvaluationRequirement }) {
  const presentation = requirementPresentation[item.status];

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="break-words text-sm font-semibold">{item.requirement}</p>
        <Badge variant="outline" className={presentation.className}>
          {presentation.label}
        </Badge>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        {presentation.description}
      </p>
      {item.evidence ? (
        <blockquote className="mt-3 border-l-2 border-primary/30 pl-3 text-xs italic leading-5 text-muted-foreground">
          “{item.evidence}”
        </blockquote>
      ) : null}
    </div>
  );
}

function FindingList({
  findings,
  emptyMessage,
  tone,
}: {
  findings: EvaluationFinding[];
  emptyMessage: string;
  tone: "positive" | "caution";
}) {
  if (!findings.length) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <div className="space-y-3">
      {findings.map((finding, index) => (
        <div key={`${finding.summary}-${index}`} className="rounded-lg border bg-card p-4">
          <div className="flex items-start gap-2.5">
            {tone === "positive" ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
            ) : (
              <CircleAlert className="mt-0.5 size-4 shrink-0 text-amber-600" />
            )}
            <p className="break-words text-sm font-medium leading-6">{finding.summary}</p>
          </div>
          {finding.evidence.length ? (
            <div className="ml-6 mt-2 space-y-1.5">
              {finding.evidence.slice(0, 2).map((evidence, evidenceIndex) => (
                <p
                  key={`${evidence}-${evidenceIndex}`}
                  className="border-l-2 border-border pl-3 text-xs italic leading-5 text-muted-foreground"
                >
                  “{evidence}”
                </p>
              ))}
            </div>
          ) : tone === "caution" ? (
            <p className="ml-6 mt-1 text-xs leading-5 text-amber-700">
              No supporting resume evidence was recorded; treat this as unverified.
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function EvaluationActionState({
  application,
  onEvaluationQueued,
}: EvaluationPreviewProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [generateEvaluation, { loading }] = useMutation<
    GenerateCandidateEvaluationData,
    { input: { applicationId: string } }
  >(GENERATE_CANDIDATE_EVALUATION);

  const state = application.evaluationProcessingState;
  const canGenerate = state === "NOT_STARTED" || state === "FAILED";

  async function handleGenerate() {
    setActionError(null);
    setMessage(null);

    try {
      const result = await generateEvaluation({
        variables: { input: { applicationId: application.id } },
      });
      const payload = result.data?.generateCandidateEvaluation;

      if (!payload?.success) {
        setActionError(
          payload?.errors[0]?.message ?? payload?.message ?? "The evaluation could not be queued.",
        );
        return;
      }

      setMessage(payload.message || "Evaluation queued successfully.");
      await onEvaluationQueued?.();
    } catch (error) {
      setActionError(graphQLErrorMessage(error, "The evaluation could not be queued."));
    }
  }

  return (
    <div
      className={cn(
        "rounded-xl border p-6 text-center",
        state === "FAILED" ? "border-rose-200 bg-rose-50/50" : "border-dashed bg-muted/20",
      )}
    >
      <div
        className={cn(
          "mx-auto flex size-10 items-center justify-center rounded-full",
          state === "FAILED" ? "bg-rose-100 text-rose-700" : "bg-[#e8f3f0] text-primary",
        )}
      >
        {state === "PROCESSING" ? (
          <LoaderCircle className="size-5 animate-spin" />
        ) : state === "FAILED" ? (
          <AlertCircle className="size-5" />
        ) : (
          <FileSearch className="size-5" />
        )}
      </div>
      <p className="mt-3 text-sm font-semibold">
        {state === "NOT_STARTED"
          ? "AI evaluation has not started"
          : state === "PROCESSING"
            ? "Candidate evaluation is processing"
            : "Candidate evaluation failed"}
      </p>
      <p className="mx-auto mt-1 max-w-xl text-xs leading-5 text-muted-foreground">
        {state === "NOT_STARTED"
          ? "Generate an evidence-based report from the parsed resume and this job’s evaluation criteria."
          : state === "PROCESSING"
            ? "The report is running in the background. This page will refresh when it is ready."
            : "The previous attempt did not complete. You can retry without changing the candidate’s hiring status."}
      </p>
      {canGenerate ? (
        <Button className="mt-4" onClick={() => void handleGenerate()} disabled={loading}>
          {loading ? (
            <LoaderCircle className="animate-spin" />
          ) : state === "FAILED" ? (
            <RefreshCw />
          ) : (
            <Sparkles />
          )}
          {loading ? "Queuing…" : state === "FAILED" ? "Retry AI Report" : "Generate AI Report"}
        </Button>
      ) : null}
      {message ? <p className="mt-3 text-xs text-emerald-700">{message}</p> : null}
      {actionError ? (
        <p role="alert" className="mt-3 text-xs text-rose-700">
          {actionError}
        </p>
      ) : null}
    </div>
  );
}

export function EvaluationPreview({
  application,
  onEvaluationQueued,
}: EvaluationPreviewProps) {
  const state = application.evaluationProcessingState;
  const evaluation = application.evaluation;
  const overallScore = application.fitScore ?? evaluation?.overallScore ?? 0;

  const matchedRequirements = evaluation?.matchedRequirements ?? [];
  const missingRequirements = evaluation?.missingRequirements ?? [];
  const allRequirements = [...matchedRequirements, ...missingRequirements];
  const strongMatches = matchedRequirements.filter((item) => item.status === "MATCH");
  const partialMatches = matchedRequirements.filter((item) => item.status === "PARTIAL_MATCH");
  const unverified = missingRequirements.filter((item) => item.status === "MISSING_EVIDENCE");
  const confirmedGaps = missingRequirements.filter((item) => item.status === "NOT_MET");

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 border-b">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-[#e8f3f0] p-2 text-primary">
            <Sparkles className="size-4.5" />
          </div>
          <div>
            <CardTitle>AI candidate evaluation</CardTitle>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Explainable decision support based only on this resume and job criteria.
            </p>
          </div>
        </div>
        <ProcessingStateBadge state={state} label={evaluationStateLabel(state)} />
      </CardHeader>
      <CardContent className="pt-5">
        {state !== "COMPLETED" ? (
          <EvaluationActionState
            application={application}
            onEvaluationQueued={onEvaluationQueued}
          />
        ) : !evaluation ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-center">
            <p className="text-sm font-semibold text-amber-900">Evaluation result unavailable</p>
            <p className="mt-1 text-xs leading-5 text-amber-800">
              Processing is marked complete, but no persisted evaluation was returned.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            <section className="grid gap-5 rounded-xl border bg-muted/20 p-5 md:grid-cols-[180px_minmax(0,1fr)] md:items-center">
              <div className="border-b pb-5 md:border-b-0 md:border-r md:pb-0 md:pr-5">
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                  Overall fit
                </p>
                <p className="mt-2 text-4xl font-semibold tracking-tight tabular-nums">
                  {Math.round(numericScore(overallScore))}
                  <span className="ml-1 text-lg font-medium text-muted-foreground">/ 100</span>
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${numericScore(overallScore)}%` }}
                  />
                </div>
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="border-sky-200 bg-sky-50 text-sky-700">
                    <ShieldCheck className="size-3.5" /> Confidence: {titleCase(evaluation.confidence)}
                  </Badge>
                </div>
                <p className="mt-3 break-words text-lg font-semibold leading-7">
                  {formatEvaluationRecommendation(evaluation.recommendation)}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  This report supports recruiter review. It does not make or change a hiring decision.
                </p>
              </div>
            </section>

            <section aria-labelledby="category-scores-heading">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <h3 id="category-scores-heading" className="text-sm font-semibold">
                    Category scores
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Scores follow the weighted evaluation rubric for this job.
                  </p>
                </div>
              </div>
              {evaluation.categoryScores.length ? (
                <div className="mt-4 space-y-3">
                  {evaluation.categoryScores.map((category) => {
                    const score = numericScore(category.score);
                    return (
                      <div key={category.name} className="rounded-lg border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="break-words text-sm font-semibold">{category.name}</p>
                            <p className="mt-1 break-words text-xs leading-5 text-muted-foreground">
                              {category.rationale || "No category explanation was recorded."}
                            </p>
                          </div>
                          <div className="shrink-0 text-right">
                            <p className="text-sm font-semibold tabular-nums">{Math.round(score)} / 100</p>
                            <p className="text-[11px] text-muted-foreground">Weight {category.weight}%</p>
                          </div>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-primary" style={{ width: `${score}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  No category scores were recorded for this evaluation.
                </p>
              )}
            </section>

            <section aria-labelledby="requirements-heading">
              <h3 id="requirements-heading" className="text-sm font-semibold">
                Requirement matching
              </h3>
              <p className="mt-1 text-xs text-muted-foreground">
                A quick view of supported, partial, unverified, and unmet requirements.
              </p>
              {allRequirements.length ? (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {(
                    [
                      ["Matched", strongMatches],
                      ["Partial", partialMatches],
                      ["Needs verification", unverified],
                      ["Not met", confirmedGaps],
                    ] as const
                  ).map(([label, items]) => (
                    <div key={label} className="rounded-lg border p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                          {label}
                        </p>
                        <span className="text-xs font-semibold tabular-nums">{items.length}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {items.length ? (
                          items.map((item) => (
                            <Badge key={`${item.status}-${item.requirement}`} variant="outline">
                              {item.requirement}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">None recorded</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  Detailed requirement matching was not recorded for this evaluation.
                </p>
              )}
            </section>

            <div className="grid gap-8 xl:grid-cols-2">
              <section aria-labelledby="strong-matches-heading">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-emerald-600" />
                  <h3 id="strong-matches-heading" className="text-sm font-semibold">
                    Strong matches
                  </h3>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Requirements and strengths supported by resume evidence.
                </p>
                <div className="mt-4 space-y-3">
                  {strongMatches.length || partialMatches.length ? (
                    [...strongMatches, ...partialMatches].map((item) => (
                      <RequirementCard key={`${item.status}-${item.requirement}`} item={item} />
                    ))
                  ) : (
                    <FindingList
                      findings={evaluation.strengths}
                      emptyMessage="No strong matches were recorded."
                      tone="positive"
                    />
                  )}
                  {evaluation.strengths.length &&
                  (strongMatches.length || partialMatches.length) ? (
                    <FindingList
                      findings={evaluation.strengths}
                      emptyMessage="No additional strengths were recorded."
                      tone="positive"
                    />
                  ) : null}
                </div>
              </section>

              <section aria-labelledby="potential-gaps-heading">
                <div className="flex items-center gap-2">
                  <CircleAlert className="size-4 text-amber-600" />
                  <h3 id="potential-gaps-heading" className="text-sm font-semibold">
                    Potential gaps
                  </h3>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Missing evidence is kept separate from confirmed mismatches.
                </p>
                <div className="mt-4 space-y-3">
                  {unverified.length || confirmedGaps.length ? (
                    [...unverified, ...confirmedGaps].map((item) => (
                      <RequirementCard key={`${item.status}-${item.requirement}`} item={item} />
                    ))
                  ) : null}
                  {evaluation.gaps.length || (!unverified.length && !confirmedGaps.length) ? (
                    <FindingList
                      findings={evaluation.gaps}
                      emptyMessage="No potential gaps were recorded."
                      tone="caution"
                    />
                  ) : null}
                </div>
              </section>
            </div>

            <section aria-labelledby="evidence-heading">
              <div className="flex items-center gap-2">
                <Quote className="size-4 text-primary" />
                <h3 id="evidence-heading" className="text-sm font-semibold">
                  Supporting evidence
                </h3>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Important excerpts used to support the evaluation conclusions.
              </p>
              {evaluation.evidence.length ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {evaluation.evidence.slice(0, 6).map((item, index) => (
                    <article key={`${item.claim}-${index}`} className="rounded-lg border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <p className="break-words text-sm font-semibold leading-5">{item.claim}</p>
                        {item.category ? <Badge variant="outline">{item.category}</Badge> : null}
                      </div>
                      <blockquote className="mt-3 border-l-2 border-primary/30 pl-3 text-xs italic leading-5 text-muted-foreground">
                        “{item.resumeEvidence}”
                      </blockquote>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  No supporting excerpts were recorded for this evaluation.
                </p>
              )}
            </section>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
