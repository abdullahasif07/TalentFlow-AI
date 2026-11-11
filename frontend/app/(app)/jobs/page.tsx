import type { Metadata } from "next";
import { Plus } from "lucide-react";
import Link from "next/link";

import { JobList } from "@/components/jobs/job-list";
import { PageContainer } from "@/components/shared/page-container";
import { SectionHeader } from "@/components/shared/section-header";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Jobs" };

export default function JobsPage() {
  return (
    <PageContainer>
      <SectionHeader
        title="Jobs"
        description="Manage open roles and follow hiring progress from one place."
        action={
          <Link href="/jobs/new" className={buttonVariants()}>
            <Plus /> Create job
          </Link>
        }
        className="mb-6"
      />
      <JobList />
    </PageContainer>
  );
}
