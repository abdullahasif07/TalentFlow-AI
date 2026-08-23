"use client";

import { useMutation } from "@apollo/client/react";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  LoaderCircle,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ActionFeedback } from "@/components/shared/action-feedback";
import { Button } from "@/components/ui/button";
import {
  APPLICATION_STATUSES,
  GET_APPLICATION_DETAIL,
  UPDATE_APPLICATION_STATUS,
  formatApplicationStatus,
  type ApplicationDetailQueryData,
  type ApplicationStatus,
  type UpdateApplicationStatusData,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";

const CURRENT_RECRUITER = "Alex Morgan";

const suggestedNextStatus: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  APPLIED: "HUMAN_REVIEW",
  AI_REVIEWED: "HUMAN_REVIEW",
  HUMAN_REVIEW: "SHORTLISTED",
  SHORTLISTED: "CONTACTED",
  CONTACTED: "REPLIED",
  REPLIED: "INTERVIEW",
  INTERVIEW: "OFFER",
  OFFER: "HIRED",
};

const actionLabels: Partial<Record<ApplicationStatus, string>> = {
  AI_REVIEWED: "Mark AI Reviewed",
  HUMAN_REVIEW: "Move to Human Review",
  SHORTLISTED: "Shortlist",
  CONTACTED: "Mark Contacted",
  REPLIED: "Mark Replied",
  INTERVIEW: "Move to Interview",
  OFFER: "Move to Offer",
  HIRED: "Mark Hired",
  REJECTED: "Reject Application",
};

const confirmationStatuses = new Set<ApplicationStatus>(["HIRED", "REJECTED"]);

interface ApplicationStatusControlProps {
  applicationId: string;
  jobId: string;
  currentStatus: ApplicationStatus;
  onStatusUpdated: () => Promise<unknown> | void;
}

export function ApplicationStatusControl({
  applicationId,
  jobId,
  currentStatus,
  onStatusUpdated,
}: ApplicationStatusControlProps) {
  const [statusSelection, setStatusSelection] = useState(() => ({
    forStatus: currentStatus,
    value: suggestedNextStatus[currentStatus] ?? currentStatus,
  }));
  const [confirmation, setConfirmation] = useState<{
    forStatus: ApplicationStatus;
    value: ApplicationStatus;
  } | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [retryableStatusUpdate, setRetryableStatusUpdate] = useState(false);
  const [operationLoading, setOperationLoading] = useState(false);
  const operationPending = useRef(false);
  const [updateStatus] = useMutation<
    UpdateApplicationStatusData,
    {
      input: {
        applicationId: string;
        status: ApplicationStatus;
        changedBy: string;
        automated: boolean;
      };
    }
  >(UPDATE_APPLICATION_STATUS);
  const selectedStatus =
    statusSelection.forStatus === currentStatus
      ? statusSelection.value
      : (suggestedNextStatus[currentStatus] ?? currentStatus);
  const confirmationStatus =
    confirmation?.forStatus === currentStatus ? confirmation.value : null;

  function selectStatus(status: ApplicationStatus) {
    setStatusSelection({ forStatus: currentStatus, value: status });
  }

  function confirmStatus(status: ApplicationStatus | null) {
    setConfirmation(status ? { forStatus: currentStatus, value: status } : null);
  }

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 4_000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  async function persistStatus(status: ApplicationStatus) {
    if (operationPending.current) return;
    operationPending.current = true;
    setOperationLoading(true);
    setActionError(null);
    setSuccessMessage(null);
    setRetryableStatusUpdate(false);

    try {
      const result = await updateStatus({
        variables: {
          input: {
            applicationId,
            status,
            changedBy: CURRENT_RECRUITER,
            automated: false,
          },
        },
        update(cache, mutationResult) {
          const updatedApplication =
            mutationResult.data?.updateApplicationStatus.application;
          if (mutationResult.data?.updateApplicationStatus.success && updatedApplication) {
            cache.updateQuery<ApplicationDetailQueryData>(
              {
                query: GET_APPLICATION_DETAIL,
                variables: { input: { id: applicationId } },
              },
              (cached) => {
                if (!cached?.application.application) return cached;
                return {
                  ...cached,
                  application: {
                    ...cached.application,
                    application: {
                      ...cached.application.application,
                      status: updatedApplication.status,
                      updatedAt: updatedApplication.updatedAt,
                    },
                  },
                };
              },
            );

            const jobCacheId = cache.identify({ __typename: "JobType", id: jobId });
            if (jobCacheId) {
              const countDelta = (status: ApplicationStatus) =>
                Number(updatedApplication.status === status) -
                Number(currentStatus === status);
              cache.modify({
                id: jobCacheId,
                fields: {
                  shortlistedCount(existing: number = 0) {
                    return Math.max(0, existing + countDelta("SHORTLISTED"));
                  },
                  contactedCount(existing: number = 0) {
                    return Math.max(0, existing + countDelta("CONTACTED"));
                  },
                  interviewCount(existing: number = 0) {
                    return Math.max(0, existing + countDelta("INTERVIEW"));
                  },
                  hiredCount(existing: number = 0) {
                    return Math.max(0, existing + countDelta("HIRED"));
                  },
                },
              });
            }
            cache.evict({ id: "ROOT_QUERY", fieldName: "applications" });
            cache.evict({ id: "ROOT_QUERY", fieldName: "recommendedCandidates" });
          }
        },
      });
      const payload = result.data?.updateApplicationStatus;

      if (!payload?.success || !payload.application) {
        setActionError(
          payload?.errors[0]?.message ?? "The application status could not be updated.",
        );
        setRetryableStatusUpdate(true);
        return;
      }

      setConfirmation(null);
      setStatusSelection({
        forStatus: payload.application.status,
        value:
          suggestedNextStatus[payload.application.status] ?? payload.application.status,
      });
      setSuccessMessage(`Moved to ${formatApplicationStatus(payload.application.status)}.`);
      try {
        await onStatusUpdated();
      } catch {
        setActionError(
          "The status was updated, but the latest timeline could not be loaded. Reopen this application to refresh its activity.",
        );
      }
    } catch (error) {
      setActionError(
        graphQLErrorMessage(error, "The application status could not be updated."),
      );
      setRetryableStatusUpdate(true);
    } finally {
      operationPending.current = false;
      setOperationLoading(false);
    }
  }

  function requestStatusUpdate(status: ApplicationStatus) {
    if (status === currentStatus || operationLoading) return;
    if (confirmationStatuses.has(status)) {
      confirmStatus(status);
      return;
    }
    void persistStatus(status);
  }

  const isCurrentStage = selectedStatus === currentStatus;
  const isRejected = currentStatus === "REJECTED";
  const isHired = currentStatus === "HIRED";
  const actionLabel =
    actionLabels[selectedStatus] ?? `Move to ${formatApplicationStatus(selectedStatus)}`;

  return (
    <div className="space-y-3">
      <div>
        <label
          htmlFor="application-status"
          className="mb-1.5 block text-xs font-medium text-muted-foreground"
        >
          Move applicant to
        </label>
        <div className="relative">
          <select
            id="application-status"
            value={selectedStatus}
            onChange={(event) => {
              selectStatus(event.target.value as ApplicationStatus);
              setConfirmation(null);
              setActionError(null);
            }}
            disabled={operationLoading}
            className="h-10 w-full appearance-none rounded-lg border border-input bg-card px-3 pr-9 text-sm font-medium outline-none focus:border-primary focus:ring-2 focus:ring-ring/15 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {APPLICATION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {formatApplicationStatus(status)}
                {status === currentStatus ? " (current)" : ""}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        </div>
      </div>

      {confirmationStatus ? (
        <div
          role="alertdialog"
          aria-labelledby="status-confirmation-title"
          className={
            confirmationStatus === "REJECTED"
              ? "rounded-lg border border-rose-200 bg-rose-50 p-3.5"
              : "rounded-lg border border-emerald-200 bg-emerald-50 p-3.5"
          }
        >
          <p
            id="status-confirmation-title"
            className={
              confirmationStatus === "REJECTED"
                ? "text-sm font-semibold text-rose-900"
                : "text-sm font-semibold text-emerald-900"
            }
          >
            {confirmationStatus === "REJECTED" ? "Reject this application?" : "Mark as hired?"}
          </p>
          <p
            className={
              confirmationStatus === "REJECTED"
                ? "mt-1 text-xs leading-5 text-rose-800"
                : "mt-1 text-xs leading-5 text-emerald-800"
            }
          >
            This final-stage change will be recorded in the application history.
          </p>
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              variant={confirmationStatus === "REJECTED" ? "destructive" : "default"}
              onClick={() => void persistStatus(confirmationStatus)}
              disabled={operationLoading}
            >
              {operationLoading ? <LoaderCircle className="animate-spin" /> : <CheckCircle2 />}
              Confirm
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setConfirmation(null)}
              disabled={operationLoading}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            className="min-w-0 flex-1"
            onClick={() => requestStatusUpdate(selectedStatus)}
            disabled={isCurrentStage || operationLoading}
          >
            {operationLoading ? <LoaderCircle className="animate-spin" /> : <ArrowRight />}
            <span className="truncate">{operationLoading ? "Updating…" : actionLabel}</span>
          </Button>
          {!isRejected && !isHired && selectedStatus !== "REJECTED" ? (
            <Button
              size="icon"
              variant="outline"
              className="shrink-0 border-rose-200 text-rose-700 hover:bg-rose-50"
              onClick={() => {
                selectStatus("REJECTED");
                confirmStatus("REJECTED");
              }}
              disabled={operationLoading}
              aria-label="Reject application"
              title="Reject application"
            >
              <XCircle />
            </Button>
          ) : null}
        </div>
      )}

      {successMessage ? (
        <ActionFeedback
          variant="success"
          message={successMessage}
          className="rounded-lg px-3 py-2 text-xs font-medium"
        />
      ) : null}
      {actionError ? (
        <ActionFeedback
          variant="error"
          message={actionError}
          className="rounded-lg px-3 py-2 text-xs font-medium"
          action={
            retryableStatusUpdate ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 text-xs font-semibold underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
                onClick={() => void persistStatus(selectedStatus)}
                disabled={operationLoading}
              >
                <RotateCcw className="size-3" /> Try again
              </button>
            ) : undefined
          }
        />
      ) : null}
      <p className="text-[11px] leading-4 text-muted-foreground">
        Status changes are manual and do not depend on the AI fit score.
      </p>
    </div>
  );
}
