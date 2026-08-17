import type { Metadata } from "next";
import { UserRound } from "lucide-react";

import { PlaceholderPage } from "@/components/shared/placeholder-page";

export const metadata: Metadata = { title: "Application" };

export default function ApplicationPlaceholderPage() {
  return (
    <PlaceholderPage
      title="Application details"
      description="The full candidate profile and evaluation report will be built in a future step."
      icon={UserRound}
    />
  );
}
