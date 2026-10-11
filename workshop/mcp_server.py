"""The citizen-services tools as an MCP server (used by Lab 4).

MCP (Model Context Protocol) is a standard way to plug tools into any agent.
Labs 1-3 import the tools as Python functions. An agent you don't write yourself,
such as Hermes Agent, can't do that, so this server offers the same functions over
HTTP and Hermes discovers them on start.

    python -m workshop.mcp_server              # http://127.0.0.1:8765/mcp
    python -m workshop.mcp_server --list       # print the tools and exit

`make hermes` starts it for you. The server only listens inside the container.
"""

from __future__ import annotations

import argparse

from workshop.tools import ALL_TOOLS

# Everything a front-desk officer might need. Which of these an agent may actually
# call is decided by the agent's own config: see lab_4_hermes/config.yaml.
EXPOSED = [
    "list_schemes", "get_scheme_details", "search_knowledge_base", "check_eligibility", "calculator",
    "get_appointment_slots", "book_appointment", "check_application_status", "submit_application", "get_today",
]


def build_server(host: str = "127.0.0.1", port: int = 8765):
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "citizen-services",
        instructions="Tools of a fictional citizen-services agency: schemes, eligibility, appointments, applications.",
        host=host, port=port,
    )
    for name in EXPOSED:
        tool = ALL_TOOLS[name]
        server.add_tool(tool.func, name=tool.name, description=tool.description)
    return server


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--list", action="store_true", help="print the tools and exit")
    args = ap.parse_args()
    if args.list:
        for name in EXPOSED:
            print(f"{name:26} {ALL_TOOLS[name].description.splitlines()[0]}")
        return
    print(f"[citizen-services MCP] {len(EXPOSED)} tools on http://{args.host}:{args.port}/mcp", flush=True)
    build_server(args.host, args.port).run("streamable-http")


if __name__ == "__main__":
    main()
