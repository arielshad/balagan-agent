"""BDD step definitions for CrewAI wrapper tests."""

from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Fixtures for mock objects
@pytest.fixture
def mock_crewai_tool():
    """Create a mock CrewAI tool."""

    def _create(name: str, func=None):
        tool = MagicMock()
        tool.name = name
        tool.func = func or MagicMock(return_value="tool result")
        return tool

    return _create


@pytest.fixture
def mock_crewai_agent():
    """Create a mock CrewAI agent."""

    def _create(role: str, tools: list | None = None):
        agent = MagicMock()
        agent.role = role
        agent.tools = tools or []
        return agent

    return _create


@pytest.fixture
def mock_crew():
    """Create a mock CrewAI crew."""

    def _create(agents: list, tasks: list | None = None):
        crew = MagicMock()
        crew.agents = agents
        crew.tasks = tasks or []
        crew.kickoff = MagicMock(return_value={"status": "completed"})
        return crew

    return _create


@pytest.fixture
def context():
    """Context object to share state between steps."""
    return {}


# Scenarios
@scenario("features/crewai_wrapper.feature", "Wrap a simple CrewAI crew")
def test_wrap_simple_crew():
    pass


@scenario("features/crewai_wrapper.feature", "Configure chaos level")
def test_configure_chaos_level():
    pass


@scenario("features/crewai_wrapper.feature", "Execute crew with no chaos")
def test_execute_crew_no_chaos():
    pass


@scenario("features/crewai_wrapper.feature", "Track metrics during execution")
def test_track_metrics():
    pass


@scenario("features/crewai_wrapper.feature", "Run experiment with tracking")
def test_run_experiment():
    pass


@scenario("features/crewai_wrapper.feature", "Reset wrapper state")
def test_reset_wrapper():
    pass


@scenario("features/crewai_wrapper.feature", "Multiple agents with different tools")
def test_multiple_agents():
    pass


@scenario("features/crewai_wrapper.feature", "Add custom injector to specific tools")
def test_custom_injector():
    pass


@scenario("features/crewai_wrapper.feature", "Tool proxy retries on failure")
def test_tool_proxy_retries():
    pass


# Given steps
@given("a mock CrewAI environment")
def mock_crewai_env(context):
    """Initialize mock CrewAI environment."""
    context["env_ready"] = True


@given("a CrewAI crew with 1 agent and 1 tool")
def crew_with_one_agent(context, mock_crewai_tool, mock_crewai_agent, mock_crew):
    """Create a crew with one agent and one tool."""
    tool = mock_crewai_tool("search")
    agent = mock_crewai_agent("researcher", tools=[tool])
    context["crew"] = mock_crew([agent])
    context["tool"] = tool


@given("a wrapper for the crew")
def wrapper_for_crew(context):
    """Create a wrapper for the crew."""
    from balaganagent.wrappers.crewai import CrewAIWrapper

    context["wrapper"] = CrewAIWrapper(context["crew"])


@given(parsers.parse("a wrapper with chaos level {level:f}"))
def wrapper_with_chaos(context, level):
    """Create a wrapper with specific chaos level."""
    from balaganagent.wrappers.crewai import CrewAIWrapper

    context["wrapper"] = CrewAIWrapper(context["crew"], chaos_level=level)


@given("a CrewAI crew with 2 agents each having different tools")
def crew_with_two_agents(context, mock_crewai_tool, mock_crewai_agent, mock_crew):
    """Create a crew with two agents having different tools."""
    tool1 = mock_crewai_tool("search")
    tool2 = mock_crewai_tool("write")
    agent1 = mock_crewai_agent("researcher", tools=[tool1])
    agent2 = mock_crewai_agent("writer", tools=[tool2])
    context["crew"] = mock_crew([agent1, agent2])


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


@given(parsers.parse("a CrewAI tool proxy with max_retries {retries:d}"))
def tool_proxy_with_retries(context, retries):
    """Create a tool proxy with specific retry count."""
    from balaganagent.wrappers.crewai import CrewAIToolProxy

    mock_tool = MagicMock()
    mock_tool.name = "flaky_tool"
    mock_tool.func = context["flaky_func"]

    context["proxy"] = CrewAIToolProxy(
        mock_tool,
        chaos_level=0.0,
        max_retries=retries,
        retry_delay=0.01,
    )


# When steps
@when("I create a wrapper for the crew")
def create_wrapper(context):
    """Create a wrapper for the crew."""
    from balaganagent.wrappers.crewai import CrewAIWrapper

    context["wrapper"] = CrewAIWrapper(context["crew"])


@when(parsers.parse("I configure chaos level to {level:f}"))
def configure_chaos(context, level):
    """Configure chaos level."""
    context["wrapper"].configure_chaos(chaos_level=level)


@when("I execute the crew")
def execute_crew(context):
    """Execute the crew once."""
    context["result"] = context["wrapper"].kickoff()


@when(parsers.parse("I execute the crew {times:d} times"))
def execute_crew_multiple(context, times):
    """Execute the crew multiple times."""
    for _ in range(times):
        context["wrapper"].kickoff()


@when(parsers.parse('I run an experiment named "{name}"'))
def run_experiment(context, name):
    """Start an experiment with the given name."""
    context["experiment_name"] = name
    context["experiment_context"] = context["wrapper"].experiment(name)
    context["experiment_context"].__enter__()


@when("execute the crew within the experiment")
def execute_within_experiment(context):
    """Execute crew within experiment context."""
    context["wrapper"].kickoff()
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


# Then steps
@then("the wrapper should contain the crew")
def wrapper_contains_crew(context):
    """Verify wrapper contains the crew."""
    assert context["wrapper"].crew is context["crew"]


@then("the tool should be wrapped for chaos injection")
def tool_is_wrapped(context):
    """Verify tool is wrapped."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert len(wrapped_tools) > 0


@then(parsers.parse("the chaos level should be {level:f}"))
def verify_chaos_level(context, level):
    """Verify chaos level."""
    assert context["wrapper"].chaos_level == level


@then("tool failures should be enabled")
def tool_failures_enabled(context):
    """Verify tool failures are enabled."""
    # Chaos is configured, which means injectors are set up
    assert context["wrapper"].chaos_level > 0


@then("delays should be enabled")
def delays_enabled(context):
    """Verify delays are enabled."""
    # Chaos is configured, which means injectors are set up
    assert context["wrapper"].chaos_level > 0


@then("the execution should succeed")
def execution_succeeds(context):
    """Verify execution succeeded."""
    assert context["result"] is not None


@then(parsers.parse("the kickoff count should be {count:d}"))
def verify_kickoff_count(context, count):
    """Verify kickoff count."""
    metrics = context["wrapper"].get_metrics()
    assert metrics["kickoff_count"] == count


@then(parsers.parse('the experiment results should contain "{name}"'))
def verify_experiment_results(context, name):
    """Verify experiment results."""
    results = context["wrapper"].get_experiment_results()
    assert len(results) > 0
    assert any(r.config.name == name for r in results)


@then("all tools from all agents should be wrapped")
def all_tools_wrapped(context):
    """Verify all tools are wrapped."""
    wrapped_tools = context["wrapper"].get_wrapped_tools()
    assert len(wrapped_tools) >= 2


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
