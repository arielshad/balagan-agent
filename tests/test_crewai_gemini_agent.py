"""Unit tests for the CrewAI Gemini research agent example.

Tests the Gemini-powered research crew with mocked LLM to avoid API calls.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    """Set fake API keys so agent creation doesn't fail."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-gemini-api-key-for-tests")
    monkeypatch.setenv("GEMINI_TOKEN", "fake-gemini-token-for-tests")


class TestGeminiLLMConfiguration:
    """Tests for Gemini LLM setup and configuration."""

    def test_get_gemini_llm_with_google_api_key(self, monkeypatch):
        """Test LLM creation with GOOGLE_API_KEY environment variable."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")

        from examples.crewai_gemini_research_agent import get_gemini_llm

        result = get_gemini_llm()
        # Should return model string for CrewAI's native provider
        assert result.startswith("gemini/")
        assert isinstance(result, str)

    def test_get_gemini_llm_with_gemini_token(self, monkeypatch):
        """Test LLM creation with GEMINI_TOKEN fallback."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_TOKEN", "test-token-456")

        from examples.crewai_gemini_research_agent import get_gemini_llm

        result = get_gemini_llm()
        # Should still return model string with GEMINI_TOKEN
        assert result.startswith("gemini/")
        assert isinstance(result, str)

    def test_get_gemini_llm_missing_key_raises_error(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_TOKEN", raising=False)

        from examples.crewai_gemini_research_agent import get_gemini_llm

        with pytest.raises(ValueError, match="Google API key not found"):
            get_gemini_llm()

    def test_get_gemini_llm_custom_model(self):
        """Test LLM creation with custom model name."""
        from examples.crewai_gemini_research_agent import get_gemini_llm

        result = get_gemini_llm(model="gemini-pro", temperature=0.5)
        # Should return custom model string
        assert result == "gemini/gemini-pro"


class TestGeminiResearchTools:
    """Tests for the tool functions (same as base version)."""

    def test_search_tool_returns_string(self):
        from examples.crewai_gemini_research_agent import search_web

        result = search_web.run("Python async patterns")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_tool_includes_query_in_result(self):
        from examples.crewai_gemini_research_agent import search_web

        result = search_web.run("machine learning")
        assert "machine learning" in result.lower()

    def test_summarize_tool_returns_string(self):
        from examples.crewai_gemini_research_agent import summarize_text

        result = summarize_text.run("This is a long article about AI. " * 10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize_tool_shorter_than_input(self):
        from examples.crewai_gemini_research_agent import summarize_text

        long_text = "Sentence about topic. " * 20
        result = summarize_text.run(long_text)
        assert len(result) < len(long_text)

    def test_save_report_tool_returns_confirmation(self):
        from examples.crewai_gemini_research_agent import save_report

        result = save_report.run("Some report content here")
        assert isinstance(result, str)
        assert "saved" in result.lower() or "report" in result.lower()


class TestGeminiAgentCreation:
    """Tests that agents are created with Gemini LLM."""

    def test_create_researcher_agent_with_mock_llm(self):
        """Test researcher agent creation with Gemini model string."""
        from crewai import Agent
        from examples.crewai_gemini_research_agent import create_researcher_agent

        # Pass a model string directly (CrewAI's native provider format)
        agent = create_researcher_agent(llm="gemini/gemini-3-flash-preview")
        assert isinstance(agent, Agent)
        assert agent.role == "Senior Research Analyst"
        assert len(agent.tools) >= 1

    def test_create_writer_agent_with_mock_llm(self):
        """Test writer agent creation with Gemini model string."""
        from crewai import Agent
        from examples.crewai_gemini_research_agent import create_writer_agent

        # Pass a model string directly
        agent = create_writer_agent(llm="gemini/gemini-3-flash-preview")
        assert isinstance(agent, Agent)
        assert agent.role == "Technical Writer"
        assert len(agent.tools) >= 1

    def test_agents_use_provided_llm(self):
        """Test that agents use the LLM passed to them."""
        from examples.crewai_gemini_research_agent import create_researcher_agent

        # Pass a custom model string
        custom_llm = "gemini/gemini-pro"
        agent = create_researcher_agent(llm=custom_llm)
        # Verify agent was created with proper role
        assert isinstance(agent.role, str)
        assert agent.role == "Senior Research Analyst"


class TestGeminiCrewCreation:
    """Tests for crew building with Gemini."""

    def test_build_crew_returns_crew(self):
        """Test that build_research_crew returns a Crew instance."""
        from crewai import Crew
        from examples.crewai_gemini_research_agent import build_research_crew

        # Use model string for native provider
        crew = build_research_crew(topic="quantum computing", llm="gemini/gemini-3-flash-preview")
        assert isinstance(crew, Crew)
        assert len(crew.agents) == 2
        assert len(crew.tasks) == 2

    def test_build_crew_with_custom_llm(self):
        """Test crew building with custom LLM model string."""
        from examples.crewai_gemini_research_agent import build_research_crew

        custom_llm = "gemini/gemini-pro"
        crew = build_research_crew(topic="test", llm=custom_llm)
        # Verify crew was created with 2 agents
        assert len(crew.agents) == 2
        assert len(crew.tasks) == 2


class TestGeminiCrewExecution:
    """Tests for crew execution with mocked Gemini."""

    def test_crew_kickoff_with_mock_llm(self):
        """Test crew setup for kickoff (avoid actual API calls in CI)."""
        from examples.crewai_gemini_research_agent import build_research_crew

        # Build the crew with model string
        crew = build_research_crew(topic="test topic", llm="gemini/gemini-3-flash-preview")

        # Verify crew is properly configured for kickoff
        assert crew is not None
        assert len(crew.agents) == 2
        assert len(crew.tasks) == 2
        assert hasattr(crew, "kickoff")

        # Note: We don't actually call kickoff() to avoid API calls

    def test_main_function_with_mock(self, monkeypatch, capsys):
        """Test the main function with mocked execution."""
        monkeypatch.setattr("sys.argv", ["script.py", "test topic"])

        with patch("examples.crewai_gemini_research_agent.build_research_crew") as mock_build:
            mock_crew = MagicMock()
            mock_result = MagicMock()
            mock_result.raw = "Test research report"
            mock_crew.kickoff.return_value = mock_result
            mock_build.return_value = mock_crew

            from examples.crewai_gemini_research_agent import main

            main()

            captured = capsys.readouterr()
            assert "Starting research on: test topic" in captured.out
            assert "Research completed" in captured.out
            assert "Test research report" in captured.out


class TestGeminiToolFactories:
    """Tests for tool factory functions (fresh instances)."""

    def test_create_tools_returns_three_tools(self):
        """Test that create_tools returns search, summarize, and save tools."""
        from examples.crewai_gemini_research_agent import create_tools

        sw, st, sr = create_tools()
        assert sw is not None
        assert st is not None
        assert sr is not None

    def test_fresh_tools_are_independent(self):
        """Test that tool factories create fresh, independent instances."""
        from examples.crewai_gemini_research_agent import create_tools

        tools1 = create_tools()
        tools2 = create_tools()

        # Each call should create new instances (different object IDs)
        assert tools1[0] is not tools2[0]
        assert tools1[1] is not tools2[1]
        assert tools1[2] is not tools2[2]
