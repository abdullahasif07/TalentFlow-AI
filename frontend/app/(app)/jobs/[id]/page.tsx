import type { Metadata } from "next";

import { JobDetail } from "@/components/jobs/job-detail";
import { PageContainer } from "@/components/shared/page-container";

export const metadata: Metadata = { title: "Job details" };

export default async function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <PageContainer>
      <JobDetail jobId={id} />
    </PageContainer>
  );
}
