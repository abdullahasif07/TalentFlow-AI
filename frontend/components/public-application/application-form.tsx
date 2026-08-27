"use client";

import { AlertCircle, CheckCircle2, LoaderCircle, Send } from "lucide-react";
import { useState } from "react";

import { ResumeUpload } from "@/components/public-application/resume-upload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  configuredMaxResumeSizeMb,
  maxResumeSizeBytes,
  type PublicApplicationErrors,
  type PublicApplicationField,
  type PublicApplicationValues,
  validatePublicApplication,
  validateResume,
} from "@/lib/public-application";
import {
  PublicApplicationRequestError,
  type PublicApplicationReceipt,
  publicSubmissionErrorMessage,
  submitPublicApplication,
} from "@/lib/public-application-submission";
import { cn } from "@/lib/utils";

const initialValues: PublicApplicationValues = {
  fullName: "",
  email: "",
  phone: "",
  linkedinUrl: "",
  githubUrl: "",
  portfolioUrl: "",
  coverLetter: "",
};

const inputIds: Record<PublicApplicationField, string> = {
  fullName: "full-name",
  email: "email",
  phone: "phone",
  linkedinUrl: "linkedin-url",
  githubUrl: "github-url",
  portfolioUrl: "portfolio-url",
  coverLetter: "cover-letter",
  resume: "resume-upload",
};

interface FieldProps {
  id: string;
  label: string;
  required?: boolean;
  helper?: string;
  error?: string;
  children: React.ReactNode;
}

function Field({ id, label, required, helper, error, children }: FieldProps) {
  const helperId = `${id}-help`;
  const errorId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className="text-sm font-semibold">
        {label} {required ? <span className="text-destructive">*</span> : null}
      </label>
      {helper ? (
        <p id={helperId} className="mt-1 text-xs leading-5 text-muted-foreground">
          {helper}
        </p>
      ) : null}
      <div className="mt-2">{children}</div>
      {error ? (
        <p id={errorId} role="alert" className="mt-1.5 text-xs font-medium text-rose-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function SuccessState({ receipt }: { receipt: PublicApplicationReceipt }) {
  return (
    <div className="flex min-h-[520px] flex-col items-center justify-center px-5 py-12 text-center sm:px-10">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
        <CheckCircle2 className="size-7" aria-hidden="true" />
      </span>
      <h2 className="mt-5 text-2xl font-semibold tracking-tight">
        Application submitted successfully
      </h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
        Your application for <span className="font-semibold text-foreground">{receipt.jobTitle}</span>{" "}
        has been received and will be reviewed by the recruiting team.
      </p>
      <div className="mt-7 grid w-full max-w-md gap-3 rounded-xl border bg-muted/20 p-4 text-left sm:grid-cols-2">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
            Status
          </p>
          <p className="mt-1 text-sm font-semibold text-emerald-700">Received</p>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
            Reference
          </p>
          <p className="mt-1 text-sm font-semibold">Application #{receipt.id}</p>
        </div>
      </div>
      <p className="mt-5 max-w-md text-xs leading-5 text-muted-foreground">
        You can safely close this page. Please keep your application reference for your records.
      </p>
    </div>
  );
}

export function ApplicationForm({ jobId }: { jobId: string }) {
  const maxSizeMb = configuredMaxResumeSizeMb(
    process.env.NEXT_PUBLIC_MAX_RESUME_SIZE_MB,
  );
  const maxSize = maxResumeSizeBytes(maxSizeMb);
  const [values, setValues] = useState(initialValues);
  const [resume, setResume] = useState<File | null>(null);
  const [errors, setErrors] = useState<PublicApplicationErrors>({});
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [receipt, setReceipt] = useState<PublicApplicationReceipt | null>(null);

  function updateField(field: keyof PublicApplicationValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    if (errors[field]) {
      setErrors((current) => ({ ...current, [field]: undefined }));
    }
    if (submissionError) setSubmissionError(null);
  }

  function updateResume(file: File | null) {
    setResume(file);
    const error = validateResume(file, maxSize);
    setErrors((current) => ({ ...current, resume: error }));
    if (submissionError) setSubmissionError(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const validationErrors = validatePublicApplication(values, resume, maxSize);
    setErrors(validationErrors);
    setSubmissionError(null);
    const firstInvalid = Object.keys(validationErrors)[0] as
      | PublicApplicationField
      | undefined;
    if (firstInvalid) {
      requestAnimationFrame(() => document.getElementById(inputIds[firstInvalid])?.focus());
      return;
    }
    if (!resume) return;

    setSubmitting(true);
    try {
      const payload = await submitPublicApplication({
        jobId,
        ...values,
        resume,
      });
      if (!payload.success || !payload.application) {
        const backendError = payload.errors[0];
        setSubmissionError(
          backendError
            ? publicSubmissionErrorMessage(backendError)
            : "We couldn’t submit your application. Please try again.",
        );
        return;
      }
      setReceipt(payload.application);
    } catch (error) {
      setSubmissionError(
        error instanceof PublicApplicationRequestError
          ? error.message
          : "We couldn’t submit your application. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (receipt) return <SuccessState receipt={receipt} />;

  return (
    <form className="p-5 sm:p-7 lg:p-8" noValidate onSubmit={(event) => void handleSubmit(event)}>
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.1em] text-primary">Application</p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">
          Tell us about yourself
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Fields marked with an asterisk are required.
        </p>
      </div>

      {submissionError ? (
        <div
          role="alert"
          className="mt-6 flex gap-3 rounded-xl border border-rose-200 bg-rose-50/60 p-4 text-sm text-rose-800"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{submissionError}</p>
        </div>
      ) : null}

      <div className="mt-7 grid gap-5 sm:grid-cols-2">
        <Field id="full-name" label="Full name" required error={errors.fullName}>
          <Input
            id="full-name"
            name="fullName"
            autoComplete="name"
            value={values.fullName}
            disabled={submitting}
            aria-invalid={Boolean(errors.fullName)}
            aria-describedby={errors.fullName ? "full-name-error" : undefined}
            className={cn(errors.fullName && "border-rose-300")}
            onChange={(event) => updateField("fullName", event.target.value)}
          />
        </Field>
        <Field id="email" label="Email address" required error={errors.email}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={values.email}
            disabled={submitting}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            className={cn(errors.email && "border-rose-300")}
            onChange={(event) => updateField("email", event.target.value)}
          />
        </Field>
        <Field id="phone" label="Phone" error={errors.phone}>
          <Input
            id="phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            placeholder="+1 555 000 0000"
            value={values.phone}
            disabled={submitting}
            onChange={(event) => updateField("phone", event.target.value)}
          />
        </Field>
        <Field id="linkedin-url" label="LinkedIn URL" error={errors.linkedinUrl}>
          <Input
            id="linkedin-url"
            name="linkedinUrl"
            type="url"
            autoComplete="url"
            placeholder="https://linkedin.com/in/your-name"
            value={values.linkedinUrl}
            disabled={submitting}
            aria-invalid={Boolean(errors.linkedinUrl)}
            aria-describedby={errors.linkedinUrl ? "linkedin-url-error" : undefined}
            className={cn(errors.linkedinUrl && "border-rose-300")}
            onChange={(event) => updateField("linkedinUrl", event.target.value)}
          />
        </Field>
        <Field id="github-url" label="GitHub URL" error={errors.githubUrl}>
          <Input
            id="github-url"
            name="githubUrl"
            type="url"
            placeholder="https://github.com/your-name"
            value={values.githubUrl}
            disabled={submitting}
            aria-invalid={Boolean(errors.githubUrl)}
            aria-describedby={errors.githubUrl ? "github-url-error" : undefined}
            className={cn(errors.githubUrl && "border-rose-300")}
            onChange={(event) => updateField("githubUrl", event.target.value)}
          />
        </Field>
        <Field id="portfolio-url" label="Portfolio URL" error={errors.portfolioUrl}>
          <Input
            id="portfolio-url"
            name="portfolioUrl"
            type="url"
            placeholder="https://your-portfolio.com"
            value={values.portfolioUrl}
            disabled={submitting}
            aria-invalid={Boolean(errors.portfolioUrl)}
            aria-describedby={errors.portfolioUrl ? "portfolio-url-error" : undefined}
            className={cn(errors.portfolioUrl && "border-rose-300")}
            onChange={(event) => updateField("portfolioUrl", event.target.value)}
          />
        </Field>
      </div>

      <div className="mt-5">
        <Field
          id="cover-letter"
          label="Cover letter"
          required
          helper="Briefly share why this role interests you and what experience you would bring."
          error={errors.coverLetter}
        >
          <Textarea
            id="cover-letter"
            name="coverLetter"
            rows={6}
            maxLength={10_000}
            value={values.coverLetter}
            disabled={submitting}
            aria-invalid={Boolean(errors.coverLetter)}
            aria-describedby={
              errors.coverLetter
                ? "cover-letter-help cover-letter-error"
                : "cover-letter-help"
            }
            className={cn(errors.coverLetter && "border-rose-300")}
            onChange={(event) => updateField("coverLetter", event.target.value)}
          />
        </Field>
      </div>

      <div className="mt-6">
        <ResumeUpload
          file={resume}
          error={errors.resume}
          maxSizeMb={maxSizeMb}
          disabled={submitting}
          onChange={updateResume}
        />
      </div>

      <div className="mt-8 border-t pt-6">
        <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={submitting}>
          {submitting ? <LoaderCircle className="animate-spin" /> : <Send />}
          {submitting ? "Submitting application…" : "Submit application"}
        </Button>
        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          By submitting, you confirm that the information provided is accurate.
        </p>
      </div>
    </form>
  );
}
