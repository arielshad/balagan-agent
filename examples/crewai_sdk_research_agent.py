"""Research Report Agent — built with the REAL CrewAI SDK.

This example uses crewai.Agent, crewai.Task, crewai.Crew, and the @tool
decorator from crewai.tools.  All tool logic is deterministic (no LLM
calls), so the tools themselves can be tested without an API key.

Running the *crew* end-to-end requires an LLM (or a mock).  See the
tests for how to mock the LLM layer.

Pipeline:
  1. Researcher agent  — uses ``search_web`` and ``summarize_text`` tools
  2. Writer agent      — uses ``summarize_text`` and ``save_report`` tools
"""

from __future__ import annotations

import re
import textwrap

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

# ---------------------------------------------------------------------------
# Tools (deterministic, no LLM needed)
# ---------------------------------------------------------------------------


@tool("search_web")
def search_web(query: str) -> str:
    """Search the web for information on a topic.

    Returns simulated search results for the given query.
    """
    # Deterministic "search" — returns canned results keyed on the query.
    return (
        f"Search results for '{query}':\n"
        f"1. '{query}' is a widely researched topic in computer science.\n"
        f"2. Recent advances in {query.lower()} include improved algorithms.\n"
        f"3. Experts recommend starting with foundational papers on {query.lower()}.\n"
    )


@tool("summarize_text")
def summarize_text(text: str) -> str:
    """Summarize a long piece of text into a concise version.

    Extracts the first few sentences and compresses the input.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return "No content to summarize."
    # Keep at most 3 sentences
    kept = sentences[:3]
    return " ".join(kept)


@tool("save_report")
def save_report(content: str) -> str:
    """Save a report to persistent storage.

    Returns a confirmation message.
    """
    word_count = len(content.split())
    return f"Report saved successfully ({word_count} words)."


# ---------------------------------------------------------------------------
# Tool factories (fresh instances to avoid singleton mutation by chaos wrappers)
# ---------------------------------------------------------------------------


def _make_search_web():
    @tool("search_web")
    def _search_web(query: str) -> str:
        """Search the web for information on a topic.

        Returns simulated search results for the given query.
        """
        return (
            f"Search results for '{query}':\n"
            f"1. '{query}' is a widely researched topic in computer science.\n"
            f"2. Recent advances in {query.lower()} include improved algorithms.\n"
            f"3. Experts recommend starting with foundational papers on {query.lower()}.\n"
        )

    return _search_web


def _make_summarize_text():
    @tool("summarize_text")
    def _summarize_text(text: str) -> str:
        """Summarize a long piece of text into a concise version.

        Extracts the first few sentences and compresses the input.
        """
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if not sentences:
            return "No content to summarize."
        kept = sentences[:3]
        return " ".join(kept)

    return _summarize_text


def _make_save_report():
    @tool("save_report")
    def _save_report(content: str) -> str:
        """Save a report to persistent storage.

        Returns a confirmation message.
        """
        word_count = len(content.split())
        return f"Report saved successfully ({word_count} words)."

    return _save_report


def create_tools() -> tuple:
    """Create fresh tool instances (avoids singleton mutation by chaos wrappers)."""
    return _make_search_web(), _make_summarize_text(), _make_save_report()


# ---------------------------------------------------------------------------
# Agent & Task factories
# ---------------------------------------------------------------------------


def create_researcher_agent() -> Agent:
    """Create the researcher agent with search and summarize tools."""
    sw, st, _ = create_tools()
    return Agent(
        role="Senior Research Analyst",
        goal="Find comprehensive information on the given topic",
        backstory="You are an expert researcher who excels at finding and synthesizing information.",
        tools=[sw, st],
        verbose=False,
    )


def create_writer_agent() -> Agent:
    """Create the writer agent with summarize and save tools."""
    _, st, sr = create_tools()
    return Agent(
        role="Technical Writer",
        goal="Write a clear, concise research report",
        backstory="You are a skilled technical writer who turns research into polished reports.",
        tools=[st, sr],
        verbose=False,
    )


def create_research_task(agent: Agent, topic: str) -> Task:
    """Create the research task for the given topic."""
    return Task(
        description=textwrap.dedent(f"""\
            Research the topic: {topic}
            Use the search_web tool to find information.
            Use the summarize_text tool to condense findings.
            Provide a detailed summary of your research."""),
        expected_output="A detailed research summary with key findings.",
        agent=agent,
    )


def create_report_task(agent: Agent, research_task: Task) -> Task:
    """Create the report-writing task that depends on research."""
    return Task(
        description=textwrap.dedent("""\
            Using the research provided, write a polished report.
            Use the summarize_text tool if needed to tighten prose.
            Use the save_report tool to persist the final report."""),
        expected_output="A well-structured research report.",
        agent=agent,
        context=[research_task],
    )


def build_research_crew(topic: str = "artificial intelligence") -> Crew:
    """Build a two-agent research crew using the real CrewAI SDK."""
    researcher = create_researcher_agent()
    writer = create_writer_agent()

    research_task = create_research_task(researcher, topic)
    report_task = create_report_task(writer, research_task)

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, report_task],
        process=Process.sequential,
        verbose=False,
    )
