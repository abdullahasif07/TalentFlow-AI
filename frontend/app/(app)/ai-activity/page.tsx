import type { Metadata } from "next";
import { Sparkles } from "lucide-react";

import { PlaceholderPage } from "@/components/shared/placeholder-page";

export const metadata: Metadata = { title: "AI Activity" };

export default function AIActivityPage() {
  return <PlaceholderPage title="AI Activity" description="Resume processing, criteria generation, and evaluation activity will be visible here." icon={Sparkles} />;
}
