export type ApplicationProcessingState =
  | "NOT_STARTED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export interface ApplicationProcessingPresentation {
  state: ApplicationProcessingState;
  label: string;
}

export function applicationProcessingPresentation(
  resumeState: ApplicationProcessingState | null,
  evaluationState: ApplicationProcessingState,
  hasEvaluation: boolean,
): ApplicationProcessingPresentation {
  if (evaluationState === "COMPLETED" && hasEvaluation) {
    return { state: "COMPLETED", label: "Evaluation complete" };
  }
  if (evaluationState === "PROCESSING") {
    return { state: "PROCESSING", label: "AI evaluating" };
  }
  if (evaluationState === "FAILED") {
    return { state: "FAILED", label: "AI evaluation failed" };
  }
  if (evaluationState === "COMPLETED") {
    return { state: "FAILED", label: "Evaluation unavailable" };
  }
  if (resumeState === "PROCESSING") {
    return { state: "PROCESSING", label: "Resume processing" };
  }
  if (resumeState === "FAILED") {
    return { state: "FAILED", label: "Resume processing failed" };
  }
  if (resumeState === "COMPLETED") {
    return { state: "NOT_STARTED", label: "Awaiting AI evaluation" };
  }
  return { state: "NOT_STARTED", label: "Resume queued" };
}
