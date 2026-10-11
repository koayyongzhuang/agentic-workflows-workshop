# Works in macOS/Linux Terminal and in Windows PowerShell (make from: winget install ezwinports.make).
# Uses Docker if installed, otherwise Podman. Override with: make up COMPOSE="podman compose"
ifeq ($(OS),Windows_NT)
  COMPOSE ?= $(if $(shell where docker 2>NUL),docker compose,podman compose)
  ENSURE_ENV = if not exist .env copy .env.example .env >NUL
else
  COMPOSE ?= $(shell command -v docker >/dev/null 2>&1 && echo "docker compose" || echo "podman compose")
  ENSURE_ENV = test -f .env || cp .env.example .env
endif

# Inside docker (default): commands run in the `workshop` container.
# Locally without docker:   make single LOCAL=1
EXEC = $(if $(LOCAL),,$(COMPOSE) exec workshop)
PY = $(EXEC) python

.PHONY: up up-build down logs shell check ingest restart-api clean-db single multi patterns serve studio deep hermes test traces clean

up:          ## start Postgres+pgvector, Mock Gov API and the workshop container (no rebuild)
	@$(ENSURE_ENV)
	$(COMPOSE) up -d
	@echo Ready. Next: make check

up-build:    ## rebuild the images first (after changing pyproject.toml or the Dockerfile), then start
	@$(ENSURE_ENV)
	$(COMPOSE) up -d --build
	@echo Ready. Next: make check

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

shell:       ## a shell inside the workshop container
	$(COMPOSE) exec workshop bash

check:       ## pre-flight: model, tool calling, API, RAG, memory
	$(PY) -m scripts.check_setup

ingest:      ## (re)build the RAG knowledge base
	$(PY) -m workshop.rag.ingest

restart-api: ## restart the Mock Gov API so it picks up edits to workshop/gov_api/data.py
	$(COMPOSE) restart gov-api

single:      ## Part 1: chat with the single agent
	$(PY) -m lab_1_single_agent.run $(ARGS)

multi:       ## Part 2: chat with the multi-agent platform
	$(PY) -m lab_2_multi_agent.citizen_platform.run $(ARGS)

patterns:    ## Part 2: run all design-pattern demos (or: make patterns P=pattern_3_parallel_fan_out_gather)
	$(PY) -m lab_2_multi_agent.patterns.run $(or $(P),all)

serve:       ## Part 2: serve the platform on http://localhost:8080/docs
	$(EXEC) uvicorn lab_2_multi_agent.citizen_platform.serve:app --host 0.0.0.0 --port 8080 --reload

studio:      ## LangGraph Studio on port 2024, with ready-made Lab 1 assistants (one per prompt and role)
	$(EXEC) bash -c "python -m scripts.studio_assistants --wait & exec langgraph dev --host 0.0.0.0 --port 2024 --no-browser"

deep:        ## Lab 3: chat with the Deep Agent in the terminal (the no-Studio way)
	$(PY) -m lab_3_deep_agent.run $(ARGS)

hermes:      ## Lab 4: Hermes Agent's web dashboard on http://localhost:9119 (login: workshop / stack26)
	$(COMPOSE) exec workshop bash /app/lab_4_hermes/start.sh

test:        ## offline test suite (mock model)
	$(EXEC) env MODEL=mock EMBEDDING_MODEL=hash VERBOSE=false pytest

traces:      ## key metrics from traces/traces.jsonl
	$(PY) -m scripts.trace_report

clean:       ## stop everything and delete the database volume and traces
	$(EXEC) bash -c "rm -rf traces/*.jsonl .pytest_cache"
	$(COMPOSE) down -v

clean-db:    ## empty the database (knowledge base, memories, conversations) and Studio's saved threads
	$(PY) -m scripts.clean_db