import assert from "node:assert/strict";
import test from "node:test";

import {
  configuredMaxResumeSizeMb,
  createGraphQLMultipartBody,
  formatFileSize,
  maxResumeSizeBytes,
  validatePublicApplication,
  validateResume,
} from "../lib/public-application.ts";

const validValues = {
  fullName: "Jordan Taylor",
  email: "jordan@example.com",
  phone: "+1 415 555 0142",
  linkedinUrl: "https://linkedin.com/in/jordan-taylor",
  githubUrl: "https://github.com/jordan-taylor",
  portfolioUrl: "https://jordan.example.com",
  coverLetter: "I am interested in contributing to this role.",
};

function pdfFile(name = "resume.pdf", content = "%PDF-1.7\nResume") {
  return new File([content], name, { type: "application/pdf" });
}

test("valid applicant details and PDF pass client validation", () => {
  assert.deepEqual(
    validatePublicApplication(validValues, pdfFile(), maxResumeSizeBytes(10)),
    {},
  );
});

test("required applicant fields produce clear errors", () => {
  const errors = validatePublicApplication(
    { ...validValues, fullName: " ", email: "", coverLetter: "" },
    null,
    maxResumeSizeBytes(10),
  );

  assert.match(errors.fullName ?? "", /full name/i);
  assert.match(errors.email ?? "", /email/i);
  assert.match(errors.coverLetter ?? "", /cover letter/i);
  assert.match(errors.resume ?? "", /attach/i);
});

test("email and optional URLs are validated without requiring optional links", () => {
  const invalid = validatePublicApplication(
    {
      ...validValues,
      email: "not-an-email",
      linkedinUrl: "linkedin.com/in/jordan",
      githubUrl: "javascript:alert(1)",
      portfolioUrl: "",
    },
    pdfFile(),
    maxResumeSizeBytes(10),
  );

  assert.match(invalid.email ?? "", /valid email/i);
  assert.match(invalid.linkedinUrl ?? "", /valid linkedin/i);
  assert.match(invalid.githubUrl ?? "", /valid github/i);
  assert.equal(invalid.portfolioUrl, undefined);
});

test("resume validation rejects wrong types, empty files, and oversized PDFs", () => {
  assert.match(
    validateResume(new File(["text"], "resume.txt", { type: "text/plain" }), 1024) ?? "",
    /PDF/i,
  );
  assert.match(validateResume(pdfFile("resume.pdf", ""), 1024) ?? "", /empty/i);
  assert.match(
    validateResume(pdfFile("resume.pdf", "x".repeat(1025)), 1024) ?? "",
    /smaller/i,
  );
});

test("multipart body follows the GraphQL upload map without base64 encoding", () => {
  const resume = pdfFile();
  const body = createGraphQLMultipartBody(
    "mutation Submit($input: SubmitApplicationInput!) { submitApplication(input: $input) { success } }",
    { input: { jobId: "7", resume: null } },
    resume,
  );
  const operations = JSON.parse(String(body.get("operations")));
  const uploadMap = JSON.parse(String(body.get("map")));
  const attachedFile = body.get("0");

  assert.equal(operations.variables.input.jobId, "7");
  assert.equal(operations.variables.input.resume, null);
  assert.deepEqual(uploadMap, { "0": ["variables.input.resume"] });
  assert.ok(attachedFile instanceof File);
  assert.equal(attachedFile.name, "resume.pdf");
  assert.equal(attachedFile.type, "application/pdf");
});

test("resume size configuration has a safe default", () => {
  assert.equal(configuredMaxResumeSizeMb(undefined), 10);
  assert.equal(configuredMaxResumeSizeMb("15"), 15);
  assert.equal(configuredMaxResumeSizeMb("invalid"), 10);
  assert.equal(configuredMaxResumeSizeMb("0"), 10);
  assert.equal(formatFileSize(1024), "1 KB");
});
