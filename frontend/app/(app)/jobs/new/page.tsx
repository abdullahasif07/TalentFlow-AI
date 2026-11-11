import type { Metadata } from "next";

import { CreateJobForm } from "@/components/jobs/create-job-form";
import { PageContainer } from "@/components/shared/page-container";

export const metadata: Metadata = { title: "Create job" };

export default function NewJobPage() {
  return (
    <PageContainer>
      <CreateJobForm />
    </PageContainer>
  );
}
