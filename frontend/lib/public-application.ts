export const DEFAULT_MAX_RESUME_SIZE_MB = 10;

export interface PublicApplicationValues {
  fullName: string;
  email: string;
  phone: string;
  linkedinUrl: string;
  githubUrl: string;
  portfolioUrl: string;
  coverLetter: string;
}

export type PublicApplicationField = keyof PublicApplicationValues | "resume";
export type PublicApplicationErrors = Partial<Record<PublicApplicationField, string>>;

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isHttpUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function maxResumeSizeBytes(maxSizeMb = DEFAULT_MAX_RESUME_SIZE_MB) {
  return maxSizeMb * 1024 * 1024;
}

export function configuredMaxResumeSizeMb(value: string | undefined) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : DEFAULT_MAX_RESUME_SIZE_MB;
}

export function createGraphQLMultipartBody(
  query: string,
  variables: Record<string, unknown>,
  resume: File,
) {
  const body = new FormData();
  body.append("operations", JSON.stringify({ query, variables }));
  body.append("map", JSON.stringify({ "0": ["variables.input.resume"] }));
  body.append("0", resume, resume.name);
  return body;
}

export function validateResume(
  resume: File | null,
  maxSizeBytes: number,
): string | undefined {
  if (!resume) return "Please attach your resume as a PDF.";
  if (!resume.size) return "The selected resume is empty.";
  if (
    resume.type !== "application/pdf" ||
    !resume.name.toLowerCase().endsWith(".pdf")
  ) {
    return "Resume must be a PDF file.";
  }
  if (resume.size > maxSizeBytes) {
    return `Resume must be ${Math.floor(maxSizeBytes / (1024 * 1024))} MB or smaller.`;
  }
  return undefined;
}

export function validatePublicApplication(
  values: PublicApplicationValues,
  resume: File | null,
  maxSizeBytes: number,
): PublicApplicationErrors {
  const errors: PublicApplicationErrors = {};

  if (!values.fullName.trim()) errors.fullName = "Please enter your full name.";
  if (!values.email.trim()) {
    errors.email = "Please enter your email address.";
  } else if (!emailPattern.test(values.email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  const urlFields: Array<
    ["linkedinUrl" | "githubUrl" | "portfolioUrl", string]
  > = [
    ["linkedinUrl", "LinkedIn URL"],
    ["githubUrl", "GitHub URL"],
    ["portfolioUrl", "Portfolio URL"],
  ];
  for (const [field, label] of urlFields) {
    const value = values[field].trim();
    if (value && !isHttpUrl(value)) errors[field] = `Enter a valid ${label}.`;
  }

  if (!values.coverLetter.trim()) {
    errors.coverLetter = "Please include a short cover letter.";
  } else if (values.coverLetter.trim().length > 10_000) {
    errors.coverLetter = "Cover letter must be 10,000 characters or fewer.";
  }

  const resumeError = validateResume(resume, maxSizeBytes);
  if (resumeError) errors.resume = resumeError;
  return errors;
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
