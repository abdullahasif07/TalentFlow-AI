import { gql } from "@apollo/client";

import type { OperationError, ProcessingState } from "@/lib/graphql/jobs";

export const GET_RECENT_APPLICATIONS = gql`
  query GetRecentApplications($input: ApplicationsQueryInput!) {
    applications(input: $input) {
      success
      totalCount
      errors {
        code
        message
        field
      }
      items {
        id
        status
        fitScore
        evaluationProcessingState
        appliedAt
        candidate {
          id
          name
          email
        }
        job {
          id
          title
          status
        }
      }
    }
  }
`;

export interface RecentApplication {
  id: string;
  status: string;
  fitScore: number | null;
  evaluationProcessingState: ProcessingState;
  appliedAt: string;
  candidate: {
    id: string;
    name: string;
    email: string;
  };
  job: {
    id: string;
    title: string;
    status: string;
  };
}

export interface RecentApplicationsQueryData {
  applications: {
    success: boolean;
    totalCount: number;
    items: RecentApplication[];
    errors: OperationError[];
  };
}
