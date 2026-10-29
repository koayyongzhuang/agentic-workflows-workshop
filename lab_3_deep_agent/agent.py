"""Lab 3: a Deep Agent, built with LangChain's `deepagents` harness.

In Labs 1 and 2 you wrote the agent loop yourself. Here one call,
`create_deep_agent(...)`, gives you a loop that already knows how to:

  * plan            -> `write_todos` keeps a to-do list in the state (one middleware line, below)
  * keep notes      -> `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
                       work on a file system (here: files kept in the thread's state)
  * delegate        -> the `task` tool starts a sub-agent with a fresh, empty context
  * ask first       -> `interrupt_on` pauses before the tools you name
  * load know-how   -> skills (SKILL.md files) are read only when the agent needs them
  * follow house rules -> memory files (AGENTS.md) go into every system prompt

You supply what is specific to your job: the tools, the prompts, the sub-agents.

The job here: a caseworker asks for one case file covering every scheme a household
might get. Too long for Lab 1's agent: it needs a plan, research per scheme, notes,
and a written file at the end.

    python -m lab_3_deep_agent.run           # chat (make deep)
    Studio graph: lab_3_deep_agent           # make studio
"""

from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain.agents.middleware import TodoListMiddleware

from lab_3_deep_agent import studio_answers  # noqa: F401  lets Studio's resume box take typed answers
from lab_3_deep_agent.studio_input import with_text_input
from workshop.llm import get_chat_model
from workshop.tools import ALL_TOOLS

AGENCY_DIR = Path(__file__).parent / "agency"   # AGENTS.md + skills/, read from disk
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"   # case files the agent writes, as real files

CASEWORKER_PROMPT = """You are a caseworker's assistant at a citizen-services agency.
You prepare case files: for one household, which schemes they can get, why, and what to do next.

How to work:
1. Start with write_todos: one item per scheme worth checking, plus "write case file".
2. For each scheme, delegate to the eligibility_researcher sub-agent with the task tool.
   Give it the scheme and every household fact it needs (ages, income, household size, residency).
3. Write the case file to /outputs/case_file.md. Before writing it, read the case-file-format skill.
4. Book or submit only when the caseworker asked for it. Never invent facts: if one is missing, ask."""

RESEARCHER_PROMPT = """You check ONE scheme for ONE household.
Use get_scheme_details for the rules and check_eligibility for the decision.
Show the per-capita income calculation. Reply in at most 6 lines:
scheme, eligible yes/no, the reason, the amount if eligible, documents needed, [source]."""

ELIGIBILITY_RESEARCHER = {
    "name": "eligibility_researcher",
    "description": "Checks one scheme for one household: rules, eligibility decision, amount and documents. "
                   "Give it the scheme name and all the household facts.",
    "system_prompt": RESEARCHER_PROMPT,
    "tools": [ALL_TOOLS[t] for t in ("get_scheme_details", "check_eligibility", "calculator", "search_knowledge_base")],
}

# The main agent's own tools. The researcher's tools are listed above.
MAIN_TOOLS = ["list_schemes", "get_scheme_details", "get_appointment_slots", "book_appointment",
              "submit_application", "check_application_status", "get_today"]

# Pause for a person before these tool calls run. (Exercise: is anything missing?)
INTERRUPT_ON = {"book_appointment": True}


def build_deep_agent(checkpointer=None):
    backend = CompositeBackend(
        default=StateBackend(),   # scratch notes live in the thread's state (visible in Studio)
        routes={
            "/agency/": FilesystemBackend(root_dir=AGENCY_DIR, virtual_mode=True),    # read the house rules
            "/outputs/": FilesystemBackend(root_dir=OUTPUTS_DIR, virtual_mode=True),  # outputs/ in the repo
        },
    )
    return create_deep_agent(
        model=get_chat_model(role="deep_agent"),
        tools=[ALL_TOOLS[t] for t in MAIN_TOOLS],
        system_prompt=CASEWORKER_PROMPT,
        subagents=[ELIGIBILITY_RESEARCHER],
        skills=["/agency/skills/"],
        memory=["/agency/AGENTS.md"],
        backend=backend,
        interrupt_on=INTERRUPT_ON,
        middleware=[TodoListMiddleware()],   # adds the write_todos planning tool
        checkpointer=checkpointer,
        name="lab_3_deep_agent",
    )


def make_graph():
    """Entry point for `langgraph dev` (Studio supplies the checkpointer).

    Wrapped so Studio shows one `message` text box instead of a message list (see studio_input.py).
    """
    return with_text_input(build_deep_agent())
