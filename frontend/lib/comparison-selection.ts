export const MIN_COMPARISON_CANDIDATES = 2;
export const MAX_COMPARISON_CANDIDATES = 5;

export type ComparisonSelectionOutcome =
  | "selected"
  | "deselected"
  | "ineligible"
  | "invalid"
  | "limit_reached";

export interface ComparisonSelectionChange {
  ids: string[];
  outcome: ComparisonSelectionOutcome;
}

export interface ParsedComparisonSelection {
  ids: string[];
  error: string | null;
}

export interface CandidateComparisonInput {
  jobId: string;
  applicationIds: string[];
}

export interface VisibleComparisonEligibility {
  applicationId: string;
  eligible: boolean;
}

const EMPTY_SELECTION: readonly string[] = [];
const selectionListeners = new Set<() => void>();
let activeSelection: { jobId: string | null; ids: readonly string[] } = {
  jobId: null,
  ids: EMPTY_SELECTION,
};

export function isPositiveIntegerId(value: string): boolean {
  return /^[1-9]\d*$/.test(value);
}

export function comparisonJobIdError(jobId: string): string | null {
  return isPositiveIntegerId(jobId.trim())
    ? null
    : "The comparison URL contains an invalid Job ID.";
}

export function normalizeComparisonIds(ids: readonly string[]): string[] {
  const normalized = ids
    .map((id) => id.trim())
    .filter((id) => isPositiveIntegerId(id));
  return [...new Set(normalized)].slice(0, MAX_COMPARISON_CANDIDATES);
}

export function updateComparisonSelection(
  currentIds: readonly string[],
  applicationId: string,
  eligible: boolean,
): ComparisonSelectionChange {
  const ids = normalizeComparisonIds(currentIds);
  const normalizedId = applicationId.trim();

  if (!isPositiveIntegerId(normalizedId)) return { ids, outcome: "invalid" };
  if (ids.includes(normalizedId)) {
    return {
      ids: ids.filter((id) => id !== normalizedId),
      outcome: "deselected",
    };
  }
  if (!eligible) return { ids, outcome: "ineligible" };
  if (ids.length >= MAX_COMPARISON_CANDIDATES) {
    return { ids, outcome: "limit_reached" };
  }

  return { ids: [...ids, normalizedId], outcome: "selected" };
}

export function canCompareCandidates(ids: readonly string[]): boolean {
  const normalizedIds = normalizeComparisonIds(ids);
  return normalizedIds.length >= MIN_COMPARISON_CANDIDATES;
}

export function clearComparisonSelection(_ids: readonly string[] = []): string[] {
  return [];
}

export function removeIneligibleVisibleSelections(
  selectedIds: readonly string[],
  visibleApplications: readonly VisibleComparisonEligibility[],
): string[] {
  const ineligibleVisibleIds = new Set(
    visibleApplications
      .filter((application) => !application.eligible)
      .map((application) => application.applicationId),
  );
  return normalizeComparisonIds(selectedIds).filter(
    (applicationId) => !ineligibleVisibleIds.has(applicationId),
  );
}

export function activateComparisonJob(jobId: string): void {
  if (activeSelection.jobId === jobId) return;
  activeSelection = { jobId, ids: EMPTY_SELECTION };
  selectionListeners.forEach((listener) => listener());
}

export function getStoredComparisonSelection(jobId: string): readonly string[] {
  return activeSelection.jobId === jobId ? activeSelection.ids : EMPTY_SELECTION;
}

export function getServerComparisonSelection(): readonly string[] {
  return EMPTY_SELECTION;
}

export function storeComparisonSelection(jobId: string, ids: readonly string[]): void {
  activeSelection = { jobId, ids: normalizeComparisonIds(ids) };
  selectionListeners.forEach((listener) => listener());
}

export function subscribeComparisonSelection(listener: () => void): () => void {
  selectionListeners.add(listener);
  return () => selectionListeners.delete(listener);
}

export function parseComparisonSelection(
  value: string | string[] | undefined,
): ParsedComparisonSelection {
  const values = value === undefined ? [] : Array.isArray(value) ? value : [value];
  const rawIds = values
    .flatMap((item) => item.split(","))
    .map((id) => id.trim())
    .filter(Boolean);
  const malformed = rawIds.some((id) => !isPositiveIntegerId(id));
  const ids = [...new Set(rawIds.filter((id) => isPositiveIntegerId(id)))];

  if (malformed) {
    return {
      ids,
      error: "Application IDs must be positive integers.",
    };
  }

  if (ids.length < MIN_COMPARISON_CANDIDATES) {
    return {
      ids,
      error: "Select at least 2 evaluated applicants to compare.",
    };
  }
  if (ids.length > MAX_COMPARISON_CANDIDATES) {
    return {
      ids,
      error: "You can compare no more than 5 applicants at once.",
    };
  }
  return { ids, error: null };
}

export function buildComparisonUrl(jobId: string, applicationIds: readonly string[]): string {
  const input = buildCandidateComparisonInput(jobId, applicationIds);

  const searchParams = new URLSearchParams({ applications: input.applicationIds.join(",") });
  return `/jobs/${encodeURIComponent(input.jobId)}/compare?${searchParams.toString()}`;
}

export function buildCandidateComparisonInput(
  jobId: string,
  applicationIds: readonly string[],
): CandidateComparisonInput {
  const normalizedJobId = jobId.trim();
  const jobError = comparisonJobIdError(normalizedJobId);
  const parsedSelection = parseComparisonSelection([...applicationIds]);

  if (jobError) throw new Error(jobError);
  if (parsedSelection.error) throw new Error(parsedSelection.error);
  return { jobId: normalizedJobId, applicationIds: parsedSelection.ids };
}

export function buildApplicantsUrl(jobId: string): string {
  const normalizedJobId = jobId.trim();
  if (!isPositiveIntegerId(normalizedJobId)) return "/jobs";
  return `/jobs/${encodeURIComponent(normalizedJobId)}`;
}
