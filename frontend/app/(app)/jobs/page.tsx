import type { Metadata } from "next";

import { JobList } from "@/components/jobs/job-list";
import { PageContainer } from "@/components/shared/page-container";
import { SectionHeader } from "@/components/shared/section-header";

export const metadata: Metadata = { title: "Jobs" };

export default function JobsPage() {
  return (
    <PageContainer>
      <SectionHeader
        title="Your open positions"
        description="Track active roles, applicant volume, and recruiting progress."
        className="mb-6"
      />
      <JobList />
    </PageContainer>
  );
}
