import type { Metadata } from "next";

import { PublicApplicationPage } from "@/components/public-application/public-application-page";

export const metadata: Metadata = {
  title: "Apply for a role",
  description: "Submit your application securely through TalentFlow AI.",
};

export default async function ApplyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PublicApplicationPage jobId={id} />;
}
