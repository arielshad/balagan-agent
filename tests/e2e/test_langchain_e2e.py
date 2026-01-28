"""End-to-end integration tests for LangChain wrapper with mocked LLM responses.

These tests simulate complete workflows using LangChain with chaos injection,
using mocks to avoid the need for actual API tokens.

Following ralph-claude-code style: comprehensive testing with 100% pass rate.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest


class MockLLM:
    """Mock LangChain LLM for testing."""

    def __init__(self, responses: list | None = None):
        self.responses = responses or ["Default LLM response"]
        self._call_count = 0

    def invoke(self, prompt, **kwargs):
        response = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        return response

    async def ainvoke(self, prompt, **kwargs):
        return self.invoke(prompt, **kwargs)


class MockTool:
    """Mock LangChain tool for testing."""

    def __init__(self, name: str, func=None, description: str = ""):
        self.name = name
        self.description = description or f"Mock tool: {name}"
        self.func = func or self._default_func

    def _default_func(self, *args, **kwargs):
        return f"{self.name} result"

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class MockAgentExecutor:
    """Mock LangChain AgentExecutor for testing."""

    def __init__(self, tools: list | None = None, llm=None):
        self.tools = tools or []
        self.llm = llm or MockLLM()
        self._invoke_count = 0

    def invoke(self, input_data: dict, **kwargs) -> dict:
        """Simulate agent execution."""
        self._invoke_count += 1
        query = input_data.get("input", "")

        # Simulate tool usage
        results = []
        for tool in self.tools:
            if tool.name.lower() in query.lower():
                result = tool.func(query)
                results.append(f"{tool.name}: {result}")

        output = f"Agent response to: {query}"
        if results:
            output += f" (used tools: {', '.join(results)})"

        return {"output": output, "intermediate_steps": results}

    async def ainvoke(self, input_data: dict, **kwargs) -> dict:
        """Async invoke."""
        return self.invoke(input_data, **kwargs)

    def stream(self, input_data: dict, **kwargs):
        """Stream responses."""
        result = self.invoke(input_data, **kwargs)
        for char in result["output"]:
            yield char

    async def astream(self, input_data: dict, **kwargs):
        """Async stream."""
        for chunk in self.stream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list, **kwargs) -> list:
        """Batch invoke."""
        return [self.invoke(inp, **kwargs) for inp in inputs]

    async def abatch(self, inputs: list, **kwargs) -> list:
        """Async batch."""
        return self.batch(inputs, **kwargs)


class MockChain:
    """Mock LangChain chain (LCEL) for testing."""

    def __init__(self, transform_func=None):
        self._transform = transform_func or (lambda x: {"result": str(x)})
        self._invoke_count = 0

    def invoke(self, input_data: dict, **kwargs) -> Any:
        self._invoke_count += 1
        return self._transform(input_data)

    def stream(self, input_data: dict, **kwargs):
        result = self.invoke(input_data, **kwargs)
        for item in str(result).split():
            yield item

    def batch(self, inputs: list, **kwargs) -> list:
        return [self.invoke(inp, **kwargs) for inp in inputs]


class TestLangChainE2EWorkflow:
    """End-to-end tests for LangChain workflow with chaos injection."""

    def test_simple_agent_workflow_no_chaos(self):
        """Test a simple agent workflow without chaos injection."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        # Create mock tools
        def search_func(query: str) -> str:
            return f"Search results for: {query}"

        def calc_func(expr: str) -> str:
            return "42"

        search_tool = MockTool("search", search_func)
        calc_tool = MockTool("calculator", calc_func)

        # Create mock agent
        agent = MockAgentExecutor(tools=[search_tool, calc_tool])

        # Wrap with chaos
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # Execute
        result = wrapper.invoke({"input": "search for AI agents"})

        # Verify
        assert result is not None
        assert "output" in result

        metrics = wrapper.get_metrics()
        assert metrics["invoke_count"] == 1

    def test_agent_workflow_with_tool_failure_injection(self):
        """Test agent workflow with tool failure chaos injection."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        call_count = 0

        def unreliable_search(query: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"Results: {query}"

        search_tool = MockTool("search", unreliable_search)
        agent = MockAgentExecutor(tools=[search_tool])

        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # Add failure injector
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1))
        wrapper.add_injector(injector, tools=["search"])

        wrapped_tools = wrapper.get_wrapped_tools()
        assert "search" in wrapped_tools

    def test_agent_workflow_with_delays(self):
        """Test agent workflow with artificial delays."""
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        def fast_tool(x: str) -> str:
            return f"fast: {x}"

        tool = MockTool("fast_tool", fast_tool)
        agent = MockAgentExecutor(tools=[tool])

        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # Add delay injector
        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=10, max_delay_ms=10))
        wrapper.add_injector(injector, tools=["fast_tool"])

        wrapped_tools = wrapper.get_wrapped_tools()
        assert "fast_tool" in wrapped_tools

    def test_agent_workflow_with_experiment_tracking(self):
        """Test agent workflow within an experiment context."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        with wrapper.experiment("test-experiment"):
            wrapper.invoke({"input": "test1"})
            wrapper.invoke({"input": "test2"})

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-experiment"

    def test_multi_tool_agent_workflow(self):
        """Test agent with multiple tools."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        def search_web(query: str) -> dict:
            return {"source": "web", "query": query}

        def search_db(query: str) -> dict:
            return {"source": "database", "query": query}

        def write_file(content: str) -> str:
            return f"Written: {content}"

        tools = [
            MockTool("search_web", search_web),
            MockTool("search_db", search_db),
            MockTool("write_file", write_file),
        ]

        agent = MockAgentExecutor(tools=tools)
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # Verify all tools are wrapped
        wrapped_tools = wrapper.get_wrapped_tools()
        assert len(wrapped_tools) == 3
        assert "search_web" in wrapped_tools
        assert "search_db" in wrapped_tools
        assert "write_file" in wrapped_tools

    def test_chaos_level_configuration(self):
        """Test configuring different chaos levels."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent)

        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=True,
            )
            assert wrapper.chaos_level == level

    def test_metrics_collection_e2e(self):
        """Test comprehensive metrics collection during workflow."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        def tracked_tool(x: str) -> str:
            return x

        tool = MockTool("tracked", tracked_tool)
        agent = MockAgentExecutor(tools=[tool])

        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # Execute multiple times
        for i in range(5):
            wrapper.invoke({"input": f"query {i}"})

        metrics = wrapper.get_metrics()
        assert metrics["invoke_count"] == 5

    def test_reset_workflow_state(self):
        """Test resetting workflow state between experiments."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        # First experiment
        with wrapper.experiment("exp1"):
            wrapper.invoke({"input": "test"})

        assert wrapper.get_metrics()["invoke_count"] == 1

        # Reset
        wrapper.reset()
        assert wrapper.get_metrics()["invoke_count"] == 0

        # Second experiment
        with wrapper.experiment("exp2"):
            wrapper.invoke({"input": "test"})
            wrapper.invoke({"input": "test2"})

        assert wrapper.get_metrics()["invoke_count"] == 2

    def test_streaming_workflow(self):
        """Test streaming response workflow."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        chunks = list(wrapper.stream({"input": "stream test"}))
        assert len(chunks) > 0

    def test_batch_workflow(self):
        """Test batch invocation workflow."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        inputs = [{"input": f"query {i}"} for i in range(3)]
        results = wrapper.batch(inputs)

        assert len(results) == 3
        assert wrapper.get_metrics()["invoke_count"] == 3


class TestLangChainChainE2E:
    """End-to-end tests for LangChain chain wrapper."""

    def test_simple_chain_workflow(self):
        """Test simple chain workflow."""
        from balaganagent.wrappers.langchain import LangChainChainWrapper

        def transform(x):
            return {"result": f"transformed: {x.get('input', '')}"}

        chain = MockChain(transform)
        wrapper = LangChainChainWrapper(chain, chaos_level=0.0)

        result = wrapper.invoke({"input": "test"})
        assert "result" in result

    def test_chain_streaming(self):
        """Test chain streaming."""
        from balaganagent.wrappers.langchain import LangChainChainWrapper

        chain = MockChain()
        wrapper = LangChainChainWrapper(chain, chaos_level=0.0)

        chunks = list(wrapper.stream({"input": "test"}))
        assert len(chunks) > 0

    def test_chain_batch(self):
        """Test chain batch."""
        from balaganagent.wrappers.langchain import LangChainChainWrapper

        chain = MockChain()
        wrapper = LangChainChainWrapper(chain, chaos_level=0.0)

        results = wrapper.batch([{"input": "1"}, {"input": "2"}])
        assert len(results) == 2


class TestLangChainAsyncE2E:
    """End-to-end tests for async LangChain operations."""

    @pytest.mark.asyncio
    async def test_async_agent_workflow(self):
        """Test async agent workflow."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        result = await wrapper.ainvoke({"input": "async test"})
        assert "output" in result

    @pytest.mark.asyncio
    async def test_async_streaming(self):
        """Test async streaming."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        chunks = []
        async for chunk in wrapper.astream({"input": "test"}):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_async_batch(self):
        """Test async batch."""
        from balaganagent.wrappers.langchain import LangChainAgentWrapper

        agent = MockAgentExecutor(tools=[])
        wrapper = LangChainAgentWrapper(agent, chaos_level=0.0)

        results = await wrapper.abatch([{"input": "1"}, {"input": "2"}])
        assert len(results) == 2


class TestLangChainCallbackE2E:
    """End-to-end tests for callback integration."""

    def test_callback_handler_workflow(self):
        """Test callback handler in workflow."""
        from balaganagent.wrappers.langchain import ChaosCallbackHandler

        handler = ChaosCallbackHandler(chaos_level=0.0)

        # Simulate a complete workflow
        handler.on_chain_start({"name": "test_chain"}, {"input": "test"})
        handler.on_llm_start({"name": "gpt-4"}, ["prompt"])
        handler.on_llm_end(MagicMock(generations=[[MagicMock(text="response")]]))
        handler.on_tool_start({"name": "search"}, "query")
        handler.on_tool_end("result")
        handler.on_chain_end({"output": "final"})

        events = handler.get_events()
        assert len(events) == 6

        metrics = handler.get_metrics()
        assert metrics["llm_calls"] == 1
        assert metrics["tool_calls"] == 1
        assert metrics["chain_runs"] == 1

    def test_callback_reset(self):
        """Test callback handler reset."""
        from balaganagent.wrappers.langchain import ChaosCallbackHandler

        handler = ChaosCallbackHandler(chaos_level=0.0)
        handler.on_llm_start({}, [])
        handler.on_tool_start({}, "")

        assert handler.get_metrics()["llm_calls"] == 1
        assert handler.get_metrics()["tool_calls"] == 1

        handler.reset()

        assert handler.get_metrics()["llm_calls"] == 0
        assert handler.get_metrics()["tool_calls"] == 0


class TestLangChainErrorHandling:
    """Error handling tests for LangChain workflows."""

    def test_tool_proxy_exhausts_retries(self):
        """Test behavior when tool exhausts all retries."""
        from balaganagent.wrappers.langchain import LangChainToolProxy

        def always_fails(*args):
            raise RuntimeError("Permanent failure")

        tool = MockTool("failing", always_fails)

        proxy = LangChainToolProxy(tool, chaos_level=0.0, max_retries=2, retry_delay=0.01)

        with pytest.raises(RuntimeError, match="Permanent failure"):
            proxy()

        history = proxy.get_call_history()
        assert len(history) == 1
        assert history[0].error is not None

    def test_tool_proxy_recovers_from_transient_failure(self):
        """Test tool proxy recovers from transient failures."""
        from balaganagent.wrappers.langchain import LangChainToolProxy

        call_count = 0

        def flaky_func(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        tool = MockTool("flaky", flaky_func)
        proxy = LangChainToolProxy(tool, chaos_level=0.0, max_retries=3, retry_delay=0.01)

        result = proxy()
        assert result == "success"
        assert call_count == 3
