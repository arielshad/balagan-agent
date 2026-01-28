"""BDD step definitions for AutoGen wrapper tests."""

from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Fixtures for mock objects
@pytest.fixture
def mock_autogen_agent():
    """Create a mock AutoGen agent."""
    def _create(name: str, function_map: dict = None):
        agent = MagicMock()
        agent.name = name
        agent.function_map = function_map or {}
        agent.generate_reply = MagicMock(return_value="Agent reply")
        return agent
    return _create


@pytest.fixture
def mock_user_proxy():
    """Create a mock user proxy agent."""
    def _create(name: str = "user"):
        proxy = MagicMock()
        proxy.name = name
        proxy.initiate_chat = MagicMock(return_value={"messages": [], "status": "completed"})
        return proxy
    return _create


@pytest.fixture
def context():
    """Context object to share state between steps."""
    return {}


# Scenarios
@scenario("features/autogen_wrapper.feature", "Wrap a simple AutoGen agent")
def test_wrap_simple_agent():
    pass


@scenario("features/autogen_wrapper.feature", "Configure chaos level for AutoGen agent")
def test_configure_chaos():
    pass


@scenario("features/autogen_wrapper.feature", "Generate reply through wrapper")
def test_generate_reply():
    pass


@scenario("features/autogen_wrapper.feature", "Initiate chat with user proxy")
def test_initiate_chat():
    pass


@scenario("features/autogen_wrapper.feature", "Track metrics during conversation")
def test_track_metrics():
    pass


@scenario("features/autogen_wrapper.feature", "Run experiment with AutoGen agent")
def test_run_experiment():
    pass


@scenario("features/autogen_wrapper.feature", "Reset AutoGen wrapper state")
def test_reset_wrapper():
    pass


@scenario("features/autogen_wrapper.feature", "Multi-agent wrapper creation")
def test_multi_agent_wrapper():
    pass


@scenario("features/autogen_wrapper.feature", "Multi-agent chaos propagation")
def test_multi_balagan_agent():
    pass


@scenario("features/autogen_wrapper.feature", "Aggregate metrics from multi-agent setup")
def test_multi_agent_metrics():
    pass


@scenario("features/autogen_wrapper.feature", "Function proxy retries on transient failure")
def test_function_proxy_retries():
    pass


@scenario("features/autogen_wrapper.feature", "Missing user proxy raises error")
def test_missing_user_proxy():
    pass


# Given steps
@given("a mock AutoGen environment")
def mock_autogen_env(context):
    """Initialize mock AutoGen environment."""
    context["env_ready"] = True


@given(parsers.parse("an AutoGen agent with function_map containing {count:d} functions"))
@given(parsers.parse("an AutoGen agent with function_map containing {count:d} function"))
def agent_with_functions(context, count, mock_autogen_agent):
    """Create an agent with specified number of functions."""
    function_map = {}
    for i in range(count):
        func_name = f"function_{i}"
        function_map[func_name] = MagicMock(return_value=f"result_{i}")

    context["agent"] = mock_autogen_agent("assistant", function_map=function_map)


@given("a wrapper for the agent")
def wrapper_for_agent(context):
    """Create a wrapper for the agent."""
    from balaganagent.wrappers.autogen import AutoGenWrapper
    context["wrapper"] = AutoGenWrapper(context["agent"])


@given(parsers.parse("a wrapper with chaos level {level:f}"))
def wrapper_with_chaos(context, level):
    """Create a wrapper with specific chaos level."""
    from balaganagent.wrappers.autogen import AutoGenWrapper
    context["wrapper"] = AutoGenWrapper(context["agent"], chaos_level=level)


@given("a user proxy agent")
def create_user_proxy(context, mock_user_proxy):
    """Create a user proxy agent."""
    context["user_proxy"] = mock_user_proxy()


@given(parsers.parse("a wrapper with both agents and chaos level {level:f}"))
def wrapper_with_both_agents(context, level):
    """Create a wrapper with both assistant and user proxy."""
    from balaganagent.wrappers.autogen import AutoGenWrapper
    context["wrapper"] = AutoGenWrapper(
        context["agent"],
        user_proxy=context["user_proxy"],
        chaos_level=level,
    )


@given(parsers.parse("{count:d} AutoGen agents each with different functions"))
def multiple_agents(context, count, mock_autogen_agent):
    """Create multiple agents with different functions."""
    agents = []
    for i in range(count):
        func_map = {f"agent{i}_func": MagicMock(return_value=f"result_{i}")}
        agent = mock_autogen_agent(f"agent{i}", function_map=func_map)
        agents.append(agent)
    context["agents"] = agents


@given("a multi-agent wrapper")
def multi_agent_wrapper(context):
    """Create a multi-agent wrapper."""
    from balaganagent.wrappers.autogen import AutoGenMultiAgentWrapper
    context["multi_wrapper"] = AutoGenMultiAgentWrapper(context["agents"])


@given(parsers.parse("a multi-agent wrapper with chaos level {level:f}"))
def multi_agent_wrapper_with_chaos(context, level):
    """Create a multi-agent wrapper with specific chaos level."""
    from balaganagent.wrappers.autogen import AutoGenMultiAgentWrapper
    context["multi_wrapper"] = AutoGenMultiAgentWrapper(context["agents"], chaos_level=level)


@given("a function that fails twice then succeeds")
def flaky_function(context):
    """Create a function that fails twice then succeeds."""
    call_count = {"count": 0}

    def flaky_func(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise Exception("Temporary failure")
        return "success"

    context["flaky_func"] = flaky_func
    context["call_count"] = call_count


@given(parsers.parse("an AutoGen function proxy with max_retries {retries:d}"))
def function_proxy_with_retries(context, retries):
    """Create a function proxy with specific retry count."""
    from balaganagent.wrappers.autogen import AutoGenFunctionProxy

    context["proxy"] = AutoGenFunctionProxy(
        context["flaky_func"],
        name="flaky_function",
        chaos_level=0.0,
        max_retries=retries,
        retry_delay=0.01,
    )


@given("a wrapper without user proxy")
def wrapper_without_user_proxy(context):
    """Create a wrapper without user proxy."""
    from balaganagent.wrappers.autogen import AutoGenWrapper
    context["wrapper"] = AutoGenWrapper(context["agent"], chaos_level=0.0)


# When steps
@when("I create a wrapper for the agent")
def create_wrapper(context):
    """Create a wrapper for the agent."""
    from balaganagent.wrappers.autogen import AutoGenWrapper
    context["wrapper"] = AutoGenWrapper(context["agent"])


@when(parsers.parse("I configure chaos level to {level:f}"))
def configure_chaos(context, level):
    """Configure chaos level."""
    context["wrapper"].configure_chaos(chaos_level=level)


@when("I generate a reply with a user message")
def generate_reply(context):
    """Generate a reply."""
    context["reply"] = context["wrapper"].generate_reply(
        [{"role": "user", "content": "Hello"}]
    )


@when(parsers.parse('I initiate a chat with message "{message}"'))
def initiate_chat(context, message):
    """Initiate a chat."""
    context["chat_result"] = context["wrapper"].initiate_chat(message)


@when(parsers.parse("I generate {count:d} replies"))
def generate_multiple_replies(context, count):
    """Generate multiple replies."""
    for i in range(count):
        context["wrapper"].generate_reply([{"role": "user", "content": f"Message {i}"}])


@when(parsers.parse('I run an experiment named "{name}"'))
def run_experiment(context, name):
    """Start an experiment with the given name."""
    context["experiment_name"] = name
    context["experiment_context"] = context["wrapper"].experiment(name)
    context["experiment_context"].__enter__()


@when("generate replies within the experiment")
def generate_within_experiment(context):
    """Generate replies within experiment context."""
    context["wrapper"].generate_reply([{"role": "user", "content": "test"}])
    context["experiment_context"].__exit__(None, None, None)


@when("reset the wrapper")
def reset_wrapper(context):
    """Reset the wrapper state."""
    context["wrapper"].reset()


@when("I create a multi-agent wrapper")
def create_multi_agent_wrapper(context):
    """Create a multi-agent wrapper."""
    from balaganagent.wrappers.autogen import AutoGenMultiAgentWrapper
    context["multi_wrapper"] = AutoGenMultiAgentWrapper(context["agents"])


@when(parsers.parse("I configure multi-agent chaos level to {level:f}"))
def configure_multi_chaos(context, level):
    """Configure chaos level for multi-agent wrapper."""
    context["multi_wrapper"].configure_chaos(chaos_level=level)


@when(parsers.parse("each agent generates {count:d} replies"))
def each_agent_generates(context, count):
    """Each agent generates specified replies."""
    for agent_wrapper in context["multi_wrapper"].get_agent_wrappers():
        for _ in range(count):
            agent_wrapper.generate_reply([{"role": "user", "content": "test"}])


@when("I call the function proxy")
def call_function_proxy(context):
    """Call the function proxy."""
    context["proxy_result"] = context["proxy"]()


@when("I try to initiate chat")
def try_initiate_chat(context):
    """Try to initiate chat (expecting failure)."""
    try:
        context["wrapper"].initiate_chat("Hello")
        context["error"] = None
    except Exception as e:
        context["error"] = e


# Then steps
@then("the wrapper should contain the agent")
def wrapper_contains_agent(context):
    """Verify wrapper contains the agent."""
    assert context["wrapper"].agent is context["agent"]


@then("the functions should be wrapped for chaos injection")
def functions_wrapped(context):
    """Verify functions are wrapped."""
    wrapped_funcs = context["wrapper"].get_wrapped_functions()
    assert len(wrapped_funcs) > 0


@then(parsers.parse("the chaos level should be {level:f}"))
def verify_chaos_level(context, level):
    """Verify chaos level."""
    assert context["wrapper"].chaos_level == level


@then("function failures should be enabled")
def function_failures_enabled(context):
    """Verify function failures are enabled."""
    assert context["wrapper"].chaos_level > 0


@then("delays should be enabled")
def delays_enabled(context):
    """Verify delays are enabled."""
    assert context["wrapper"].chaos_level > 0


@then("the reply should be generated")
def reply_generated(context):
    """Verify reply was generated."""
    assert context["reply"] is not None


@then(parsers.parse("the reply count should be {count:d}"))
def verify_reply_count(context, count):
    """Verify reply count."""
    metrics = context["wrapper"].get_metrics()
    assert metrics["reply_count"] == count


@then("the chat should be initiated successfully")
def chat_initiated(context):
    """Verify chat was initiated."""
    assert context["chat_result"] is not None


@then(parsers.parse('the experiment results should contain "{name}"'))
def verify_experiment_results(context, name):
    """Verify experiment results."""
    results = context["wrapper"].get_experiment_results()
    assert len(results) > 0
    assert any(r.config.name == name for r in results)


@then("all agents should be wrapped")
def all_agents_wrapped(context):
    """Verify all agents are wrapped."""
    wrappers = context["multi_wrapper"].get_agent_wrappers()
    assert len(wrappers) == len(context["agents"])


@then(parsers.parse("the multi-agent wrapper should have {count:d} agents"))
def verify_multi_agent_count(context, count):
    """Verify multi-agent wrapper count."""
    assert len(context["multi_wrapper"].agents) == count


@then(parsers.parse("all agent wrappers should have chaos level {level:f}"))
def verify_all_chaos_levels(context, level):
    """Verify all agent wrappers have specified chaos level."""
    for wrapper in context["multi_wrapper"].get_agent_wrappers():
        assert wrapper.chaos_level == level


@then(parsers.parse("the total replies should be {count:d}"))
def verify_total_replies(context, count):
    """Verify total replies."""
    metrics = context["multi_wrapper"].get_aggregate_metrics()
    assert metrics["total_replies"] == count


@then(parsers.parse('the result should be "{expected}"'))
def verify_result(context, expected):
    """Verify the result."""
    assert context["proxy_result"] == expected


@then(parsers.parse("the function should have been called {times:d} times"))
def verify_call_count(context, times):
    """Verify function call count."""
    assert context["call_count"]["count"] == times


@then(parsers.parse('a ValueError should be raised with message "{message}"'))
def verify_value_error(context, message):
    """Verify ValueError was raised with message."""
    assert isinstance(context["error"], ValueError)
    assert message in str(context["error"])
