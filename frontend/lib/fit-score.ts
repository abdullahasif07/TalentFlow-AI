import type { ApplicationProcessingState } from "@/lib/application-processing";

export function completedFitScore(
  score: number | string | null,
  processingState: ApplicationProcessingState,
) {
  if (processingState !== "COMPLETED" || score === null) return null;
  const numericScore = Number(score);
  return Number.isFinite(numericScore) ? numericScore : null;
}
