"""Part 1: chat with the single agent.

    python -m lab_1_single_agent.run                         # interactive
    python -m lab_1_single_agent.run -q 'Am I eligible for SMG? Age 67, citizen, household income $2,400 for 2 people'
    python -m lab_1_single_agent.run --role eligibility_checker
    python -m lab_1_single_agent.run --prompt concise
    python -m lab_1_single_agent.run --show-graph
"""

from __future__ import annotations

import argparse

from langchain_core.messages import HumanMessage

from lab_1_single_agent.agent import build_single_agent
from lab_1_single_agent.prompts import PROMPTS, ROLES
from workshop.cli import banner, chat_loop, console, run_once, show_answer
from workshop.memory import get_checkpointer
from workshop.observability import traced

EXAMPLES = [
    "What schemes are available?",
    "Who is eligible for the Senior Mobility Grant and what documents do I need?",
    "Am I eligible for the Senior Mobility Grant? I'm 67, citizen, household income $2,400 for 2 people.",
    "Book the earliest mobility assessment for SMG.",
    "Remember that I live with my wife.  (then /new and ask: what do you remember about me?)",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="helpdesk", choices=sorted(ROLES))
    ap.add_argument("--prompt", choices=sorted(PROMPTS), help="override the role's system prompt")
    ap.add_argument("--model", help="override MODEL, e.g. openai:gpt-4o-mini")
    ap.add_argument("--user", default="demo-user", help="user id for long-term memory")
    ap.add_argument("-q", "--question", help="ask one question and exit")
    ap.add_argument("--show-graph", action="store_true", help="print the graph as Mermaid and exit")
    args = ap.parse_args()

    agent = build_single_agent(
        role=args.role,
        system_prompt=PROMPTS[args.prompt] if args.prompt else None,
        model=args.model,
        checkpointer=get_checkpointer(),
    )

    def show_graph() -> None:
        console.print(agent.get_graph().draw_mermaid())

    if args.show_graph:
        show_graph()
        return

    def ask(question: str, thread: str, resume: bool = False) -> None:
        with traced(f"part1:{args.role}", question) as (config, tracer):
            config["configurable"] = {"thread_id": thread, "user_id": args.user}
            # resume=True re-runs only the step that failed (the question is already saved)
            retrying = resume and agent.get_state(config).next
            result = agent.invoke(None if retrying else {"messages": [HumanMessage(question)]}, config)
            answer = result["messages"][-1].content
            tracer.outcome = answer
        show_answer(answer, title=f"{args.role} agent")

    if args.question:
        run_once(ask, args.question)
        return
    banner("Part 1 · Single Agent", f"role: {args.role}", EXAMPLES)
    chat_loop(ask, show_graph)


if __name__ == "__main__":
    main()
