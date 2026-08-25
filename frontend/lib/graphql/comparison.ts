import { gql } from "@apollo/client";

import type { EvaluationFinding } from "@/lib/graphql/applications";
import type { OperationError } from "@/lib/graphql/jobs";

export const COMPARE_CANDIDATES = gql`
  mutation CompareCandidates($input: CompareCandidatesInput!) {
    compareCandidates(input: $input) {
      success
      job {
        id
        title
      }
      candidates {
        applicationId
        candidateId
        name
        overallScore
        confidence
        recommendation
        strengths {
          summary
          evidence
        }
        gaps {
          summary
          evidence
        }
      }
      categories {
        name
        weight
        candidates {
          applicationId
          available
          score
          summary
        }
      }
      summary {
        overview
        relativeStrengths
        tradeoffs
        differentiatingExperience
        notableGaps
        comparableAreas
      }
      errors {
        code
        message
        field
      }
    }
  }
`;

export interface ComparedCandidate {
  applicationId: string;
  candidateId: string;
  name: string;
  overallScore: number | string;
  confidence: string;
  recommendation: string;
  strengths: EvaluationFinding[];
  gaps: EvaluationFinding[];
}

export interface CandidateCategoryResult {
  applicationId: string;
  available: boolean;
  score: number | string | null;
  summary: string;
}

export interface ComparisonCategory {
  name: string;
  weight: number;
  candidates: CandidateCategoryResult[];
}

export interface CandidateComparisonSummary {
  overview: string;
  relativeStrengths: string[];
  tradeoffs: string[];
  differentiatingExperience: string[];
  notableGaps: string[];
  comparableAreas: string[];
}

export interface CandidateComparisonPayload {
  success: boolean;
  job: { id: string; title: string } | null;
  candidates: ComparedCandidate[];
  categories: ComparisonCategory[];
  summary: CandidateComparisonSummary | null;
  errors: OperationError[];
}

export interface CompareCandidatesData {
  compareCandidates: CandidateComparisonPayload;
}

export interface CompareCandidatesVariables {
  input: {
    jobId: string;
    applicationIds: string[];
  };
}
