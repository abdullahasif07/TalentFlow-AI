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
   `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` default to separate Redis databases on
   `localhost:6379`.

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

## Background AI worker

Start the included Redis service from the project root and verify it is healthy:

```bash
docker compose up -d redis
docker compose exec redis redis-cli ping
```

The second command should print `PONG`. Then start a Celery worker from `backend/` with the
virtual environment active:

```bash
celery -A app.worker.celery_app:celery_app worker --loglevel=INFO
```

In another terminal, confirm that the worker responds:

```bash
celery -A app.worker.celery_app:celery_app inspect ping
```

Tasks are deliberately separate so failures can be retried independently. They may be enqueued
through GraphQL or directly from Python:

```python
from app.worker.tasks import (
    evaluate_application,
    generate_job_criteria,
    process_resume,
)

resume_result = process_resume.delay(application_id=1)
criteria_result = generate_job_criteria.delay(job_id=1)
evaluation_result = evaluate_application.delay(application_id=1)
```

`process_resume` extracts and persists PDF text, then parses and persists structured resume data.
`generate_job_criteria` creates and persists the job rubric. `evaluate_application` requires both
structured inputs, upserts the application's single AI evaluation, and updates `fit_score` without
changing pipeline status. Run resume and criteria processing before evaluation.

Worker tasks use a fresh async event loop and Tortoise connection lifecycle for each execution.
Temporary database or AI-provider failures use bounded exponential retries. Missing records,
invalid PDFs, absent prerequisite data, and invalid structured output fail without being retried.

## AI processing GraphQL operations

The trigger mutations validate prerequisites, enqueue Celery work, and return immediately. They
never wait for the AI provider:

```graphql
mutation TriggerAIProcessing {
  generateJobCriteria(input: { jobId: "1" }) {
    success accepted resourceId state message taskId
    errors { code message field }
  }
  processApplicationResume(input: { applicationId: "1" }) {
    success accepted resourceId state message taskId
    errors { code message field }
  }
  generateCandidateEvaluation(input: { applicationId: "1" }) {
    success accepted resourceId state message taskId
    errors { code message field }
  }
}
```

Queue every eligible, unevaluated applicant for one job with:

```graphql
mutation ScreenApplicants {
  screenJobApplicants(input: { jobId: "1" }) {
    success accepted state queuedCount applicationIds failedApplicationIds message
    errors { code message field }
  }
}
```

Read the current recommendations without triggering AI work:

```graphql
query RecommendedCandidates {
  recommendedCandidates(input: { jobId: "1", limit: 5 }) {
    success totalCount limit
    items {
      candidate { id name email }
      application { id status fitScore evaluationProcessingState appliedAt }
      evaluation {
        overallScore recommendation confidence processingState
        strengths { summary evidence }
        gaps { summary evidence }
        evidence { claim resumeEvidence category }
        categoryScores { name score weight weightedScore rationale evidence }
      }
    }
    errors { code message field }
  }
}
```

Jobs expose `criteriaProcessingState`, resumes expose `processingState`, and applications expose
`evaluationProcessingState`. Each uses `NOT_STARTED`, `PROCESSING`, `COMPLETED`, or `FAILED`.

## Backend capabilities

- Public application submission with candidate reuse and duplicate-job protection
- Local PDF resume validation and storage with a replaceable storage service
- Recruiter applicant filtering, sorting, pagination, and detailed application views
- Audited individual and bulk pipeline status updates
- Recruiter notes kept separate from AI evaluation data
- PDF text extraction, structured resume parsing, job rubrics, and evidence-based candidate scoring
- Redis-backed Celery tasks for independent resume, criteria, and evaluation processing
- No automatic ranking, authentication, or frontend workflow yet

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
