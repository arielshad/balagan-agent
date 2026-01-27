"""Tests for LangChain wrapper - TDD approach.

These tests use mocks to avoid requiring actual API tokens (OpenAI, etc.).
Following ralph-claude-code style: comprehensive TDD with 100% pass rate target.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestLangChainAgentWrapper:
    """Tests for LangChain agent wrapper integration."""

    def test_wrapper_creation(self):
        """Test that wrapper can be created with mock LangChain agent."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.agent = MagicMock()

        wrapper = LangChainAgentWrapper(mock_agent)
        assert wrapper is not None
        assert wrapper.agent_executor is mock_agent

    def test_wrapper_with_chaos_level(self):
        """Test wrapper can be configured with chaos level."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.5)
        assert wrapper.chaos_level == 0.5

    def test_wrap_tools(self):
        """Test that agent tools are properly wrapped."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        # Create mock tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "search_tool"
        mock_tool1.func = MagicMock(return_value="search result")

        mock_tool2 = MagicMock()
        mock_tool2.name = "calculator"
        mock_tool2.func = MagicMock(return_value="42")

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool1, mock_tool2]

        wrapper = LangChainAgentWrapper(mock_agent)
        wrapped_tools = wrapper.get_wrapped_tools()

        assert "search_tool" in wrapped_tools
        assert "calculator" in wrapped_tools

    def test_invoke_with_chaos(self):
        """Test that invoke runs with chaos injection."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.invoke = MagicMock(return_value={"output": "Agent response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        result = wrapper.invoke({"input": "Hello"})

        assert result == {"output": "Agent response"}
        mock_agent.invoke.assert_called_once()

    def test_invoke_with_config(self):
        """Test invoke with additional config."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.invoke = MagicMock(return_value={"output": "Response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        wrapper.invoke(
            {"input": "Test query"},
            config={"callbacks": []},
        )

        mock_agent.invoke.assert_called_once()

    def test_stream_method(self):
        """Test streaming responses through wrapper."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.stream = MagicMock(return_value=iter(["chunk1", "chunk2"]))

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        chunks = list(wrapper.stream({"input": "Hello"}))

        assert chunks == ["chunk1", "chunk2"]

    def test_get_metrics(self):
        """Test that metrics are collected properly."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.invoke = MagicMock(return_value={"output": "response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        wrapper.invoke({"input": "test"})

        metrics = wrapper.get_metrics()
        assert "invoke_count" in metrics
        assert metrics["invoke_count"] == 1

    def test_chaos_injection_on_tools(self):
        """Test that chaos can be injected into tool calls."""
        from agentchaos.injectors import ToolFailureInjector
        from agentchaos.injectors.tool_failure import ToolFailureConfig
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        mock_tool.func = MagicMock(return_value="result")

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool]

        wrapper = LangChainAgentWrapper(mock_agent)

        # Add a custom injector
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["flaky_tool"])

        tools = wrapper.get_wrapped_tools()
        assert "flaky_tool" in tools

    def test_reset_wrapper(self):
        """Test wrapper state reset."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.invoke = MagicMock(return_value={"output": "response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        wrapper.invoke({"input": "test"})

        metrics_before = wrapper.get_metrics()
        assert metrics_before["invoke_count"] == 1

        wrapper.reset()
        metrics_after = wrapper.get_metrics()
        assert metrics_after["invoke_count"] == 0

    def test_experiment_context(self):
        """Test running agent within an experiment context."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.invoke = MagicMock(return_value={"output": "response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)

        with wrapper.experiment("test-langchain-experiment"):
            wrapper.invoke({"input": "test"})

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-langchain-experiment"

    def test_batch_invoke(self):
        """Test batch invocation of multiple inputs."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.batch = MagicMock(
            return_value=[{"output": "r1"}, {"output": "r2"}]
        )

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        results = wrapper.batch([{"input": "q1"}, {"input": "q2"}])

        assert len(results) == 2
        mock_agent.batch.assert_called_once()

    def test_configure_chaos_all_options(self):
        """Test configuring chaos with all options."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []

        wrapper = LangChainAgentWrapper(mock_agent)
        wrapper.configure_chaos(
            chaos_level=0.75,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        assert wrapper.chaos_level == 0.75


class TestLangChainToolProxy:
    """Tests for individual tool proxying in LangChain."""

    def test_tool_proxy_creation(self):
        """Test tool proxy is created correctly."""
        from agentchaos.wrappers.langchain import LangChainToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangChainToolProxy(mock_tool)
        assert proxy.tool_name == "test_tool"

    def test_tool_proxy_call(self):
        """Test tool proxy calls the underlying tool."""
        from agentchaos.wrappers.langchain import LangChainToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.func = MagicMock(return_value="expected result")

        proxy = LangChainToolProxy(mock_tool, chaos_level=0.0)
        result = proxy("arg1", kwarg1="value1")

        mock_tool.func.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "expected result"

    def test_tool_proxy_records_call_history(self):
        """Test tool proxy records call history."""
        from agentchaos.wrappers.langchain import LangChainToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "tracked_tool"
        mock_tool.func = MagicMock(return_value="result")

        proxy = LangChainToolProxy(mock_tool, chaos_level=0.0)
        proxy("arg1")
        proxy("arg2")

        history = proxy.get_call_history()
        assert len(history) == 2
        assert history[0].args == ("arg1",)
        assert history[1].args == ("arg2",)

    def test_tool_proxy_retry_on_failure(self):
        """Test tool proxy retries on transient failures."""
        from agentchaos.wrappers.langchain import LangChainToolProxy

        mock_tool = MagicMock()
        mock_tool.name = "flaky_tool"
        # Fail twice, then succeed
        mock_tool.func = MagicMock(
            side_effect=[Exception("fail1"), Exception("fail2"), "success"]
        )

        proxy = LangChainToolProxy(
            mock_tool, chaos_level=0.0, max_retries=3, retry_delay=0.01
        )
        result = proxy()

        assert result == "success"
        assert mock_tool.func.call_count == 3


class TestLangChainChainWrapper:
    """Tests for wrapping LangChain chains (LCEL)."""

    def test_chain_wrapper_creation(self):
        """Test chain wrapper creation."""
        from agentchaos.wrappers.langchain import LangChainChainWrapper

        mock_chain = MagicMock()
        wrapper = LangChainChainWrapper(mock_chain)
        assert wrapper.chain is mock_chain

    def test_chain_invoke(self):
        """Test chain invocation through wrapper."""
        from agentchaos.wrappers.langchain import LangChainChainWrapper

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="chain output")

        wrapper = LangChainChainWrapper(mock_chain, chaos_level=0.0)
        result = wrapper.invoke({"question": "What is AI?"})

        assert result == "chain output"
        mock_chain.invoke.assert_called_once()

    def test_chain_stream(self):
        """Test chain streaming through wrapper."""
        from agentchaos.wrappers.langchain import LangChainChainWrapper

        mock_chain = MagicMock()
        mock_chain.stream = MagicMock(return_value=iter(["a", "b", "c"]))

        wrapper = LangChainChainWrapper(mock_chain, chaos_level=0.0)
        result = list(wrapper.stream({"input": "test"}))

        assert result == ["a", "b", "c"]

    def test_chain_batch(self):
        """Test chain batch invocation."""
        from agentchaos.wrappers.langchain import LangChainChainWrapper

        mock_chain = MagicMock()
        mock_chain.batch = MagicMock(return_value=["r1", "r2", "r3"])

        wrapper = LangChainChainWrapper(mock_chain, chaos_level=0.0)
        results = wrapper.batch([{"q": "1"}, {"q": "2"}, {"q": "3"}])

        assert results == ["r1", "r2", "r3"]

    def test_chain_metrics(self):
        """Test metrics tracking for chain."""
        from agentchaos.wrappers.langchain import LangChainChainWrapper

        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="output")

        wrapper = LangChainChainWrapper(mock_chain, chaos_level=0.0)
        wrapper.invoke({})
        wrapper.invoke({})

        metrics = wrapper.get_metrics()
        assert metrics["invoke_count"] == 2


class TestLangChainAsyncSupport:
    """Tests for async LangChain operations."""

    @pytest.mark.asyncio
    async def test_async_invoke(self):
        """Test async invocation through wrapper."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.ainvoke = AsyncMock(return_value={"output": "async response"})

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        result = await wrapper.ainvoke({"input": "async test"})

        assert result == {"output": "async response"}

    @pytest.mark.asyncio
    async def test_async_stream(self):
        """Test async streaming through wrapper."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        async def mock_astream(*args, **kwargs):
            for chunk in ["c1", "c2", "c3"]:
                yield chunk

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.astream = mock_astream

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        chunks = []
        async for chunk in wrapper.astream({"input": "test"}):
            chunks.append(chunk)

        assert chunks == ["c1", "c2", "c3"]

    @pytest.mark.asyncio
    async def test_async_batch(self):
        """Test async batch through wrapper."""
        from agentchaos.wrappers.langchain import LangChainAgentWrapper

        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_agent.abatch = AsyncMock(return_value=[{"o": "1"}, {"o": "2"}])

        wrapper = LangChainAgentWrapper(mock_agent, chaos_level=0.0)
        results = await wrapper.abatch([{"i": "1"}, {"i": "2"}])

        assert len(results) == 2


class TestLangChainCallbackIntegration:
    """Tests for LangChain callback integration."""

    def test_callback_handler_creation(self):
        """Test chaos callback handler creation."""
        from agentchaos.wrappers.langchain import ChaosCallbackHandler

        handler = ChaosCallbackHandler(chaos_level=0.5)
        assert handler.chaos_level == 0.5

    def test_callback_records_events(self):
        """Test callback handler records events."""
        from agentchaos.wrappers.langchain import ChaosCallbackHandler

        handler = ChaosCallbackHandler(chaos_level=0.0)

        # Simulate LLM start
        handler.on_llm_start({"name": "gpt-4"}, ["prompt"])
        handler.on_llm_end(MagicMock(generations=[[MagicMock(text="response")]]))

        events = handler.get_events()
        assert len(events) >= 2

    def test_callback_metrics(self):
        """Test callback handler provides metrics."""
        from agentchaos.wrappers.langchain import ChaosCallbackHandler

        handler = ChaosCallbackHandler(chaos_level=0.0)
        handler.on_tool_start({"name": "search"}, "query")
        handler.on_tool_end("result")

        metrics = handler.get_metrics()
        assert "tool_calls" in metrics
