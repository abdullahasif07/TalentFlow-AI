import type { Metadata } from "next";
import { Users } from "lucide-react";

import { PlaceholderPage } from "@/components/shared/placeholder-page";

export const metadata: Metadata = { title: "Candidates" };

export default function CandidatesPage() {
  return <PlaceholderPage title="Candidates" description="The searchable talent database and candidate profiles will live here." icon={Users} />;
}
