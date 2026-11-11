# TalentFlow AI frontend

The landing page, public application flow, and recruiter workspace are built with Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui-style components, and Apollo Client.

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

Open <http://localhost:3000>.

Optionally set `NEXT_PUBLIC_API_URL` when the REST endpoints are not served next to the GraphQL
endpoint; by default it is the GraphQL URL without `/graphql`.

## Available routes

Public:

- `/` - landing page with a one-click demo login and the list of open roles
- `/login` - recruiter sign-in (email and password, or the demo account)
- `/jobs/[id]/apply` - public job details, PDF application form, and live screening progress

Recruiter (requires sign-in; signed-out visitors are sent to `/login`):

- `/dashboard` - recruiting overview
- `/jobs` - searchable, status-filtered job list
- `/jobs/new` - create a job; the AI scoring rubric is generated automatically
- `/jobs/[id]` - job details, statistics, AI screening controls, applicants, and recommendations
- `/jobs/[id]/applications/[applicationId]` - candidate detail, resume download, evaluation, notes, status, and outreach
- `/jobs/[id]/compare` - side-by-side AI comparison of 2-5 evaluated candidates
- `/pipeline` - job-specific hiring board with drag-and-drop stage changes

The session is an HTTP-only cookie set by the backend, so Apollo sends requests with
`credentials: "include"`. If the API reports an expired session, the app returns to sign-in.

OPEN Job Details pages include **Copy application link** and **Open application page** actions.
The copied URL uses the current browser origin, so the same action works in local, preview, and
production environments. Applicant lists refresh when the recruiter returns to the tab, poll
while AI processing is running, and also provide a manual Refresh action.

## Checks

```bash
npm run typecheck
npm run lint
npm run build
npm run test:public-application
npm run test:application-integration
```
