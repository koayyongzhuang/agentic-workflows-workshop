# Agentic Workflows Resources

## Knowledge

- [Article: "Building Effective AI Agents" by Erik Schluntz & Barry Zhang (Anthropic, Dec 2024)](https://www.anthropic.com/engineering/building-effective-agents)
  The clearest primary source on workflows vs agents and the five workflow patterns. Use for: the "why" behind every pattern lesson. Note the naming differences from the slide (see reference/patterns.html).
- [Docs: "Workflows and agents" (LangGraph)](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
  The same patterns implemented in LangGraph: prompt chaining, parallelization, routing, orchestrator-worker, evaluator-optimizer, agents. Use for: code-level comparison with the repo.
- [Docs: "Graph API overview" (LangGraph)](https://docs.langchain.com/oss/python/langgraph/graph-api)
  Definitions of state, nodes, edges, reducers, Send, super-steps and MessagesState. Use for: glossary terms and any "how does LangGraph do X" question.
- [Docs: "Interrupts" (LangGraph)](https://docs.langchain.com/oss/python/langgraph/interrupts)
  `interrupt()` and `Command(resume=...)`, and why a checkpointer is required. Use for: the human approval step in Lab 2.
- [Docs: "Tools" (LangChain)](https://docs.langchain.com/oss/python/langchain/tools)
  How a function's name, docstring and type hints become what the model sees. Use for: Lab 1 Exercise B and C.
- [Docs: "LangSmith Studio" (LangChain)](https://docs.langchain.com/oss/python/langgraph/studio)
  Running graphs visually with `langgraph dev`. Use for: every "See it in Studio" section, and the Safari limitation.
- [Standard: "LLM01:2025 Prompt Injection" (OWASP GenAI Security Project)](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
  Definition and mitigations: least privilege, human approval, input/output filtering. Use for: the guardrails part of Lab 2.

## Wisdom (Communities)

- [LangChain Forum](https://forum.langchain.com/)
  Official forum, staffed by the LangGraph team. Use for: "is this a bug or my code?" questions after the workshop.
- Local: the workshop room itself
  Facilitators and the person next to you. Use for: comparing traces and answers between models.

## Gaps

- No single primary source covers guardrails for public-sector agents end to end; the lessons combine OWASP with the repo's own `workshop/guardrails/` code.
