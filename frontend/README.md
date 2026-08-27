# TalentFlow AI frontend

The recruiter workspace is built with Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui-style components, and Apollo Client.

## Local setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_GRAPHQL_URL` in `.env.local` to the TalentFlow backend GraphQL endpoint. The local default is:

```text
NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8000/graphql
NEXT_PUBLIC_MAX_RESUME_SIZE_MB=10
```

Open <http://localhost:3000>. The root route redirects to `/dashboard`.

## Available routes

- `/dashboard` — live recruiter overview powered by the jobs GraphQL query
- `/jobs` — searchable, status-filtered job list
- `/jobs/[id]` — job details, requirements, and hiring statistics
- `/jobs/[id]/apply` — public job details and multipart PDF application form
- `/jobs/[id]/applications/[applicationId]` — candidate detail, evaluation, notes, and status actions
- `/pipeline` — job-specific hiring board with filters and recruiter-controlled drag-and-drop
- `/candidates`, `/ai-activity` — foundation placeholder routes

OPEN Job Details pages include **Copy application link** and **Open application page** actions.
The copied URL uses the current browser origin, so the same action works in local, preview, and
production environments. Applicant lists refetch when the recruiter returns to the tab and also
provide a manual Refresh action.

## Checks

```bash
npm run typecheck
npm run lint
npm run build
npm run test:public-application
npm run test:application-integration
```
