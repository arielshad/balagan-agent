"""Tests for Claude Agent SDK wrapper - TDD approach."""

from unittest.mock import MagicMock

import pytest

from balaganagent.wrappers.claude_sdk import (
    ClaudeAgentSDKToolCall,
    ClaudeAgentSDKToolProxy,
    ClaudeAgentSDKWrapper,
)


class TestClaudeAgentSDKToolCall:
    """Tests for the tool call dataclass."""

    def test_duration_ms_with_times(self):
        call = ClaudeAgentSDKToolCall(
            tool_name="test",
            args=(),
            kwargs={},
            start_time=1.0,
            end_time=2.0,
        )
        assert call.duration_ms == 1000.0

    def test_duration_ms_no_end_time(self):
        call = ClaudeAgentSDKToolCall(
            tool_name="test",
            args=(),
            kwargs={},
            start_time=1.0,
        )
        assert call.duration_ms == 0.0

    def test_success_no_error(self):
        call = ClaudeAgentSDKToolCall(tool_name="test", args=(), kwargs={}, start_time=1.0)
        assert call.success is True

    def test_success_with_error(self):
        call = ClaudeAgentSDKToolCall(
            tool_name="test", args=(), kwargs={}, start_time=1.0, error="boom"
        )
        assert call.success is False


class TestClaudeAgentSDKToolProxy:
    """Tests for individual tool proxying in Claude Agent SDK."""

    def test_proxy_creation(self):
        func = MagicMock(return_value="result")
        proxy = ClaudeAgentSDKToolProxy(func, name="my_tool")
        assert proxy.tool_name == "my_tool"

    def test_proxy_call(self):
        func = MagicMock(return_value="expected")
        proxy = ClaudeAgentSDKToolProxy(func, name="my_tool", chaos_level=0.0)
        result = proxy("arg1", key="val")
        func.assert_called_once_with("arg1", key="val")
        assert result == "expected"

    def test_proxy_records_call_history(self):
        func = MagicMock(return_value="result")
        proxy = ClaudeAgentSDKToolProxy(func, name="tracked", chaos_level=0.0)
        proxy("a")
        proxy("b")
        history = proxy.get_call_history()
        assert len(history) == 2
        assert history[0].args == ("a",)
        assert history[1].args == ("b",)

    def test_proxy_retry_on_failure(self):
        func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        proxy = ClaudeAgentSDKToolProxy(
            func, name="flaky", chaos_level=0.0, max_retries=3, retry_delay=0.01
        )
        result = proxy()
        assert result == "ok"
        assert func.call_count == 3

    def test_proxy_exhausts_retries(self):
        func = MagicMock(side_effect=Exception("always fails"))
        proxy = ClaudeAgentSDKToolProxy(
            func, name="broken", chaos_level=0.0, max_retries=2, retry_delay=0.01
        )
        with pytest.raises(Exception, match="always fails"):
            proxy()

    def test_proxy_get_metrics(self):
        func = MagicMock(return_value="ok")
        proxy = ClaudeAgentSDKToolProxy(func, name="t", chaos_level=0.0)
        proxy()
        metrics = proxy.get_metrics()
        assert "operations" in metrics

    def test_proxy_reset(self):
        func = MagicMock(return_value="ok")
        proxy = ClaudeAgentSDKToolProxy(func, name="t", chaos_level=0.0)
        proxy()
        assert len(proxy.get_call_history()) == 1
        proxy.reset()
        assert len(proxy.get_call_history()) == 0

    def test_add_remove_clear_injectors(self):
        func = MagicMock(return_value="ok")
        proxy = ClaudeAgentSDKToolProxy(func, name="t")
        mock_inj = MagicMock()
        proxy.add_injector(mock_inj)
        assert mock_inj in proxy._injectors
        proxy.remove_injector(mock_inj)
        assert mock_inj not in proxy._injectors
        proxy.add_injector(mock_inj)
        proxy.clear_injectors()
        assert len(proxy._injectors) == 0

    def test_proxy_with_injector_that_fires(self):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        func = MagicMock(return_value="ok")
        proxy = ClaudeAgentSDKToolProxy(func, name="t", chaos_level=1.0)
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        proxy.add_injector(injector)
        # With 100% failure, the injector should fire
        result = proxy()
        # The tool func should NOT have been called since injector returned first
        func.assert_not_called()
        # Result is whatever the injector returns (error dict)
        assert result is not None


class TestClaudeAgentSDKWrapper:
    """Tests for Claude Agent SDK wrapper integration."""

    def _make_mock_agent(self, tools=None):
        """Create a mock Claude Agent SDK agent."""
        agent = MagicMock()
        agent.tools = tools or []
        agent.name = "test-agent"
        return agent

    def test_wrapper_creation(self):
        agent = self._make_mock_agent()
        wrapper = ClaudeAgentSDKWrapper(agent)
        assert wrapper is not None
        assert wrapper.agent is agent

    def test_wrapper_with_chaos_level(self):
        agent = self._make_mock_agent()
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.7)
        assert wrapper.chaos_level == 0.7

    def test_wrap_tools_from_dict(self):
        """Test wrapping tools provided as a dict of name->callable."""
        tool1 = MagicMock(return_value="r1")
        tool1.__name__ = "search"
        tool2 = MagicMock(return_value="r2")
        tool2.__name__ = "calculate"

        agent = MagicMock()
        agent.tools = {"search": tool1, "calculate": tool2}
        agent.name = "agent"

        wrapper = ClaudeAgentSDKWrapper(agent)
        wrapped = wrapper.get_wrapped_tools()
        assert "search" in wrapped
        assert "calculate" in wrapped

    def test_wrap_tools_from_list(self):
        """Test wrapping tools provided as list of objects with name/func."""
        tool1 = MagicMock()
        tool1.name = "fetch"
        tool1.func = MagicMock(return_value="data")

        agent = MagicMock()
        agent.tools = [tool1]
        agent.name = "agent"

        wrapper = ClaudeAgentSDKWrapper(agent)
        wrapped = wrapper.get_wrapped_tools()
        assert "fetch" in wrapped

    def test_run_delegates_to_agent(self):
        agent = self._make_mock_agent()
        agent.run = MagicMock(return_value="agent output")
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)
        result = wrapper.run("do something")
        assert result == "agent output"
        agent.run.assert_called_once_with("do something")

    def test_run_with_kwargs(self):
        agent = self._make_mock_agent()
        agent.run = MagicMock(return_value="output")
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)
        wrapper.run("task", stream=True)
        agent.run.assert_called_once_with("task", stream=True)

    def test_get_metrics(self):
        agent = self._make_mock_agent()
        agent.run = MagicMock(return_value="out")
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)
        wrapper.run("x")
        metrics = wrapper.get_metrics()
        assert "run_count" in metrics
        assert metrics["run_count"] == 1

    def test_configure_chaos_all_options(self):
        agent = self._make_mock_agent()
        wrapper = ClaudeAgentSDKWrapper(agent)
        wrapper.configure_chaos(
            chaos_level=0.8,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )
        assert wrapper.chaos_level == 0.8

    def test_add_injector_to_specific_tools(self):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        tool1 = MagicMock()
        tool1.name = "t1"
        tool1.func = MagicMock(return_value="r1")

        tool2 = MagicMock()
        tool2.name = "t2"
        tool2.func = MagicMock(return_value="r2")

        agent = MagicMock()
        agent.tools = [tool1, tool2]
        agent.name = "agent"

        wrapper = ClaudeAgentSDKWrapper(agent)
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["t1"])

        tools = wrapper.get_wrapped_tools()
        assert len(tools["t1"]._injectors) == 1
        assert len(tools["t2"]._injectors) == 0

    def test_reset(self):
        agent = self._make_mock_agent()
        agent.run = MagicMock(return_value="out")
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)
        wrapper.run("x")
        assert wrapper.get_metrics()["run_count"] == 1
        wrapper.reset()
        assert wrapper.get_metrics()["run_count"] == 0

    def test_experiment_context(self):
        agent = self._make_mock_agent()
        agent.run = MagicMock(return_value="out")
        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)

        with wrapper.experiment("test-experiment"):
            wrapper.run("x")

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-experiment"

    def test_get_mttr_stats(self):
        agent = self._make_mock_agent()
        wrapper = ClaudeAgentSDKWrapper(agent)
        stats = wrapper.get_mttr_stats()
        assert "tools" in stats
        assert "aggregate" in stats


class TestClaudeAgentSDKChaosExample:
    """Tests that demonstrate chaos testing a Claude Agent SDK agent with balagan."""

    def test_agent_under_tool_failure_chaos(self):
        """Test that an agent's tools can be chaos-tested."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        # Simulate a Claude Agent SDK agent with tools
        def search(query: str) -> str:
            return f"Results for {query}"

        def save(content: str) -> str:
            return f"Saved: {content}"

        agent = MagicMock()
        agent.tools = {"search": search, "save": save}
        agent.name = "research-agent"
        agent.run = MagicMock(return_value="done")

        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=1.0)
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["search"])

        # Call the wrapped search tool directly
        tools = wrapper.get_wrapped_tools()
        result = tools["search"]("AI")
        # Injector fires, returns error result
        assert result is not None

        # save tool should work fine (no injector)
        result = tools["save"]("report")
        assert result == "Saved: report"

    def test_agent_resilience_metrics(self):
        """Test collecting resilience metrics from chaos experiment."""
        func = MagicMock(return_value="ok")

        agent = MagicMock()
        agent.tools = {"tool_a": func}
        agent.name = "metrics-agent"
        agent.run = MagicMock(return_value="done")

        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)

        # Run multiple tool calls
        tools = wrapper.get_wrapped_tools()
        for _ in range(5):
            tools["tool_a"]()

        metrics = wrapper.get_metrics()
        assert "tools" in metrics
        assert "tool_a" in metrics["tools"]

    def test_full_chaos_experiment_workflow(self):
        """Test a full chaos experiment workflow."""
        func = MagicMock(return_value="ok")

        agent = MagicMock()
        agent.tools = {"my_tool": func}
        agent.name = "workflow-agent"
        agent.run = MagicMock(return_value="done")

        wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)
        wrapper.configure_chaos(
            chaos_level=0.5,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        with wrapper.experiment("chaos-test"):
            wrapper.run("task")

        results = wrapper.get_experiment_results()
        assert len(results) == 1
