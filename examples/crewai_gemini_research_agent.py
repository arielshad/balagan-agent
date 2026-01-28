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
import sys
from datetime import datetime
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


def get_gemini_llm(model: str = "gemini-3-flash-preview", temperature: float = 0.0):
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
    # Deterministic "search" — returns concise results for faster processing
    return f"Search results for '{query}': '{query}' is a widely researched topic with recent advances in improved algorithms."


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
        # Deterministic "search" — returns concise results for faster processing
        return f"Search results for '{query}': '{query}' is a widely researched topic with recent advances in improved algorithms."

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
        verbose=True,
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
        verbose=True,
    )


def create_research_task(agent: Agent, topic: str) -> Task:
    """Create the research task for the given topic."""
    return Task(
        description=f"Research '{topic}'. Call search_web ONCE, then summarize the results briefly in 2-3 sentences.",
        expected_output="A brief 2-3 sentence research summary.",
        agent=agent,
    )


def create_report_task(agent: Agent, research_task: Task) -> Task:
    """Create the report-writing task that depends on research."""
    return Task(
        description="Write a concise 1-paragraph report from the research. Call save_report with the final text.",
        expected_output="A concise 1-paragraph report.",
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
        verbose=True,
    )


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------


class TeeOutput:
    """Write to both file and console simultaneously."""

    def __init__(self, file_handle):
        self.file = file_handle
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def main():
    """Run the research crew with Gemini."""
    topic = sys.argv[1] if len(sys.argv) > 1 else "artificial intelligence"

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"crew_output_{timestamp}.log"

    print(f"\n🔍 Starting research on: {topic}")
    print(f"📝 Logging to: {log_filename}")
    print("=" * 60)

    try:
        # Open log file and redirect output to both console and file
        with open(log_filename, "w", encoding="utf-8") as log_file:
            # Write header to log file
            log_file.write("CrewAI Research Agent Log\n")
            log_file.write(f"Topic: {topic}\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
            log_file.write("=" * 60 + "\n\n")

            # Redirect stdout to both console and file
            original_stdout = sys.stdout
            sys.stdout = TeeOutput(log_file)

            try:
                crew = build_research_crew(topic=topic)
                result = crew.kickoff()

                print("\n✅ Research completed!")
                print("=" * 60)
                print("\nFinal Report:")
                print(result.raw)

            finally:
                # Restore original stdout
                sys.stdout = original_stdout

        print(f"\n✅ Log saved to: {log_filename}")

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
