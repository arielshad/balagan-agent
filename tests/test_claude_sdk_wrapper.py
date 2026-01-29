"""Tests for Claude Agent SDK wrapper — TDD approach.

The Claude Agent SDK uses ``query()`` / ``ClaudeSDKClient`` for the agentic
loop and ``@tool`` + ``create_sdk_mcp_server()`` for custom tools.
BalaganAgent wraps the **tool functions** before they are registered with the
SDK, so every invocation flows through the chaos engine.
"""

from unittest.mock import MagicMock

import pytest

from balaganagent.wrappers.claude_sdk import (
    ClaudeAgentSDKToolCall,
    ClaudeAgentSDKToolProxy,
    ClaudeAgentSDKWrapper,
)

# -----------------------------------------------------------------------
# ClaudeAgentSDKToolCall
# -----------------------------------------------------------------------


class TestClaudeAgentSDKToolCall:
    """Tests for the tool-call dataclass."""

    def test_duration_ms_with_times(self):
        call = ClaudeAgentSDKToolCall(
            tool_name="test", args=(), kwargs={}, start_time=1.0, end_time=2.0
        )
        assert call.duration_ms == 1000.0

    def test_duration_ms_no_end_time(self):
        call = ClaudeAgentSDKToolCall(tool_name="test", args=(), kwargs={}, start_time=1.0)
        assert call.duration_ms == 0.0

    def test_success_no_error(self):
        call = ClaudeAgentSDKToolCall(tool_name="test", args=(), kwargs={}, start_time=1.0)
        assert call.success is True

    def test_success_with_error(self):
        call = ClaudeAgentSDKToolCall(
            tool_name="test", args=(), kwargs={}, start_time=1.0, error="boom"
        )
        assert call.success is False


# -----------------------------------------------------------------------
# ClaudeAgentSDKToolProxy
# -----------------------------------------------------------------------


class TestClaudeAgentSDKToolProxy:
    """Tests for individual tool proxying."""

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
        # 100% failure → injector fires on every call and raises
        # a ToolFailureException.  A call record is still created.
        with pytest.raises(Exception):
            proxy()
        assert len(proxy.get_call_history()) == 1

    def test_proxy_preserves_func_metadata(self):
        def my_search(query: str) -> str:
            """Search the web."""
            return query

        proxy = ClaudeAgentSDKToolProxy(my_search, name="search")
        assert proxy.__name__ == "my_search"
        assert "Search" in proxy.__doc__


# -----------------------------------------------------------------------
# ClaudeAgentSDKWrapper — tool registration
# -----------------------------------------------------------------------


class TestClaudeAgentSDKWrapper:
    """Tests for the wrapper that sits between tool defs and the SDK."""

    def test_wrapper_creation_no_tools(self):
        wrapper = ClaudeAgentSDKWrapper()
        assert wrapper.chaos_level == 0.0
        assert wrapper.get_wrapped_tools() == {}

    def test_wrapper_with_callables(self):
        """Registering plain callables (like @tool-decorated functions)."""

        def search(args):
            return {"content": [{"type": "text", "text": "hi"}]}

        def save(args):
            return {"content": [{"type": "text", "text": "saved"}]}

        wrapper = ClaudeAgentSDKWrapper(tools=[search, save], chaos_level=0.5)
        tools = wrapper.get_wrapped_tools()
        assert "search" in tools
        assert "save" in tools
        assert wrapper.chaos_level == 0.5

    def test_wrapper_with_dict_tools(self):
        func = MagicMock(return_value="r")
        wrapper = ClaudeAgentSDKWrapper(tools=[{"name": "greet", "func": func}])
        assert "greet" in wrapper.get_wrapped_tools()

    def test_wrapper_with_object_tools(self):
        tool_obj = MagicMock()
        tool_obj.name = "fetch"
        tool_obj.func = MagicMock(return_value="data")

        wrapper = ClaudeAgentSDKWrapper(tools=[tool_obj])
        assert "fetch" in wrapper.get_wrapped_tools()

    def test_add_tool_after_construction(self):
        wrapper = ClaudeAgentSDKWrapper()

        def lookup(args):
            return args

        wrapper.add_tool(lookup, name="lookup")
        assert "lookup" in wrapper.get_wrapped_tools()

    def test_get_wrapped_tool_list(self):
        def a():
            pass

        def b():
            pass

        wrapper = ClaudeAgentSDKWrapper(tools=[a, b])
        lst = wrapper.get_wrapped_tool_list()
        assert len(lst) == 2
        assert all(isinstance(p, ClaudeAgentSDKToolProxy) for p in lst)

    def test_configure_chaos_all_options(self):
        def t():
            pass

        wrapper = ClaudeAgentSDKWrapper(tools=[t])
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

        def t1():
            pass

        def t2():
            pass

        wrapper = ClaudeAgentSDKWrapper(tools=[t1, t2])
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["t1"])

        tools = wrapper.get_wrapped_tools()
        assert len(tools["t1"]._injectors) == 1
        assert len(tools["t2"]._injectors) == 0

    def test_record_query_and_metrics(self):
        wrapper = ClaudeAgentSDKWrapper()
        wrapper.record_query()
        wrapper.record_query()
        metrics = wrapper.get_metrics()
        assert metrics["query_count"] == 2

    def test_reset(self):
        def t():
            pass

        wrapper = ClaudeAgentSDKWrapper(tools=[t])
        wrapper.record_query()
        assert wrapper.get_metrics()["query_count"] == 1
        wrapper.reset()
        assert wrapper.get_metrics()["query_count"] == 0

    def test_experiment_context(self):
        wrapper = ClaudeAgentSDKWrapper()
        with wrapper.experiment("test-experiment"):
            wrapper.record_query()

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-experiment"

    def test_get_mttr_stats(self):
        wrapper = ClaudeAgentSDKWrapper()
        stats = wrapper.get_mttr_stats()
        assert "tools" in stats
        assert "aggregate" in stats


# -----------------------------------------------------------------------
# Integration / chaos scenario tests
# -----------------------------------------------------------------------


class TestClaudeAgentSDKChaosExample:
    """Tests that demonstrate chaos-testing Claude Agent SDK tools with balagan."""

    def test_tool_under_failure_injection(self):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        def search_web(args):
            return {"content": [{"type": "text", "text": f"Results for {args['query']}"}]}

        def save_report(args):
            return {"content": [{"type": "text", "text": "Saved"}]}

        wrapper = ClaudeAgentSDKWrapper(
            tools=[
                {"name": "search_web", "func": search_web},
                {"name": "save_report", "func": save_report},
            ],
            chaos_level=1.0,
        )
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["search_web"])

        tools = wrapper.get_wrapped_tools()
        # search_web has 100% failure injection — always raises
        with pytest.raises(Exception):
            tools["search_web"]({"query": "AI"})

        # save_report has no injector — works normally
        result = tools["save_report"]({"content": "hello"})
        assert result["content"][0]["text"] == "Saved"

    def test_tool_resilience_metrics(self):
        func = MagicMock(return_value={"content": [{"type": "text", "text": "ok"}]})

        wrapper = ClaudeAgentSDKWrapper(
            tools=[{"name": "tool_a", "func": func}],
            chaos_level=0.0,
        )
        tools = wrapper.get_wrapped_tools()
        for _ in range(5):
            tools["tool_a"]()

        metrics = wrapper.get_metrics()
        assert "tools" in metrics
        assert "tool_a" in metrics["tools"]

    def test_full_chaos_experiment_workflow(self):
        """Simulate a full chaos experiment on SDK custom tools."""
        func = MagicMock(return_value={"content": [{"type": "text", "text": "ok"}]})

        wrapper = ClaudeAgentSDKWrapper(
            tools=[{"name": "my_tool", "func": func}],
            chaos_level=0.0,
        )
        wrapper.configure_chaos(
            chaos_level=0.5,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        with wrapper.experiment("chaos-test"):
            wrapper.record_query()
            tools = wrapper.get_wrapped_tools()
            try:
                tools["my_tool"]()
            except Exception:
                pass  # Tool may fail under chaos — that's expected

        results = wrapper.get_experiment_results()
        assert len(results) == 1
