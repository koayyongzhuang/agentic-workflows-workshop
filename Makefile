# Uses Docker if installed, otherwise Podman. Override with: make up COMPOSE="podman compose"
COMPOSE ?= $(shell command -v docker >/dev/null 2>&1 && echo "docker compose" || echo "podman compose")

# Inside docker (default): commands run in the `workshop` container.
# Locally without docker:   make single LOCAL=1
EXEC = $(if $(LOCAL),,$(COMPOSE) exec workshop)
PY = $(EXEC) python

.PHONY: up up-build down logs shell check ingest clean-db single multi patterns serve studio test traces clean

up:          ## start Postgres+pgvector, Mock Gov API and the workshop container (no rebuild)
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d
	@echo "Ready. Next: make check"

up-build:    ## rebuild the images first (after changing pyproject.toml or the Dockerfile), then start
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build
	@echo "Ready. Next: make check"

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

single:      ## Part 1: chat with the single agent
	$(PY) -m lab_1_single_agent.run $(ARGS)

multi:       ## Part 2: chat with the multi-agent platform
	$(PY) -m lab_2_multi_agent.citizen_platform.run $(ARGS)

patterns:    ## Part 2: run all design-pattern demos (or: make patterns P=pattern_3_parallel_fan_out_gather)
	$(PY) -m lab_2_multi_agent.patterns.run $(or $(P),all)

serve:       ## Part 2: serve the platform on http://localhost:8080/docs
	$(EXEC) uvicorn lab_2_multi_agent.citizen_platform.serve:app --host 0.0.0.0 --port 8080 --reload

studio:      ## LangGraph Studio (visual graph debugger) on port 2024
	$(EXEC) langgraph dev --host 0.0.0.0 --port 2024 --no-browser

test:        ## offline test suite (mock model)
	$(EXEC) env MODEL=mock EMBEDDING_MODEL=hash VERBOSE=false pytest

traces:      ## key metrics from traces/traces.jsonl
	$(PY) -m scripts.trace_report

clean:       ## stop everything and delete the database volume and traces
	rm -rf traces/*.jsonl .pytest_cache
	$(COMPOSE) down -v

clean-db:    ## empty the database (knowledge base, memories, conversations) and Studio's saved threads
	$(PY) -m scripts.clean_db