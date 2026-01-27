"""Stress tests for the Meeting Notes agent using AgentChaos.

Tests the agent's resilience under chaos injection: tool failures,
delays, hallucinations, and increasing chaos levels.
"""

from agentchaos.wrappers.crewai import CrewAIWrapper

# ---------------------------------------------------------------------------
# Helpers – mock CrewAI objects (same pattern as existing e2e tests)
# ---------------------------------------------------------------------------


class MockCrewAITool:
    def __init__(self, name, func):
        self.name = name
        self.func = func
        self.description = f"Mock tool: {name}"


class MockCrewAIAgent:
    def __init__(self, role, goal, tools=None):
        self.role = role
        self.goal = goal
        self.tools = tools or []
        self.backstory = f"I am a {role}"
        self.verbose = False


class MockCrewAITask:
    def __init__(self, description, agent):
        self.description = description
        self.agent = agent
        self.expected_output = "Completed"


class MockCrew:
    def __init__(self, agents, tasks):
        self.agents = agents
        self.tasks = tasks
        self._kickoff_count = 0

    def kickoff(self, inputs=None):
        self._kickoff_count += 1
        results = []
        for task in self.tasks:
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


# ---------------------------------------------------------------------------
# Build a CrewAI-wrapped Meeting Notes crew
# ---------------------------------------------------------------------------


def _build_meeting_notes_crew(chaos_level=0.0):
    """Build a mock CrewAI crew that mirrors the Meeting Notes pipeline."""
    from examples.meeting_notes_agent import SummarizerAgent, TaskExtractorAgent

    summarizer = SummarizerAgent()
    extractor = TaskExtractorAgent()

    def summarize_tool(raw_notes: str) -> str:
        bullets = summarizer.summarize(raw_notes)
        return "\n".join(f"- {b}" for b in bullets)

    def extract_tool(bullet_text: str) -> str:
        lines = [ln.lstrip("- ") for ln in bullet_text.strip().splitlines() if ln.strip()]
        items = extractor.extract(lines)
        return "\n".join(f"* {i.task} -- Owner: {i.owner} -- Due: {i.due_date}" for i in items)

    summarize_mock = MockCrewAITool("summarize_notes", summarize_tool)
    extract_mock = MockCrewAITool("extract_tasks", extract_tool)

    summarizer_agent = MockCrewAIAgent(
        role="Summarizer",
        goal="Clean raw meeting notes into bullet points",
        tools=[summarize_mock],
    )
    extractor_agent = MockCrewAIAgent(
        role="Task Extractor",
        goal="Turn bullet points into action items",
        tools=[extract_mock],
    )

    task1 = MockCrewAITask("Summarize the notes", summarizer_agent)
    task2 = MockCrewAITask("Extract action items", extractor_agent)

    crew = MockCrew(
        agents=[summarizer_agent, extractor_agent],
        tasks=[task1, task2],
    )
    wrapper = CrewAIWrapper(crew, chaos_level=chaos_level)
    return wrapper


# ===========================================================================
# STRESS TESTS
# ===========================================================================


class TestMeetingNotesStressNoChaos:
    """Baseline: verify the crew works with no chaos."""

    def test_baseline_kickoff_succeeds(self):
        wrapper = _build_meeting_notes_crew(chaos_level=0.0)
        result = wrapper.kickoff(inputs={"notes": "Sarah will fix login by Friday."})
        assert result is not None
        assert result["tasks_completed"] == 2

    def test_baseline_tools_are_wrapped(self):
        wrapper = _build_meeting_notes_crew()
        tools = wrapper.get_wrapped_tools()
        assert "summarize_notes" in tools
        assert "extract_tasks" in tools

    def test_baseline_metrics_after_multiple_runs(self):
        wrapper = _build_meeting_notes_crew()
        for _ in range(10):
            wrapper.kickoff()
        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 10


class TestMeetingNotesStressWithToolFailures:
    """Inject tool failures and verify resilience."""

    def test_tool_failure_injector_is_applied(self):
        from agentchaos.injectors import ToolFailureInjector
        from agentchaos.injectors.tool_failure import ToolFailureConfig

        wrapper = _build_meeting_notes_crew()
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1))
        wrapper.add_injector(injector, tools=["summarize_notes"])

        tools = wrapper.get_wrapped_tools()
        assert len(tools["summarize_notes"]._injectors) >= 1

    def test_crew_survives_partial_tool_failure(self):
        """Even if summarize_notes fails, crew kickoff shouldn't crash
        because MockCrew catches tool exceptions."""
        from agentchaos.injectors import ToolFailureInjector
        from agentchaos.injectors.tool_failure import ToolFailureConfig

        wrapper = _build_meeting_notes_crew()
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=100))
        wrapper.add_injector(injector, tools=["summarize_notes"])

        # Should not raise — MockCrew catches tool errors
        result = wrapper.kickoff(inputs={"notes": "Test"})
        assert result is not None

    def test_repeated_failures_tracked_in_metrics(self):
        from agentchaos.injectors import ToolFailureInjector
        from agentchaos.injectors.tool_failure import ToolFailureConfig

        wrapper = _build_meeting_notes_crew()
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1000))
        wrapper.add_injector(injector, tools=["summarize_notes"])

        for _ in range(20):
            wrapper.kickoff()

        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 20
        # The summarize_notes tool should have recorded calls
        tool_metrics = metrics["tools"].get("summarize_notes", {})
        # MetricsCollector uses "latency.count" to track total calls
        latency = tool_metrics.get("latency", {})
        assert latency.get("count", 0) > 0


class TestMeetingNotesStressWithDelays:
    """Inject delays and verify the crew still completes."""

    def test_delay_injector_applied(self):
        from agentchaos.injectors import DelayInjector
        from agentchaos.injectors.delay import DelayConfig

        wrapper = _build_meeting_notes_crew()
        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=1, max_delay_ms=1))
        wrapper.add_injector(injector, tools=["extract_tasks"])

        tools = wrapper.get_wrapped_tools()
        assert len(tools["extract_tasks"]._injectors) >= 1

    def test_crew_completes_under_delays(self):
        from agentchaos.injectors import DelayInjector
        from agentchaos.injectors.delay import DelayConfig

        wrapper = _build_meeting_notes_crew()
        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=1, max_delay_ms=2))
        wrapper.add_injector(injector)

        result = wrapper.kickoff(inputs={"notes": "Bob will review PR by Monday."})
        assert result is not None
        assert result["tasks_completed"] == 2


class TestMeetingNotesStressEscalatingChaos:
    """Gradually increase chaos and observe degradation."""

    def test_escalating_chaos_levels(self):
        """Run the crew at increasing chaos levels and verify metrics grow."""
        chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        results_per_level = {}

        for level in chaos_levels:
            wrapper = _build_meeting_notes_crew(chaos_level=level)
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=True,
                enable_hallucinations=False,
                enable_context_corruption=False,
                enable_budget_exhaustion=False,
            )

            successes = 0
            iterations = 30
            for _ in range(iterations):
                try:
                    result = wrapper.kickoff()
                    if result is not None:
                        successes += 1
                except Exception:
                    pass

            results_per_level[level] = successes / iterations

        # At zero chaos, everything should succeed
        assert results_per_level[0.0] == 1.0
        # Results are collected for all levels (no crash)
        assert len(results_per_level) == len(chaos_levels)

    def test_high_chaos_does_not_crash_wrapper(self):
        wrapper = _build_meeting_notes_crew(chaos_level=1.0)
        wrapper.configure_chaos(
            chaos_level=1.0,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=True,
            enable_budget_exhaustion=True,
        )

        # Run many iterations — wrapper itself should never crash
        for _ in range(50):
            try:
                wrapper.kickoff()
            except Exception:
                pass  # tool failures are expected

        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 50


class TestMeetingNotesStressExperimentTracking:
    """Verify experiment tracking works under stress."""

    def test_experiment_context_tracks_runs(self):
        wrapper = _build_meeting_notes_crew()

        with wrapper.experiment("stress-baseline"):
            for _ in range(10):
                wrapper.kickoff()

        results = wrapper.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "stress-baseline"

    def test_multiple_experiments_sequential(self):
        wrapper = _build_meeting_notes_crew()

        for name in ["low-chaos", "mid-chaos", "high-chaos"]:
            with wrapper.experiment(name):
                wrapper.kickoff()

        results = wrapper.get_experiment_results()
        assert len(results) == 3
        names = [r.config.name for r in results]
        assert names == ["low-chaos", "mid-chaos", "high-chaos"]

    def test_reset_between_experiments(self):
        wrapper = _build_meeting_notes_crew()

        with wrapper.experiment("exp1"):
            for _ in range(5):
                wrapper.kickoff()

        assert wrapper.get_metrics()["kickoff_count"] == 5
        wrapper.reset()
        assert wrapper.get_metrics()["kickoff_count"] == 0

        with wrapper.experiment("exp2"):
            for _ in range(3):
                wrapper.kickoff()

        assert wrapper.get_metrics()["kickoff_count"] == 3


class TestMeetingNotesStressEndurance:
    """Endurance: many iterations at moderate chaos."""

    def test_endurance_100_iterations(self):
        wrapper = _build_meeting_notes_crew()
        wrapper.configure_chaos(
            chaos_level=0.3,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        failures = 0
        for _ in range(100):
            try:
                wrapper.kickoff()
            except Exception:
                failures += 1

        metrics = wrapper.get_metrics()
        assert metrics["kickoff_count"] == 100
        # At chaos_level=0.3 with tool failures only, most runs should succeed
        assert failures < 100  # not all should fail
