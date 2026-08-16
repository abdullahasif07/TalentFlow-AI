import type { Metadata } from "next";

import { ApolloProvider } from "@/components/providers/apollo-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "TalentFlow AI",
    template: "%s | TalentFlow AI",
  },
  description: "A focused AI recruiting workspace for modern hiring teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ApolloProvider>{children}</ApolloProvider>
      </body>
    </html>
  );
}
