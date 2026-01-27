"""Tests for AutoGen wrapper - TDD approach."""

from unittest.mock import MagicMock


class TestAutoGenWrapper:
    """Tests for AutoGen wrapper integration."""

    def test_wrapper_creation(self):
        """Test wrapper creation with mock AutoGen components."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        # Create mock assistant agent
        mock_assistant = MagicMock()
        mock_assistant.name = "assistant"

        wrapper = AutoGenWrapper(mock_assistant)
        assert wrapper is not None
        assert wrapper.agent is mock_assistant

    def test_wrapper_with_user_proxy(self):
        """Test wrapper with assistant and user proxy agents."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_assistant = MagicMock()
        mock_assistant.name = "assistant"

        mock_user_proxy = MagicMock()
        mock_user_proxy.name = "user_proxy"

        wrapper = AutoGenWrapper(mock_assistant, user_proxy=mock_user_proxy)
        assert wrapper.agent is mock_assistant
        assert wrapper.user_proxy is mock_user_proxy

    def test_wrapper_with_chaos_level(self):
        """Test wrapper configured with chaos level."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "test_agent"

        wrapper = AutoGenWrapper(mock_agent, chaos_level=0.7)
        assert wrapper.chaos_level == 0.7

    def test_wrap_function_map(self):
        """Test that function_map functions are wrapped."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        # Create mock agent with function_map
        def search_func(query: str) -> str:
            return f"Results for {query}"

        def calc_func(expr: str) -> str:
            return "42"

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {
            "search": search_func,
            "calculate": calc_func,
        }

        wrapper = AutoGenWrapper(mock_agent)
        wrapped_functions = wrapper.get_wrapped_functions()

        assert "search" in wrapped_functions
        assert "calculate" in wrapped_functions

    def test_initiate_chat(self):
        """Test initiating a chat with chaos injection."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_assistant = MagicMock()
        mock_assistant.name = "assistant"
        mock_assistant.function_map = {}

        mock_user_proxy = MagicMock()
        mock_user_proxy.name = "user_proxy"
        mock_user_proxy.initiate_chat = MagicMock(return_value={"messages": ["hello"]})

        wrapper = AutoGenWrapper(mock_assistant, user_proxy=mock_user_proxy, chaos_level=0.0)
        wrapper.initiate_chat("Hello, agent!")

        mock_user_proxy.initiate_chat.assert_called_once()

    def test_initiate_chat_with_config(self):
        """Test initiate_chat with additional config."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_assistant = MagicMock()
        mock_assistant.name = "assistant"
        mock_assistant.function_map = {}

        mock_user_proxy = MagicMock()
        mock_user_proxy.name = "user_proxy"
        mock_user_proxy.initiate_chat = MagicMock(return_value={"messages": []})

        wrapper = AutoGenWrapper(mock_assistant, user_proxy=mock_user_proxy, chaos_level=0.0)
        wrapper.initiate_chat(
            message="Test message",
            max_turns=5,
            clear_history=True,
        )

        call_args = mock_user_proxy.initiate_chat.call_args
        assert call_args.kwargs.get("max_turns") == 5
        assert call_args.kwargs.get("clear_history") is True

    def test_generate_reply(self):
        """Test generate_reply through wrapper."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {}
        mock_agent.generate_reply = MagicMock(return_value="Agent reply")

        wrapper = AutoGenWrapper(mock_agent, chaos_level=0.0)
        messages = [{"role": "user", "content": "Hello"}]
        result = wrapper.generate_reply(messages)

        assert result == "Agent reply"
        mock_agent.generate_reply.assert_called_once()

    def test_get_metrics(self):
        """Test metrics collection."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {}
        mock_agent.generate_reply = MagicMock(return_value="reply")

        wrapper = AutoGenWrapper(mock_agent, chaos_level=0.0)
        wrapper.generate_reply([{"role": "user", "content": "test"}])
        wrapper.generate_reply([{"role": "user", "content": "test2"}])

        metrics = wrapper.get_metrics()
        assert "reply_count" in metrics
        assert metrics["reply_count"] == 2

    def test_chaos_injection_on_functions(self):
        """Test chaos injection on function_map functions."""
        from agentchaos.injectors import ToolFailureInjector
        from agentchaos.injectors.tool_failure import ToolFailureConfig
        from agentchaos.wrappers.autogen import AutoGenWrapper

        def my_function(x: int) -> int:
            return x * 2

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {"my_function": my_function}

        wrapper = AutoGenWrapper(mock_agent)
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, functions=["my_function"])

        wrapped = wrapper.get_wrapped_functions()
        assert "my_function" in wrapped

    def test_reset_wrapper(self):
        """Test wrapper state reset."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {}
        mock_agent.generate_reply = MagicMock(return_value="reply")

        wrapper = AutoGenWrapper(mock_agent, chaos_level=0.0)
        wrapper.generate_reply([])

        metrics_before = wrapper.get_metrics()
        assert metrics_before["reply_count"] == 1

        wrapper.reset()
        metrics_after = wrapper.get_metrics()
        assert metrics_after["reply_count"] == 0

    def test_experiment_context(self):
        """Test running agent within an experiment context."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {}
        mock_agent.generate_reply = MagicMock(return_value="reply")

        wrapper = AutoGenWrapper(mock_agent, chaos_level=0.0)

        with wrapper.experiment("test-autogen-experiment"):
            wrapper.generate_reply([])

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-autogen-experiment"

    def test_group_chat_support(self):
        """Test wrapper with group chat configuration."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1"
        mock_agent1.function_map = {}

        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2"
        mock_agent2.function_map = {}

        mock_group_chat = MagicMock()
        mock_group_chat.agents = [mock_agent1, mock_agent2]

        wrapper = AutoGenWrapper(mock_agent1, group_chat=mock_group_chat)
        assert wrapper.group_chat is mock_group_chat

    def test_configure_chaos_all_options(self):
        """Test configuring chaos with all options."""
        from agentchaos.wrappers.autogen import AutoGenWrapper

        mock_agent = MagicMock()
        mock_agent.name = "assistant"
        mock_agent.function_map = {}

        wrapper = AutoGenWrapper(mock_agent)
        wrapper.configure_chaos(
            chaos_level=0.6,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=False,
            enable_context_corruption=True,
            enable_budget_exhaustion=False,
        )

        assert wrapper.chaos_level == 0.6


class TestAutoGenFunctionProxy:
    """Tests for function proxying in AutoGen."""

    def test_function_proxy_creation(self):
        """Test function proxy is created correctly."""
        from agentchaos.wrappers.autogen import AutoGenFunctionProxy

        def my_func(x: int) -> int:
            return x * 2

        proxy = AutoGenFunctionProxy(my_func, name="my_func")
        assert proxy.function_name == "my_func"

    def test_function_proxy_call(self):
        """Test function proxy calls the underlying function."""
        from agentchaos.wrappers.autogen import AutoGenFunctionProxy

        def add_numbers(a: int, b: int) -> int:
            return a + b

        proxy = AutoGenFunctionProxy(add_numbers, name="add_numbers", chaos_level=0.0)
        result = proxy(5, 3)

        assert result == 8

    def test_function_proxy_records_history(self):
        """Test function proxy records call history."""
        from agentchaos.wrappers.autogen import AutoGenFunctionProxy

        def my_func(x: int) -> int:
            return x

        proxy = AutoGenFunctionProxy(my_func, name="my_func", chaos_level=0.0)
        proxy(1)
        proxy(2)
        proxy(3)

        history = proxy.get_call_history()
        assert len(history) == 3

    def test_function_proxy_retry_on_failure(self):
        """Test function proxy retries on transient failures."""
        from agentchaos.wrappers.autogen import AutoGenFunctionProxy

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Failure {call_count}")
            return "success"

        proxy = AutoGenFunctionProxy(
            flaky_func, name="flaky", chaos_level=0.0, max_retries=3, retry_delay=0.01
        )
        result = proxy()

        assert result == "success"
        assert call_count == 3


class TestAutoGenMultiAgent:
    """Tests for multi-agent scenarios with AutoGen."""

    def test_wrap_multiple_agents(self):
        """Test wrapping multiple agents in a conversation."""
        from agentchaos.wrappers.autogen import AutoGenMultiAgentWrapper

        mock_agent1 = MagicMock()
        mock_agent1.name = "researcher"
        mock_agent1.function_map = {"search": MagicMock()}

        mock_agent2 = MagicMock()
        mock_agent2.name = "writer"
        mock_agent2.function_map = {"write": MagicMock()}

        wrapper = AutoGenMultiAgentWrapper([mock_agent1, mock_agent2])
        assert len(wrapper.agents) == 2

    def test_multi_agent_chaos_propagation(self):
        """Test chaos settings propagate to all agents."""
        from agentchaos.wrappers.autogen import AutoGenMultiAgentWrapper

        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1"
        mock_agent1.function_map = {}

        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2"
        mock_agent2.function_map = {}

        wrapper = AutoGenMultiAgentWrapper([mock_agent1, mock_agent2])
        wrapper.configure_chaos(chaos_level=0.8)

        # All wrapped agents should have chaos level 0.8
        for agent_wrapper in wrapper.get_agent_wrappers():
            assert agent_wrapper.chaos_level == 0.8

    def test_multi_agent_metrics(self):
        """Test aggregated metrics from multiple agents."""
        from agentchaos.wrappers.autogen import AutoGenMultiAgentWrapper

        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1"
        mock_agent1.function_map = {}
        mock_agent1.generate_reply = MagicMock(return_value="reply1")

        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2"
        mock_agent2.function_map = {}
        mock_agent2.generate_reply = MagicMock(return_value="reply2")

        wrapper = AutoGenMultiAgentWrapper([mock_agent1, mock_agent2], chaos_level=0.0)

        # Simulate replies
        wrapper.get_agent_wrapper("agent1").generate_reply([])
        wrapper.get_agent_wrapper("agent2").generate_reply([])

        metrics = wrapper.get_aggregate_metrics()
        assert "total_replies" in metrics
        assert metrics["total_replies"] == 2
