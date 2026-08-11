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
  applications(input: { jobId: "1" }) {
    success
    totalCount
    items {
      id status fitScore
      candidate { name email }
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
  }) {
    success
    application { id status updatedAt }
    errors { code message field }
  }
}
```

All operations use named input objects and typed result payloads. Expected errors are returned in
the payload as `OperationError` values with a stable `code`, readable `message`, and optional
`field`. Transport-level GraphQL errors are reserved for malformed documents and invalid scalar
shapes.

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
