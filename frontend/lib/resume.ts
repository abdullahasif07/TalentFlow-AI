export interface EmploymentEntry {
  company: string | null;
  role: string | null;
  startDate: string | null;
  endDate: string | null;
  description: string | null;
  technologies: string[];
}

export interface EducationEntry {
  institution: string | null;
  degree: string | null;
  field: string | null;
  startDate: string | null;
  endDate: string | null;
}

export interface ResumeProject {
  name: string | null;
  description: string | null;
  technologies: string[];
  url: string | null;
}

export interface ParsedResumeData {
  professionalSummary: string | null;
  skills: string[];
  technologies: string[];
  totalExperienceYears: number | null;
  employmentHistory: EmploymentEntry[];
  education: EducationEntry[];
  projects: ResumeProject[];
  certifications: Array<{
    name: string | null;
    issuer: string | null;
    date: string | null;
  }>;
}

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
}

function recordArray(value: unknown): JsonRecord[] {
  return Array.isArray(value)
    ? value.map(asRecord).filter((item): item is JsonRecord => item !== null)
    : [];
}

export function normalizeParsedResume(value: unknown): ParsedResumeData | null {
  const data = asRecord(value);
  if (!data) return null;

  const experienceValue =
    typeof data.total_experience_years === "number" ||
    (typeof data.total_experience_years === "string" &&
      data.total_experience_years.trim())
      ? Number(data.total_experience_years)
      : Number.NaN;
  const parsed: ParsedResumeData = {
    professionalSummary: optionalString(data.professional_summary),
    skills: stringArray(data.skills),
    technologies: stringArray(data.technologies),
    totalExperienceYears: Number.isFinite(experienceValue) ? experienceValue : null,
    employmentHistory: recordArray(data.employment_history).map((entry) => ({
      company: optionalString(entry.company),
      role: optionalString(entry.role),
      startDate: optionalString(entry.start_date),
      endDate: optionalString(entry.end_date),
      description: optionalString(entry.description),
      technologies: stringArray(entry.technologies),
    })),
    education: recordArray(data.education).map((entry) => ({
      institution: optionalString(entry.institution),
      degree: optionalString(entry.degree),
      field: optionalString(entry.field),
      startDate: optionalString(entry.start_date),
      endDate: optionalString(entry.end_date),
    })),
    projects: recordArray(data.projects).map((entry) => ({
      name: optionalString(entry.name),
      description: optionalString(entry.description),
      technologies: stringArray(entry.technologies),
      url: optionalString(entry.url),
    })),
    certifications: recordArray(data.certifications).map((entry) => ({
      name: optionalString(entry.name),
      issuer: optionalString(entry.issuer),
      date: optionalString(entry.date),
    })),
  };

  const hasContent =
    parsed.professionalSummary !== null ||
    parsed.totalExperienceYears !== null ||
    parsed.skills.length > 0 ||
    parsed.technologies.length > 0 ||
    parsed.employmentHistory.length > 0 ||
    parsed.education.length > 0 ||
    parsed.projects.length > 0 ||
    parsed.certifications.length > 0;

  return hasContent ? parsed : null;
}

export function externalHttpUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function resumeFilename(fileUrl: string) {
  try {
    const pathname = new URL(fileUrl, "http://local").pathname;
    return decodeURIComponent(pathname.split("/").filter(Boolean).at(-1) ?? "Resume.pdf");
  } catch {
    return "Resume.pdf";
  }
}
