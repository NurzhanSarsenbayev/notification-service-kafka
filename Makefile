SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml

API_URL ?= http://localhost:18100
MAILPIT_URL ?= http://localhost:18025
API_V1_PREFIX ?= /api/v1

# Services in docker-compose.yml (update if your service names differ)
API_SVC ?= notifications_api
WORKER_SVC ?= notifications_worker
SCHEDULER_SVC ?= campaign_scheduler
DB_SVC ?= postgres
KAFKA_SVC ?= kafka
MAILPIT_SVC ?= mailpit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- Compose lifecycle ---
up: ## Start the whole stack
	$(COMPOSE) up -d

up-build: ## Build images and start the stack
	$(COMPOSE) up -d --build

build: ## Build images
	$(COMPOSE) build

down: ## Stop the stack
	$(COMPOSE) down -v

reset: ## Stop the stack and remove volumes (DANGEROUS)
	$(COMPOSE) down -v

ps: ## Show containers
	$(COMPOSE) ps

logs: ## Tail all logs
	$(COMPOSE) logs -f --tail=200

logs-api: ## Tail API logs
	$(COMPOSE) logs -f --tail=200 $(API_SVC)

logs-worker: ## Tail Worker logs
	$(COMPOSE) logs -f --tail=200 $(WORKER_SVC)

logs-scheduler: ## Tail Scheduler logs
	$(COMPOSE) logs -f --tail=200 $(SCHEDULER_SVC)

# --- Quick links ---
docs: ## Print API docs URL
	@echo "$(API_URL)/docs"

mailpit: ## Print Mailpit URL
	@echo "$(MAILPIT_URL)"

# --- Shell / debug ---
sh-api: ## Shell into API container
	$(COMPOSE) exec $(API_SVC) bash

sh-worker: ## Shell into Worker container
	$(COMPOSE) exec $(WORKER_SVC) bash

sh-scheduler: ## Shell into Scheduler container
	$(COMPOSE) exec $(SCHEDULER_SVC) bash

psql: ## Open psql inside Postgres container
	$(COMPOSE) exec $(DB_SVC) psql -U $$POSTGRES_USER -d $$POSTGRES_DB

# --- Kafka (requires kafka CLI in the container image) ---
kafka-topics: ## List Kafka topics (if kafka image has CLI)
	$(COMPOSE) exec $(KAFKA_SVC) bash -lc 'kafka-topics.sh --bootstrap-server localhost:9092 --list'

# --- Quality gate (assumes these tools exist in your API image or locally) ---
lint: ## Run ruff check (local)
	ruff check .

fmt: ## Run ruff format (local)
	ruff format .

test: ## Run pytest (local)
	pytest -q

ci: lint test ## Run lint + tests

# --- Demo scenario (basic E2E) ---
demo: ## Run minimal E2E demo (template + user_registered event)
	@set -e; \
	API="$(API_URL)"; \
	MAIL="$(MAILPIT_URL)"; \
	EVENT_ID="$$(python -c "import uuid; print(uuid.uuid4())")"; \
	USER_ID="$$(python -c "import uuid; print(uuid.uuid4())")"; \
	echo "Creating template (welcome_email / en / email)..."; \
	curl -s -X POST "$$API/api/v1/templates" \
	  -H "Content-Type: application/json" \
	  -d '{"template_code":"welcome_email","locale":"en","channel":"email","subject":"Welcome!","body":"Registered via: {registration_channel}\nUser-Agent: {user_agent}"}' | cat; \
	echo ""; \
	echo "Publishing event user_registered..."; \
	curl -s -X POST "$$API/api/v1/events" \
	  -H "Content-Type: application/json" \
	  -d "$$(printf '%s' '{"event_id":"'"$$EVENT_ID"'","event_type":"user_registered","source":"demo","occurred_at":"2026-02-04T12:00:00Z","payload":{"user_id":"'"$$USER_ID"'","registration_channel":"web","locale":"en","user_agent":"make-demo"}}')" | cat; \
	echo ""; \
	echo "Expected recipient email (demo mode): user-$$USER_ID@example.com"; \
	echo "Now check Mailpit: $$MAIL"