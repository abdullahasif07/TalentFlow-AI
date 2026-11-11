# TalentFlow AI - shortcuts for everyday commands.
# Run `make` or `make help` to see everything.

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE  := docker compose
BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(CURDIR)/$(VENV)/bin/python
AERICH   := $(CURDIR)/$(VENV)/bin/aerich
CELERY   := $(CURDIR)/$(VENV)/bin/celery

# Must match DATABASE_URL in backend/.env and the postgres service in compose.yaml.
PG_USER := postgres
PG_DB   := talentflow_ai
PSQL    := $(COMPOSE) exec postgres psql -U $(PG_USER) -d $(PG_DB)

# Defaults for commands that take arguments.
TABLE ?= jobs
LIMIT ?= 20

.PHONY: help setup install env check-venv \
        services-up services-down services-status logs db-wait \
        backend worker frontend dev stop exit \
        db-shell db-tables db-describe db-show db-count db-query db-backup db-restore db-wipe redis-cli \
        migrate upgrade downgrade migration-history migration-heads \
        seed reset-demo \
        test test-backend test-frontend lint typecheck build

##@ Help

help: ## Show this list of commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<command>\033[0m [VAR=value]\n"} \
	  /^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } \
	  /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)
	@echo ""

##@ First-time setup

setup: env install services-up upgrade seed ## Everything for a fresh clone: env files, deps, databases, migrations, demo data
	@echo ""
	@echo "Setup complete. Start everything with: make dev"

install: ## Install backend (venv + pip) and frontend (npm) dependencies
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r $(BACKEND)/requirements.txt
	cd $(FRONTEND) && npm install

env: ## Create backend/.env and frontend/.env.local from the examples (never overwrites)
	@if [ ! -f $(BACKEND)/.env ]; then \
	  cp $(BACKEND)/.env.example $(BACKEND)/.env; \
	  secret=$$(python3 -c "import secrets; print(secrets.token_urlsafe(48))"); \
	  sed -i '' "s|^SESSION_SECRET=.*|SESSION_SECRET=$$secret|" $(BACKEND)/.env; \
	  echo "Created backend/.env (add your OPENAI_API_KEY)"; \
	else echo "backend/.env already exists"; fi
	@if [ ! -f $(FRONTEND)/.env.local ]; then \
	  cp $(FRONTEND)/.env.example $(FRONTEND)/.env.local; echo "Created frontend/.env.local"; \
	else echo "frontend/.env.local already exists"; fi

check-venv:
	@test -x $(PY) || { echo "Backend virtualenv missing. Run: make install"; exit 1; }

##@ Databases (Docker)

services-up: ## Start Postgres and Redis in Docker and wait until they are ready
	@docker info >/dev/null 2>&1 || { echo "Docker is not running. Open Docker Desktop and try again."; exit 1; }
	$(COMPOSE) up -d postgres redis
	@$(MAKE) --no-print-directory db-wait

services-down: ## Stop Postgres and Redis (your data is kept)
	$(COMPOSE) stop

services-status: ## Show whether Postgres and Redis are running
	$(COMPOSE) ps

logs: ## Follow Postgres and Redis logs (Ctrl+C to stop)
	$(COMPOSE) logs -f postgres redis

db-wait:
	@printf "Waiting for Postgres"; \
	for i in $$(seq 1 30); do \
	  if $(COMPOSE) exec -T postgres pg_isready -U $(PG_USER) -d $(PG_DB) >/dev/null 2>&1; then echo " ready."; exit 0; fi; \
	  printf "."; sleep 1; \
	done; echo " timed out. Check: make logs"; exit 1

##@ Run the app

dev: check-venv ## Run API, worker, and frontend together (Ctrl+C stops all three)
	@echo "API http://localhost:8000  |  Frontend http://localhost:3000  |  Ctrl+C to stop"
	@trap 'kill 0' INT TERM EXIT; \
	(cd $(BACKEND) && $(PY) -m uvicorn app.main:app --reload 2>&1 | sed -e 's/^/[api]    /') & \
	(cd $(BACKEND) && $(CELERY) -A app.worker.celery_app:celery_app worker -B --loglevel=INFO 2>&1 | sed -e 's/^/[worker] /') & \
	(cd $(FRONTEND) && npm run dev 2>&1 | sed -e 's/^/[web]    /') & \
	wait

backend: check-venv ## Run only the FastAPI server (http://localhost:8000, auto-reload)
	cd $(BACKEND) && $(PY) -m uvicorn app.main:app --reload

worker: check-venv ## Run only the Celery worker (with the nightly demo-reset scheduler)
	cd $(BACKEND) && $(CELERY) -A app.worker.celery_app:celery_app worker -B --loglevel=INFO

frontend: ## Run only the Next.js dev server (http://localhost:3000)
	cd $(FRONTEND) && npm run dev

stop: ## Stop the API, worker, and frontend if they are running in the background
	@for port in 8000 3000; do \
	  pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null); \
	  if [ -n "$$pids" ]; then kill $$pids && echo "Stopped process on port $$port"; fi; \
	done
	@pkill -f "celery -A app.worker.celery_app" 2>/dev/null && echo "Stopped Celery worker" || true

exit: stop services-down ## Shut down everything: app servers, Postgres, and Redis (data is kept)
	@echo "TalentFlow AI is stopped."

##@ Inspect and edit data

db-shell: ## Open an interactive Postgres shell (\dt lists tables, \q quits)
	$(PSQL)

db-tables: ## List all tables
	@$(PSQL) -c '\dt'

db-describe: ## Show the columns of a table: make db-describe TABLE=applications
	@$(PSQL) -c '\d "$(TABLE)"'

db-show: ## Show rows from a table: make db-show TABLE=candidates LIMIT=5
	@$(PSQL) -c 'SELECT * FROM "$(TABLE)" ORDER BY 1 DESC LIMIT $(LIMIT);'

db-count: ## Count the rows in every main table
	@$(PSQL) -c "SELECT 'companies' AS table_name, count(*) FROM companies UNION ALL SELECT 'recruiters', count(*) FROM recruiters UNION ALL SELECT 'jobs', count(*) FROM jobs UNION ALL SELECT 'candidates', count(*) FROM candidates UNION ALL SELECT 'applications', count(*) FROM applications UNION ALL SELECT 'ai_evaluations', count(*) FROM ai_evaluations;"

db-query: ## Run any SQL, including updates: make db-query SQL="UPDATE jobs SET status='OPEN' WHERE id=4"
	@test -n "$(SQL)" || { echo 'Usage: make db-query SQL="SELECT ..."'; exit 1; }
	@$(PSQL) -c "$(SQL)"

db-backup: ## Save the database to backups/<timestamp>.sql
	@mkdir -p backups
	@file=backups/talentflow-$$(date +%Y%m%d-%H%M%S).sql; \
	$(COMPOSE) exec -T postgres pg_dump -U $(PG_USER) -d $(PG_DB) > $$file && echo "Saved $$file"

db-restore: ## Restore a backup (replaces current data): make db-restore FILE=backups/x.sql
	@test -f "$(FILE)" || { echo "Usage: make db-restore FILE=backups/<file>.sql"; exit 1; }
	@read -p "This replaces ALL data in $(PG_DB). Type 'yes' to continue: " ok; [ "$$ok" = yes ] || exit 1
	$(PSQL) -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
	$(COMPOSE) exec -T postgres psql -U $(PG_USER) -d $(PG_DB) < $(FILE)

db-wipe: ## DELETE the Postgres and Redis data volumes and start empty (asks first)
	@read -p "This permanently deletes ALL database data. Type 'yes' to continue: " ok; [ "$$ok" = yes ] || exit 1
	$(COMPOSE) down -v
	@echo "Data deleted. Rebuild with: make services-up upgrade seed"

redis-cli: ## Open a Redis shell (e.g. KEYS talentflow:*)
	$(COMPOSE) exec redis redis-cli

##@ Migrations (Aerich)

migrate: check-venv ## Create a migration after changing models: make migrate NAME=add_job_location
	@test -n "$(NAME)" || { echo "Usage: make migrate NAME=describe_the_change"; exit 1; }
	cd $(BACKEND) && $(AERICH) migrate --name $(NAME)
	@echo "Review the new file in backend/migrations/models/, then run: make upgrade"

upgrade: check-venv ## Apply all pending migrations to the database
	cd $(BACKEND) && $(AERICH) upgrade

downgrade: check-venv ## Undo the most recent migration (asks first)
	cd $(BACKEND) && $(AERICH) downgrade

migration-history: check-venv ## List every migration file
	cd $(BACKEND) && $(AERICH) history

migration-heads: check-venv ## Show migrations not yet applied
	cd $(BACKEND) && $(AERICH) heads

##@ Demo data

seed: check-venv ## Create demo logins and sample data (safe to re-run)
	cd $(BACKEND) && $(PY) -m scripts.seed

reset-demo: check-venv ## Delete all applicants and reload fresh demo data (asks first)
	@read -p "This deletes all applicants and jobs. Type 'yes' to continue: " ok; [ "$$ok" = yes ] || exit 1
	cd $(BACKEND) && $(PY) -m scripts.reset_demo --yes

##@ Quality checks

test: test-backend test-frontend ## Run all tests

test-backend: check-venv ## Run backend tests
	cd $(BACKEND) && $(PY) -m unittest discover -s tests

test-frontend: ## Run frontend tests
	cd $(FRONTEND) && npm run test:public-application && npm run test:application-integration && npm run test:selection

lint: ## Lint the frontend
	cd $(FRONTEND) && npm run lint

typecheck: ## Typecheck the frontend
	cd $(FRONTEND) && npm run typecheck

build: ## Production build of the frontend
	cd $(FRONTEND) && npm run build
