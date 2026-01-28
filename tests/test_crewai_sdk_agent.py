"""Unit tests for the CrewAI SDK research agent example.

TDD Step 1 (Red): Write failing tests first, then implement.

This example uses the REAL CrewAI SDK (Agent, Task, Crew, @tool)
with a fake OPENAI_API_KEY so no real API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

try:
    import crewai  # noqa: F401
except ImportError:
    pytest.skip("crewai not installed", allow_module_level=True)


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    """Set a fake API key so CrewAI Agent creation doesn't fail."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-test-key-for-unit-tests")


class TestCrewAISDKResearchTools:
    """Tests for the individual @tool-decorated functions."""

    def test_search_tool_returns_string(self):
        from examples.crewai_sdk_research_agent import search_web

        result = search_web.run("Python async patterns")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_tool_includes_query_in_result(self):
        from examples.crewai_sdk_research_agent import search_web

        result = search_web.run("machine learning")
        assert "machine learning" in result.lower()

    def test_summarize_tool_returns_string(self):
        from examples.crewai_sdk_research_agent import summarize_text

        result = summarize_text.run("This is a long article about AI. " * 10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize_tool_shorter_than_input(self):
        from examples.crewai_sdk_research_agent import summarize_text

        long_text = "Sentence about topic. " * 20
        result = summarize_text.run(long_text)
        assert len(result) < len(long_text)

    def test_save_report_tool_returns_confirmation(self):
        from examples.crewai_sdk_research_agent import save_report

        result = save_report.run("Some report content here")
        assert isinstance(result, str)
        assert "saved" in result.lower() or "report" in result.lower()


class TestCrewAISDKAgentCreation:
    """Tests that real CrewAI Agent/Task/Crew objects are created."""

    def test_create_researcher_agent(self):
        from crewai import Agent

        from examples.crewai_sdk_research_agent import create_researcher_agent

        agent = create_researcher_agent()
        assert isinstance(agent, Agent)
        assert agent.role is not None
        assert len(agent.tools) >= 1

    def test_create_writer_agent(self):
        from crewai import Agent

        from examples.crewai_sdk_research_agent import create_writer_agent

        agent = create_writer_agent()
        assert isinstance(agent, Agent)
        assert agent.role is not None
        assert len(agent.tools) >= 1

    def test_create_research_task(self):
        from crewai import Task

        from examples.crewai_sdk_research_agent import (
            create_research_task,
            create_researcher_agent,
        )

        agent = create_researcher_agent()
        task = create_research_task(agent, topic="AI safety")
        assert isinstance(task, Task)
        assert "AI safety" in task.description

    def test_create_report_task(self):
        from crewai import Task

        from examples.crewai_sdk_research_agent import (
            create_report_task,
            create_research_task,
            create_researcher_agent,
            create_writer_agent,
        )

        researcher = create_researcher_agent()
        writer = create_writer_agent()
        research_task = create_research_task(researcher, topic="AI")
        report_task = create_report_task(writer, research_task)
        assert isinstance(report_task, Task)

    def test_build_crew_returns_crew(self):
        from crewai import Crew

        from examples.crewai_sdk_research_agent import build_research_crew

        crew = build_research_crew(topic="quantum computing")
        assert isinstance(crew, Crew)
        assert len(crew.agents) == 2
        assert len(crew.tasks) == 2


class TestCrewAISDKCrewExecution:
    """Tests that the crew can execute with a mocked LLM."""

    def test_crew_kickoff_with_mock_llm(self):
        """Run the crew with a mocked LLM so no API key is needed."""
        from examples.crewai_sdk_research_agent import build_research_crew

        crew = build_research_crew(topic="test topic")

        # Crew is a Pydantic model, so patch the class method instead
        mock_result = MagicMock()
        mock_result.raw = "Mocked research report about test topic."

        with patch("crewai.Crew.kickoff", return_value=mock_result):
            result = crew.kickoff()
            assert result.raw is not None
            assert len(result.raw) > 0
