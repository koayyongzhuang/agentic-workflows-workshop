"""Helpers shared by the pattern demos."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from workshop.llm import get_chat_model
from workshop.observability import traced

console = Console()

ENQUIRY = (
    "Hi, my father is 72 and lives with me and my wife. Our household income is about $3,900 a month. "
    "He needs a wheelchair. What help can we get and what should we do next?"
)


def ask_llm(role: str, system: str, user: str, config: RunnableConfig | None = None) -> str:
    """One LLM call as a named 'agent'. Each role can use its own model via MODEL_<ROLE>."""
    llm = get_chat_model(role=role)
    return str(llm.invoke([SystemMessage(system), HumanMessage(user)], config).content)


def run_demo(name: str, graph, inputs: dict, output_key: str) -> dict:
    console.print(Panel.fit(f"[bold]Pattern: {name}[/]", border_style="magenta"))
    console.print(graph.get_graph().draw_ascii() if _has_grandalf() else graph.get_graph().draw_mermaid())
    with traced(f"pattern:{name}", str(inputs)[:200]) as (config, tracer):
        result = graph.invoke(inputs, config)
        tracer.outcome = str(result.get(output_key, ""))
    console.print(Panel(Markdown(str(result.get(output_key, ""))), title=f"{name}: {output_key}", border_style="green"))
    return result


def _has_grandalf() -> bool:
    try:
        import grandalf  # noqa: F401
        return True
    except ImportError:
        return False
