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

export function normalizeComparisonIds(ids: readonly string[]): string[] {
  const normalized = ids.map((id) => id.trim()).filter(Boolean);
  return [...new Set(normalized)].slice(0, MAX_COMPARISON_CANDIDATES);
}

export function updateComparisonSelection(
  currentIds: readonly string[],
  applicationId: string,
  eligible: boolean,
): ComparisonSelectionChange {
  const ids = normalizeComparisonIds(currentIds);
  const normalizedId = applicationId.trim();

  if (!normalizedId) return { ids, outcome: "invalid" };
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

export function parseComparisonSelection(
  value: string | string[] | undefined,
): ParsedComparisonSelection {
  const values = value === undefined ? [] : Array.isArray(value) ? value : [value];
  const ids = values
    .flatMap((item) => item.split(","))
    .map((id) => id.trim())
    .filter(Boolean);

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
  if (new Set(ids).size !== ids.length) {
    return {
      ids,
      error: "Each selected Application must be unique.",
    };
  }

  return { ids, error: null };
}

export function buildComparisonUrl(jobId: string, applicationIds: readonly string[]): string {
  const normalizedJobId = jobId.trim();
  const normalizedIds = normalizeComparisonIds(applicationIds);

  if (!normalizedJobId) throw new Error("A Job ID is required for comparison.");
  if (!canCompareCandidates(normalizedIds)) {
    throw new Error("Select between 2 and 5 candidates for comparison.");
  }

  const searchParams = new URLSearchParams({ applications: normalizedIds.join(",") });
  return `/jobs/${encodeURIComponent(normalizedJobId)}/compare?${searchParams.toString()}`;
}

export function buildApplicantsUrl(jobId: string): string {
  const normalizedJobId = jobId.trim();
  if (!normalizedJobId) throw new Error("A Job ID is required.");
  return `/jobs/${encodeURIComponent(normalizedJobId)}`;
}
