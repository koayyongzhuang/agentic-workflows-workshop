# From Chatbots to Agents: Hands-On Labs

Code for the two hands-on sessions of the workshop **"From Chatbots to Agents: Architecting Autonomous Workflows with Tool-Use and Reasoning"**.

| Session | Time | You will build |
|---|---|---|
| **Part 1: Single Agent Hands-On** | 40 min | A tool-using LangGraph agent for a (fictional) citizen-services helpdesk. Then adjust prompts, swap tools and design agent roles. |
| **Part 2: Multi-Agent Hands-On** | 40 min | A **Citizen Services Platform**: a supervisor coordinating **Retrieval**, **Validation** and **Action** agents over a Mock Gov Service, with RAG on PostgreSQL + pgvector, guardrails, human approval, tracing and tests. Plus runnable demos of the five multi-agent design patterns. |

Stack: **Python · LangGraph · PostgreSQL/pgvector · FastAPI · Docker**. Any LLM with tool calling works (OpenAI, Anthropic, Azure OpenAI, Bedrock, Ollama…), and an **offline mock model** lets everything run with no API key.

> All schemes, policies and data in this repo are **fictional** and exist only for teaching.

---

## Quick start (docker, recommended)

```bash
git clone <this-repo> workshop-repo && cd workshop-repo
cp .env.example .env            # set MODEL and your API key (or keep MODEL=mock)
docker compose up -d --build    # Postgres+pgvector, Mock Gov API, workshop container
make check                      # every line should be green
make single                     # Part 1
make multi                      # Part 2
```

This starts three containers:

| Service | What it is | Port |
|---|---|---|
| `db` | PostgreSQL 16 + pgvector: RAG vectors, agent checkpoints (memory), long-term memories | 5432 |
| `gov-api` | Mock Gov Service (FastAPI): schemes, eligibility, appointments, applications | 8000 (`/docs`) |
| `workshop` | Your Python environment. The repo is mounted, so edit on your laptop and run in the container | 8080, 2024 |

## Quick start (no docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[openai,dev]"       # or [anthropic], [azure], [bedrock], [ollama]
cp .env.example .env
python -m scripts.check_setup
python -m part1_single_agent.run
```

Without `DATABASE_URL`, the vector store and memory are in-memory and the Mock Gov API runs in-process. Nothing else needs to be started.

## Choosing a model

Set `MODEL` in `.env` to `provider:model`:

```ini
MODEL=openai:gpt-4o-mini                 # OPENAI_API_KEY
MODEL=anthropic:claude-sonnet-4-5        # ANTHROPIC_API_KEY
MODEL=azure_openai:<deployment>          # AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION
MODEL=ollama:llama3.1                    # local, needs a tool-calling model
MODEL=mock                               # offline and deterministic (default)
```

Per-agent overrides use the role name in capitals, e.g. `MODEL_SUPERVISOR=openai:gpt-4o-mini`, `MODEL_VALIDATION_AGENT=openai:gpt-4o`.
For semantic RAG, also set `EMBEDDING_MODEL=openai:text-embedding-3-small` and run `make ingest`.

**About mock mode:** the mock model picks tools by keyword overlap and fills arguments with regexes. It demonstrates the *mechanics* (graphs, tool calls, routing, guardrails, approval) reliably and powers the test suite, but it does not follow prompts. Use a real model for the prompt and role exercises.

---

## Part 1: Single Agent Hands-On

```bash
make single                                         # interactive chat
make single ARGS='--role eligibility_checker'       # a specialist role
make single ARGS='--show-graph'                     # Mermaid diagram of the graph
```

Walkthrough: [`part1_single_agent/README.md`](part1_single_agent/README.md)

| # | Exercise | Time |
|---|---|---|
| 1 | [Adjust prompts](part1_single_agent/exercises/01_adjust_prompts.md) | 10 min |
| 2 | [Swap tools](part1_single_agent/exercises/02_swap_tools.md) | 15 min |
| 3 | [Agent roles](part1_single_agent/exercises/03_agent_roles.md) | 10 min |

## Part 2: Multi-Agent Hands-On

```bash
make multi                                  # chat with the platform (you approve bookings)
make patterns                               # run all 6 pattern demos (or P=parallel)
make serve                                  # HTTP API at http://localhost:8080/docs
make traces                                 # success rate, tools used, avg response time
```

Walkthrough: [`part2_multi_agent/README.md`](part2_multi_agent/README.md)

| # | Exercise (the "Your Multi-Agent Journey" slide) | Time |
|---|---|---|
| 1 | [Experiment with patterns](part2_multi_agent/exercises/01_experiment_with_patterns.md) | 10 min |
| 2 | [Add more agents](part2_multi_agent/exercises/02_add_more_agents.md) | 15 min |
| 3 | [Advanced guardrails](part2_multi_agent/exercises/03_advanced_guardrails.md) | 10 min |
| 4 | [Deploy to production](part2_multi_agent/exercises/04_deploy_to_production.md) | 10 min |

---

## How the code maps to the slides

| Slide | Where in the code |
|---|---|
| Single Agent Architecture (LLM core, tools, memory, state) | `part1_single_agent/agent.py` (`reason` / `act` nodes, `AgentState`, checkpointer) |
| Tool Selection → Invocation → Result Processing | `reason` → `act` → `reason` loop; live in the console via `workshop/observability.py` |
| Multi-Agent Design Patterns | `part2_multi_agent/patterns/` (sequential, coordinator, parallel, hierarchical, generator_critic) |
| Why LangGraph (explicit state, graph control flow) | every `build_graph()` / `build_platform()`; `make studio` to see them visually |
| Multi-Agent Orchestration: the "Build" | `part2_multi_agent/citizen_platform/graph.py` |
| Orchestration in Action: Travel Booking | `part2_multi_agent/patterns/supervisor_travel.py` |
| RAG with PostgreSQL (Loading, Indexing, Storing, Querying) | `workshop/rag/ingest.py`, `workshop/rag/store.py` (`python -m workshop.rag.ingest -q "..."`) |
| Agent Reasoning & Observability (key metrics) | `workshop/observability.py`, `scripts/trace_report.py`, `/metrics` endpoint |
| Memory in AI Agents (short-term / long-term) | `workshop/memory.py` (checkpointer), `remember_fact` / `recall_facts` in `workshop/tools.py` |
| Guardrails (tool governance, PII, policy, with vs without) | `workshop/guardrails/`, `input_guard` / `output_guard` / `human_approval` nodes |
| Citizen Services Platform (Retrieval / Validation / Action) | `part2_multi_agent/citizen_platform/agents.py` |

## Repository map

```
.
├── docker-compose.yml, Dockerfile, Makefile, .env.example, langgraph.json
├── data/knowledge_base/          fictional scheme policies (RAG source)
├── workshop/                     shared building blocks
│   ├── config.py, llm.py         settings; provider-agnostic model factory
│   ├── mock_llm.py               offline deterministic model
│   ├── tools.py                  citizen-services tools (the agents' "hands")
│   ├── agents.py                 specialist runner with guardrail hooks
│   ├── memory.py                 checkpointers (in-memory / Postgres)
│   ├── observability.py          live tracing + traces.jsonl
│   ├── rag/                      embeddings, pgvector store, ingest pipeline
│   ├── guardrails/               PII, injection/toxicity, tool policy
│   └── gov_api/                  Mock Gov Service (FastAPI) + client
├── part1_single_agent/           agent.py, prompts.py, extra_tools.py, run.py, exercises/
├── part2_multi_agent/
│   ├── citizen_platform/         state, agents, graph, run (CLI), serve (HTTP)
│   ├── patterns/                 5 design patterns + travel supervisor
│   └── exercises/
├── scripts/                      check_setup.py, trace_report.py
└── tests/                        offline test suite (mock model), also run against Postgres in CI
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `make check` fails on "LLM responds" | Key missing or wrong provider string. Check `.env`, then `docker compose up -d` to reload env |
| "model did not call the tool" | Use a model that supports tool calling (most current OpenAI/Anthropic models do; for Ollama use e.g. `llama3.1`) |
| `Collection ... was embedded with 'hash' but EMBEDDING_MODEL is ...` | You changed embeddings: run `make ingest` |
| `No module named langchain_openai` | `pip install -e ".[openai]"` (docker installs OpenAI + Anthropic by default) |
| Port 5432 already in use | Stop your local Postgres, or change the host port in `docker-compose.yml` |
| Conference wifi down | `MODEL=mock` keeps every demo and test working offline |

## Facilitator notes

- Run `make up && make check` on the venue network **before** the session; pre-pull images (`docker compose pull && docker compose build`).
- Keep `MODEL=mock` as the fallback if keys or rate limits fail; the graphs, traces and guardrail demos still work.
- Budget: with `gpt-4o-mini`, a full Part 2 platform turn is about 5 LLM calls. `make traces` shows tokens per run.
- `make test` is the safety net after live-coding: 42 offline tests in about 2 seconds.
