import type { Metadata } from "next";

import { ApolloProvider } from "@/components/providers/apollo-provider";
import { SessionProvider } from "@/components/providers/session-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "TalentFlow AI",
    template: "%s | TalentFlow AI",
  },
  description: "AI-assisted applicant screening: structured resume parsing, evidence-based fit scores, and a recruiter pipeline.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ApolloProvider>
          <SessionProvider>{children}</SessionProvider>
        </ApolloProvider>
      </body>
    </html>
  );
}
