import assert from "node:assert/strict";
import test from "node:test";

import {
  publicApplicationPath,
  publicApplicationUrl,
} from "../lib/application-link.ts";
import { applicationProcessingPresentation } from "../lib/application-processing.ts";
import { completedFitScore } from "../lib/fit-score.ts";

test("public application links use the supplied runtime origin", () => {
  assert.equal(publicApplicationPath("42"), "/jobs/42/apply");
  assert.equal(
    publicApplicationUrl("https://talentflow.example", "42"),
    "https://talentflow.example/jobs/42/apply",
  );
  assert.doesNotMatch(
    publicApplicationUrl("https://talentflow.example", "42"),
    /localhost/,
  );
});

test("application processing moves through resume, evaluation, and completion labels", () => {
  assert.deepEqual(
    applicationProcessingPresentation("PROCESSING", "NOT_STARTED", false),
    { state: "PROCESSING", label: "Resume processing" },
  );
  assert.deepEqual(
    applicationProcessingPresentation("COMPLETED", "PROCESSING", false),
    { state: "PROCESSING", label: "AI evaluating" },
  );
  assert.deepEqual(
    applicationProcessingPresentation("COMPLETED", "COMPLETED", true),
    { state: "COMPLETED", label: "Evaluation complete" },
  );
});

test("resume and evaluation failures remain distinguishable", () => {
  assert.equal(
    applicationProcessingPresentation("FAILED", "NOT_STARTED", false).label,
    "Resume processing failed",
  );
  assert.equal(
    applicationProcessingPresentation("COMPLETED", "FAILED", false).label,
    "AI evaluation failed",
  );
});

test("fit scores are visible only after evaluation completes", () => {
  assert.equal(completedFitScore(92, "NOT_STARTED"), null);
  assert.equal(completedFitScore("92.5", "PROCESSING"), null);
  assert.equal(completedFitScore("92.5", "COMPLETED"), 92.5);
  assert.equal(completedFitScore(null, "COMPLETED"), null);
  assert.equal(completedFitScore("invalid", "COMPLETED"), null);
});

test("job skill lists are trimmed, de-duplicated, and split on commas or newlines", async () => {
  const { parseSkillList } = await import("../lib/graphql/jobs.ts");
  assert.deepEqual(parseSkillList(" Python, FastAPI ,python\nPostgreSQL,, "), [
    "Python",
    "FastAPI",
    "PostgreSQL",
  ]);
  assert.deepEqual(parseSkillList("   "), []);
});
