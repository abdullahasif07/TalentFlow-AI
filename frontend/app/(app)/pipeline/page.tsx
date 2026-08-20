import type { Metadata } from "next";

import { HiringPipelineBoard } from "@/components/pipeline/hiring-pipeline-board";
import { PageContainer } from "@/components/shared/page-container";

export const metadata: Metadata = { title: "Pipeline" };

export default function PipelinePage() {
  return (
    <PageContainer className="max-w-none overflow-hidden">
      <HiringPipelineBoard />
    </PageContainer>
  );
}
