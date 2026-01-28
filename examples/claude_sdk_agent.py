"""Research agent built with the Claude Agent SDK.

This example defines a simple research agent that uses deterministic tools
(no LLM calls required), making the tools themselves fully testable without
an API key.

Tools:
  - search_web: simulated web search
  - summarize_text: deterministic text summarization
  - save_report: simulated persistence

The agent object exposes a ``tools`` dict and a ``run`` method, matching the
interface expected by :class:`balaganagent.wrappers.claude_sdk.ClaudeAgentSDKWrapper`.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Tool functions (deterministic, no LLM)
# ---------------------------------------------------------------------------


def search_web(query: str) -> str:
    """Return simulated search results for *query*."""
    return (
        f"Search results for '{query}':\n"
        f"1. '{query}' is a widely researched topic.\n"
        f"2. Recent advances in {query.lower()} include new techniques.\n"
        f"3. Experts recommend foundational reading on {query.lower()}.\n"
    )


def summarize_text(text: str) -> str:
    """Return the first three sentences of *text*."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return "No content to summarize."
    return " ".join(sentences[:3])


def save_report(content: str) -> str:
    """Persist *content* and return a confirmation."""
    word_count = len(content.split())
    return f"Report saved successfully ({word_count} words)."


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class ResearchAgent:
    """A minimal agent that follows the Claude Agent SDK tool convention.

    Attributes:
        name: human-readable agent name.
        tools: dict mapping tool names to callables.
    """

    def __init__(self, name: str = "research-agent"):
        self.name = name
        self.tools: dict[str, object] = {
            "search_web": search_web,
            "summarize_text": summarize_text,
            "save_report": save_report,
        }

    def run(self, prompt: str, **kwargs) -> str:  # type: ignore[override]
        """Execute the agent pipeline (deterministic demo version).

        In a real Claude Agent SDK agent, the LLM would decide which tools to
        call.  Here we hard-code a simple pipeline so the example is runnable
        without an API key.
        """
        # 1. Search
        search_result = self.tools["search_web"](prompt)  # type: ignore[operator]
        # 2. Summarize
        summary = self.tools["summarize_text"](search_result)  # type: ignore[operator]
        # 3. Save
        save_result = self.tools["save_report"](summary)  # type: ignore[operator]
        return f"Agent completed: {save_result}"


def build_research_agent(name: str = "research-agent") -> ResearchAgent:
    """Factory that returns a fresh ``ResearchAgent``."""
    return ResearchAgent(name=name)
