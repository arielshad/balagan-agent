"""Tests for CrewAI wrapper - TDD approach."""

from unittest.mock import MagicMock


class TestCrewAIWrapper:
    """Tests for CrewAI wrapper integration."""

    def test_wrapper_creation(self):
        """Test that wrapper can be created with mock CrewAI components."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        # Create mock crew
        mock_crew = MagicMock()
        mock_crew.agents = [MagicMock(name="agent1"), MagicMock(name="agent2")]
        mock_crew.tasks = [MagicMock(name="task1")]

        wrapper = CrewAIWrapper(mock_crew)
        assert wrapper is not None
        assert wrapper.crew is mock_crew

    def test_wrapper_with_chaos_level(self):
        """Test wrapper can be configured with chaos level."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.5)
        assert wrapper.chaos_level == 0.5

    def test_wrap_agent_tools(self):
        """Test that agent tools are properly wrapped."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        # Create mock agent with tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "search_tool"
        mock_tool1.func = MagicMock(return_value="search result")

        mock_tool2 = MagicMock()
        mock_tool2.name = "calc_tool"
        mock_tool2.func = MagicMock(return_value="42")

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool1, mock_tool2]
        mock_agent.role = "researcher"

        mock_crew = MagicMock()
        mock_crew.agents = [mock_agent]
        mock_crew.tasks = []

        wrapper = CrewAIWrapper(mock_crew)
        wrapped_tools = wrapper.get_wrapped_tools()

        assert "search_tool" in wrapped_tools
        assert "calc_tool" in wrapped_tools

    def test_kickoff_with_chaos(self):
        """Test that kickoff runs with chaos injection."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []
        mock_crew.kickoff = MagicMock(return_value="Crew output")

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.0)  # No chaos for predictable test
        result = wrapper.kickoff()

        assert result == "Crew output"
        mock_crew.kickoff.assert_called_once()

    def test_kickoff_with_inputs(self):
        """Test kickoff with input parameters."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []
        mock_crew.kickoff = MagicMock(return_value="Result with inputs")

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.0)
        wrapper.kickoff(inputs={"topic": "AI agents"})

        mock_crew.kickoff.assert_called_once_with(inputs={"topic": "AI agents"})

    def test_get_metrics(self):
        """Test that metrics are collected properly."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []
        mock_crew.kickoff = MagicMock(return_value="output")

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.0)
        wrapper.kickoff()

        metrics = wrapper.get_metrics()
        assert "kickoff_count" in metrics
        assert metrics["kickoff_count"] == 1

    def test_chaos_injection_on_tools(self):
        """Test that chaos can be injected into tool calls."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        mock_tool.func = MagicMock(return_value="result")

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool]
        mock_agent.role = "worker"

        mock_crew = MagicMock()
        mock_crew.agents = [mock_agent]
        mock_crew.tasks = []

        wrapper = CrewAIWrapper(mock_crew)

        # Add a custom injector
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["flaky_tool"])

        # The tool should now potentially fail
        tools = wrapper.get_wrapped_tools()
        assert "flaky_tool" in tools

    def test_reset_wrapper(self):
        """Test wrapper state reset."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []
        mock_crew.kickoff = MagicMock(return_value="output")

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.0)
        wrapper.kickoff()

        metrics_before = wrapper.get_metrics()
        assert metrics_before["kickoff_count"] == 1

        wrapper.reset()
        metrics_after = wrapper.get_metrics()
        assert metrics_after["kickoff_count"] == 0

    def test_experiment_context(self):
        """Test running crew within an experiment context."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []
        mock_crew.kickoff = MagicMock(return_value="output")

        wrapper = CrewAIWrapper(mock_crew, chaos_level=0.0)

        with wrapper.experiment("test-crew-experiment"):
            wrapper.kickoff()

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-crew-experiment"

    def test_multiple_agents_tools(self):
        """Test handling multiple agents with different tools."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        # Agent 1 tools
        tool1 = MagicMock()
        tool1.name = "agent1_search"
        tool1.func = MagicMock(return_value="search1")

        agent1 = MagicMock()
        agent1.tools = [tool1]
        agent1.role = "searcher"

        # Agent 2 tools
        tool2 = MagicMock()
        tool2.name = "agent2_write"
        tool2.func = MagicMock(return_value="written")

        agent2 = MagicMock()
        agent2.tools = [tool2]
        agent2.role = "writer"

        mock_crew = MagicMock()
        mock_crew.agents = [agent1, agent2]
        mock_crew.tasks = []

        wrapper = CrewAIWrapper(mock_crew)
        wrapped_tools = wrapper.get_wrapped_tools()

        assert "agent1_search" in wrapped_tools
        assert "agent2_write" in wrapped_tools

    def test_configure_chaos_all_options(self):
        """Test configuring chaos with all options."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        mock_crew = MagicMock()
        mock_crew.agents = []
        mock_crew.tasks = []

        wrapper = CrewAIWrapper(mock_crew)
        wrapper.configure_chaos(
            chaos_level=0.75,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        assert wrapper.chaos_level == 0.75


class TestCrewAIToolProxy:
    """Tests for individual tool proxying in CrewAI."""

    def test_tool_proxy_creation(self):
        """Test tool proxy is created correctly."""
        from balaganagent.wrappers.crewai import CrewAIToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = CrewAIToolProxy(mock_tool)
        assert proxy.tool_name == "test_tool"

    def test_tool_proxy_call(self):
        """Test tool proxy calls the underlying tool."""
        from balaganagent.wrappers.crewai import CrewAIToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="expected result")

        proxy = CrewAIToolProxy(mock_tool, chaos_level=0.0)
        result = proxy("arg1", kwarg1="value1")

        mock_tool.func.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "expected result"

    def test_tool_proxy_records_call_history(self):
        """Test tool proxy records call history."""
        from balaganagent.wrappers.crewai import CrewAIToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "tracked_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = CrewAIToolProxy(mock_tool, chaos_level=0.0)
        proxy("arg1")
        proxy("arg2")

        history = proxy.get_call_history()
        assert len(history) == 2
        assert history[0].args == ("arg1",)
        assert history[1].args == ("arg2",)

    def test_tool_proxy_retry_on_failure(self):
        """Test tool proxy retries on transient failures."""
        from balaganagent.wrappers.crewai import CrewAIToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        # Fail twice, then succeed
        mock_tool.func = MagicMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])

        proxy = CrewAIToolProxy(mock_tool, chaos_level=0.0, max_retries=3, retry_delay=0.01)
        result = proxy()

        assert result == "success"
        assert mock_tool.func.call_count == 3
