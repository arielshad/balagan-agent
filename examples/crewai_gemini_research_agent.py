"""Research Report Agent — built with CrewAI SDK using Google Gemini 3.0 Flash.

This example uses crewai.Agent, crewai.Task, crewai.Crew with Google's Gemini
3.0 Flash model via LangChain integration. Environment variables are loaded
from a .env file.

Environment Setup:
  Create a .env file with:
    GOOGLE_API_KEY=your_gemini_api_key_here
  or
    GEMINI_TOKEN=your_gemini_api_key_here

Dependencies:
  - crewai>=0.28.0
  - langchain-google-genai
  - python-dotenv

Pipeline:
  1. Researcher agent — uses search_web and summarize_text tools
  2. Writer agent      — uses summarize_text and save_report tools
"""

from __future__ import annotations

import os
import re
import textwrap
from typing import Optional

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")


# ---------------------------------------------------------------------------
# LLM Configuration
# ---------------------------------------------------------------------------


def get_gemini_llm(model: str = "gemini-3-flash-preview", temperature: float = 0.7):
    """Configure and return a Gemini model string for CrewAI's native provider.

    Args:
        model: The Gemini model name (default: gemini-3-flash-preview)
        temperature: Sampling temperature (0.0 to 1.0)

    Returns:
        Model string that CrewAI's native Gemini provider can use.
        CrewAI will automatically read GOOGLE_API_KEY from environment.

    Raises:
        ValueError: If API key is not found in environment
    """
    # Support both GOOGLE_API_KEY and GEMINI_TOKEN environment variables
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_TOKEN")

    if not api_key:
        raise ValueError(
            "Google API key not found. Set GOOGLE_API_KEY or GEMINI_TOKEN in your .env file"
        )

    # Return model string for CrewAI's native Gemini provider
    # Format: "gemini/model-name"
    return f"gemini/{model}"


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


def create_researcher_agent(llm: Optional[object] = None) -> Agent:
    """Create the researcher agent with search and summarize tools.

    Args:
        llm: Optional LLM model string (e.g., "gemini/gemini-3-flash-preview").
             If None, uses Gemini 3 Flash from environment.
    """
    if llm is None:
        llm = get_gemini_llm()

    sw, st, _ = create_tools()
    return Agent(
        role="Senior Research Analyst",
        goal="Find comprehensive information on the given topic",
        backstory="You are an expert researcher who excels at finding and synthesizing information.",
        tools=[sw, st],
        llm=llm,
        verbose=False,
    )


def create_writer_agent(llm: Optional[object] = None) -> Agent:
    """Create the writer agent with summarize and save tools.

    Args:
        llm: Optional LLM model string (e.g., "gemini/gemini-3-flash-preview").
             If None, uses Gemini 3 Flash from environment.
    """
    if llm is None:
        llm = get_gemini_llm()

    _, st, sr = create_tools()
    return Agent(
        role="Technical Writer",
        goal="Write a clear, concise research report",
        backstory="You are a skilled technical writer who turns research into polished reports.",
        tools=[st, sr],
        llm=llm,
        verbose=False,
    )


def create_research_task(agent: Agent, topic: str) -> Task:
    """Create the research task for the given topic."""
    return Task(
        description=textwrap.dedent(
            f"""\
            Research the topic: {topic}
            Use the search_web tool to find information.
            Use the summarize_text tool to condense findings.
            Provide a detailed summary of your research."""
        ),
        expected_output="A detailed research summary with key findings.",
        agent=agent,
    )


def create_report_task(agent: Agent, research_task: Task) -> Task:
    """Create the report-writing task that depends on research."""
    return Task(
        description=textwrap.dedent(
            """\
            Using the research provided, write a polished report.
            Use the summarize_text tool if needed to tighten prose.
            Use the save_report tool to persist the final report."""
        ),
        expected_output="A well-structured research report.",
        agent=agent,
        context=[research_task],
    )


def build_research_crew(
    topic: str = "artificial intelligence", llm: Optional[object] = None
) -> Crew:
    """Build a two-agent research crew using CrewAI SDK with Gemini 3 Flash.

    Args:
        topic: The research topic for the crew to investigate
        llm: Optional LLM model string (e.g., "gemini/gemini-3-flash-preview").
             If None, uses Gemini 3 Flash from environment.

    Returns:
        Configured Crew ready to kickoff
    """
    if llm is None:
        llm = get_gemini_llm()

    researcher = create_researcher_agent(llm=llm)
    writer = create_writer_agent(llm=llm)

    research_task = create_research_task(researcher, topic)
    report_task = create_report_task(writer, research_task)

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, report_task],
        process=Process.sequential,
        verbose=False,
    )


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------


def main():
    """Run the research crew with Gemini."""
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "artificial intelligence"

    print(f"\n🔍 Starting research on: {topic}")
    print("=" * 60)

    try:
        crew = build_research_crew(topic=topic)
        result = crew.kickoff()

        print("\n✅ Research completed!")
        print("=" * 60)
        print("\nFinal Report:")
        print(result.raw)

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure your .env file contains:")
        print("  GOOGLE_API_KEY=your_api_key_here")
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Dependency error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
