import { ProcessingStateBadge } from "@/components/shared/processing-state-badge";
import {
  applicationProcessingPresentation,
  type ApplicationProcessingState,
} from "@/lib/application-processing";

export function ApplicationProcessingBadge({
  resumeState,
  evaluationState,
  hasEvaluation,
}: {
  resumeState: ApplicationProcessingState | null;
  evaluationState: ApplicationProcessingState;
  hasEvaluation: boolean;
}) {
  const presentation = applicationProcessingPresentation(
    resumeState,
    evaluationState,
    hasEvaluation,
  );
  return <ProcessingStateBadge state={presentation.state} label={presentation.label} />;
}
