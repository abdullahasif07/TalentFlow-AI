# TalentFlow AI backend

## Setup

The commands below assume Python 3.11+ and PostgreSQL are installed.

```bash
cd backend
```

1. Create the PostgreSQL database:

   ```bash
   createdb talentflow_ai
   ```

2. Configure the environment:

   ```bash
   cp .env.example .env
   ```

   Update `DATABASE_URL` if your PostgreSQL username, password, host, or port differs.
   `UPLOAD_ROOT` controls local file storage and `MAX_RESUME_SIZE_BYTES` defaults to 10 MB.

3. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Initialize and run Aerich migrations. Run `init-db` only once for a new database; for subsequent model changes use `migrate` followed by `upgrade`:

   ```bash
   aerich init-db
   aerich upgrade
   # Later: aerich migrate --name describe_change && aerich upgrade
   ```

5. Insert demo data (the script is safe to run repeatedly):

   ```bash
   python -m scripts.seed
   ```

6. Start FastAPI:

   ```bash
   uvicorn app.main:app --reload
   ```

7. Open the Strawberry GraphQL IDE at <http://localhost:8000/graphql>.

## Day 2 backend capabilities

- Public application submission with candidate reuse and duplicate-job protection
- Local PDF resume validation and storage with a replaceable storage service
- Recruiter applicant filtering, sorting, pagination, and detailed application views
- Audited individual and bulk pipeline status updates
- Recruiter notes kept separate from AI evaluation data
- No AI parsing, scoring, background workers, authentication, or frontend workflow yet

## Example operations

```graphql
query Jobs {
  jobs(input: { status: OPEN }) {
    success
    totalCount
    items { id title status requiredSkills }
    errors { code message field }
  }
}

query Job {
  job(input: { id: "1" }) {
    success
    job { id title status }
    errors { code message field }
  }
}

query Applications {
  applications(input: {
    jobId: "1"
    filters: {
      status: SHORTLISTED
      minimumFitScore: 70
      candidateSearch: "jordan"
    }
    sort: FIT_SCORE_DESC
    pagination: { limit: 25, offset: 0 }
  }) {
    success
    totalCount
    pageInfo { limit offset hasNextPage hasPreviousPage }
    items {
      id
      status
      fitScore
      appliedAt
      candidate {
        id name email phone linkedinUrl githubUrl portfolioUrl
      }
      resume { id fileUrl }
      evaluation { overallScore recommendation confidence }
    }
    errors { code message field }
  }
}

query ApplicationDetail {
  application(input: { id: "1" }) {
    success
    application {
      id status fitScore coverLetter appliedAt updatedAt
      candidate { id name email phone linkedinUrl githubUrl portfolioUrl }
      job { id companyId title description status }
      resume { id fileUrl }
      evaluation { overallScore recommendation confidence }
      statusHistory { previousStatus newStatus changedBy createdAt }
      notes { id content recruiter { id name email } createdAt updatedAt }
      outreachEmails { subject body status generatedAt approvedAt sentAt }
    }
    errors { code message field }
  }
}

query JobStatistics {
  job(input: { id: "1" }) {
    success
    job {
      id title
      applicantCount
      shortlistedCount
      contactedCount
      interviewCount
      hiredCount
      recommendedCandidateCount
    }
    errors { code message field }
  }
}

mutation CreateJob {
  createJob(input: {
    companyId: "1"
    title: "Engineering Manager"
    description: "Lead a product engineering team."
    requiredSkills: ["Engineering leadership", "System design"]
    preferredSkills: ["B2B SaaS"]
    status: OPEN
  }) {
    success
    job { id title status }
    errors { code message field }
  }
}

mutation UpdateApplicationStatus {
  updateApplicationStatus(input: {
    applicationId: "1"
    status: SHORTLISTED
    changedBy: "maya.patel@northstar.example.com"
    recruiterId: "1"
  }) {
    success
    application { id status updatedAt }
    errors { code message field }
  }
}

mutation AddApplicationNote {
  addApplicationNote(input: {
    applicationId: "1"
    recruiterId: "1"
    content: "Strong communication during the initial screen."
  }) {
    success
    note { id content recruiter { id name email } createdAt }
    errors { code message field }
  }
}

mutation BulkUpdateApplicationStatus {
  bulkUpdateApplicationStatus(input: {
    applicationIds: ["1", "2", "3"]
    status: INTERVIEW
    changedBy: "maya.patel@northstar.example.com"
    recruiterId: "1"
  }) {
    success
    applications { id status }
    failures { applicationId errors { code message field } }
    errors { code message field }
  }
}
```

All operations use named input objects and typed result payloads. Expected errors are returned in
the payload as `OperationError` values with a stable `code`, readable `message`, and optional
`field`. Transport-level GraphQL errors are reserved for malformed documents and invalid scalar
shapes. Applicant lists default to newest first and 25 records per page, allow at most 100 records
per request, and always include total and offset pagination metadata. Applications without fit
scores remain queryable and are placed last when sorting by fit score.

Pipeline status changes are audited in chronological `statusHistory`. Repeating the current status
does not add another history entry. Human updates are intentionally flexible; callers should set
`automated: true` only for system-driven transitions, which use stricter transition rules. Bulk
updates may partially succeed, so clients should inspect both `applications` and `failures`.

## Submit an application with a resume

Application submission uses the GraphQL multipart request specification because the input
contains a file. Only non-empty PDF files up to the configured size limit are accepted.

With the API running and an open job whose ID is `1`, test the mutation from another terminal:

```bash
curl http://localhost:8000/graphql \
  -F 'operations={"query":"mutation Submit($input: SubmitApplicationInput!) { submitApplication(input: $input) { success application { id status resumeUrl candidate { id name email } job { id title } } errors { code message field } } }","variables":{"input":{"jobId":"1","fullName":"Jordan Taylor","email":"jordan@example.com","phone":"+1 415 555 0142","linkedinUrl":"https://linkedin.com/in/jordan-taylor","githubUrl":"https://github.com/jordantaylor","portfolioUrl":"https://jordantaylor.example.com","coverLetter":"I am excited to apply for this role.","resume":null}}}' \
  -F 'map={"0":["variables.input.resume"]}' \
  -F '0=@/absolute/path/to/resume.pdf;type=application/pdf'
```

The mutation normalizes the email, reuses an existing candidate, prevents a second application
to the same job, creates an initial `APPLIED` history entry, and stores the file at
`uploads/resumes/{candidate_id}/{generated_filename}.pdf`. A later application to a different
job is allowed and updates that candidate's current `Resume` record.

Run the submission tests with:

```bash
python -m unittest discover -s tests -v
```

The application deliberately does not auto-create tables on startup. Aerich owns schema changes so development and production follow the same migration path.
