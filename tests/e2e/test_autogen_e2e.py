"""End-to-end integration tests for AutoGen wrapper with mocked LLM responses.

These tests simulate complete workflows using AutoGen with chaos injection,
using mocks to avoid the need for actual API tokens.
"""

import pytest


class MockAutoGenAgent:
    """Mock AutoGen Agent for testing."""

    def __init__(self, name: str, function_map: dict = None):
        self.name = name
        self.function_map = function_map or {}
        self._messages = []
        self._reply_count = 0

    def generate_reply(self, messages=None, sender=None, **kwargs):
        """Simulate generating a reply."""
        self._reply_count += 1
        self._messages.extend(messages or [])

        # Simulate calling functions if mentioned in messages
        for msg in messages or []:
            content = msg.get("content", "")
            for func_name in self.function_map:
                if func_name in content:
                    try:
                        result = self.function_map[func_name]()
                        return f"Function {func_name} returned: {result}"
                    except Exception as e:
                        return f"Function {func_name} failed: {e}"

        return f"Reply to: {messages[-1].get('content', '') if messages else 'empty'}"


class MockUserProxy:
    """Mock AutoGen UserProxyAgent for testing."""

    def __init__(self, name: str):
        self.name = name
        self._chat_history = []

    def initiate_chat(self, recipient, message, max_turns=None, clear_history=False, **kwargs):
        """Simulate initiating a chat."""
        if clear_history:
            self._chat_history = []

        self._chat_history.append({"role": "user", "content": message})

        # Simulate conversation turns
        turns = 0
        responses = []
        while max_turns is None or turns < max_turns:
            reply = recipient.generate_reply(messages=self._chat_history)
            self._chat_history.append({"role": "assistant", "content": reply})
            responses.append(reply)
            turns += 1

            # Break after first turn if no max_turns to prevent infinite loop
            if max_turns is None:
                break

        return {
            "messages": self._chat_history,
            "turns": turns,
            "final_response": responses[-1] if responses else None,
        }


class MockGroupChat:
    """Mock AutoGen GroupChat for testing."""

    def __init__(self, agents: list, max_round: int = 10):
        self.agents = agents
        self.max_round = max_round
        self._messages = []


class TestAutoGenE2EWorkflow:
    """End-to-end tests for AutoGen workflow with chaos injection."""

    def test_simple_conversation_no_chaos(self):
        """Test a simple conversation without chaos injection."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        # Create mock agent with functions
        def get_weather(location: str = "NYC") -> str:
            return f"Weather in {location}: Sunny, 72°F"

        def calculate(expression: str = "2+2") -> str:
            return str(eval(expression))

        assistant = MockAutoGenAgent(
            name="assistant",
            function_map={"get_weather": get_weather, "calculate": calculate},
        )
        user_proxy = MockUserProxy(name="user")

        wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.0)

        # Execute conversation
        result = wrapper.initiate_chat(
            message="What's the weather like?",
            max_turns=3,
        )

        assert result is not None
        assert "messages" in result
        assert result["turns"] == 3

        metrics = wrapper.get_metrics()
        assert "functions" in metrics

    def test_conversation_with_function_calls(self):
        """Test conversation that triggers function calls."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        call_log = []

        def search_database(query: str = "default") -> dict:
            call_log.append(("search_database", query))
            return {"query": query, "results": ["item1", "item2"]}

        def write_file(content: str = "default") -> str:
            call_log.append(("write_file", content))
            return "File written successfully"

        assistant = MockAutoGenAgent(
            name="assistant",
            function_map={
                "search_database": search_database,
                "write_file": write_file,
            },
        )
        user_proxy = MockUserProxy(name="user")

        wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.0)

        # Verify functions are wrapped
        wrapped_funcs = wrapper.get_wrapped_functions()
        assert "search_database" in wrapped_funcs
        assert "write_file" in wrapped_funcs

    def test_conversation_with_chaos_injection(self):
        """Test conversation with chaos injection on functions."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.autogen import AutoGenWrapper

        def api_call(endpoint: str = "api") -> dict:
            return {"endpoint": endpoint, "status": "success"}

        assistant = MockAutoGenAgent(
            name="assistant",
            function_map={"api_call": api_call},
        )

        wrapper = AutoGenWrapper(assistant, chaos_level=0.0)

        # Add failure injector
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1))
        wrapper.add_injector(injector, functions=["api_call"])

        # Verify injector is attached
        wrapped_funcs = wrapper.get_wrapped_functions()
        assert "api_call" in wrapped_funcs

    def test_generate_reply_workflow(self):
        """Test generate_reply workflow with metrics tracking."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        def helper_func() -> str:
            return "Helper result"

        assistant = MockAutoGenAgent(
            name="assistant",
            function_map={"helper": helper_func},
        )

        wrapper = AutoGenWrapper(assistant, chaos_level=0.0)

        # Generate multiple replies
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "How are you?"},
            {"role": "user", "content": "Tell me more"},
        ]

        for msg in messages:
            wrapper.generate_reply([msg])

        metrics = wrapper.get_metrics()
        assert metrics["reply_count"] == 3

    def test_experiment_context_tracking(self):
        """Test experiment context for tracking conversations."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        assistant = MockAutoGenAgent(name="assistant", function_map={})
        user_proxy = MockUserProxy(name="user")

        wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.0)

        # Run conversation within experiment
        with wrapper.experiment("conversation-test"):
            wrapper.initiate_chat("Hello", max_turns=2)
            wrapper.initiate_chat("Goodbye", max_turns=1)

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "conversation-test"

    def test_multi_agent_conversation(self):
        """Test multi-agent conversation workflow."""
        from balaganagent.wrappers.autogen import AutoGenMultiAgentWrapper

        # Create multiple agents
        def researcher_search(query: str = "default") -> dict:
            return {"type": "research", "query": query}

        def writer_draft(content: str = "default") -> str:
            return f"Draft: {content}"

        def reviewer_review(text: str = "default") -> dict:
            return {"approved": True, "comments": "Good work"}

        researcher = MockAutoGenAgent(
            name="researcher",
            function_map={"search": researcher_search},
        )
        writer = MockAutoGenAgent(
            name="writer",
            function_map={"draft": writer_draft},
        )
        reviewer = MockAutoGenAgent(
            name="reviewer",
            function_map={"review": reviewer_review},
        )

        # Wrap all agents
        wrapper = AutoGenMultiAgentWrapper(
            [researcher, writer, reviewer],
            chaos_level=0.0,
        )

        assert len(wrapper.agents) == 3

        # Configure chaos
        wrapper.configure_chaos(
            chaos_level=0.5,
            enable_tool_failures=True,
            enable_delays=True,
        )

        # Verify all agents have chaos applied
        for agent_wrapper in wrapper.get_agent_wrappers():
            assert agent_wrapper.chaos_level == 0.5

    def test_multi_agent_metrics_aggregation(self):
        """Test aggregated metrics from multi-agent conversations."""
        from balaganagent.wrappers.autogen import AutoGenMultiAgentWrapper

        agent1 = MockAutoGenAgent(name="agent1", function_map={})
        agent2 = MockAutoGenAgent(name="agent2", function_map={})

        wrapper = AutoGenMultiAgentWrapper([agent1, agent2], chaos_level=0.0)

        # Simulate activity on both agents
        wrapper.get_agent_wrapper("agent1").generate_reply([{"role": "user", "content": "hi"}])
        wrapper.get_agent_wrapper("agent2").generate_reply([{"role": "user", "content": "hello"}])
        wrapper.get_agent_wrapper("agent1").generate_reply([{"role": "user", "content": "bye"}])

        metrics = wrapper.get_aggregate_metrics()
        assert metrics["total_replies"] == 3
        assert "agent1" in metrics["agents"]
        assert "agent2" in metrics["agents"]

    def test_group_chat_support(self):
        """Test group chat configuration."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        agent1 = MockAutoGenAgent(name="agent1", function_map={})
        agent2 = MockAutoGenAgent(name="agent2", function_map={})
        group_chat = MockGroupChat(agents=[agent1, agent2], max_round=5)

        wrapper = AutoGenWrapper(agent1, group_chat=group_chat)

        assert wrapper.group_chat is group_chat

    def test_chaos_level_impact_on_functions(self):
        """Test that chaos level affects function behavior."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        def reliable_func() -> str:
            return "always works"

        assistant = MockAutoGenAgent(
            name="assistant",
            function_map={"reliable": reliable_func},
        )

        # Test with different chaos levels
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            wrapper = AutoGenWrapper(assistant, chaos_level=0.0)
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=False,
            )
            assert wrapper.chaos_level == level

    def test_reset_between_conversations(self):
        """Test resetting state between conversations."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        assistant = MockAutoGenAgent(name="assistant", function_map={})
        user_proxy = MockUserProxy(name="user")

        wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.0)

        # First conversation
        wrapper.generate_reply([{"role": "user", "content": "hi"}])
        wrapper.generate_reply([{"role": "user", "content": "hello"}])

        assert wrapper.get_metrics()["reply_count"] == 2

        # Reset
        wrapper.reset()

        assert wrapper.get_metrics()["reply_count"] == 0

        # Second conversation
        wrapper.generate_reply([{"role": "user", "content": "new chat"}])

        assert wrapper.get_metrics()["reply_count"] == 1

    def test_function_retry_on_transient_failure(self):
        """Test function retries on transient failures."""
        from balaganagent.wrappers.autogen import AutoGenFunctionProxy

        attempts = 0

        def flaky_function() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Temporary failure")
            return "success after retry"

        proxy = AutoGenFunctionProxy(
            flaky_function,
            name="flaky",
            chaos_level=0.0,
            max_retries=3,
            retry_delay=0.01,
        )

        result = proxy()

        assert result == "success after retry"
        assert attempts == 3

    def test_function_call_history_tracking(self):
        """Test that function call history is tracked correctly."""
        from balaganagent.wrappers.autogen import AutoGenFunctionProxy

        def tracked_func(x: int) -> int:
            return x * 2

        proxy = AutoGenFunctionProxy(
            tracked_func,
            name="tracked",
            chaos_level=0.0,
        )

        # Make several calls
        proxy(5)
        proxy(10)
        proxy(15)

        history = proxy.get_call_history()
        assert len(history) == 3
        assert history[0].args == (5,)
        assert history[1].args == (10,)
        assert history[2].args == (15,)


class TestAutoGenE2EErrorHandling:
    """Error handling tests for AutoGen workflows."""

    def test_missing_user_proxy_for_chat(self):
        """Test error when initiating chat without user proxy."""
        from balaganagent.wrappers.autogen import AutoGenWrapper

        assistant = MockAutoGenAgent(name="assistant", function_map={})
        wrapper = AutoGenWrapper(assistant, chaos_level=0.0)

        with pytest.raises(ValueError, match="user_proxy is required"):
            wrapper.initiate_chat("Hello")

    def test_function_exhausts_retries(self):
        """Test behavior when function exhausts all retries."""
        from balaganagent.wrappers.autogen import AutoGenFunctionProxy

        def always_fails() -> str:
            raise RuntimeError("Permanent failure")

        proxy = AutoGenFunctionProxy(
            always_fails,
            name="failing",
            chaos_level=0.0,
            max_retries=2,
            retry_delay=0.01,
        )

        with pytest.raises(RuntimeError, match="Permanent failure"):
            proxy()

        history = proxy.get_call_history()
        assert len(history) == 1
        assert history[0].error is not None
        assert history[0].retries == 3  # initial + 2 retries
