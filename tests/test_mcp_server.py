"""Lab 4: the MCP server offers the citizen-services tools."""

import asyncio

from workshop.mcp_server import EXPOSED, build_server


def test_mcp_server_lists_and_calls_tools():
    server = build_server()
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == set(EXPOSED)
    result = asyncio.run(server.call_tool("list_schemes", {}))
    text = str(result)
    assert "Senior Mobility Grant" in text
