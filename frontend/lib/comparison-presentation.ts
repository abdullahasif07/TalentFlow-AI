export function comparisonScoreAvailable(
  available: boolean,
  score: number | string | null,
): boolean {
  return available && score !== null && Number.isFinite(Number(score));
}

export function gapEvidenceLabel(evidence: readonly string[]): string {
  return evidence.length ? "Evidence recorded" : "Missing evidence";
}
