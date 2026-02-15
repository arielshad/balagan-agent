"""End-to-end integration tests for LangGraph wrapper with mocked graph execution.

These tests simulate complete LangGraph workflows using chaos injection,
using mocks to avoid the need for actual LangGraph/LangChain installations.

Following project style: comprehensive testing with 100% pass rate.
"""

from typing import Any

import pytest


class MockTool:
    """Mock LangChain/LangGraph tool for testing."""

    def __init__(self, name: str, func=None, description: str = ""):
        self.name = name
        self.description = description or f"Mock tool: {name}"
        self.func = func or self._default_func

    def _default_func(self, *args, **kwargs):
        return f"{self.name} result"

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class MockToolNode:
    """Mock LangGraph ToolNode."""

    def __init__(self, tools: list):
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}

    def __call__(self, state: dict) -> dict:
        return state


class MockCompiledGraph:
    """Mock LangGraph CompiledGraph for testing."""

    def __init__(self, nodes: dict | None = None, tools: list | None = None):
        self.nodes = nodes or {}
        self.tools = tools
        self._invoke_count = 0

    def invoke(self, input_data: dict, **kwargs) -> dict:
        self._invoke_count += 1
        state = dict(input_data)
        for node_name, node_func in self.nodes.items():
            result = node_func(state)
            if result is not None:
                state = result
        return state

    async def ainvoke(self, input_data: dict, **kwargs) -> dict:
        return self.invoke(input_data, **kwargs)

    def stream(self, input_data: dict, **kwargs):
        for node_name in self.nodes:
            yield {node_name: {"messages": [f"Output from {node_name}"]}}

    async def astream(self, input_data: dict, **kwargs):
        for chunk in self.stream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list, **kwargs) -> list:
        return [self.invoke(inp, **kwargs) for inp in inputs]

    async def abatch(self, inputs: list, **kwargs) -> list:
        return self.batch(inputs, **kwargs)

    def get_state(self, config: dict) -> dict:
        return {"messages": [], "step": 0}

    def update_state(self, config: dict, values: dict, **kwargs) -> dict:
        return values


class TestLangGraphE2EWorkflow:
    """End-to-end tests for LangGraph workflow with chaos injection."""

    def test_simple_graph_workflow_no_chaos(self):
        """Test a simple graph workflow without chaos injection."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def agent_node(state):
            return {"messages": state.get("messages", []) + ["agent response"]}

        graph = MockCompiledGraph(nodes={"agent": agent_node})

        wrapper = LangGraphWrapper(graph, chaos_level=0.0)
        result = wrapper.invoke({"messages": ["hello"]})

        assert result is not None
        assert "messages" in result
        assert "agent response" in result["messages"]

        metrics = wrapper.get_metrics()
        assert metrics["invoke_count"] == 1

    def test_graph_with_tool_failure_injection(self):
        """Test graph workflow with tool failure chaos injection."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def search_func(query: str) -> str:
            return f"Results: {query}"

        search_tool = MockTool("search", search_func)
        tool_node = MockToolNode([search_tool])

        graph = MockCompiledGraph(nodes={"tools": tool_node})

        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1))
        wrapper.add_injector(injector, tools=["search"])

        wrapped_tools = wrapper.get_wrapped_tools()
        assert "search" in wrapped_tools

    def test_graph_with_delays(self):
        """Test graph workflow with artificial delays."""
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def fast_tool(x: str) -> str:
            return f"fast: {x}"

        tool = MockTool("fast_tool", fast_tool)
        tool_node = MockToolNode([tool])

        graph = MockCompiledGraph(nodes={"tools": tool_node})

        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=10, max_delay_ms=10))
        wrapper.add_injector(injector, tools=["fast_tool"])

        wrapped_tools = wrapper.get_wrapped_tools()
        assert "fast_tool" in wrapped_tools

    def test_experiment_tracking(self):
        """Test graph workflow within an experiment context."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        with wrapper.experiment("langgraph-chaos-experiment"):
            wrapper.invoke({"messages": ["test1"]})
            wrapper.invoke({"messages": ["test2"]})

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "langgraph-chaos-experiment"

    def test_multi_tool_graph(self):
        """Test graph with multiple tools."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        tools = [
            MockTool("search_web", lambda q: {"source": "web", "query": q}),
            MockTool("search_db", lambda q: {"source": "db", "query": q}),
            MockTool("write_file", lambda c: f"Written: {c}"),
        ]

        tool_node = MockToolNode(tools)
        graph = MockCompiledGraph(nodes={"tools": tool_node})

        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        wrapped_tools = wrapper.get_wrapped_tools()
        assert len(wrapped_tools) == 3
        assert "search_web" in wrapped_tools
        assert "search_db" in wrapped_tools
        assert "write_file" in wrapped_tools

    def test_chaos_level_configuration(self):
        """Test configuring different chaos levels."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph)

        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=True,
            )
            assert wrapper.chaos_level == level

    def test_metrics_collection_e2e(self):
        """Test comprehensive metrics collection during workflow."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        for i in range(5):
            wrapper.invoke({"messages": [f"query {i}"]})

        metrics = wrapper.get_metrics()
        assert metrics["invoke_count"] == 5

    def test_reset_workflow_state(self):
        """Test resetting workflow state between experiments."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        with wrapper.experiment("exp1"):
            wrapper.invoke({"messages": ["test"]})

        assert wrapper.get_metrics()["invoke_count"] == 1

        wrapper.reset()
        assert wrapper.get_metrics()["invoke_count"] == 0

        with wrapper.experiment("exp2"):
            wrapper.invoke({"messages": ["test1"]})
            wrapper.invoke({"messages": ["test2"]})

        assert wrapper.get_metrics()["invoke_count"] == 2

    def test_streaming_workflow(self):
        """Test streaming response workflow (node-by-node)."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def agent_node(state):
            return state

        def tools_node(state):
            return state

        graph = MockCompiledGraph(nodes={"agent": agent_node, "tools": tools_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        chunks = list(wrapper.stream({"messages": ["stream test"]}))
        assert len(chunks) == 2  # One per node

    def test_batch_workflow(self):
        """Test batch invocation workflow."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        inputs = [{"messages": [f"query {i}"]} for i in range(3)]
        results = wrapper.batch(inputs)

        assert len(results) == 3
        assert wrapper.get_metrics()["invoke_count"] == 3


class TestLangGraphNodeChaosE2E:
    """End-to-end tests for node-level chaos injection."""

    def test_node_delay_injection(self):
        """Test injecting delays at a specific node."""
        import time

        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def slow_node(state):
            return {"messages": state.get("messages", []) + ["processed"]}

        graph = MockCompiledGraph(nodes={"processor": slow_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        proxy = wrapper.wrap_node("processor")
        assert proxy is not None

        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=50, max_delay_ms=50))
        wrapper.add_injector(injector, nodes=["processor"])

        start = time.time()
        proxy({"messages": ["test"]})
        elapsed = (time.time() - start) * 1000

        # Should have at least the injected delay
        assert elapsed >= 40  # Allow small timing tolerance

    def test_node_metrics_tracking(self):
        """Test that node execution metrics are tracked."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def my_node(state):
            return state

        graph = MockCompiledGraph(nodes={"my_node": my_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        wrapper.wrap_node("my_node")
        node_proxy = wrapper.get_wrapped_nodes()["my_node"]

        node_proxy({"step": 1})
        node_proxy({"step": 2})

        events = node_proxy.get_event_history()
        assert len(events) == 2
        assert all(e.success for e in events)

        metrics = wrapper.get_metrics()
        assert "my_node" in metrics["nodes"]

    def test_mixed_tool_and_node_chaos(self):
        """Test combining tool-level and node-level chaos."""
        from balaganagent.injectors import DelayInjector, ToolFailureInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        search_tool = MockTool("search", lambda q: f"results: {q}")
        tool_node = MockToolNode([search_tool])

        def agent_node(state):
            return state

        graph = MockCompiledGraph(nodes={"agent": agent_node, "tools": tool_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        # Tool-level chaos
        tool_injector = ToolFailureInjector(ToolFailureConfig(probability=0.5))
        wrapper.add_injector(tool_injector, tools=["search"])

        # Node-level chaos
        wrapper.wrap_node("agent")
        node_injector = DelayInjector(DelayConfig(probability=0.5, min_delay_ms=10, max_delay_ms=10))
        wrapper.add_injector(node_injector, nodes=["agent"])

        # Both should be tracked independently
        assert len(wrapper.get_wrapped_tools()) >= 1
        assert len(wrapper.get_wrapped_nodes()) == 1

    def test_node_failure_propagation(self):
        """Test that node failures are recorded and propagated."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def failing_node(state):
            raise ValueError("Node processing failed")

        graph = MockCompiledGraph(nodes={"processor": failing_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        proxy = wrapper.wrap_node("processor")
        assert proxy is not None

        with pytest.raises(ValueError, match="Node processing failed"):
            proxy({"step": 1})

        events = proxy.get_event_history()
        assert len(events) == 1
        assert events[0].success is False


class TestLangGraphAsyncE2E:
    """End-to-end tests for async LangGraph operations."""

    @pytest.mark.asyncio
    async def test_async_graph_workflow(self):
        """Test async graph workflow."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        result = await wrapper.ainvoke({"messages": ["async test"]})
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_streaming(self):
        """Test async streaming."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        def agent_node(state):
            return state

        graph = MockCompiledGraph(nodes={"agent": agent_node})
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        chunks = []
        async for chunk in wrapper.astream({"messages": ["test"]}):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_async_batch(self):
        """Test async batch."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph, chaos_level=0.0)

        results = await wrapper.abatch([{"messages": ["1"]}, {"messages": ["2"]}])
        assert len(results) == 2


class TestLangGraphStateManagement:
    """Tests for LangGraph state management pass-through."""

    def test_get_state(self):
        """Test get_state passes through to compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph)

        state = wrapper.get_state({"thread_id": "123"})
        assert "messages" in state
        assert "step" in state

    def test_update_state(self):
        """Test update_state passes through to compiled graph."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper

        graph = MockCompiledGraph()
        wrapper = LangGraphWrapper(graph)

        result = wrapper.update_state({"thread_id": "123"}, {"step": 5})
        assert result == {"step": 5}


class TestLangGraphErrorHandling:
    """Error handling tests for LangGraph workflows."""

    def test_tool_proxy_exhausts_retries(self):
        """Test behavior when tool exhausts all retries."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        def always_fails(*args):
            raise RuntimeError("Permanent failure")

        tool = MockTool("failing", always_fails)

        proxy = LangGraphToolProxy(tool, chaos_level=0.0, max_retries=2, retry_delay=0.01)

        with pytest.raises(RuntimeError, match="Permanent failure"):
            proxy()

        history = proxy.get_call_history()
        assert len(history) == 1
        assert history[0].error is not None

    def test_tool_proxy_recovers_from_transient_failure(self):
        """Test tool proxy recovers from transient failures."""
        from balaganagent.wrappers.langgraph import LangGraphToolProxy

        call_count = 0

        def flaky_func(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        tool = MockTool("flaky", flaky_func)
        proxy = LangGraphToolProxy(tool, chaos_level=0.0, max_retries=3, retry_delay=0.01)

        result = proxy()
        assert result == "success"
        assert call_count == 3
