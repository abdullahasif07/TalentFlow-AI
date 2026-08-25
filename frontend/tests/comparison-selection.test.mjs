import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_COMPARISON_CANDIDATES,
  buildApplicantsUrl,
  buildComparisonUrl,
  canCompareCandidates,
  clearComparisonSelection,
  normalizeComparisonIds,
  parseComparisonSelection,
  updateComparisonSelection,
} from "../lib/comparison-selection.ts";
import {
  formatComparisonScore,
  gapEvidenceLabel,
} from "../lib/comparison-presentation.ts";

test("one candidate cannot be compared and two candidates can", () => {
  assert.equal(canCompareCandidates(["a1"]), false);
  assert.equal(canCompareCandidates(["a1", "a2"]), true);
});

test("five candidates can be selected and a sixth is rejected", () => {
  const selected = ["a1", "a2", "a3", "a4", "a5"];

  assert.equal(selected.length, MAX_COMPARISON_CANDIDATES);
  assert.equal(canCompareCandidates(selected), true);
  assert.deepEqual(updateComparisonSelection(selected, "a6", true), {
    ids: selected,
    outcome: "limit_reached",
  });
});

test("an unevaluated candidate cannot be selected", () => {
  assert.deepEqual(updateComparisonSelection(["a1"], "a2", false), {
    ids: ["a1"],
    outcome: "ineligible",
  });
});

test("selection can be cleared without retaining IDs", () => {
  assert.deepEqual(clearComparisonSelection(["a1", "a2"]), []);
});

test("duplicate and empty IDs are normalized", () => {
  assert.deepEqual(normalizeComparisonIds(["a1", "", " a1 ", "a2"]), [
    "a1",
    "a2",
  ]);
});

test("comparison navigation contains the selected Application IDs", () => {
  assert.equal(
    buildComparisonUrl("job-1", ["a1", "a2", "a3"]),
    "/jobs/job-1/compare?applications=a1%2Ca2%2Ca3",
  );
});

test("comparison route accepts 2 through 5 unique Application IDs", () => {
  assert.deepEqual(parseComparisonSelection("1,2"), {
    ids: ["1", "2"],
    error: null,
  });
  assert.deepEqual(parseComparisonSelection("1,2,3"), {
    ids: ["1", "2", "3"],
    error: null,
  });
  assert.deepEqual(parseComparisonSelection("1,2,3,4,5"), {
    ids: ["1", "2", "3", "4", "5"],
    error: null,
  });
});

test("comparison route rejects invalid selection counts and duplicates", () => {
  assert.match(parseComparisonSelection("1").error, /at least 2/i);
  assert.match(parseComparisonSelection("1,2,3,4,5,6").error, /no more than 5/i);
  assert.match(parseComparisonSelection("1,1").error, /unique/i);
});

test("missing category values render as unavailable without inventing a score", () => {
  assert.equal(formatComparisonScore(null), "Not available");
  assert.equal(formatComparisonScore("92.0"), "92");
  assert.equal(formatComparisonScore("92.75"), "92.75");
});

test("gap evidence labels distinguish unverified and evidence-backed findings", () => {
  assert.equal(gapEvidenceLabel([]), "Missing evidence");
  assert.equal(gapEvidenceLabel(["Resume evidence"]), "Evidence recorded");
});

test("back navigation returns to the selected Job applicant page", () => {
  assert.equal(buildApplicantsUrl("job-1"), "/jobs/job-1");
});
