"use client";

import { ArrowLeft, FlaskConical, LoaderCircle, LogIn, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useSession } from "@/components/providers/session-provider";
import { useDemoMode } from "@/components/public-application/use-demo-mode";
import { ActionFeedback } from "@/components/shared/action-feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthRequestError, safeNextPath, signIn, signInAsDemo } from "@/lib/auth";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));
  const { status, setRecruiter } = useSession();
  const demoMode = useDemoMode();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState<"password" | "demo" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") router.replace(nextPath);
  }, [status, router, nextPath]);

  async function run(kind: "password" | "demo") {
    setPending(kind);
    setError(null);
    try {
      const session = kind === "demo" ? await signInAsDemo() : await signIn(email, password);
      setRecruiter(session);
      router.replace(nextPath);
    } catch (caught) {
      setError(
        caught instanceof AuthRequestError ? caught.message : "Unable to sign in. Please try again.",
      );
      setPending(null);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#f7f9f8]">
      <div className="mx-auto w-full max-w-md px-4 pt-6">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" /> Back to home
        </Link>
      </div>
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 pb-16">
        <div className="rounded-2xl border bg-card p-6 shadow-[0_16px_45px_rgba(23,32,51,0.06)] sm:p-8">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="size-5" aria-hidden="true" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight">Recruiter sign in</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Sign in to review applicants and manage your hiring pipeline.
          </p>

          {demoMode ? (
            <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                <FlaskConical className="size-4" aria-hidden="true" /> Just exploring?
              </p>
              <p className="mt-1 text-xs leading-5 text-amber-900">
                Use the demo recruiter account - fictional data, no sign-up needed.
              </p>
              <Button
                className="mt-3 w-full"
                disabled={pending !== null}
                onClick={() => void run("demo")}
              >
                {pending === "demo" ? <LoaderCircle className="animate-spin" /> : <LogIn />}
                Continue as demo recruiter
              </Button>
            </div>
          ) : null}

          <form
            className="mt-6 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void run("password");
            }}
          >
            <div>
              <label htmlFor="login-email" className="text-sm font-semibold">
                Email
              </label>
              <Input
                id="login-email"
                type="email"
                autoComplete="username"
                required
                className="mt-2"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div>
              <label htmlFor="login-password" className="text-sm font-semibold">
                Password
              </label>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                className="mt-2"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            {error ? <ActionFeedback variant="error" message={error} /> : null}
            <Button
              type="submit"
              variant={demoMode ? "outline" : "default"}
              className="w-full"
              disabled={pending !== null}
            >
              {pending === "password" ? <LoaderCircle className="animate-spin" /> : null}
              Sign in
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
