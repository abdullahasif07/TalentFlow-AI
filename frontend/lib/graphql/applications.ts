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

export const GET_APPLICATION_DETAIL = gql`
  query GetApplicationDetail($input: ApplicationQueryInput!) {
    application(input: $input) {
      success
      errors {
        code
        message
        field
      }
      application {
        id
        candidateId
        jobId
        status
        fitScore
        evaluationProcessingState
        resumeUrl
        coverLetter
        appliedAt
        updatedAt
        candidate {
          id
          name
          email
          phone
          linkedinUrl
          githubUrl
          portfolioUrl
        }
        job {
          id
          companyId
          title
          description
          status
        }
        resume {
          id
          fileUrl
          parsedData
          processingState
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
          matchedRequirements {
            requirement
            status
            evidence
          }
          missingRequirements {
            requirement
            status
            evidence
          }
          evidence {
            claim
            resumeEvidence
            category
          }
          categoryScores {
            name
            score
            weight
            weightedScore
            rationale
            evidence
          }
        }
        statusHistory {
          id
          previousStatus
          newStatus
          changedBy
          createdAt
        }
        notes {
          id
          content
          recruiter {
            id
            name
            email
          }
          createdAt
          updatedAt
        }
      }
    }
  }
`;

export const GENERATE_CANDIDATE_EVALUATION = gql`
  mutation GenerateCandidateEvaluation($input: GenerateCandidateEvaluationInput!) {
    generateCandidateEvaluation(input: $input) {
      success
      accepted
      resourceId
      state
      message
      taskId
      errors {
        code
        message
        field
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

export interface EvaluationCategoryScore {
  name: string;
  score: number | string;
  weight: number;
  weightedScore: number | string;
  rationale: string;
  evidence: string[];
}

export type RequirementMatchStatus =
  | "MATCH"
  | "PARTIAL_MATCH"
  | "MISSING_EVIDENCE"
  | "NOT_MET";

export interface EvaluationRequirement {
  requirement: string;
  status: RequirementMatchStatus;
  evidence: string | null;
}

export interface EvaluationEvidence {
  claim: string;
  resumeEvidence: string;
  category: string | null;
}

export interface ApplicationDetail {
  id: string;
  candidateId: string;
  jobId: string;
  status: string;
  fitScore: number | string | null;
  evaluationProcessingState: ProcessingState;
  resumeUrl: string | null;
  coverLetter: string | null;
  appliedAt: string;
  updatedAt: string;
  candidate: {
    id: string;
    name: string;
    email: string;
    phone: string | null;
    linkedinUrl: string | null;
    githubUrl: string | null;
    portfolioUrl: string | null;
  };
  job: {
    id: string;
    companyId: string;
    title: string;
    description: string;
    status: string;
  };
  resume: {
    id: string;
    fileUrl: string;
    parsedData: unknown;
    processingState: ProcessingState;
  } | null;
  evaluation: {
    id: string;
    overallScore: number | string;
    recommendation: string;
    confidence: string;
    processingState: ProcessingState;
    strengths: EvaluationFinding[];
    gaps: EvaluationFinding[];
    matchedRequirements: EvaluationRequirement[];
    missingRequirements: EvaluationRequirement[];
    evidence: EvaluationEvidence[];
    categoryScores: EvaluationCategoryScore[];
  } | null;
  statusHistory: Array<{
    id: string;
    previousStatus: string | null;
    newStatus: string;
    changedBy: string;
    createdAt: string;
  }>;
  notes: Array<{
    id: string;
    content: string;
    recruiter: {
      id: string;
      name: string;
      email: string;
    } | null;
    createdAt: string;
    updatedAt: string;
  }>;
}

export interface ApplicationDetailQueryData {
  application: {
    success: boolean;
    application: ApplicationDetail | null;
    errors: OperationError[];
  };
}

export interface GenerateCandidateEvaluationData {
  generateCandidateEvaluation: {
    success: boolean;
    accepted: boolean;
    resourceId: string | null;
    state: ProcessingState;
    message: string;
    taskId: string | null;
    errors: OperationError[];
  };
}
