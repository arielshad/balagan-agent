"""End-to-end integration tests for CrewAI wrapper with mocked LLM responses.

These tests simulate complete workflows using CrewAI with chaos injection,
using mocks to avoid the need for actual API tokens.
"""

from unittest.mock import MagicMock

import pytest

try:
    import crewai  # noqa: F401
except ImportError:
    pytest.skip("crewai not installed", allow_module_level=True)


class MockLLMResponse:
    """Mock LLM response for testing."""

    def __init__(self, content: str):
        self.content = content
        self.choices = [MagicMock(message=MagicMock(content=content))]


class MockCrewAITool:
    """Mock CrewAI tool for testing."""

    def __init__(self, name: str, func):
        self.name = name
        self.func = func
        self.description = f"Mock tool: {name}"


class MockCrewAIAgent:
    """Mock CrewAI Agent for testing."""

    def __init__(self, role: str, goal: str, tools: list | None = None):
        self.role = role
        self.goal = goal
        self.tools = tools or []
        self.backstory = f"I am a {role}"
        self.verbose = False


class MockCrewAITask:
    """Mock CrewAI Task for testing."""

    def __init__(self, description: str, agent: MockCrewAIAgent):
        self.description = description
        self.agent = agent
        self.expected_output = "Completed task output"


class MockCrew:
    """Mock CrewAI Crew for testing."""

    def __init__(self, agents: list, tasks: list):
        self.agents = agents
        self.tasks = tasks
        self._kickoff_count = 0

    def kickoff(self, inputs: dict | None = None):
        """Simulate crew execution."""
        self._kickoff_count += 1
        results = []

        for task in self.tasks:
            # Simulate agent working on task
            for tool in task.agent.tools:
                if hasattr(tool, "func"):
                    try:
                        result = tool.func(f"input for {tool.name}")
                        results.append(result)
                    except Exception as e:
                        results.append(f"Tool failed: {e}")

        return {
            "inputs": inputs,
            "results": results,
            "tasks_completed": len(self.tasks),
        }


class TestCrewAIE2EWorkflow:
    """End-to-end tests for CrewAI workflow with chaos injection."""

    def test_simple_crew_workflow_no_chaos(self):
        """Test a simple crew workflow without chaos injection."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        # Create mock tools
        def search_tool(query: str) -> dict:
            return {"query": query, "results": ["result1", "result2"]}

        def writer_tool(content: str) -> str:
            return f"Written: {content}"

        mock_search = MockCrewAITool("search", search_tool)
        mock_writer = MockCrewAITool("writer", writer_tool)

        # Create mock agents
        researcher = MockCrewAIAgent(
            role="Researcher",
            goal="Research topics thoroughly",
            tools=[mock_search],
        )
        writer = MockCrewAIAgent(
            role="Writer",
            goal="Write compelling content",
            tools=[mock_writer],
        )

        # Create mock tasks
        research_task = MockCrewAITask("Research the topic", researcher)
        write_task = MockCrewAITask("Write about findings", writer)

        # Create and wrap crew
        crew = MockCrew(agents=[researcher, writer], tasks=[research_task, write_task])
        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Execute
        result = wrapper.kickoff(inputs={"topic": "AI agents"})

        # Verify
        assert result is not None
        assert result["tasks_completed"] == 2
        assert len(result["results"]) == 2

        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 1

    def test_crew_workflow_with_tool_failure_injection(self):
        """Test crew workflow with tool failure chaos injection."""
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig
        from balaganagent.wrappers.crewai import CrewAIWrapper

        call_count = 0

        def unreliable_tool(query: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"query": query, "data": "some data"}

        mock_tool = MockCrewAITool("unreliable_search", unreliable_tool)
        agent = MockCrewAIAgent(
            role="Researcher",
            goal="Research",
            tools=[mock_tool],
        )
        task = MockCrewAITask("Research", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Add a deterministic failure injector (always fails)
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1))
        wrapper.add_injector(injector, tools=["unreliable_search"])

        # The wrapped tool should have the injector
        wrapped_tools = wrapper.get_wrapped_tools()
        assert "unreliable_search" in wrapped_tools

    def test_crew_workflow_with_delays(self):
        """Test crew workflow with artificial delays."""

        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig
        from balaganagent.wrappers.crewai import CrewAIWrapper

        def fast_tool(x: str) -> str:
            return f"fast: {x}"

        mock_tool = MockCrewAITool("fast_tool", fast_tool)
        agent = MockCrewAIAgent(role="Worker", goal="Work fast", tools=[mock_tool])
        task = MockCrewAITask("Do work", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Add delay injector with small fixed delay (in milliseconds)
        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=10, max_delay_ms=10))
        wrapper.add_injector(injector, tools=["fast_tool"])

        wrapped_tools = wrapper.get_wrapped_tools()
        assert "fast_tool" in wrapped_tools

    def test_crew_workflow_with_experiment_tracking(self):
        """Test crew workflow within an experiment context."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        def simple_tool(x: str) -> str:
            return x

        mock_tool = MockCrewAITool("simple", simple_tool)
        agent = MockCrewAIAgent(role="Worker", goal="Work", tools=[mock_tool])
        task = MockCrewAITask("Task", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Run within experiment
        with wrapper.experiment("test-experiment"):
            wrapper.kickoff()
            wrapper.kickoff()

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-experiment"

    def test_multi_agent_crew_workflow(self):
        """Test complex crew with multiple agents and tools."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        # Create multiple tools
        def search_web(query: str) -> dict:
            return {"source": "web", "query": query, "results": ["web_result1"]}

        def search_db(query: str) -> dict:
            return {"source": "database", "query": query, "results": ["db_result1"]}

        def analyze(data: str) -> dict:
            return {"analysis": f"Analyzed: {data}"}

        def write_report(content: str) -> str:
            return f"Report: {content}"

        # Create agents with different tools
        researcher = MockCrewAIAgent(
            role="Researcher",
            goal="Research comprehensively",
            tools=[
                MockCrewAITool("search_web", search_web),
                MockCrewAITool("search_db", search_db),
            ],
        )
        analyst = MockCrewAIAgent(
            role="Analyst",
            goal="Analyze findings",
            tools=[MockCrewAITool("analyze", analyze)],
        )
        writer = MockCrewAIAgent(
            role="Writer",
            goal="Write reports",
            tools=[MockCrewAITool("write_report", write_report)],
        )

        # Create tasks
        tasks = [
            MockCrewAITask("Research the topic", researcher),
            MockCrewAITask("Analyze findings", analyst),
            MockCrewAITask("Write the report", writer),
        ]

        crew = MockCrew(agents=[researcher, analyst, writer], tasks=tasks)
        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Verify all tools are wrapped
        wrapped_tools = wrapper.get_wrapped_tools()
        assert len(wrapped_tools) == 4
        assert "search_web" in wrapped_tools
        assert "search_db" in wrapped_tools
        assert "analyze" in wrapped_tools
        assert "write_report" in wrapped_tools

        # Execute workflow
        result = wrapper.kickoff(inputs={"topic": "AI Safety"})
        assert result["tasks_completed"] == 3

    def test_chaos_level_configuration(self):
        """Test configuring different chaos levels."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        def simple_tool(x: str) -> str:
            return x

        mock_tool = MockCrewAITool("tool", simple_tool)
        agent = MockCrewAIAgent(role="Worker", goal="Work", tools=[mock_tool])
        task = MockCrewAITask("Task", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew)

        # Test various chaos levels
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=True,
                enable_hallucinations=False,
                enable_context_corruption=False,
                enable_budget_exhaustion=False,
            )
            assert wrapper.chaos_level == level

    def test_metrics_collection_e2e(self):
        """Test comprehensive metrics collection during workflow."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        call_counts = {"search": 0, "process": 0}

        def search_tool(q: str) -> dict:
            call_counts["search"] += 1
            return {"query": q}

        def process_tool(data: str) -> dict:
            call_counts["process"] += 1
            return {"processed": data}

        search = MockCrewAITool("search", search_tool)
        processor = MockCrewAITool("process", process_tool)

        agent = MockCrewAIAgent(role="Worker", goal="Work", tools=[search, processor])
        task = MockCrewAITask("Task", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # Execute multiple times
        for _ in range(3):
            wrapper.kickoff()

        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 3

    def test_reset_workflow_state(self):
        """Test resetting workflow state between experiments."""
        from balaganagent.wrappers.crewai import CrewAIWrapper

        def tool_func(x: str) -> str:
            return x

        mock_tool = MockCrewAITool("tool", tool_func)
        agent = MockCrewAIAgent(role="Worker", goal="Work", tools=[mock_tool])
        task = MockCrewAITask("Task", agent)
        crew = MockCrew(agents=[agent], tasks=[task])

        wrapper = CrewAIWrapper(crew, chaos_level=0.0)

        # First experiment
        with wrapper.experiment("exp1"):
            wrapper.kickoff()

        assert wrapper.get_metrics()["kickoff_count"] == 1

        # Reset
        wrapper.reset()

        # After reset, metrics should be cleared
        assert wrapper.get_metrics()["kickoff_count"] == 0

        # Second experiment
        with wrapper.experiment("exp2"):
            wrapper.kickoff()
            wrapper.kickoff()

        assert wrapper.get_metrics()["kickoff_count"] == 2
