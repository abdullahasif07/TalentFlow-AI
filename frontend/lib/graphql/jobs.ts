import { gql } from "@apollo/client";

export const JOB_FIELDS = gql`
  fragment RecruiterJobFields on JobType {
    id
    companyId
    title
    description
    requiredSkills
    preferredSkills
    experienceRequirement
    evaluationCriteria
    criteriaProcessingState
    status
    applicantCount
    shortlistedCount
    contactedCount
    interviewCount
    hiredCount
    recommendedCandidateCount
    createdAt
    updatedAt
  }
`;

export const GET_JOBS = gql`
  query GetJobs($input: JobsQueryInput) {
    jobs(input: $input) {
      success
      totalCount
      errors {
        code
        message
        field
      }
      items {
        ...RecruiterJobFields
      }
    }
  }
  ${JOB_FIELDS}
`;

export const GET_JOB = gql`
  query GetJob($input: JobQueryInput!) {
    job(input: $input) {
      success
      errors {
        code
        message
        field
      }
      job {
        ...RecruiterJobFields
      }
    }
  }
  ${JOB_FIELDS}
`;

export type JobStatus = "DRAFT" | "OPEN" | "CLOSED";
export type ProcessingState = "NOT_STARTED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface RecruiterJob {
  id: string;
  companyId: string;
  title: string;
  description: string;
  requiredSkills: unknown;
  preferredSkills: unknown;
  experienceRequirement: string | null;
  evaluationCriteria: unknown;
  criteriaProcessingState: ProcessingState;
  status: JobStatus;
  applicantCount: number;
  shortlistedCount: number;
  contactedCount: number;
  interviewCount: number;
  hiredCount: number;
  recommendedCandidateCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface OperationError {
  code: string;
  message: string;
  field: string | null;
}

export interface JobsQueryData {
  jobs: {
    success: boolean;
    totalCount: number;
    items: RecruiterJob[];
    errors: OperationError[];
  };
}

export interface JobQueryData {
  job: {
    success: boolean;
    job: RecruiterJob | null;
    errors: OperationError[];
  };
}

export function stringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  if (value && typeof value === "object") {
    return Object.values(value).filter((item): item is string => typeof item === "string");
  }
  return [];
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
