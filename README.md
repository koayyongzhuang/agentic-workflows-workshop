# From Chatbots to Agents: Hands-On Labs

Code for the two hands-on sessions of the workshop **"From Chatbots to Agents: Architecting Autonomous Workflows with Tool-Use and Reasoning"**.

| Session | Time | You will build |
|---|---|---|
| **Part 1: Single Agent Hands-On** | 50 min | A tool-using LangGraph agent for a (fictional) citizen-services helpdesk. Read its trace, change its prompt, tools and role, then add a new scheme. |
| **Part 2: Multi-Agent Hands-On** | 60 min | The five multi-agent design patterns as small runnable graphs, then a **Citizen Services Platform**: a supervisor coordinating **Retrieval**, **Validation** and **Action** agents over a Mock Gov Service, with RAG on PostgreSQL + pgvector, guardrails, human approval, tracing and tests. |
| **Part 3 (optional): Agent Harnesses** | about 40 min | The same agency on two ready-made harnesses: LangChain's **Deep Agents** (a library) and Nous Research's **Hermes Agent** (a product, connected over MCP). |

**Participants follow the step-by-step guides in [`guides/`](guides/index.html)** (open `guides/index.html` in a browser). Every lab runs in **LangGraph Studio**, with a terminal fallback for each step.

Stack: **Python · LangGraph · Deep Agents · Hermes Agent · MCP · PostgreSQL/pgvector · FastAPI · Docker/Podman**. Any LLM with tool calling works (OpenRouter, OpenAI, Anthropic, Azure OpenAI, Bedrock, Ollama…), and an **offline mock model** lets everything run with no API key.

> All schemes, policies and data in this repo are **fictional** and exist only for teaching.

---

## Quick start (docker, recommended)

```bash
git clone <this-repo> workshop-repo && cd workshop-repo
cp .env.example .env            # paste your Bifrost key into BIFROST_API_KEY (or set MODEL=mock)
make up                         # Postgres+pgvector, Mock Gov API, workshop container (builds on first run)
make check                      # every line should be green
make studio                     # LangGraph Studio: leave it running, then open the URL below in Chrome
```

Studio: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024` (needs a free LangSmith account). No Studio? `make single` (Part 1) and `make multi` (Part 2) run the same graphs in the terminal.

Needs Docker Desktop or Podman (with Compose), plus `make`.
- **macOS**: [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) or [Podman Desktop](https://podman-desktop.io/docs/installation/macos-install) (then *Settings → Resources → Compose → Setup*); `xcode-select --install` for `make`.
- **Windows 10/11**: [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) or [Podman Desktop](https://podman-desktop.io/docs/installation/windows-install) (then *Settings → Resources → Compose → Setup*); `winget install ezwinports.make` and `winget install Git.Git`, then run every command in PowerShell. Clone with Git (not a ZIP) so `.gitattributes` keeps Unix line endings.

Step-by-step setup for participants: `guides/index.html`, "Before you start".

This starts three containers:

| Service | What it is | Port |
|---|---|---|
| `db` | PostgreSQL 16 + pgvector: RAG vectors, agent checkpoints (memory), long-term memories | 5432 |
| `gov-api` | Mock Gov Service (FastAPI): schemes, eligibility, appointments, applications | 8000 (`/docs`) |
| `workshop` | Your Python environment, plus Hermes Agent. The repo is mounted, so edit on your laptop and run in the container | 8080 (`make serve`), 2024 (`make studio`), 9119 (`make hermes`, this laptop only) |

`make up` reuses the image it already built. After a change to `Dockerfile` or `pyproject.toml`, run `make up-build`.

## Quick start (no docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[openai,dev]"       # or [anthropic], [azure], [bedrock], [ollama]
cp .env.example .env
python -m scripts.check_setup
python -m lab_1_single_agent.run
```

Without `DATABASE_URL`, the vector store and memory are in-memory and the Mock Gov API runs in-process. Nothing else needs to be started.

## Choosing a model

Set `MODEL` in `.env` to `provider:model`:

```ini
MODEL=bifrost:bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0   # the default: our Bifrost gateway (BIFROST_URL, BIFROST_API_KEY)
MODEL=bedrock_converse:global.anthropic.claude-sonnet-4-6   # straight to Bedrock: AWS_BEARER_TOKEN_BEDROCK, AWS_REGION
MODEL=bedrock_converse:global.anthropic.claude-haiku-4-5-20251001-v1:0   # cheaper and faster
MODEL=openrouter:openai/gpt-6-luna       # OPENROUTER_API_KEY: one key, any model
MODEL=openai:gpt-4o-mini                 # OPENAI_API_KEY
MODEL=anthropic:claude-sonnet-4-5        # ANTHROPIC_API_KEY
MODEL=azure_openai:<deployment>          # AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION
MODEL=ollama:llama3.1                    # local, needs a tool-calling model
MODEL=mock                               # offline and deterministic (default)
```

**Bifrost** is an LLM gateway with an OpenAI-compatible API. After `bifrost:` comes Bifrost's own `provider/model` name; the code calls `BIFROST_URL` + `/v1`.

**Bedrock** authenticates with a Bedrock API key in `AWS_BEARER_TOKEN_BEDROCK` (boto3 1.39+ reads it), or with normal AWS credentials. Use the `global.` inference profile IDs: newer Claude models on Bedrock reject plain model IDs. The model must be enabled for your account in the region set by `AWS_REGION` (default `ap-southeast-1`).

With `gpt-6-luna` on OpenRouter or OpenAI, leave `TEMPERATURE=` **empty**: the model rejects a temperature setting. After editing `.env`, run `make up` so the container reloads it.

Per-agent overrides use the role name in capitals, e.g. `MODEL_SUPERVISOR=openai:gpt-4o-mini`, `MODEL_VALIDATION_AGENT=openai:gpt-4o`.
For semantic RAG, also set `EMBEDDING_MODEL=openai:text-embedding-3-small` and run `make ingest`.

**About mock mode:** the mock model picks tools by keyword overlap and fills arguments with regexes. It demonstrates the *mechanics* (graphs, tool calls, routing, guardrails, approval) reliably and powers the test suite, but it does not follow prompts. Use a real model for the prompt and role exercises.

---

## LangGraph Studio

`make studio` serves every graph in `langgraph.json`: `lab_1_single_agent`, `pattern_1_sequential_pipeline` to `pattern_5_generator_critic`, `lab_2_citizen_platform` and `lab_3_deep_agent`. It also creates one Lab 1 assistant per prompt and role (`scripts/studio_assistants.py`).

Code changes reload on their own; there is no need to restart `make studio`. File watching uses polling (`WATCHFILES_FORCE_POLLING`) because file events don't cross into Podman or Docker containers, and `scripts/studio_dev.py` limits the watch to the lab folders and `workshop/`.

## Part 1: Single Agent Hands-On

Guide: `guides/lessons/0001-lab-1-single-agent.html`

```bash
make single                                         # interactive chat
make single ARGS='--role eligibility_checker'       # a specialist role
make single ARGS='--show-graph'                     # Mermaid diagram of the graph
```

Walkthrough: [`lab_1_single_agent/README.md`](lab_1_single_agent/README.md)

| # | Exercise | Time |
|---|---|---|
| 1 | [Adjust prompts](lab_1_single_agent/exercises/01_adjust_prompts.md) | 10 min |
| 2 | [Swap tools](lab_1_single_agent/exercises/02_swap_tools.md) | 15 min |
| 3 | [Agent roles](lab_1_single_agent/exercises/03_agent_roles.md) | 10 min |

## Part 2: Multi-Agent Hands-On

Guides: `guides/lessons/0002-…` to `0006-…` (one per pattern), then `0007-lab-2-citizen-platform.html`.

```bash
make multi                                  # chat with the platform (you approve bookings)
make patterns                               # run all 5 pattern demos
make patterns P=pattern_4_parallel_fan_out_gather   # or just one
make serve                                  # HTTP API at http://localhost:8080/docs
make traces                                 # success rate, tools used, avg response time
```

Walkthrough: [`lab_2_multi_agent/README.md`](lab_2_multi_agent/README.md)

| # | Exercise (the "Your Multi-Agent Journey" slide) | Time |
|---|---|---|
| 1 | [Experiment with patterns](lab_2_multi_agent/exercises/01_experiment_with_patterns.md) | 10 min |
| 2 | [Add more agents](lab_2_multi_agent/exercises/02_add_more_agents.md) | 15 min |
| 3 | [Advanced guardrails](lab_2_multi_agent/exercises/03_advanced_guardrails.md) | 10 min |
| 4 | [Deploy to production](lab_2_multi_agent/exercises/04_deploy_to_production.md) | 10 min |

## Part 3 (optional): Agent Harnesses

The same agency on two ready-made harnesses. Guides: `guides/lessons/0008-lab-3-deep-agent.html` and `0009-lab-4-hermes-agent.html`.

```bash
make studio        # Lab 3: pick the lab_3_deep_agent graph (or: make deep)
make hermes        # Lab 4: Hermes Agent at http://localhost:9119 (login workshop / stack26)
```

| | Lab 3 · Deep Agents (LangChain) | Lab 4 · Hermes Agent (Nous Research) |
|---|---|---|
| Kind | a harness **library** you build on in Python | a harness **product** you run and configure |
| Code | `lab_3_deep_agent/agent.py` | `lab_4_hermes/config.yaml`, `workshop/mcp_server.py` |
| Job | write a household case file: plan, delegate per scheme, ask before booking | an officer's assistant (tools over MCP, memory, skills, cron), then a coding helper |

**Lab 3** writes its case file to `outputs/case_file.md` in the repo (a real file on your laptop; the folder is git-ignored). When it pauses before booking, type `yes` in Studio to approve, or any other text to reject with that text as the reason (`lab_3_deep_agent/studio_answers.py`).

**Lab 4** runs Hermes inside the workshop container, in its own venv (`/opt/hermes`), with Node.js 22 for the dashboard chat. Containers built before that need `make up-build` once.
- **Model:** `make hermes` fills in `lab_4_hermes/config.yaml` from `.env`. It uses Bifrost if `BIFROST_API_KEY` is set (a custom provider in `config.yaml`), then Bedrock (`AWS_BEARER_TOKEN_BEDROCK`), then OpenRouter (`OPENROUTER_API_KEY`), then OpenAI direct (`OPENAI_API_KEY`). Set `HERMES_PROVIDER` (`bifrost`, `bedrock`, `openrouter` or `openai`) and `HERMES_MODEL` to choose yourself. The terminal prints the model it picked.
- **Tools:** the citizen-services tools reach Hermes through the MCP server in `workshop/mcp_server.py`. The `include` list in `config.yaml` decides which ones it gets; `submit_application` is left out on purpose. Edit `config.yaml` in the repo, not in the dashboard, and restart `make hermes` after a change: Hermes reads it only at start.
- **State:** memory, skills and sessions live in the `hermes-home` volume, so they survive restarts. `make clean` deletes it.

---

## How the code maps to the slides

| Slide | Where in the code |
|---|---|
| Single Agent Architecture (LLM core, tools, memory, state) | `lab_1_single_agent/agent.py` (`reason` / `act` nodes, `AgentState`, checkpointer) |
| Tool Selection → Invocation → Result Processing | `reason` → `act` → `reason` loop; live in the console via `workshop/observability.py` |
| Multi-Agent Design Patterns | `lab_2_multi_agent/patterns/pattern_1_…` to `pattern_5_…` (same names as the Studio graphs) |
| Why LangGraph (explicit state, graph control flow) | every `build_graph()` / `build_platform()`; `make studio` to see them visually |
| Multi-Agent Orchestration: the "Build" | `lab_2_multi_agent/citizen_platform/graph.py` |
| RAG with PostgreSQL (Loading, Indexing, Storing, Querying) | `workshop/rag/ingest.py`, `workshop/rag/store.py` (`python -m workshop.rag.ingest -q "..."`) |
| Agent Reasoning & Observability (key metrics) | `workshop/observability.py`, `scripts/trace_report.py`, `/metrics` endpoint |
| Memory in AI Agents (short-term / long-term) | `workshop/memory.py` (checkpointer), `remember_fact` / `recall_facts` in `workshop/tools.py` |
| Guardrails (tool governance, PII, policy, with vs without) | `workshop/guardrails/`, `input_guard` / `output_guard` / `human_approval` nodes |
| Citizen Services Platform (Retrieval / Validation / Action) | `lab_2_multi_agent/citizen_platform/agents.py` |

## Repository map

```
.
├── docker-compose.yml, Dockerfile, Makefile, langgraph.json
├── .env.example                  the settings you fill in (copy to .env)
├── .env.backup                   extra settings: other providers, Bedrock direct, Lab 4 overrides, embeddings
├── guides/                       participant guides (index.html, lessons/, reference/, assets/)
├── data/knowledge_base/          fictional scheme policies (RAG source)
├── workshop/                     shared building blocks
│   ├── config.py, llm.py         settings; provider-agnostic model factory
│   ├── mock_llm.py               offline deterministic model
│   ├── tools.py                  citizen-services tools (the agents' "hands")
│   ├── mcp_server.py             the same tools as an MCP server (Lab 4)
│   ├── agents.py                 specialist runner with guardrail hooks
│   ├── memory.py                 checkpointers (in-memory / Postgres)
│   ├── observability.py          live tracing + traces.jsonl
│   ├── rag/                      embeddings, pgvector store, ingest pipeline
│   ├── guardrails/               PII, injection/toxicity, tool policy
│   └── gov_api/                  Mock Gov Service (FastAPI) + client
├── lab_1_single_agent/           agent.py, prompts.py, extra_tools.py, run.py, exercises/
├── lab_2_multi_agent/
│   ├── citizen_platform/         state, agents, graph, run (CLI), serve (HTTP)
│   ├── patterns/                 the 5 design patterns, pattern_1_… to pattern_5_…
│   └── exercises/
├── lab_3_deep_agent/             agent.py (create_deep_agent), run.py, studio_answers.py, agency/ (AGENTS.md, skills/)
├── lab_4_hermes/                 config.yaml, SOUL.md, start.sh (make hermes)
├── outputs/                      files the Lab 3 agent writes (git-ignored)
├── scripts/                      check_setup.py, trace_report.py, clean_db.py, studio_dev.py, studio_assistants.py
└── tests/                        offline test suite (mock model), also run against Postgres in CI
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `make check` fails on "LLM responds" | Key missing or wrong provider string. Check `.env`, then `make up` to reload it |
| Model rejects `temperature` | Leave `TEMPERATURE=` empty in `.env` (gpt-6-luna), then `make up` |
| "model did not call the tool" | Use a model that supports tool calling (most current OpenAI/Anthropic models do; for Ollama use e.g. `llama3.1`) |
| `Collection ... was embedded with 'hash' but EMBEDDING_MODEL is ...` | You changed embeddings: run `make ingest` |
| `No module named langchain_openai` | `pip install -e ".[openai]"` (docker installs OpenAI + Anthropic by default) |
| Old answers, memories or a stale knowledge base | `make clean-db` empties the database; the knowledge base reloads on the next search |
| Port 5432 already in use | Stop your local Postgres, or change the host port in `docker-compose.yml` |
| Conference wifi down | `MODEL=mock` keeps every demo and test working offline |
| Podman build stops with `unexpected EOF` | The Podman machine ran out of memory. Run `podman system prune -a`, build one image with `podman compose build workshop`, then `make up`; or give the machine more memory |
| Hermes: "Hermes isn't installed", "Node.js is missing" or "Chat unavailable" | The image is older than Lab 4: `make up-build` once |
| Hermes: chat says no provider is configured | Set `BIFROST_API_KEY` (or `AWS_BEARER_TOKEN_BEDROCK`, or `OPENROUTER_API_KEY` / `OPENAI_API_KEY`) in `.env`, `make up`, then `make hermes` |
| Bedrock: `AccessDeniedException` or "model identifier is invalid" | The key is wrong, or the model isn't enabled for your account in `AWS_REGION`. Check the key, or try the Haiku 4.5 profile |
| Bedrock: "on-demand throughput isn't supported" | Use the `global.` profile ID in `MODEL`, not the plain model ID |
| Studio: `BlockingError` | Code that runs per request made a blocking call (for example `os.mkdir`). Move it to import time or remove it |

## Facilitator notes

- Run `make up && make check` on the venue network **before** the session (`make up-build` after changing dependencies); pre-pull images (`docker compose pull && docker compose build`). Ask Podman users with a small machine to build before the day.
- Before the workshop, revert any exercise edits you tried locally (`git status` should be clean), so the guides' expected results match.
- Keep `MODEL=mock` as the fallback if keys or rate limits fail; the graphs, traces and guardrail demos still work.
- Budget: with `gpt-4o-mini`, a full Part 2 platform turn is about 5 LLM calls. `make traces` shows tokens per run.
- `make test` is the safety net after live-coding: the offline test suite runs in a few seconds with the mock model.
