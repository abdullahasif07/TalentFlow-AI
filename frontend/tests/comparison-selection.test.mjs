import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_COMPARISON_CANDIDATES,
  activateComparisonJob,
  buildApplicantsUrl,
  buildCandidateComparisonInput,
  buildComparisonUrl,
  canCompareCandidates,
  clearComparisonSelection,
  getStoredComparisonSelection,
  normalizeComparisonIds,
  parseComparisonSelection,
  removeIneligibleVisibleSelections,
  storeComparisonSelection,
  updateComparisonSelection,
} from "../lib/comparison-selection.ts";
import {
  comparisonScoreAvailable,
  gapEvidenceLabel,
} from "../lib/comparison-presentation.ts";

test("one candidate cannot be compared and two candidates can", () => {
  assert.equal(canCompareCandidates(["1"]), false);
  assert.equal(canCompareCandidates(["1", "2"]), true);
});

test("five candidates can be selected and a sixth is rejected", () => {
  const selected = ["1", "2", "3", "4", "5"];

  assert.equal(selected.length, MAX_COMPARISON_CANDIDATES);
  assert.equal(canCompareCandidates(selected), true);
  assert.deepEqual(updateComparisonSelection(selected, "6", true), {
    ids: selected,
    outcome: "limit_reached",
  });
});

test("an unevaluated candidate cannot be selected", () => {
  assert.deepEqual(updateComparisonSelection(["1"], "2", false), {
    ids: ["1"],
    outcome: "ineligible",
  });
});

test("selection can be cleared without retaining IDs", () => {
  assert.deepEqual(clearComparisonSelection(["1", "2"]), []);
});

test("duplicate, malformed, and empty IDs are sanitized", () => {
  assert.deepEqual(normalizeComparisonIds(["1", "", " 1 ", "bad", "2"]), [
    "1",
    "2",
  ]);
});

test("comparison navigation contains the selected Application IDs", () => {
  assert.equal(
    buildComparisonUrl("42", ["10", "11", "12"]),
    "/jobs/42/compare?applications=10%2C11%2C12",
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

test("comparison route rejects invalid counts and malformed values", () => {
  assert.match(parseComparisonSelection("1").error, /at least 2/i);
  assert.match(parseComparisonSelection("1,2,3,4,5,6").error, /no more than 5/i);
  assert.match(parseComparisonSelection("1,not-an-id").error, /positive integers/i);
});

test("comparison route removes duplicate IDs before validation", () => {
  assert.deepEqual(parseComparisonSelection("1,1,2,2"), {
    ids: ["1", "2"],
    error: null,
  });
  assert.match(parseComparisonSelection("1,1").error, /at least 2/i);
});

test("comparison variables preserve the correct Job and unique Applications", () => {
  assert.deepEqual(buildCandidateComparisonInput("42", ["10", "10", "11"]), {
    jobId: "42",
    applicationIds: ["10", "11"],
  });
  assert.throws(
    () => buildCandidateComparisonInput("invalid-job", ["10", "11"]),
    /invalid Job ID/i,
  );
});

test("missing category values remain unavailable without inventing a score", () => {
  assert.equal(comparisonScoreAvailable(false, null), false);
  assert.equal(comparisonScoreAvailable(false, "92"), false);
  assert.equal(comparisonScoreAvailable(true, null), false);
  assert.equal(comparisonScoreAvailable(true, "92.75"), true);
});

test("gap evidence labels distinguish unverified and evidence-backed findings", () => {
  assert.equal(gapEvidenceLabel([]), "Missing evidence");
  assert.equal(gapEvidenceLabel(["Resume evidence"]), "Evidence recorded");
});

test("selection survives comparison navigation but clears when the Job changes", () => {
  activateComparisonJob("42");
  storeComparisonSelection("42", ["10", "11"]);
  assert.deepEqual(getStoredComparisonSelection("42"), ["10", "11"]);

  activateComparisonJob("43");
  assert.deepEqual(getStoredComparisonSelection("42"), []);
  assert.deepEqual(getStoredComparisonSelection("43"), []);
});

test("visible stale evaluations are removed while filtered selections remain", () => {
  assert.deepEqual(
    removeIneligibleVisibleSelections(["10", "11", "12"], [
      { applicationId: "10", eligible: true },
      { applicationId: "11", eligible: false },
    ]),
    ["10", "12"],
  );
});

test("back navigation returns to the selected Job applicant page", () => {
  assert.equal(buildApplicantsUrl("42"), "/jobs/42");
  assert.equal(buildApplicantsUrl("invalid"), "/jobs");
});
