# Part 1: Single Agent Hands-On (40 min)

**You will:** run a tool-using agent, read its graph, watch it select and call tools, then change its behaviour
by editing prompts, tools and roles.

| Time | Activity |
|---|---|
| 0–5 | Setup: `make up`, `make check` |
| 5–15 | Walkthrough: this page, run the agent, read `agent.py` |
| 15–35 | Exercises 1–3 |
| 35–40 | Share findings, bridge to Part 2 |

## 1. Run it

```bash
make single
```

Ask:

```
What schemes are available?
Am I eligible for the Senior Mobility Grant? I'm 67, citizen, household income $2,400 for 2 people.
Book the earliest mobility assessment for SMG.
```

Watch the console. Every step is traced:

```
▶ node reason                       ← the LLM decides (tool selection)
▶ node act
  🔧 tool selected check_eligibility  {"scheme": "Senior Mobility Grant", "age": 67, ...}   ← tool invocation
  ✓ result (190 ms) {"eligible": true, "per_capita_income": 1200.0, ...}
▶ node reason                       ← the LLM reads the result (result processing)
trace 3f2a…: 1.84s · 2 LLM calls · 1 tool calls · path: reason → act → reason
```

## 2. Read the code (in this order)

| File | What to look at |
|---|---|
| [`agent.py`](agent.py) | The whole agent: two nodes (`reason`, `act`), one conditional edge, a loop. About 40 lines of logic. |
| [`../workshop/tools.py`](../workshop/tools.py) | Tools are plain functions. The **name + docstring + typed arguments** are all the LLM sees. |
| [`prompts.py`](prompts.py) | System prompts and **roles** (prompt + allowed tools). |
| [`../workshop/memory.py`](../workshop/memory.py) | Short-term memory = checkpointer per `thread_id`; long-term = vector store. |

## 3. Architecture

```
            ┌───────── AgentState (messages) ─ saved by the checkpointer after every step ─────────┐
 user ──▶  reason (LLM core) ──tool calls?──▶ act (ToolNode) ──results──▶ reason ──no calls──▶ answer
            │  system prompt + tools bound                                   ▲
            └── safety valve: after 6 tool calls, answer without tools ──────┘
```

**Memory:**
- *Short-term:* ask "What was the first thing I asked you?", then `/new` and ask again. The new thread starts empty, so it can't say.
- *Long-term:* say "I'm 67 and I live with my wife", then `/new`, then "How old am I, and who do I live with?".
  The agent decides to call `remember_fact` on its own (its docstring says to save durable facts about the user),
  so the facts survive `/new`. They are stored as vectors, with PII redacted first.

## 4. Exercises

1. [Adjust prompts](exercises/01_adjust_prompts.md): same code, different behaviour.
2. [Swap tools](exercises/02_swap_tools.md): vector vs keyword search, write a tool, tool overload.
3. [Agent roles](exercises/03_agent_roles.md): specialists, and why a prompt alone is not a guardrail.

## Limitations to notice (Part 2 fixes them)

- **Complexity bottleneck:** one prompt has to cover every task.
- **Limited specialization:** 11 tools compete for attention.
- **Single point of failure:** a bad tool choice derails the whole answer.
- **Debugging:** everything happens in one loop, so "why did it do that?" is hard to answer.
- **No enforced policy:** nothing in code stops a submission before eligibility is checked.
