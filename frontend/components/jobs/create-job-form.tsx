"use client";

import { useMutation } from "@apollo/client/react";
import { ArrowLeft, LoaderCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ActionFeedback } from "@/components/shared/action-feedback";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import {
  CREATE_JOB,
  type CreateJobData,
  type CreateJobInput,
  type JobStatus,
  parseSkillList,
} from "@/lib/graphql/jobs";
import { cn } from "@/lib/utils";

type Field = "title" | "description" | "requiredSkills";

function FieldLabel({ htmlFor, children, required }: {
  htmlFor: string;
  children: React.ReactNode;
  required?: boolean;
}) {
  return (
    <label htmlFor={htmlFor} className="text-sm font-semibold">
      {children} {required ? <span className="text-destructive">*</span> : null}
    </label>
  );
}

function SkillPreview({ value }: { value: string }) {
  const skills = parseSkillList(value);
  if (!skills.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <Badge key={skill} variant="secondary">{skill}</Badge>
      ))}
    </div>
  );
}

export function CreateJobForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [preferredSkills, setPreferredSkills] = useState("");
  const [experience, setExperience] = useState("");
  const [status, setStatus] = useState<JobStatus>("OPEN");
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createJob, { loading }] = useMutation<CreateJobData, { input: CreateJobInput }>(
    CREATE_JOB,
    { refetchQueries: ["GetJobs"] },
  );

  function validate() {
    const next: Partial<Record<Field, string>> = {};
    if (!title.trim()) next.title = "Enter a job title.";
    else if (title.trim().length > 255) next.title = "Keep the title under 255 characters.";
    if (description.trim().length < 30) {
      next.description = "Add a description of at least 30 characters so the AI can build a useful rubric.";
    }
    if (!parseSkillList(requiredSkills).length) next.requiredSkills = "Add at least one required skill.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    if (!validate()) return;
    try {
      const result = await createJob({
        variables: {
          input: {
            title: title.trim(),
            description: description.trim(),
            requiredSkills: parseSkillList(requiredSkills),
            preferredSkills: parseSkillList(preferredSkills),
            experienceRequirement: experience.trim() || null,
            status,
          },
        },
      });
      const payload = result.data?.createJob;
      if (!payload?.success || !payload.job) {
        setSubmitError(payload?.errors[0]?.message ?? "Unable to create the job.");
        return;
      }
      router.push(`/jobs/${payload.job.id}`);
    } catch (error) {
      setSubmitError(graphQLErrorMessage(error));
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        href="/jobs"
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3 text-muted-foreground")}
      >
        <ArrowLeft /> Back to jobs
      </Link>
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Create a job</h2>
        <p className="mt-2 flex items-start gap-2 text-sm text-muted-foreground">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          After you save, AI turns this description into a weighted scoring rubric and scores
          every applicant against it.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form className="space-y-5" noValidate onSubmit={(event) => void handleSubmit(event)}>
            <div>
              <FieldLabel htmlFor="job-title" required>Job title</FieldLabel>
              <Input
                id="job-title"
                className="mt-2"
                placeholder="e.g. Senior Backend Engineer"
                value={title}
                aria-invalid={Boolean(errors.title)}
                onChange={(event) => setTitle(event.target.value)}
              />
              {errors.title ? <p role="alert" className="mt-1.5 text-xs text-rose-700">{errors.title}</p> : null}
            </div>

            <div>
              <FieldLabel htmlFor="job-description" required>Description</FieldLabel>
              <Textarea
                id="job-description"
                className="mt-2"
                rows={7}
                placeholder="What the person will own, the team, and what success looks like."
                value={description}
                aria-invalid={Boolean(errors.description)}
                onChange={(event) => setDescription(event.target.value)}
              />
              {errors.description ? (
                <p role="alert" className="mt-1.5 text-xs text-rose-700">{errors.description}</p>
              ) : null}
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="job-required" required>Required skills</FieldLabel>
                <Input
                  id="job-required"
                  className="mt-2"
                  placeholder="Python, PostgreSQL, APIs"
                  value={requiredSkills}
                  aria-invalid={Boolean(errors.requiredSkills)}
                  onChange={(event) => setRequiredSkills(event.target.value)}
                />
                <p className="mt-1 text-xs text-muted-foreground">Separate skills with commas.</p>
                {errors.requiredSkills ? (
                  <p role="alert" className="mt-1 text-xs text-rose-700">{errors.requiredSkills}</p>
                ) : null}
                <SkillPreview value={requiredSkills} />
              </div>
              <div>
                <FieldLabel htmlFor="job-preferred">Preferred skills</FieldLabel>
                <Input
                  id="job-preferred"
                  className="mt-2"
                  placeholder="AWS, GraphQL"
                  value={preferredSkills}
                  onChange={(event) => setPreferredSkills(event.target.value)}
                />
                <p className="mt-1 text-xs text-muted-foreground">Optional.</p>
                <SkillPreview value={preferredSkills} />
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="job-experience">Experience requirement</FieldLabel>
                <Input
                  id="job-experience"
                  className="mt-2"
                  placeholder="e.g. 4+ years in backend engineering"
                  value={experience}
                  onChange={(event) => setExperience(event.target.value)}
                />
              </div>
              <fieldset>
                <legend className="text-sm font-semibold">Visibility</legend>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  {([
                    ["OPEN", "Open", "Accepting applications"],
                    ["DRAFT", "Draft", "Hidden from applicants"],
                  ] as const).map(([value, label, hint]) => (
                    <label
                      key={value}
                      className={cn(
                        "cursor-pointer rounded-lg border p-3 text-sm transition",
                        status === value ? "border-primary bg-[#eef7f4]" : "hover:bg-muted/40",
                      )}
                    >
                      <input
                        type="radio"
                        name="job-status"
                        value={value}
                        checked={status === value}
                        onChange={() => setStatus(value)}
                        className="sr-only"
                      />
                      <span className="block font-semibold">{label}</span>
                      <span className="block text-xs text-muted-foreground">{hint}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>

            {submitError ? <ActionFeedback variant="error" message={submitError} /> : null}

            <div className="flex justify-end gap-2 border-t pt-5">
              <Link href="/jobs" className={buttonVariants({ variant: "ghost" })}>Cancel</Link>
              <Button type="submit" disabled={loading}>
                {loading ? <LoaderCircle className="animate-spin" /> : null}
                Create job
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
