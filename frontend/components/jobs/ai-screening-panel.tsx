"use client";

import { useMutation } from "@apollo/client/react";
import { LoaderCircle, RefreshCw, Sparkles, WandSparkles } from "lucide-react";
import { useState } from "react";

import { ActionFeedback } from "@/components/shared/action-feedback";
import { Button } from "@/components/ui/button";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import {
  GENERATE_JOB_CRITERIA,
  type GenerateJobCriteriaData,
  type RecruiterJob,
  SCREEN_JOB_APPLICANTS,
  type ScreenJobApplicantsData,
} from "@/lib/graphql/jobs";

interface Feedback {
  variant: "success" | "error";
  message: string;
}

export function AIScreeningPanel({
  job,
  onQueued,
}: {
  job: RecruiterJob;
  onQueued: () => void;
}) {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [generateCriteria, { loading: generating }] = useMutation<GenerateJobCriteriaData>(
    GENERATE_JOB_CRITERIA,
  );
  const [screenApplicants, { loading: screening }] = useMutation<ScreenJobApplicantsData>(
    SCREEN_JOB_APPLICANTS,
    { refetchQueries: ["GetJobApplications"] },
  );
  const state = job.criteriaProcessingState;
  const unscored = Math.max(job.applicantCount - job.recommendedCandidateCount, 0);

  async function handleGenerate() {
    setFeedback(null);
    try {
      const result = await generateCriteria({ variables: { input: { jobId: job.id } } });
      const payload = result.data?.generateJobCriteria;
      if (!payload?.success) {
        setFeedback({
          variant: "error",
          message: payload?.errors[0]?.message ?? "Unable to start rubric generation.",
        });
        return;
      }
      setFeedback({
        variant: "success",
        message: "Generating the scoring rubric. Waiting applicants are scored automatically afterwards.",
      });
      onQueued();
    } catch (error) {
      setFeedback({ variant: "error", message: graphQLErrorMessage(error) });
    }
  }

  async function handleScreen() {
    setFeedback(null);
    try {
      const result = await screenApplicants({ variables: { input: { jobId: job.id } } });
      const payload = result.data?.screenJobApplicants;
      if (!payload?.success) {
        setFeedback({
          variant: "error",
          message: payload?.errors[0]?.message ?? "Unable to start screening.",
        });
        return;
      }
      setFeedback({
        variant: "success",
        message:
          payload.queuedCount > 0
            ? `Scoring ${payload.queuedCount} applicant${payload.queuedCount === 1 ? "" : "s"}. Scores appear in the list as they finish.`
            : "Every applicant with a processed resume already has a score.",
      });
      onQueued();
    } catch (error) {
      setFeedback({ variant: "error", message: graphQLErrorMessage(error) });
    }
  }

  return (
    <div className="w-full max-w-sm space-y-2 rounded-xl border bg-card p-3.5 xl:w-80">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#eef7f4] text-primary">
          <Sparkles className="size-3.5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">AI screening</p>
          <p className="text-xs leading-5 text-muted-foreground">
            {state === "COMPLETED"
              ? unscored > 0
                ? `Rubric ready · ${unscored} applicant${unscored === 1 ? "" : "s"} without a score`
                : "Rubric ready · all applicants scored"
              : state === "PROCESSING"
                ? "Generating a weighted scoring rubric from this job…"
                : state === "FAILED"
                  ? "Rubric generation failed. You can retry it."
                  : "No scoring rubric yet."}
          </p>
        </div>
      </div>

      {state === "COMPLETED" ? (
        <Button
          size="sm"
          variant="outline"
          className="w-full"
          disabled={screening}
          onClick={() => void handleScreen()}
        >
          {screening ? <LoaderCircle className="animate-spin" /> : <WandSparkles />}
          Screen unscored applicants
        </Button>
      ) : state === "PROCESSING" ? (
        <Button size="sm" variant="outline" className="w-full" disabled>
          <LoaderCircle className="animate-spin" /> Generating rubric…
        </Button>
      ) : (
        <Button size="sm" className="w-full" disabled={generating} onClick={() => void handleGenerate()}>
          {generating ? <LoaderCircle className="animate-spin" /> : state === "FAILED" ? <RefreshCw /> : <WandSparkles />}
          {state === "FAILED" ? "Retry rubric generation" : "Generate scoring rubric"}
        </Button>
      )}

      {feedback ? <ActionFeedback variant={feedback.variant} message={feedback.message} /> : null}
    </div>
  );
}
