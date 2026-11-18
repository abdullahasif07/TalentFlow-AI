# Deploying TalentFlow AI

Cheapest setup that runs the full product, including the AI features. No domain needed.

```
Recruiter's browser
      │  https://<project>.vercel.app          (one domain → first-party session cookie)
      ▼
Vercel (free)  ── Next.js frontend
      │  /backend/*  forwarded by frontend/proxy.ts, with a shared secret
      ▼
VPS (~€4–6/month) ── Caddy (HTTPS via <ip>.sslip.io)
                      ├─ api     FastAPI + GraphQL
                      ├─ worker  Celery (AI screening)
                      ├─ beat    demo cleanup (expired sandboxes)
                      ├─ postgres
                      └─ redis
```

**How this fixes the cookie problem:** the browser only talks to the Vercel domain.
Vercel forwards `/backend/*` to the API, so the API's session cookie is set on the
Vercel domain itself. Browsers that block third-party cookies (Safari, incognito)
still keep recruiters signed in.

**How the API is protected:** the API refuses any request without the secret that
only the Vercel proxy sends. The OpenAI hard spending limit (step 2) and the daily AI
call limit cap cost, and per-IP rate limits apply to each real visitor.

---

## 1. Push the code

Commit and push to GitHub. The server and Vercel both pull from there.

## 2. OpenAI: create a key with a hard spending cap

1. https://platform.openai.com → **Projects** → create a project called `talentflow-demo`.
2. In that project, open **Limits** and set a **monthly budget**, such as $5. This is
   the backstop: the bill can't go over it even if everything else fails.
3. Create an API key in that project and keep it for step 6.

## 3. Rent a VPS

Any provider works. Hetzner Cloud is the cheapest; a **CX22** (2 vCPU, 4 GB RAM) costs
about €4–5/month. DigitalOcean, Lightsail and Linode have similar $5–6 plans with 1–2 GB RAM.

- Image: **Ubuntu 24.04**
- SSH key: if you don't have one, run `ssh-keygen -t ed25519` on your Mac and paste
  the contents of `~/.ssh/id_ed25519.pub` into the provider's form.
- After it's created, copy the server's **public IPv4**, for example `203.0.113.10`.

Your API's free HTTPS hostname is that IP with dashes: **`203-0-113-10.sslip.io`**.
sslip.io simply resolves that name to that IP.

## 4. Prepare the server (one time)

From your Mac:

```bash
ssh root@203.0.113.10
```

On the server:

```bash
# Updates and firewall: allow only SSH and web traffic
apt update && apt upgrade -y
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

# Docker
curl -fsSL https://get.docker.com | sh

# 2 GB swap so builds don't run out of memory on small plans
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 5. Get the code onto the server

```bash
git clone https://github.com/abdullahasif07/TalentFlow-AI.git /opt/talentflow
cd /opt/talentflow
```

If the repo is private, GitHub asks for a username and password. Use your GitHub
username, and for the password a
[personal access token](https://github.com/settings/tokens?type=beta) with read
access to that repo.

## 6. Create the server's settings file

```bash
cp deploy/.env.production.example deploy/.env.production
openssl rand -hex 24   # → POSTGRES_PASSWORD
openssl rand -hex 32   # → SESSION_SECRET
openssl rand -hex 32   # → PROXY_SHARED_SECRET  (save it; Vercel needs the same value)
nano deploy/.env.production
```

Fill in every `<...>` value:

| Setting | Value |
|---|---|
| `API_HOST` | `203-0-113-10.sslip.io` (your IP with dashes) |
| `POSTGRES_PASSWORD`, `SESSION_SECRET`, `PROXY_SHARED_SECRET` | the generated values |
| `OPENAI_API_KEY` | the key from step 2 |
| `CORS_ORIGINS` | leave the placeholder for now; set it in step 9 |

Save with `Ctrl+O`, `Enter`, then `Ctrl+X`. This file stays only on the server, and
git ignores it.

## 7. Start the backend

```bash
docker compose -f compose.prod.yaml --env-file deploy/.env.production up -d --build
docker compose -f compose.prod.yaml --env-file deploy/.env.production ps
```

The first build takes a few minutes. When `api` shows **healthy**, load the demo data:

```bash
docker compose -f compose.prod.yaml --env-file deploy/.env.production exec api python -m scripts.seed
```

Check it from your Mac:

```bash
curl https://203-0-113-10.sslip.io/health        # → {"status":"ok","environment":"production"}
curl https://203-0-113-10.sslip.io/auth/config   # → {"detail":"Not found."}  (correct: no secret)
```

## 8. Deploy the frontend on Vercel

1. https://vercel.com → sign in with GitHub (the free **Hobby** plan is enough).
2. **Add New → Project** → import `TalentFlow-AI`.
3. Set **Root Directory** to `frontend`. The framework is detected as Next.js.
4. Add these **Environment Variables**:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_GRAPHQL_URL` | `/backend/graphql` |
   | `NEXT_PUBLIC_MAX_RESUME_SIZE_MB` | `4` |
   | `BACKEND_ORIGIN` | `https://203-0-113-10.sslip.io` |
   | `PROXY_SHARED_SECRET` | same value as on the server |

5. **Deploy**. Note your URL, for example `https://talentflow-ai.vercel.app`.

> If you change any `NEXT_PUBLIC_*` variable later, redeploy. Those values are baked
> in when the site is built.

## 9. Point the backend at your Vercel URL

On the server, set `CORS_ORIGINS=["https://talentflow-ai.vercel.app"]` in
`deploy/.env.production`, then:

```bash
docker compose -f compose.prod.yaml --env-file deploy/.env.production up -d --force-recreate api worker beat
```

## 10. Test the whole recruiter flow

Open the Vercel URL in a private window and check that each step works:

- [ ] **Try the demo** logs you in, and a refresh keeps you logged in
- [ ] Create a job, and AI criteria are generated
- [ ] Open the job's public apply link and submit a PDF resume
- [ ] The application moves to processed with an AI score and evaluation
- [ ] Compare candidates and generate outreach
- [ ] Download a resume from the application page

Then add the URL to `README.md` (there's a placeholder at the top) and send it to recruiters.

---

## Day-to-day

```bash
cd /opt/talentflow
C="docker compose -f compose.prod.yaml --env-file deploy/.env.production"

git pull && $C up -d --build          # deploy new backend code (Vercel redeploys the frontend on push)
$C logs -f api worker                  # follow logs (Ctrl+C to stop)
$C exec api python -m scripts.reset_demo --yes   # reset the demo data now
$C exec redis redis-cli -n 2 GET talentflow:ai-calls:$(date -u +%F)   # AI calls used today
```

Data is kept in Docker volumes across restarts and redeploys.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `curl https://<ip>.sslip.io/health` fails | `$C logs caddy`. Check ports 80/443 are open (`ufw status`, and the provider's firewall if it has one) and that `API_HOST` matches the IP. |
| Caddy can't get a certificate for sslip.io | Rare rate limit. Use a free [DuckDNS](https://www.duckdns.org) name pointed at the IP, put it in `API_HOST` and `BACKEND_ORIGIN`, then restart. |
| Site loads but every action fails / "not configured" | Check the Vercel env vars: `BACKEND_ORIGIN` must start with `https://` and have no trailing slash, and `PROXY_SHARED_SECRET` must match the server exactly. Redeploy after changes. |
| Login works but is lost on refresh | `NEXT_PUBLIC_GRAPHQL_URL` must be `/backend/graphql` (relative), not the sslip.io URL. Redeploy. |
| Applications stay "processing" | `$C logs worker`. Usually a missing or invalid `OPENAI_API_KEY`, or the daily AI limit was reached. |
| Resume upload rejected | The 4 MB limit is intentional, because the Vercel proxy can't pass larger bodies. |

## Monthly cost

| Item | Cost |
|---|---|
| Vercel Hobby | $0 |
| VPS | ~€4–6 |
| sslip.io hostname + Let's Encrypt HTTPS | $0 |
| OpenAI (`gpt-4.1-mini`) | usage based, capped by your project budget |
