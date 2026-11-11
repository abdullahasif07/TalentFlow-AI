import type { Metadata } from "next";

import { LandingPage } from "@/components/landing/landing-page";

export const metadata: Metadata = {
  title: { absolute: "TalentFlow AI - AI-assisted applicant screening" },
};

export default function Home() {
  return <LandingPage />;
}
