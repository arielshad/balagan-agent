"""Research tools for Claude Agent SDK.

This module provides deterministic research tools that follow the Claude Agent SDK
convention. Tools are MCP-style callables that receive an ``args`` dict and return
a result dict with content blocks.

Tools available:
- search_web: Search for information on a topic
- summarize_text: Summarize text into concise version
- save_report: Save report to file

Usage:
    tools = get_research_tools(mode="mock")
    search = next(t["func"] for t in tools if t["name"] == "search_web")
    result = search({"query": "AI safety"})
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Tool Functions (MCP Convention)
# ---------------------------------------------------------------------------


def search_web(args: dict) -> dict:
    """Search the web for information on a topic.

    Args:
        args: Dict with "query" key containing search string

    Returns:
        MCP-style result dict with content blocks
    """
    query = args.get("query", "")
    text = (
        f"Search results for '{query}':\n"
        f"1. '{query}' is a widely researched and important topic.\n"
        f"2. Recent advances in {query.lower()} include novel approaches and methodologies.\n"
        f"3. Key experts recommend studying foundational research on {query.lower()}.\n"
        f"4. Current trends in {query.lower()} focus on practical applications.\n"
        f"5. Future research directions in {query.lower()} are promising."
    )
    return {
        "content": [{
            "type": "text",
            "text": text
        }]
    }


def summarize_text(args: dict) -> dict:
    """Summarize a piece of text into a concise version.

    Args:
        args: Dict with "text" key containing text to summarize

    Returns:
        MCP-style result dict with summarized content
    """
    text = args.get("text", "")

    # Split into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

    if not sentences:
        return {
            "content": [{
                "type": "text",
                "text": "No content to summarize."
            }]
        }

    # Keep first 3 sentences for summary
    summary = " ".join(sentences[:3])

    return {
        "content": [{
            "type": "text",
            "text": summary
        }]
    }


def save_report(args: dict) -> dict:
    """Save a report to persistent storage.

    Args:
        args: Dict with "content" (required) and optional "filename" keys

    Returns:
        MCP-style result dict with confirmation message
    """
    content = args.get("content", "")
    filename = args.get("filename", None)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_report_{timestamp}.md"

    # Create reports directory if needed
    report_dir = os.path.dirname(filename) if os.path.dirname(filename) else "."
    if report_dir and not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)

    # Write report
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        word_count = len(content.split())
        return {
            "content": [{
                "type": "text",
                "text": f"Report saved to {filename} ({word_count} words)."
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error saving report: {str(e)}"
            }],
            "is_error": True
        }


# ---------------------------------------------------------------------------
# Tool Factory Functions
# ---------------------------------------------------------------------------


def _make_search_web():
    """Factory to create fresh search_web tool instance."""
    def _search_web(args: dict) -> dict:
        return search_web(args)

    _search_web.__name__ = "search_web"
    _search_web.__doc__ = search_web.__doc__
    return _search_web


def _make_summarize_text():
    """Factory to create fresh summarize_text tool instance."""
    def _summarize_text(args: dict) -> dict:
        return summarize_text(args)

    _summarize_text.__name__ = "summarize_text"
    _summarize_text.__doc__ = summarize_text.__doc__
    return _summarize_text


def _make_save_report():
    """Factory to create fresh save_report tool instance."""
    def _save_report(args: dict) -> dict:
        return save_report(args)

    _save_report.__name__ = "save_report"
    _save_report.__doc__ = save_report.__doc__
    return _save_report


# ---------------------------------------------------------------------------
# Tool List Builders
# ---------------------------------------------------------------------------


def get_research_tools(mode: str = "mock") -> list[dict]:
    """Get research tools for a given mode.

    Args:
        mode: Tool mode - "mock" for deterministic testing,
              "production" for real SDK integration

    Returns:
        List of tool dicts with "name" and "func" keys
    """
    if mode == "mock":
        return [
            {
                "name": "search_web",
                "func": _make_search_web()
            },
            {
                "name": "summarize_text",
                "func": _make_summarize_text()
            },
            {
                "name": "save_report",
                "func": _make_save_report()
            }
        ]
    elif mode == "production":
        # In production mode, you would configure real tools
        # For now, return mock tools (actual SDK integration would happen here)
        return get_research_tools(mode="mock")
    else:
        raise ValueError(f"Unknown mode: {mode}")


def create_research_tools() -> list[dict]:
    """Create fresh research tools (backward compatible)."""
    return get_research_tools(mode="mock")
