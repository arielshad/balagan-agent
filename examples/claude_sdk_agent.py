"""Example agent built with the Claude Agent SDK.

This example defines custom tools following the Claude Agent SDK convention
(``@tool`` decorator + ``create_sdk_mcp_server``), then shows how to wire
them into ``query()`` or ``ClaudeSDKClient``.

The tools here are **deterministic** — no LLM or API key required — so
they can be tested without any external dependencies.

Real SDK usage::

    from claude_agent_sdk import (
        tool, create_sdk_mcp_server, query, ClaudeAgentOptions
    )

    @tool("search_web", "Search the web", {"query": str})
    async def search_web(args):
        ...

    server = create_sdk_mcp_server(
        name="research-tools", version="1.0.0", tools=[search_web, summarize, save]
    )

    options = ClaudeAgentOptions(
        mcp_servers={"tools": server},
        allowed_tools=["mcp__tools__search_web", "mcp__tools__summarize", "mcp__tools__save"],
        permission_mode="acceptEdits",
    )

    async for msg in query(prompt="Research AI safety", options=options):
        ...
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Custom tool functions (Claude Agent SDK @tool convention)
#
# In the real SDK each tool receives an ``args`` dict and returns an
# MCP-style result dict:
#   {"content": [{"type": "text", "text": "..."}]}
# ---------------------------------------------------------------------------


def search_web(args: dict) -> dict:
    """Search the web for information on a topic."""
    query = args.get("query", "")
    text = (
        f"Search results for '{query}':\n"
        f"1. '{query}' is a widely researched topic.\n"
        f"2. Recent advances in {query.lower()} include new techniques.\n"
        f"3. Experts recommend foundational reading on {query.lower()}.\n"
    )
    return {"content": [{"type": "text", "text": text}]}


def summarize_text(args: dict) -> dict:
    """Summarize a piece of text into a concise version."""
    text = args.get("text", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return {"content": [{"type": "text", "text": "No content to summarize."}]}
    summary = " ".join(sentences[:3])
    return {"content": [{"type": "text", "text": summary}]}


def save_report(args: dict) -> dict:
    """Save a report to persistent storage."""
    content = args.get("content", "")
    word_count = len(content.split())
    return {"content": [{"type": "text", "text": f"Report saved ({word_count} words)."}]}


# ---------------------------------------------------------------------------
# Convenience list for use with BalaganAgent wrapper
# ---------------------------------------------------------------------------

TOOLS = [
    {"name": "search_web", "func": search_web},
    {"name": "summarize_text", "func": summarize_text},
    {"name": "save_report", "func": save_report},
]


def get_tool_list() -> list[dict]:
    """Return a fresh copy of the tool definitions."""
    return list(TOOLS)
