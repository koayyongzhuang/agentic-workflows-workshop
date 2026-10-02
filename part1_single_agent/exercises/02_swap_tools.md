# Exercise 2: Swap tools (about 15 minutes)

**Goal:** see how tool names, descriptions and the size of the tool list change what the agent does.

## A. Vector search vs keyword search

Open a Python shell in the repo (`python`, or `make shell` in docker):

```python
from langchain_core.messages import HumanMessage
from part1_single_agent.agent import build_single_agent
from part1_single_agent.extra_tools import keyword_faq_search
from workshop.tools import ALL_TOOLS

q = {"messages": [HumanMessage("Can I get help paying for a wheelchair for my mum?")]}

rag = build_single_agent(tools=[ALL_TOOLS["search_knowledge_base"]])
kw  = build_single_agent(tools=[keyword_faq_search])

print(rag.invoke(q)["messages"][-1].content)
print(kw.invoke(q)["messages"][-1].content)
```

Which one finds the Senior Mobility Grant? Why? (Hint: "mum" and "paying" are not in the documents.)

## B. Write a new tool

1. Implement `estimate_energy_rebate` in [`extra_tools.py`](../extra_tools.py) using the rebate table in
   `data/knowledge_base/household_energy_rebate.md`.
2. Add `"estimate_energy_rebate"` to the `helpdesk` role's tool list in `prompts.py`
   (tools in `extra_tools.py` are found by name automatically).
3. Ask: *"My household of 3 earns $4,200 a month. How much energy rebate would we get?"*
4. In the trace, confirm the agent called **your** tool with the right arguments.

## C. Tool overload

Add `get_weather` and a few other irrelevant tools to the list. Does the agent still pick the right tool?
Now rename `check_eligibility` to `tool_7` and change its docstring to "Runs a check."
What happens to tool selection?

## Takeaways

- The model only sees the **name, docstring and argument schema**. Those are the tool's interface.
- Fewer, sharper tools beat many vague ones. This is one reason to split work across several agents (Part 2).
