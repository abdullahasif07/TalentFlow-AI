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

export const GET_JOB_APPLICATIONS = gql`
  query GetJobApplications($input: ApplicationsQueryInput!) {
    applications(input: $input) {
      success
      totalCount
      pageInfo {
        limit
        offset
        hasNextPage
        hasPreviousPage
      }
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
          phone
        }
        evaluation {
          id
          overallScore
          recommendation
          confidence
          processingState
        }
      }
    }
  }
`;

export const GET_RECOMMENDED_CANDIDATES = gql`
  query GetRecommendedCandidates($input: RecommendedCandidatesInput!) {
    recommendedCandidates(input: $input) {
      success
      totalCount
      limit
      errors {
        code
        message
        field
      }
      items {
        candidate {
          id
          name
          email
        }
        application {
          id
          status
          fitScore
          evaluationProcessingState
          appliedAt
        }
        evaluation {
          id
          overallScore
          recommendation
          confidence
          processingState
          strengths {
            summary
            evidence
          }
          gaps {
            summary
            evidence
          }
        }
      }
    }
  }
`;

export interface RecentApplication {
  id: string;
  status: string;
  fitScore: number | string | null;
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

export type ApplicationSort =
  | "NEWEST"
  | "OLDEST"
  | "FIT_SCORE_ASC"
  | "FIT_SCORE_DESC";

export interface ApplicantListItem {
  id: string;
  status: string;
  fitScore: number | string | null;
  evaluationProcessingState: ProcessingState;
  appliedAt: string;
  candidate: {
    id: string;
    name: string;
    email: string;
    phone: string | null;
  };
  evaluation: {
    id: string;
    overallScore: number | string;
    recommendation: string;
    confidence: string;
    processingState: ProcessingState;
  } | null;
}

export interface JobApplicationsQueryData {
  applications: {
    success: boolean;
    totalCount: number;
    pageInfo: {
      limit: number;
      offset: number;
      hasNextPage: boolean;
      hasPreviousPage: boolean;
    } | null;
    items: ApplicantListItem[];
    errors: OperationError[];
  };
}

export interface EvaluationFinding {
  summary: string;
  evidence: string[];
}

export interface RecommendedCandidate {
  candidate: {
    id: string;
    name: string;
    email: string;
  };
  application: {
    id: string;
    status: string;
    fitScore: number | string;
    evaluationProcessingState: ProcessingState;
    appliedAt: string;
  };
  evaluation: {
    id: string;
    overallScore: number | string;
    recommendation: string;
    confidence: string;
    processingState: ProcessingState;
    strengths: EvaluationFinding[];
    gaps: EvaluationFinding[];
  };
}

export interface RecommendedCandidatesQueryData {
  recommendedCandidates: {
    success: boolean;
    totalCount: number;
    limit: number;
    items: RecommendedCandidate[];
    errors: OperationError[];
  };
}
