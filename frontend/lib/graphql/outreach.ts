import { gql } from "@apollo/client";

import type { OperationError } from "@/lib/graphql/jobs";

export const OUTREACH_EMAIL_FIELDS = gql`
  fragment OutreachEmailFields on OutreachEmailType {
    id
    subject
    body
    status
    generatedAt
    approvedAt
    sentAt
  }
`;

export const GENERATE_OUTREACH = gql`
  mutation GenerateOutreach($input: GenerateOutreachInput!) {
    generateOutreach(input: $input) {
      success
      outreach {
        ...OutreachEmailFields
      }
      errors {
        code
        message
        field
      }
    }
  }
  ${OUTREACH_EMAIL_FIELDS}
`;

export const UPDATE_OUTREACH_DRAFT = gql`
  mutation UpdateOutreachDraft($input: UpdateOutreachDraftInput!) {
    updateOutreachDraft(input: $input) {
      success
      outreach {
        ...OutreachEmailFields
      }
      errors {
        code
        message
        field
      }
    }
  }
  ${OUTREACH_EMAIL_FIELDS}
`;

export const APPROVE_OUTREACH = gql`
  mutation ApproveOutreach($input: ApproveOutreachInput!) {
    approveOutreach(input: $input) {
      success
      outreach {
        ...OutreachEmailFields
      }
      errors {
        code
        message
        field
      }
    }
  }
  ${OUTREACH_EMAIL_FIELDS}
`;

export const SEND_OUTREACH = gql`
  mutation SendOutreach($input: SendOutreachInput!) {
    sendOutreach(input: $input) {
      success
      outreach {
        ...OutreachEmailFields
      }
      errors {
        code
        message
        field
      }
    }
  }
  ${OUTREACH_EMAIL_FIELDS}
`;

export type OutreachStatus = "DRAFT" | "APPROVED" | "SENT";

export interface OutreachEmail {
  id: string;
  subject: string;
  body: string;
  status: OutreachStatus;
  generatedAt: string;
  approvedAt: string | null;
  sentAt: string | null;
}

interface OutreachMutationPayload {
  success: boolean;
  outreach: OutreachEmail | null;
  errors: OperationError[];
}

export interface GenerateOutreachData {
  generateOutreach: OutreachMutationPayload;
}

export interface UpdateOutreachDraftData {
  updateOutreachDraft: OutreachMutationPayload;
}

export interface ApproveOutreachData {
  approveOutreach: OutreachMutationPayload;
}

export interface SendOutreachData {
  sendOutreach: OutreachMutationPayload;
}
