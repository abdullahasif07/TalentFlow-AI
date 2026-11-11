import { RecruiterGuard } from "@/components/auth/recruiter-guard";
import { AppShell } from "@/components/layout/app-shell";

export default function RecruiterLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <RecruiterGuard>
      <AppShell>{children}</AppShell>
    </RecruiterGuard>
  );
}
