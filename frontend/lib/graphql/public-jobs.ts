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
