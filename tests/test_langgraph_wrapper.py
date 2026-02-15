"""Tests for LangGraph wrapper - TDD approach.

These tests use mocks to avoid requiring actual LangGraph/LangChain installations.
Following project style: comprehensive TDD with 100% pass rate target.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestLangGraphWrapper:
    """Tests for LangGraph compiled graph wrapper."""

    def test_wrapper_creation(self):
        """Test that wrapper can be created with mock compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)
        assert wrapper is not None
        assert wrapper.compiled_graph is mock_graph

    def test_wrapper_with_chaos_level(self):
        """Test wrapper can be configured with chaos level."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.5)
        assert wrapper.chaos_level == 0.5

    def test_wrap_tools_from_tool_node(self):
        """Test that tools are discovered from ToolNode instances in graph.nodes."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        # Create mock tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "search_tool"
        mock_tool1.func = MagicMock(return_value="search result")

        mock_tool2 = MagicMock()
        mock_tool2.name = "calculator"
        mock_tool2.func = MagicMock(return_value="42")

        # Create mock ToolNode
        mock_tool_node = MagicMock()
        mock_tool_node.tools = [mock_tool1, mock_tool2]
        mock_tool_node.tools_by_name = None  # Avoid double-discovery

        mock_graph = MagicMock()
        mock_graph.nodes = {"tools": mock_tool_node}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        wrapped_tools = wrapper.get_wrapped_tools()

        assert "search_tool" in wrapped_tools
        assert "calculator" in wrapped_tools

    def test_wrap_tools_explicit(self):
        """Test that explicitly passed tools are wrapped."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_tool = MagicMock()
        mock_tool.name = "explicit_tool"
        mock_tool.func = MagicMock(return_value="result")

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph, tools=[mock_tool])
        wrapped_tools = wrapper.get_wrapped_tools()

        assert "explicit_tool" in wrapped_tools

    def test_wrap_tools_deduplication(self):
        """Test that duplicate tools are not wrapped twice."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_tool = MagicMock()
        mock_tool.name = "shared_tool"
        mock_tool.func = MagicMock(return_value="result")

        mock_tool_node = MagicMock()
        mock_tool_node.tools = [mock_tool]
        mock_tool_node.tools_by_name = None

        mock_graph = MagicMock()
        mock_graph.nodes = {"tools": mock_tool_node}
        mock_graph.tools = None

        # Pass the same tool explicitly AND let it be discovered from node
        wrapper = LangGraphWrapper(mock_graph, tools=[mock_tool])
        wrapped_tools = wrapper.get_wrapped_tools()

        assert len(wrapped_tools) == 1
        assert "shared_tool" in wrapped_tools

    def test_invoke(self):
        """Test that invoke runs through to the compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"messages": ["response"]})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        result = wrapper.invoke({"messages": ["Hello"]})

        assert result == {"messages": ["response"]}
        mock_graph.invoke.assert_called_once()

    def test_invoke_with_config(self):
        """Test invoke with additional config."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"output": "done"})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        wrapper.invoke({"input": "test"}, config={"thread_id": "abc"})

        mock_graph.invoke.assert_called_once()

    def test_stream_method(self):
        """Test streaming responses through wrapper."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.stream = MagicMock(
            return_value=iter([{"agent": {"messages": ["hi"]}}, {"tools": {"messages": ["done"]}}])
        )

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        chunks = list(wrapper.stream({"messages": ["Hello"]}))

        assert len(chunks) == 2

    def test_batch_invoke(self):
        """Test batch invocation of multiple inputs."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.batch = MagicMock(return_value=[{"o": "1"}, {"o": "2"}])

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        results = wrapper.batch([{"i": "q1"}, {"i": "q2"}])

        assert len(results) == 2
        mock_graph.batch.assert_called_once()

    def test_get_metrics(self):
        """Test that metrics are collected properly."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"output": "done"})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        wrapper.invoke({"input": "test"})

        metrics = wrapper.get_metrics()
        assert "invoke_count" in metrics
        assert metrics["invoke_count"] == 1
        assert "tools" in metrics
        assert "nodes" in metrics

    def test_chaos_injection_on_tools(self):
        """Test that chaos injectors can be added to tools."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        mock_tool.func = MagicMock(return_value="result")

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph, tools=[mock_tool])

        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["flaky_tool"])

        tools = wrapper.get_wrapped_tools()
        assert "flaky_tool" in tools

    def test_reset_wrapper(self):
        """Test wrapper state reset."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"output": "done"})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        wrapper.invoke({"input": "test"})

        metrics_before = wrapper.get_metrics()
        assert metrics_before["invoke_count"] == 1

        wrapper.reset()
        metrics_after = wrapper.get_metrics()
        assert metrics_after["invoke_count"] == 0

    def test_experiment_context(self):
        """Test running graph within an experiment context."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"output": "done"})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)

        with wrapper.experiment("test-langgraph-experiment"):
            wrapper.invoke({"input": "test"})

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-langgraph-experiment"

    def test_configure_chaos_all_options(self):
        """Test configuring chaos with all options."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        wrapper.configure_chaos(
            chaos_level=0.75,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        assert wrapper.chaos_level == 0.75

    def test_get_state_passthrough(self):
        """Test get_state passes through to compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.get_state = MagicMock(return_value={"messages": [], "step": 0})

        wrapper = LangGraphWrapper(mock_graph)
        state = wrapper.get_state({"thread_id": "123"})

        assert state == {"messages": [], "step": 0}
        mock_graph.get_state.assert_called_once()

    def test_update_state_passthrough(self):
        """Test update_state passes through to compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.update_state = MagicMock(return_value={"step": 1})

        wrapper = LangGraphWrapper(mock_graph)
        result = wrapper.update_state({"thread_id": "123"}, {"step": 1})

        assert result == {"step": 1}
        mock_graph.update_state.assert_called_once()

    def test_get_mttr_stats(self):
        """Test MTTR stats collection."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        stats = wrapper.get_mttr_stats()

        assert "tools" in stats
        assert "aggregate" in stats


class TestLangGraphToolProxy:
    """Tests for individual tool proxying in LangGraph."""

    def test_tool_proxy_creation(self):
        """Test tool proxy is created correctly."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangGraphToolProxy(mock_tool)
        assert proxy.tool_name == "test_tool"

    def test_tool_proxy_call(self):
        """Test tool proxy calls the underlying tool."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="expected result")

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0)
        result = proxy("arg1", kwarg1="value1")

        mock_tool.func.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "expected result"

    def test_tool_proxy_records_call_history(self):
        """Test tool proxy records call history."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "tracked_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0)
        proxy("arg1")
        proxy("arg2")

        history = proxy.get_call_history()
        assert len(history) == 2
        assert history[0].args == ("arg1",)
        assert history[1].args == ("arg2",)

    def test_tool_proxy_retry_on_failure(self):
        """Test tool proxy retries on transient failures."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        mock_tool.func = MagicMock(
            side_effect=[Exception("fail1"), Exception("fail2"), "success"]
        )

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0, max_retries=3, retry_delay=0.01)
        result = proxy()

        assert result == "success"
        assert mock_tool.func.call_count == 3

    def test_tool_proxy_exhausts_retries(self):
        """Test tool proxy raises after exhausting retries."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "broken_tool"
        mock_tool.func = MagicMock(side_effect=Exception("always fails"))

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0, max_retries=2, retry_delay=0.01)

        with pytest.raises(Exception, match="always fails"):
            proxy()

    def test_tool_proxy_metrics(self):
        """Test tool proxy collects metrics."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "metric_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0)
        proxy("test")

        metrics = proxy.get_metrics()
        assert metrics is not None

    def test_tool_proxy_reset(self):
        """Test tool proxy reset clears state."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "reset_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangGraphToolProxy(mock_tool, chaos_level=0.0)
        proxy("test")
        assert len(proxy.get_call_history()) == 1

        proxy.reset()
        assert len(proxy.get_call_history()) == 0


class TestLangGraphNodeProxy:
    """Tests for LangGraph node proxying."""

    def test_node_proxy_creation(self):
        """Test node proxy is created correctly."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def my_node(state):
            return state

        proxy = LangGraphNodeProxy(my_node, node_name="my_node")
        assert proxy.node_name == "my_node"

    def test_node_proxy_call_success(self):
        """Test node proxy calls the underlying function."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def my_node(state):
            return {"messages": state.get("messages", []) + ["processed"]}

        proxy = LangGraphNodeProxy(my_node, node_name="my_node")
        result = proxy({"messages": ["hello"]})

        assert result == {"messages": ["hello", "processed"]}

    def test_node_proxy_records_event_history(self):
        """Test node proxy records execution events."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def my_node(state):
            return state

        proxy = LangGraphNodeProxy(my_node, node_name="my_node")
        proxy({"step": 1})
        proxy({"step": 2})

        events = proxy.get_event_history()
        assert len(events) == 2
        assert events[0].node_name == "my_node"
        assert events[0].success is True

    def test_node_proxy_failure_propagation(self):
        """Test node proxy records errors and re-raises."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def failing_node(state):
            raise ValueError("node crashed")

        proxy = LangGraphNodeProxy(failing_node, node_name="failing_node")

        with pytest.raises(ValueError, match="node crashed"):
            proxy({"step": 1})

        events = proxy.get_event_history()
        assert len(events) == 1
        assert events[0].success is False
        assert "node crashed" in events[0].error

    def test_node_proxy_metrics(self):
        """Test node proxy collects metrics."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def my_node(state):
            return state

        proxy = LangGraphNodeProxy(my_node, node_name="my_node")
        proxy({"step": 1})

        metrics = proxy.get_metrics()
        assert metrics is not None

    def test_node_proxy_reset(self):
        """Test node proxy reset clears state."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def my_node(state):
            return state

        proxy = LangGraphNodeProxy(my_node, node_name="my_node")
        proxy({"step": 1})
        assert len(proxy.get_event_history()) == 1

        proxy.reset()
        assert len(proxy.get_event_history()) == 0


class TestLangGraphNodeWrapping:
    """Tests for wrapping nodes in the compiled graph."""

    def test_wrap_node(self):
        """Test wrapping a node replaces it in graph.nodes."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def tool_executor(state):
            return state

        mock_graph = MagicMock()
        mock_graph.nodes = {"tool_executor": tool_executor}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        proxy = wrapper.wrap_node("tool_executor")

        assert proxy is not None
        assert proxy.node_name == "tool_executor"
        assert mock_graph.nodes["tool_executor"] is proxy

    def test_wrap_nonexistent_node(self):
        """Test wrapping a nonexistent node returns None."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        proxy = wrapper.wrap_node("nonexistent")

        assert proxy is None

    def test_wrapped_node_appears_in_get_wrapped_nodes(self):
        """Test wrapped nodes are tracked."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def my_node(state):
            return state

        mock_graph = MagicMock()
        mock_graph.nodes = {"my_node": my_node}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        wrapper.wrap_node("my_node")

        wrapped = wrapper.get_wrapped_nodes()
        assert "my_node" in wrapped

    def test_node_metrics_in_get_metrics(self):
        """Test node metrics appear in wrapper.get_metrics()."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def my_node(state):
            return state

        mock_graph = MagicMock()
        mock_graph.nodes = {"my_node": my_node}
        mock_graph.tools = None
        mock_graph.invoke = MagicMock(return_value={"output": "done"})

        wrapper = LangGraphWrapper(mock_graph)
        wrapper.wrap_node("my_node")

        # Execute the node proxy directly to generate metrics
        wrapper.get_wrapped_nodes()["my_node"]({"step": 1})

        metrics = wrapper.get_metrics()
        assert "nodes" in metrics
        assert "my_node" in metrics["nodes"]

    def test_add_injector_to_nodes(self):
        """Test adding injectors to specific nodes."""
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def my_node(state):
            return state

        mock_graph = MagicMock()
        mock_graph.nodes = {"my_node": my_node}
        mock_graph.tools = None

        wrapper = LangGraphWrapper(mock_graph)
        wrapper.wrap_node("my_node")

        injector = DelayInjector(DelayConfig(probability=0.5))
        wrapper.add_injector(injector, nodes=["my_node"])

        # Verify injector was added (node proxy has injectors)
        node_proxy = wrapper.get_wrapped_nodes()["my_node"]
        assert len(node_proxy._injectors) == 1


class TestLangGraphAsyncSupport:
    """Tests for async LangGraph operations."""

    @pytest.mark.asyncio
    async def test_async_invoke(self):
        """Test async invocation through wrapper."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.ainvoke = AsyncMock(return_value={"output": "async response"})

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        result = await wrapper.ainvoke({"input": "async test"})

        assert result == {"output": "async response"}

    @pytest.mark.asyncio
    async def test_async_stream(self):
        """Test async streaming through wrapper."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        async def mock_astream(*args, **kwargs):
            for chunk in [{"agent": "output1"}, {"tools": "output2"}]:
                yield chunk

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.astream = mock_astream

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        chunks = []
        async for chunk in wrapper.astream({"input": "test"}):
            chunks.append(chunk)

        assert chunks == [{"agent": "output1"}, {"tools": "output2"}]

    @pytest.mark.asyncio
    async def test_async_batch(self):
        """Test async batch through wrapper."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.tools = None
        mock_graph.abatch = AsyncMock(return_value=[{"o": "1"}, {"o": "2"}])

        wrapper = LangGraphWrapper(mock_graph, chaos_level=0.0)
        results = await wrapper.abatch([{"i": "1"}, {"i": "2"}])

        assert len(results) == 2
