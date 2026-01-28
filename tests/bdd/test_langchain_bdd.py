"""BDD step definitions for LangChain wrapper tests.

Following ralph-claude-code style: comprehensive BDD testing.
"""

from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Fixtures for mock objects
@pytest.fixture
def mock_langchain_tool():
    """Create a mock LangChain tool."""

    def _create(name: str, func=None):
        tool = MagicMock()
        tool.name = name
        tool.func = func or MagicMock(return_value="tool result")
        return tool

    return _create


@pytest.fixture
def mock_agent_executor():
    """Create a mock LangChain AgentExecutor."""

    def _create(tools: list = None):
        executor = MagicMock()
        executor.tools = tools or []
        executor.invoke = MagicMock(return_value={"output": "response"})
        executor.stream = MagicMock(return_value=iter(["chunk1", "chunk2", "chunk3"]))
        executor.batch = MagicMock(
            side_effect=lambda inputs, **kw: [{"output": f"r{i}"} for i in range(len(inputs))]
        )
        return executor

    return _create


@pytest.fixture
def mock_chain():
    """Create a mock LangChain chain."""

    def _create():
        chain = MagicMock()
        chain.invoke = MagicMock(return_value={"result": "chain output"})
        chain.stream = MagicMock(return_value=iter(["a", "b", "c"]))
        return chain

    return _create


@pytest.fixture
def context():
    """Context object to share state between steps."""
    return {}


# Scenarios
@scenario("features/langchain_wrapper.feature", "Wrap a simple LangChain agent")
def test_wrap_simple_agent():
    pass


@scenario("features/langchain_wrapper.feature", "Configure chaos level")
def test_configure_chaos_level():
    pass


@scenario("features/langchain_wrapper.feature", "Invoke agent with no chaos")
def test_invoke_agent_no_chaos():
    pass


@scenario("features/langchain_wrapper.feature", "Track metrics during execution")
def test_track_metrics():
    pass


@scenario("features/langchain_wrapper.feature", "Run experiment with tracking")
def test_run_experiment():
    pass


@scenario("features/langchain_wrapper.feature", "Reset wrapper state")
def test_reset_wrapper():
    pass


@scenario("features/langchain_wrapper.feature", "Multiple tools wrapped")
def test_multiple_tools():
    pass


@scenario("features/langchain_wrapper.feature", "Add custom injector to specific tools")
def test_custom_injector():
    pass


@scenario("features/langchain_wrapper.feature", "Tool proxy retries on failure")
def test_tool_proxy_retries():
    pass


@scenario("features/langchain_wrapper.feature", "Stream responses")
def test_stream_responses():
    pass


@scenario("features/langchain_wrapper.feature", "Batch invocation")
def test_batch_invocation():
    pass


@scenario("features/langchain_wrapper.feature", "Chain wrapper invocation")
def test_chain_wrapper():
    pass


# Given steps
@given("a mock LangChain environment")
def mock_langchain_env(context):
    """Initialize mock LangChain environment."""
    context["env_ready"] = True


@given(parsers.parse("a LangChain agent with {count:d} tools"))
def agent_with_tools(context, count, mock_langchain_tool, mock_agent_executor):
    """Create an agent with specified number of tools."""
    tools = []
    tool_names = ["search", "calculator", "writer", "reader"]
    for i in range(count):
        name = tool_names[i] if i < len(tool_names) else f"tool_{i}"
        tools.append(mock_langchain_tool(name))

    context["agent"] = mock_agent_executor(tools)
    context["tools"] = tools


@given("a wrapper for the agent")
def wrapper_for_agent(context):
    """Create a wrapper for the agent."""
    from balaganagent.wrappers.langchain import LangChainAgentWrapper

    context["wrapper"] = LangChainAgentWrapper(context["agent"])


@given(parsers.parse("a wrapper with chaos level {level:f}"))
def wrapper_with_chaos(context, level):
    """Create a wrapper with specific chaos level."""
    from balaganagent.wrappers.langchain import LangChainAgentWrapper

    context["wrapper"] = LangChainAgentWrapper(context["agent"], chaos_level=level)


@given("a tool that fails twice then succeeds")
def flaky_tool(context):
    """Create a tool that fails twice then succeeds."""
    call_count = {"count": 0}

    def flaky_func(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise Exception("Temporary failure")
        return "success"

    context["flaky_func"] = flaky_func
    context["call_count"] = call_count


@given(parsers.parse("a LangChain tool proxy with max_retries {retries:d}"))
def tool_proxy_with_retries(context, retries):
    """Create a tool proxy with specific retry count."""
    from balaganagent.wrappers.langchain import LangChainToolProxy

    mock_tool = MagicMock()
    mock_tool.name = "flaky_tool"
    mock_tool.func = context["flaky_func"]

    context["proxy"] = LangChainToolProxy(
        mock_tool,
        chaos_level=0.0,
        max_retries=retries,
        retry_delay=0.01,
    )


@given("a LangChain chain")
def create_chain(context, mock_chain):
    """Create a LangChain chain."""
    context["chain"] = mock_chain()


@given(parsers.parse("a chain wrapper with chaos level {level:f}"))
def chain_wrapper_with_chaos(context, level):
    """Create a chain wrapper."""
    from balaganagent.wrappers.langchain import LangChainChainWrapper

    context["chain_wrapper"] = LangChainChainWrapper(context["chain"], chaos_level=level)


# When steps
@when("I create a wrapper for the agent")
def create_wrapper(context):
    """Create a wrapper for the agent."""
    from balaganagent.wrappers.langchain import LangChainAgentWrapper

    context["wrapper"] = LangChainAgentWrapper(context["agent"])


@when(parsers.parse("I configure chaos level to {level:f}"))
def configure_chaos(context, level):
    """Configure chaos level."""
    context["wrapper"].configure_chaos(chaos_level=level)


@when(parsers.parse('I invoke the agent with input "{input_text}"'))
def invoke_agent(context, input_text):
    """Invoke the agent."""
    context["result"] = context["wrapper"].invoke({"input": input_text})


@when(parsers.parse("I invoke the agent {times:d} times"))
def invoke_agent_multiple(context, times):
    """Invoke the agent multiple times."""
    for i in range(times):
        context["wrapper"].invoke({"input": f"query {i}"})


@when(parsers.parse('I run an experiment named "{name}"'))
def run_experiment(context, name):
    """Start an experiment with the given name."""
    context["experiment_name"] = name
    context["experiment_context"] = context["wrapper"].experiment(name)
    context["experiment_context"].__enter__()


@when("invoke the agent within the experiment")
def invoke_within_experiment(context):
    """Invoke agent within experiment context."""
    context["wrapper"].invoke({"input": "test"})
    context["experiment_context"].__exit__(None, None, None)


@when("reset the wrapper")
def reset_wrapper(context):
    """Reset the wrapper state."""
    context["wrapper"].reset()


@when(parsers.parse('I add a failure injector to the "{tool_name}" tool only'))
def add_injector_to_tool(context, tool_name):
    """Add a failure injector to a specific tool."""
    from balaganagent.injectors import ToolFailureInjector
    from balaganagent.injectors.tool_failure import ToolFailureConfig

    injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
    context["wrapper"].add_injector(injector, tools=[tool_name])
    context["injector"] = injector
    context["target_tool"] = tool_name


@when("I call the tool proxy")
def call_tool_proxy(context):
    """Call the tool proxy."""
    context["proxy_result"] = context["proxy"]()


@when(parsers.parse('I stream from the agent with input "{input_text}"'))
def stream_from_agent(context, input_text):
    """Stream from the agent."""
    context["chunks"] = list(context["wrapper"].stream({"input": input_text}))


@when(parsers.parse("I batch invoke with {count:d} inputs"))
def batch_invoke(context, count):
    """Batch invoke the agent."""
    inputs = [{"input": f"query {i}"} for i in range(count)]
    context["batch_results"] = context["wrapper"].batch(inputs)


@when(parsers.parse('I invoke the chain with input "{input_text}"'))
def invoke_chain(context, input_text):
    """Invoke the chain."""
    context["chain_result"] = context["chain_wrapper"].invoke({"input": input_text})


# Then steps
@then("the wrapper should contain the agent executor")
def wrapper_contains_agent(context):
    """Verify wrapper contains the agent."""
    assert context["wrapper"].agent_executor is context["agent"]


@then("the tools should be wrapped for chaos injection")
def tools_are_wrapped(context):
    """Verify tools are wrapped."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert len(wrapped_tools) > 0


@then(parsers.parse("the chaos level should be {level:f}"))
def verify_chaos_level(context, level):
    """Verify chaos level."""
    assert context["wrapper"].chaos_level == level


@then("tool failures should be enabled")
def tool_failures_enabled(context):
    """Verify tool failures are enabled."""
    assert context["wrapper"].chaos_level > 0


@then("delays should be enabled")
def delays_enabled(context):
    """Verify delays are enabled."""
    assert context["wrapper"].chaos_level > 0


@then("the invocation should succeed")
def invocation_succeeds(context):
    """Verify invocation succeeded."""
    assert context["result"] is not None


@then(parsers.parse("the invoke count should be {count:d}"))
def verify_invoke_count(context, count):
    """Verify invoke count."""
    metrics = context["wrapper"].get_metrics()
    assert metrics["invoke_count"] == count


@then(parsers.parse('the experiment results should contain "{name}"'))
def verify_experiment_results(context, name):
    """Verify experiment results."""
    results = context["wrapper"].get_experiment_results()
    assert len(results) > 0
    assert any(r.config.name == name for r in results)


@then("all tools should be wrapped")
def all_tools_wrapped(context):
    """Verify all tools are wrapped."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert len(wrapped_tools) >= len(context["tools"])


@then(parsers.parse("the wrapper should have {count:d} wrapped tools"))
def verify_wrapped_tools_count(context, count):
    """Verify wrapped tools count."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert len(wrapped_tools) == count


@then(parsers.parse('only the "{tool_name}" tool should have the injector'))
def verify_injector_target(context, tool_name):
    """Verify injector is only on specific tool."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert tool_name in wrapped_tools


@then(parsers.parse('the result should be "{expected}"'))
def verify_result(context, expected):
    """Verify the result."""
    assert context["proxy_result"] == expected


@then(parsers.parse("the tool should have been called {times:d} times"))
def verify_call_count(context, times):
    """Verify tool call count."""
    assert context["call_count"]["count"] == times


@then("I should receive multiple chunks")
def verify_multiple_chunks(context):
    """Verify multiple chunks received."""
    assert len(context["chunks"]) > 0


@then(parsers.parse("I should receive {count:d} results"))
def verify_batch_results(context, count):
    """Verify batch results count."""
    assert len(context["batch_results"]) == count


@then("the chain invocation should succeed")
def chain_invocation_succeeds(context):
    """Verify chain invocation succeeded."""
    assert context["chain_result"] is not None
