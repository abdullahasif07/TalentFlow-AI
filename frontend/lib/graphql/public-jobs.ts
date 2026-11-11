import { gql } from "@apollo/client";

import type { JobStatus, OperationError } from "@/lib/graphql/jobs";

export const GET_PUBLIC_JOB = gql`
  query GetPublicJob($input: PublicJobQueryInput!) {
    publicJob(input: $input) {
      success
      job {
        id
        title
        description
        requiredSkills
        preferredSkills
        experienceRequirement
        status
        company {
          name
          website
        }
      }
      errors {
        code
        message
        field
      }
    }
  }
`;

export interface PublicJob {
  id: string;
  title: string;
  description: string;
  requiredSkills: unknown;
  preferredSkills: unknown;
  experienceRequirement: string | null;
  status: JobStatus;
  company: {
    name: string;
    website: string | null;
  };
}

export interface PublicJobQueryData {
  publicJob: {
    success: boolean;
    job: PublicJob | null;
    errors: OperationError[];
  };
}

export const GET_PUBLIC_JOBS = gql`
  query GetPublicJobs {
    publicJobs {
      success
      items {
        id
        title
        experienceRequirement
        requiredSkills
        company {
          name
        }
      }
      errors {
        code
        message
        field
      }
    }
  }
`;

export interface PublicJobSummary {
  id: string;
  title: string;
  experienceRequirement: string | null;
  requiredSkills: unknown;
  company: { name: string };
}

export interface PublicJobsQueryData {
  publicJobs: {
    success: boolean;
    items: PublicJobSummary[];
    errors: Array<{ code: string; message: string; field: string | null }>;
  };
}

export const GET_PUBLIC_APPLICATION_STATUS = gql`
  query GetPublicApplicationStatus($input: PublicApplicationStatusInput!) {
    publicApplicationStatus(input: $input) {
      success
      progress {
        stage
        message
        jobTitle
        candidateName
        finished
      }
      errors {
        code
        message
        field
      }
    }
  }
`;

export type ApplicationProgressStage =
  | "RECEIVED"
  | "READING_RESUME"
  | "SCORING"
  | "COMPLETE"
  | "NEEDS_MANUAL_REVIEW";

export interface PublicApplicationStatusData {
  publicApplicationStatus: {
    success: boolean;
    progress: {
      stage: ApplicationProgressStage;
      message: string;
      jobTitle: string;
      candidateName: string;
      finished: boolean;
    } | null;
    errors: Array<{ code: string; message: string; field: string | null }>;
  };
}
