"""Lab 3: chat with the Deep Agent in the terminal (the no-Studio way).

    python -m lab_3_deep_agent.run
    python -m lab_3_deep_agent.run -q 'Prepare a case file for ...'
    python -m lab_3_deep_agent.run --auto-approve -q '...'

After each answer it lists the agent's to-do list and the files it wrote.
"""

from __future__ import annotations

import argparse

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from rich.panel import Panel

from lab_3_deep_agent.agent import build_deep_agent
from workshop.cli import banner, chat_loop, console, run_once, show_answer
from workshop.memory import get_checkpointer
from workshop.observability import traced

EXAMPLES = [
    "Prepare a case file for a household: grandparents aged 68 and 72, two working adults earning "
    "$5,500 a month together, household of 4, all citizens. One adult wants to retrain. "
    "Check every scheme that could apply and book the earliest SMG assessment if they qualify.",
    "Show me /outputs/case_file.md",
]
STATUS = {"pending": "○", "in_progress": "◐", "completed": "●"}


def show_work(values: dict) -> None:
    todos = values.get("todos") or []
    if todos:
        console.print("[bold]to-do list[/]")
        for t in todos:
            console.print(f"  {STATUS.get(t.get('status'), '·')} {t.get('content')}")
    files = values.get("files") or {}
    if files:
        console.print("[bold]files[/] " + ", ".join(sorted(files)))


def decide(request: dict, auto_approve: bool) -> dict:
    """One approval decision for one paused tool call."""
    console.print(Panel(f"[bold]{request['name']}[/]\n{request['args']}",
                        title="⏸  approval required", border_style="yellow"))
    if auto_approve:
        return {"type": "approve"}
    answer = console.input("[yellow]Approve? (yes/no)[/] ").strip().lower()
    if answer in {"y", "yes"}:
        return {"type": "approve"}
    return {"type": "reject", "message": "The caseworker said no. Do not retry this action."}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--question", help="ask one question and exit")
    ap.add_argument("--auto-approve", action="store_true", help="approve paused tool calls automatically")
    ap.add_argument("--show-graph", action="store_true")
    args = ap.parse_args()

    agent = build_deep_agent(checkpointer=get_checkpointer())

    def show_graph() -> None:
        console.print(agent.get_graph().draw_mermaid())

    if args.show_graph:
        show_graph()
        return

    def ask(question: str, thread: str, resume: bool = False) -> None:
        with traced("lab3:deep_agent", question) as (config, tracer):
            config["configurable"] = {"thread_id": thread}
            config["recursion_limit"] = 100   # a deep agent takes many more steps than Lab 1's
            retrying = resume and agent.get_state(config).next
            result = agent.invoke(None if retrying else {"messages": [HumanMessage(question)]}, config)
            # interrupt_on: the agent pauses before the tools you listed and waits for decisions.
            while result.get("__interrupt__"):
                hitl = result["__interrupt__"][0].value
                decisions = [decide(r, args.auto_approve) for r in hitl["action_requests"]]
                result = agent.invoke(Command(resume={"decisions": decisions}), config)
            answer = result["messages"][-1].content
            tracer.outcome = str(answer)
        show_work(agent.get_state(config).values)
        show_answer(answer if isinstance(answer, str) else str(answer), title="deep agent")

    if args.question:
        run_once(ask, args.question)
        return
    banner("Lab 3 · Deep Agent", "a harness: plan → delegate → write files → ask before acting", EXAMPLES)
    chat_loop(ask, show_graph)


if __name__ == "__main__":
    main()
