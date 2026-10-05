# Mission: Build and govern LangGraph agents in the STACK workshop

## Why
Participants at the "From Chatbots to Agents" workshop should leave able to build a tool-using agent, choose a multi-agent pattern for a real public-service problem, and put guardrails around it in code. They should go back to their own teams able to prototype an agent the same week.

## Success looks like
- Run the single agent, read its trace, and explain the reason → act → reason loop.
- Change an agent's behaviour three ways: its prompt, its tools and its role.
- For each of the five slide patterns, name when to use it and point to the LangGraph feature that makes it work.
- Trace one request through the Citizen Services Platform and say which guardrail fired and why.
- Add one new specialist agent to the platform without breaking the tests.

## Constraints
- Two 40-minute hands-on sessions (Lab 1 single agent, Lab 2 multi-agent), on the participant's own laptop.
- Participants are developers who can read Python. Most have not used LangGraph before.
- Everything runs in containers (Docker or Podman). Conference wifi may fail, so `MODEL=mock` must keep the mechanics working.
- LangGraph Studio needs a free LangSmith account and Chrome; the command line is always the fallback.

## Out of scope
- Deploying to a cloud (Exercise 4 in the repo is take-home).
- Fine-tuning or training models.
