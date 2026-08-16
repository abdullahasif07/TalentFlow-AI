import type { Metadata } from "next";
import { Columns3 } from "lucide-react";

import { PlaceholderPage } from "@/components/shared/placeholder-page";

export const metadata: Metadata = { title: "Pipeline" };

export default function PipelinePage() {
  return <PlaceholderPage title="Pipeline" description="A visual stage-by-stage view of applications will be added here." icon={Columns3} />;
}
