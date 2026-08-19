import {
  Award,
  BriefcaseBusiness,
  ExternalLink,
  FileText,
  FolderGit2,
  GraduationCap,
  Sparkles,
} from "lucide-react";

import { ProcessingStateBadge } from "@/components/shared/processing-state-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationDetail } from "@/lib/graphql/applications";
import {
  externalHttpUrl,
  normalizeParsedResume,
  resumeFilename,
} from "@/lib/resume";
import { cn } from "@/lib/utils";

type Resume = ApplicationDetail["resume"];

function dateRange(start: string | null, end: string | null) {
  if (!start && !end) return "Dates not provided";
  return [start || "Start not provided", end || "Present"].join(" – ");
}

function ProcessingMessage({ state }: { state: NonNullable<Resume>["processingState"] }) {
  const messages = {
    NOT_STARTED: "This resume has been uploaded but has not been processed yet.",
    PROCESSING: "Resume text and structured information are currently being processed.",
    COMPLETED: "Processing completed, but no structured resume information was returned.",
    FAILED: "Resume processing failed. The original file is still available where supported.",
  } as const;

  return (
    <div className="rounded-lg border border-dashed bg-muted/20 p-5 text-center">
      <p className="text-sm font-medium">Structured resume unavailable</p>
      <p className="mx-auto mt-1 max-w-xl text-xs leading-5 text-muted-foreground">
        {messages[state]}
      </p>
    </div>
  );
}

export function ResumeOverview({
  resume,
  fallbackFileUrl,
}: {
  resume: Resume;
  fallbackFileUrl: string | null;
}) {
  const fileUrl = resume?.fileUrl ?? fallbackFileUrl;
  const publicFileUrl = externalHttpUrl(fileUrl);
  const parsed = normalizeParsedResume(resume?.parsedData);
  const state = resume?.processingState ?? "NOT_STARTED";

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="rounded-lg bg-muted p-2 text-muted-foreground">
            <FileText className="size-4.5" />
          </div>
          <div className="min-w-0">
            <CardTitle>Resume</CardTitle>
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {fileUrl ? resumeFilename(fileUrl) : "No resume file supplied"}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <ProcessingStateBadge state={state} />
          {publicFileUrl ? (
            <a
              href={publicFileUrl}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Open resume <ExternalLink />
            </a>
          ) : fileUrl ? (
            <span
              title="Local resume downloads are not exposed by the backend yet"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), "cursor-not-allowed opacity-50")}
            >
              File stored locally
            </span>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-7">
        {!resume ? (
          <div className="rounded-lg border border-dashed bg-muted/20 p-5 text-center">
            <p className="text-sm font-medium">Resume record unavailable</p>
            <p className="mt-1 text-xs text-muted-foreground">
              The application does not currently have an associated resume record.
            </p>
          </div>
        ) : !parsed ? (
          <ProcessingMessage state={state} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg border bg-muted/20 p-4 sm:col-span-2">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  <Sparkles className="size-3.5" /> Professional summary
                </div>
                <p className="mt-2 whitespace-pre-line break-words text-sm leading-6 text-foreground">
                  {parsed.professionalSummary || "No professional summary was identified."}
                </p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-4">
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  Total experience
                </p>
                <p className="mt-2 text-2xl font-semibold tracking-tight">
                  {parsed.totalExperienceYears === null
                    ? "Not stated"
                    : `${parsed.totalExperienceYears} years`}
                </p>
              </div>
            </div>

            {(parsed.skills.length > 0 || parsed.technologies.length > 0) ? (
              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Skills</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {parsed.skills.map((skill) => <Badge key={skill} variant="secondary" className="max-w-full break-all">{skill}</Badge>)}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">Technologies</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {parsed.technologies.map((technology) => <Badge key={technology} variant="outline" className="max-w-full break-all">{technology}</Badge>)}
                  </div>
                </div>
              </div>
            ) : null}

            {parsed.employmentHistory.length ? (
              <section>
                <div className="flex items-center gap-2">
                  <BriefcaseBusiness className="size-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold">Employment history</h3>
                </div>
                <div className="mt-4 space-y-0 border-l-2 border-border pl-5">
                  {parsed.employmentHistory.map((employment, index) => (
                    <article key={`${employment.company}-${employment.role}-${index}`} className="relative pb-6 last:pb-0">
                      <span className="absolute -left-[27px] top-1 size-3 rounded-full border-2 border-primary bg-card" />
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                        <div>
                          <p className="break-words text-sm font-semibold">{employment.role || "Role not provided"}</p>
                          <p className="break-words text-xs text-muted-foreground">{employment.company || "Company not provided"}</p>
                        </div>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {dateRange(employment.startDate, employment.endDate)}
                        </span>
                      </div>
                      {employment.description ? (
                        <p className="mt-2 whitespace-pre-line break-words text-sm leading-6 text-muted-foreground">{employment.description}</p>
                      ) : null}
                      {employment.technologies.length ? (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {employment.technologies.map((technology) => (
                            <Badge key={technology} variant="outline" className="max-w-full break-all text-[10px]">{technology}</Badge>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {parsed.education.length ? (
              <section>
                <div className="flex items-center gap-2">
                  <GraduationCap className="size-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold">Education</h3>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {parsed.education.map((education, index) => (
                    <article key={`${education.institution}-${index}`} className="rounded-lg border p-3.5">
                      <p className="break-words text-sm font-semibold">{education.degree || "Degree not provided"}</p>
                      <p className="mt-1 break-words text-xs text-muted-foreground">
                        {[education.field, education.institution].filter(Boolean).join(" · ") || "Institution not provided"}
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {dateRange(education.startDate, education.endDate)}
                      </p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {parsed.projects.length ? (
              <section>
                <div className="flex items-center gap-2">
                  <FolderGit2 className="size-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold">Projects</h3>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {parsed.projects.map((project, index) => {
                    const projectUrl = externalHttpUrl(project.url);
                    return (
                      <article key={`${project.name}-${index}`} className="rounded-lg border p-3.5">
                        <div className="flex items-start justify-between gap-3">
                          <p className="break-words text-sm font-semibold">{project.name || "Unnamed project"}</p>
                          {projectUrl ? (
                            <a href={projectUrl} target="_blank" rel="noreferrer" className="text-primary hover:text-primary/75" aria-label={`Open ${project.name || "project"}`}>
                              <ExternalLink className="size-3.5" />
                            </a>
                          ) : null}
                        </div>
                        {project.description ? <p className="mt-2 whitespace-pre-line break-words text-xs leading-5 text-muted-foreground">{project.description}</p> : null}
                        {project.technologies.length ? (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {project.technologies.map((technology) => <Badge key={technology} variant="outline" className="max-w-full break-all text-[10px]">{technology}</Badge>)}
                          </div>
                        ) : null}
                      </article>
                    );
                  })}
                </div>
              </section>
            ) : null}

            {parsed.certifications.length ? (
              <section>
                <div className="flex items-center gap-2">
                  <Award className="size-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold">Certifications</h3>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {parsed.certifications.map((certification, index) => (
                    <Badge key={`${certification.name}-${index}`} variant="secondary" className="max-w-full whitespace-normal break-words">
                      {certification.name || "Certification"}
                      {certification.issuer ? ` · ${certification.issuer}` : ""}
                    </Badge>
                  ))}
                </div>
              </section>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
