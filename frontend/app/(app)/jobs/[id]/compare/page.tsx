import type { Metadata } from "next";

import { CandidateComparison } from "@/components/jobs/candidate-comparison";
import { PageContainer } from "@/components/shared/page-container";
import {
  comparisonJobIdError,
  parseComparisonSelection,
} from "@/lib/comparison-selection";

export const metadata: Metadata = { title: "Candidate comparison" };

export default async function CandidateComparisonPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ applications?: string | string[] }>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const selection = parseComparisonSelection(query.applications);
  const inputError = comparisonJobIdError(id) ?? selection.error;

  return (
    <PageContainer>
      <CandidateComparison
        jobId={id}
        applicationIds={selection.ids}
        inputError={inputError}
      />
    </PageContainer>
  );
}
