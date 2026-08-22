"use client";

import { useApolloClient, useMutation } from "@apollo/client/react";
import { CheckCircle2, MailPlus, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { OutreachDraftEditor } from "@/components/applications/outreach/outreach-draft-editor";
import {
  OutreachEmailView,
  OutreachHistory,
} from "@/components/applications/outreach/outreach-email-view";
import { OutreachGenerator } from "@/components/applications/outreach/outreach-generator";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  GET_APPLICATION_DETAIL,
  type ApplicationDetailQueryData,
} from "@/lib/graphql/applications";
import { graphQLErrorMessage } from "@/lib/graphql/errors";
import {
  APPROVE_OUTREACH,
  GENERATE_OUTREACH,
  SEND_OUTREACH,
  UPDATE_OUTREACH_DRAFT,
  type ApproveOutreachData,
  type GenerateOutreachData,
  type OutreachEmail,
  type SendOutreachData,
  type UpdateOutreachDraftData,
} from "@/lib/graphql/outreach";
import type { OperationError } from "@/lib/graphql/jobs";
import { formatDateTime } from "@/lib/graphql/jobs";

type BusyAction = "generate" | "save" | "approve" | "send" | null;

export function OutreachSection({
  applicationId,
  candidateName,
  candidateEmail,
  jobTitle,
  outreachEmails,
  onApplicationUpdated,
}: {
  applicationId: string;
  candidateName: string;
  candidateEmail: string;
  jobTitle: string;
  outreachEmails: OutreachEmail[];
  onApplicationUpdated: () => Promise<unknown> | void;
}) {
  const client = useApolloClient();
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showNewGenerator, setShowNewGenerator] = useState(false);
  const [generateOutreach] = useMutation<
    GenerateOutreachData,
    { input: { applicationId: string; instruction: string | null } }
  >(GENERATE_OUTREACH);
  const [updateOutreachDraft] = useMutation<
    UpdateOutreachDraftData,
    { input: { outreachId: string; subject: string; body: string } }
  >(UPDATE_OUTREACH_DRAFT);
  const [approveOutreach] = useMutation<
    ApproveOutreachData,
    { input: { outreachId: string } }
  >(APPROVE_OUTREACH);
  const [sendOutreach] = useMutation<
    SendOutreachData,
    { input: { outreachId: string } }
  >(SEND_OUTREACH);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 4_000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  const currentOutreach = outreachEmails[0] ?? null;

  function updateOutreachCache(email: OutreachEmail) {
    client.cache.updateQuery<ApplicationDetailQueryData>(
      {
        query: GET_APPLICATION_DETAIL,
        variables: { input: { id: applicationId } },
      },
      (cached) => {
        const application = cached?.application.application;
        if (!cached || !application) return cached;
        const updatedEmails = [
          email,
          ...application.outreachEmails.filter((item) => item.id !== email.id),
        ].sort((first, second) => {
          const timestampDifference =
            new Date(second.generatedAt).getTime() -
            new Date(first.generatedAt).getTime();
          if (timestampDifference !== 0) return timestampDifference;
          return Number(second.id) - Number(first.id);
        });
        return {
          ...cached,
          application: {
            ...cached.application,
            application: {
              ...application,
              outreachEmails: updatedEmails,
            },
          },
        };
      },
    );
  }

  async function refreshAfterConflict(errors: OperationError[]) {
    if (!errors.some((error) => error.code === "CONFLICT")) return;
    try {
      await onApplicationUpdated();
    } catch {
      // Keep the mutation error visible; the recruiter can retry or refresh manually.
    }
  }

  async function handleMutationFailure(
    errors: OperationError[],
    fallback: string,
  ) {
    setActionError(errors[0]?.message ?? fallback);
    await refreshAfterConflict(errors);
  }

  async function handleGenerate(instruction: string | null) {
    setBusyAction("generate");
    setActionError(null);
    setSuccessMessage(null);
    try {
      const result = await generateOutreach({
        variables: { input: { applicationId, instruction } },
      });
      const payload = result.data?.generateOutreach;
      if (!payload?.success || !payload.outreach) {
        await handleMutationFailure(
          payload?.errors ?? [],
          "The outreach draft could not be generated.",
        );
        return false;
      }
      updateOutreachCache(payload.outreach);
      setShowNewGenerator(false);
      setSuccessMessage(
        currentOutreach?.status === "DRAFT"
          ? "A new version of the draft is ready for review."
          : "Outreach draft generated. Review every detail before approval.",
      );
      return true;
    } catch (error) {
      setActionError(
        graphQLErrorMessage(error, "The outreach draft could not be generated."),
      );
      return false;
    } finally {
      setBusyAction(null);
    }
  }

  async function saveDraftRequest(
    outreachId: string,
    subject: string,
    body: string,
  ) {
    try {
      const result = await updateOutreachDraft({
        variables: { input: { outreachId, subject, body } },
      });
      const payload = result.data?.updateOutreachDraft;
      if (!payload?.success || !payload.outreach) {
        await handleMutationFailure(
          payload?.errors ?? [],
          "The outreach draft could not be saved.",
        );
        return false;
      }
      updateOutreachCache(payload.outreach);
      return true;
    } catch (error) {
      setActionError(
        graphQLErrorMessage(error, "The outreach draft could not be saved."),
      );
      return false;
    }
  }

  async function handleSave(subject: string, body: string) {
    if (!currentOutreach) return false;
    setBusyAction("save");
    setActionError(null);
    setSuccessMessage(null);
    try {
      const saved = await saveDraftRequest(currentOutreach.id, subject, body);
      if (saved) setSuccessMessage("Draft saved.");
      return saved;
    } finally {
      setBusyAction(null);
    }
  }

  async function handleApprove(
    subject: string,
    body: string,
    hasUnsavedChanges: boolean,
  ) {
    if (!currentOutreach) return false;
    setBusyAction("approve");
    setActionError(null);
    setSuccessMessage(null);
    try {
      if (hasUnsavedChanges) {
        const saved = await saveDraftRequest(currentOutreach.id, subject, body);
        if (!saved) return false;
      }
      const result = await approveOutreach({
        variables: { input: { outreachId: currentOutreach.id } },
      });
      const payload = result.data?.approveOutreach;
      if (!payload?.success || !payload.outreach) {
        await handleMutationFailure(
          payload?.errors ?? [],
          "The outreach draft could not be approved.",
        );
        return false;
      }
      updateOutreachCache(payload.outreach);
      setSuccessMessage("Outreach approved. It will not be sent until you click Send email.");
      return true;
    } catch (error) {
      setActionError(
        graphQLErrorMessage(error, "The outreach draft could not be approved."),
      );
      return false;
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSend() {
    if (!currentOutreach) return false;
    if (!candidateEmail.trim()) {
      setActionError("This candidate has no email address.");
      return false;
    }
    setBusyAction("send");
    setActionError(null);
    setSuccessMessage(null);
    try {
      const result = await sendOutreach({
        variables: { input: { outreachId: currentOutreach.id } },
      });
      const payload = result.data?.sendOutreach;
      if (!payload?.success || !payload.outreach) {
        await handleMutationFailure(
          payload?.errors ?? [],
          "The outreach email could not be sent.",
        );
        return false;
      }
      updateOutreachCache(payload.outreach);
      client.cache.evict({ id: "ROOT_QUERY", fieldName: "applications" });
      client.cache.evict({ id: "ROOT_QUERY", fieldName: "jobs" });
      client.cache.evict({ id: "ROOT_QUERY", fieldName: "recommendedCandidates" });
      try {
        await onApplicationUpdated();
      } catch {
        setActionError(
          "The email was sent, but the latest application status could not be loaded. Refresh the page to try again.",
        );
      }
      setSuccessMessage(`Outreach sent to ${candidateEmail}.`);
      return true;
    } catch (error) {
      setActionError(
        graphQLErrorMessage(error, "The outreach email could not be sent."),
      );
      return false;
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start gap-3">
        <div className="rounded-lg bg-[#e8f3f0] p-2 text-primary">
          <MailPlus className="size-4.5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Outreach</CardTitle>
            {currentOutreach ? <StatusBadge status={currentOutreach.status} /> : null}
          </div>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Generate, review, and approve a personalized recruiter email. Nothing is sent without
            your explicit confirmation.
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-start gap-2.5 rounded-xl border border-[#cfe2de] bg-[#f1f8f6] px-3.5 py-3 text-xs leading-5 text-[#2d625c]">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>
            Drafts use {candidateName}&apos;s available resume and evaluation evidence, the {jobTitle}
            role, and company context. Internal scores and prompts are never shown in the email.
          </p>
        </div>

        {actionError ? (
          <div
            role="alert"
            className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
          >
            {actionError}
          </div>
        ) : null}
        {successMessage ? (
          <div
            role="status"
            className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
          >
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
            {successMessage}
          </div>
        ) : null}

        {!currentOutreach ? (
          <OutreachGenerator
            loading={busyAction === "generate"}
            onGenerate={handleGenerate}
          />
        ) : null}

        {currentOutreach?.status === "DRAFT" ? (
          <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">Review and edit draft</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Generated {formatDateTime(currentOutreach.generatedAt)}
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Sparkles className="size-3.5 text-primary" /> AI-assisted draft
              </span>
            </div>
            <OutreachDraftEditor
              key={`${currentOutreach.id}:${currentOutreach.generatedAt}`}
              email={currentOutreach}
              busyAction={busyAction}
              onSave={handleSave}
              onRegenerate={handleGenerate}
              onApprove={handleApprove}
            />
          </div>
        ) : null}

        {currentOutreach && currentOutreach.status !== "DRAFT" ? (
          <OutreachEmailView
            email={currentOutreach}
            candidateEmail={candidateEmail}
            sending={busyAction === "send"}
            onSend={handleSend}
          />
        ) : null}

        {currentOutreach?.status === "SENT" ? (
          <div className="border-t pt-4">
            {showNewGenerator ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold">Generate another outreach</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowNewGenerator(false)}
                    disabled={busyAction !== null}
                  >
                    Cancel
                  </Button>
                </div>
                <OutreachGenerator
                  loading={busyAction === "generate"}
                  onGenerate={handleGenerate}
                  compact
                />
              </div>
            ) : (
              <Button
                variant="outline"
                onClick={() => setShowNewGenerator(true)}
                disabled={busyAction !== null}
              >
                <MailPlus /> Generate another outreach
              </Button>
            )}
          </div>
        ) : null}

        <OutreachHistory emails={outreachEmails} />
      </CardContent>
    </Card>
  );
}
