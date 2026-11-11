import { graphqlUrl } from "@/lib/graphql/config";
import {
  createGraphQLMultipartBody,
  type PublicApplicationValues,
} from "@/lib/public-application";

const SUBMIT_PUBLIC_APPLICATION = `
  mutation SubmitPublicApplication($input: SubmitApplicationInput!) {
    submitApplication(input: $input) {
      success
      application {
        id
        candidateName
        jobTitle
        status
        submittedAt
        processingState
        processingMessage
        statusToken
      }
      errors {
        code
        message
        field
      }
    }
  }
`;

export interface PublicApplicationReceipt {
  id: string;
  candidateName: string;
  jobTitle: string;
  status: "APPLIED";
  submittedAt: string;
  processingState: "NOT_STARTED" | "PROCESSING" | "COMPLETED" | "FAILED";
  processingMessage: string;
  statusToken: string;
}

export interface PublicSubmissionError {
  code: string;
  message: string;
  field: string | null;
}

export interface PublicSubmissionPayload {
  success: boolean;
  application: PublicApplicationReceipt | null;
  errors: PublicSubmissionError[];
}

interface GraphQLSubmissionResponse {
  data?: { submitApplication: PublicSubmissionPayload };
  errors?: Array<{ message?: string }>;
}

export interface SubmitPublicApplicationInput extends PublicApplicationValues {
  jobId: string;
  resume: File;
  /** Honeypot value from a field hidden from people; real applicants leave it empty. */
  website?: string;
}

type Fetcher = typeof fetch;

export class PublicApplicationRequestError extends Error {}

export async function submitPublicApplication(
  input: SubmitPublicApplicationInput,
  fetcher: Fetcher = fetch,
): Promise<PublicSubmissionPayload> {
  const operations = {
    query: SUBMIT_PUBLIC_APPLICATION,
    variables: {
      input: {
        jobId: input.jobId,
        fullName: input.fullName.trim(),
        email: input.email.trim(),
        phone: input.phone.trim() || null,
        linkedinUrl: input.linkedinUrl.trim() || null,
        githubUrl: input.githubUrl.trim() || null,
        portfolioUrl: input.portfolioUrl.trim() || null,
        coverLetter: input.coverLetter.trim(),
        website: input.website?.trim() || null,
        resume: null,
      },
    },
  };
  const body = createGraphQLMultipartBody(
    operations.query,
    { input: operations.variables.input },
    input.resume,
  );

  let response: Response;
  try {
    response = await fetcher(graphqlUrl, {
      method: "POST",
      body,
    });
  } catch {
    throw new PublicApplicationRequestError(
      "We couldn’t reach the application service. Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    throw new PublicApplicationRequestError(
      "The application service is temporarily unavailable. Please try again.",
    );
  }

  let result: GraphQLSubmissionResponse;
  try {
    result = (await response.json()) as GraphQLSubmissionResponse;
  } catch {
    throw new PublicApplicationRequestError(
      "The application service returned an unexpected response. Please try again.",
    );
  }

  if (!result.data?.submitApplication) {
    throw new PublicApplicationRequestError(
      result.errors?.[0]?.message
        ? "The application could not be submitted. Please review your details and try again."
        : "The application service returned an incomplete response. Please try again.",
    );
  }
  return result.data.submitApplication;
}

export function publicSubmissionErrorMessage(error: PublicSubmissionError) {
  switch (error.code) {
    case "CONFLICT":
      return "An application using this email has already been submitted for this job.";
    case "JOB_CLOSED":
    case "NOT_FOUND":
      return "This job is no longer accepting applications.";
    case "INVALID_FILE":
      return "Please attach a valid, non-empty PDF resume.";
    case "FILE_TOO_LARGE":
      return error.message || "The selected resume is too large.";
    case "RATE_LIMITED":
      return error.message || "Too many applications were submitted. Please try again later.";
    case "VALIDATION_ERROR":
      return error.message || "Please review the highlighted application details.";
    default:
      return "We couldn’t submit your application. Please try again.";
  }
}
