export function formatComparisonScore(score: number | string | null): string {
  if (score === null) return "Not available";
  const numericScore = Number(score);
  if (!Number.isFinite(numericScore)) return "Not available";
  return Number.isInteger(numericScore)
    ? String(numericScore)
    : numericScore.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

export function gapEvidenceLabel(evidence: readonly string[]): string {
  return evidence.length ? "Evidence recorded" : "Missing evidence";
}
