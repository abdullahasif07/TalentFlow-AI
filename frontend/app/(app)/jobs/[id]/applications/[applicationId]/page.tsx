import type { Metadata } from "next";

import { ApplicationDetailPage } from "@/components/applications/application-detail";
import { PageContainer } from "@/components/shared/page-container";

export const metadata: Metadata = { title: "Application" };

export default async function ApplicationPage({
  params,
}: {
  params: Promise<{ id: string; applicationId: string }>;
}) {
  const { id, applicationId } = await params;

  return (
    <PageContainer>
      <ApplicationDetailPage jobId={id} applicationId={applicationId} />
    </PageContainer>
  );
}
