"use client";

import { useQuery } from "@apollo/client/react";
import {
  ArrowRight,
  BriefcaseBusiness,
  Columns3,
  FileSearch,
  LoaderCircle,
  Scale,
  Sparkles,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useSession } from "@/components/providers/session-provider";
import { useDemoMode } from "@/components/public-application/use-demo-mode";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthRequestError, signInAsDemo } from "@/lib/auth";
import { stringList } from "@/lib/graphql/jobs";
import { GET_PUBLIC_JOBS, type PublicJobsQueryData } from "@/lib/graphql/public-jobs";
import { cn } from "@/lib/utils";

const FEATURES = [
  {
    icon: FileSearch,
    title: "Resume parsing",
    body: "Uploaded PDFs become structured experience, skills, and education - no manual data entry.",
  },
  {
    icon: Sparkles,
    title: "Evidence-based fit scores",
    body: "Each applicant is scored against a weighted, job-specific rubric, with resume evidence for every claim.",
  },
  {
    icon: Scale,
    title: "Side-by-side comparison",
    body: "Compare up to five evaluated candidates to see real trade-offs, not just a single number.",
  },
  {
    icon: Columns3,
    title: "Recruiter pipeline",
    body: "Drag candidates through stages, leave notes, and draft outreach - every change is audited.",
  },
];

export function LandingPage() {
  const router = useRouter();
  const { status, setRecruiter } = useSession();
  const demoMode = useDemoMode();
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const { data, loading } = useQuery<PublicJobsQueryData>(GET_PUBLIC_JOBS, {
    fetchPolicy: "cache-and-network",
  });
  const jobs = data?.publicJobs.items ?? [];
  const signedIn = status === "authenticated";

  async function tryAsRecruiter() {
    if (signedIn) {
      router.push("/dashboard");
      return;
    }
    if (!demoMode) {
      router.push("/login");
      return;
    }
    setDemoLoading(true);
    setDemoError(null);
    try {
      setRecruiter(await signInAsDemo());
      router.push("/dashboard");
    } catch (error) {
      setDemoError(
        error instanceof AuthRequestError ? error.message : "The demo is unavailable right now.",
      );
      setDemoLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f9f8]">
      <header className="border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Sparkles className="size-4.5" aria-hidden="true" />
            </span>
            <span className="font-semibold tracking-tight">TalentFlow AI</span>
          </Link>
          <Link
            href={signedIn ? "/dashboard" : "/login"}
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            {signedIn ? "Open dashboard" : "Recruiter sign in"}
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-6xl px-4 pb-14 pt-14 sm:px-6 sm:pt-20 lg:px-8">
          <Badge variant="outline" className="border-[#d7e8e3] bg-[#eef7f4] text-primary">
            <Sparkles className="size-3.5" /> AI-assisted recruiting
          </Badge>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-[-0.035em] sm:text-5xl">
            Screen applicants with evidence, not guesswork.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            TalentFlow AI reads every resume, scores it against a job-specific rubric, and shows
            recruiters exactly why - then keeps the human in charge of every decision.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:max-w-3xl">
            <button
              type="button"
              onClick={() => void tryAsRecruiter()}
              disabled={demoLoading}
              className="group flex items-start gap-4 rounded-2xl border bg-card p-5 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md disabled:opacity-70"
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                {demoLoading ? (
                  <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
                ) : (
                  <BriefcaseBusiness className="size-5" aria-hidden="true" />
                )}
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-1.5 font-semibold">
                  {signedIn ? "Open the recruiter dashboard" : "Try it as a recruiter"}
                  <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
                </span>
                <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                  {signedIn || !demoMode
                    ? "Review applicants, scores, and the hiring pipeline."
                    : "One click, no sign-up. Explore a workspace full of sample applicants."}
                </span>
              </span>
            </button>
            <a
              href="#open-roles"
              className="group flex items-start gap-4 rounded-2xl border bg-card p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#eef7f4] text-primary">
                <UserRound className="size-5" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-1.5 font-semibold">
                  Apply as a candidate
                  <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
                </span>
                <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                  Submit a sample resume and watch it get parsed and scored live.
                </span>
              </span>
            </a>
          </div>
          {demoError ? (
            <p role="alert" className="mt-4 text-sm text-rose-700">
              {demoError}
            </p>
          ) : null}
          <p className="mt-6 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Try the full loop:</span> apply to a role
            below, then open the recruiter view and find yourself in the applicant list.
          </p>
        </section>

        <section className="border-y bg-white">
          <div className="mx-auto grid max-w-6xl gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="bg-white px-6 py-8">
                <Icon className="size-5 text-primary" aria-hidden="true" />
                <h2 className="mt-4 font-semibold">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="open-roles" className="mx-auto max-w-6xl scroll-mt-6 px-4 py-14 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold tracking-tight">Open roles</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Pick a role and apply. A sample resume is available on the application page.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {loading && !data
              ? Array.from({ length: 3 }, (_, index) => (
                  <Skeleton key={index} className="h-40 w-full rounded-2xl" />
                ))
              : null}
            {!loading && jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No roles are open right now. Run the backend seed script to load demo roles.
              </p>
            ) : null}
            {jobs.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}/apply`}
                className="group flex flex-col rounded-2xl border bg-card p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md"
              >
                <span className="text-xs font-semibold text-primary">{job.company.name}</span>
                <span className="mt-1.5 font-semibold">{job.title}</span>
                {job.experienceRequirement ? (
                  <span className="mt-1 text-xs text-muted-foreground">
                    {job.experienceRequirement}
                  </span>
                ) : null}
                <span className="mt-4 flex flex-wrap gap-1.5">
                  {stringList(job.requiredSkills)
                    .slice(0, 4)
                    .map((skill) => (
                      <Badge key={skill} variant="secondary">
                        {skill}
                      </Badge>
                    ))}
                </span>
                <span
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "mt-5 self-start group-hover:border-primary/40",
                  )}
                >
                  Apply <ArrowRight />
                </span>
              </Link>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t bg-white/60">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:justify-between sm:px-6 lg:px-8">
          <span>Next.js · FastAPI · GraphQL · PostgreSQL · Celery · OpenAI</span>
          <span>All companies, people, and applications in the demo are fictional.</span>
        </div>
      </footer>
    </div>
  );
}

