import type { Metadata } from "next";
import { Plus } from "lucide-react";

import { JobList } from "@/components/jobs/job-list";
import { PageContainer } from "@/components/shared/page-container";
import { SectionHeader } from "@/components/shared/section-header";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Jobs" };

export default function JobsPage() {
  return (
    <PageContainer>
      <SectionHeader
        title="Jobs"
        description="Manage open roles and follow hiring progress from one place."
        action={
          <Button disabled title="Job creation will be available soon">
            <Plus /> Create Job
          </Button>
        }
        className="mb-6"
      />
      <JobList />
    </PageContainer>
  );
}
