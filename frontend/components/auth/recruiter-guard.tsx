"use client";

import { LoaderCircle, ServerCrash } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/button";

export function RecruiterGuard({ children }: Readonly<{ children: React.ReactNode }>) {
  const { status, refresh } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (status === "authenticated") return <>{children}</>;

  if (status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-sm text-center">
          <ServerCrash className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
          <h1 className="mt-4 text-lg font-semibold">Can’t reach the TalentFlow API</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Make sure the backend is running, then try again.
          </p>
          <Button className="mt-5" variant="outline" onClick={() => void refresh()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background" aria-busy="true">
      <LoaderCircle className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
    </div>
  );
}
