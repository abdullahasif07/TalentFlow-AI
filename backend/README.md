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
  jobs { id title status requiredSkills }
}

query Applications {
  applications(jobId: "1") {
    id status fitScore
    candidate { name email }
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
  }) { id title status }
}

mutation UpdateApplicationStatus {
  updateApplicationStatus(
    applicationId: "1"
    status: SHORTLISTED
    changedBy: "maya.patel@northstar.example.com"
  ) { id status updatedAt }
}
```

The application deliberately does not auto-create tables on startup. Aerich owns schema changes so development and production follow the same migration path.
