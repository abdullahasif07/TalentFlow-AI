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
```

Open <http://localhost:3000>. The root route redirects to `/dashboard`.

## Available routes

- `/dashboard` — live recruiter overview powered by the jobs GraphQL query
- `/jobs` — searchable, status-filtered job list
- `/jobs/[id]` — job details, requirements, and hiring statistics
- `/jobs/[id]/applications/[applicationId]` — candidate detail, evaluation, notes, and status actions
- `/pipeline` — job-specific hiring board with filters and recruiter-controlled drag-and-drop
- `/candidates`, `/ai-activity` — foundation placeholder routes

## Checks

```bash
npm run typecheck
npm run lint
npm run build
```
