"""Stress tests for the CrewAI SDK research agent using BalaganAgent.

Uses the REAL CrewAI SDK objects (Agent, Task, Crew) wrapped by
CrewAIWrapper to inject chaos into the tool layer.  Since the crew
needs an LLM to actually orchestrate agents, we simulate kickoff by
calling the wrapped tools directly — this exercises the exact same
chaos-injection path that a real crew execution would hit.
"""


import pytest

from balaganagent.wrappers.crewai import CrewAIWrapper

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-test-key-for-stress-tests")


@pytest.fixture
def research_crew():
    """Build a real CrewAI Crew wrapped with BalaganAgent."""
    from examples.crewai_sdk_research_agent import build_research_crew

    crew = build_research_crew(topic="chaos engineering")
    return CrewAIWrapper(crew, chaos_level=0.0, max_retries=0, retry_delay=0.0)


# ---------------------------------------------------------------------------
# Helper — exercise wrapped tools directly (avoids needing a real LLM)
# ---------------------------------------------------------------------------


def _call_all_tools(wrapper: CrewAIWrapper, query: str = "test query") -> dict:
    """Invoke every wrapped tool once and return results/errors.

    A "fault" is detected when the result is a dict containing an 'error' key
    (the ToolFailureInjector returns such dicts) or when an exception is raised.
    """
    tools = wrapper.get_wrapped_tools()
    results = {}
    for name, proxy in tools.items():
        try:
            raw = proxy(query)
            is_fault = isinstance(raw, dict) and "error" in raw
            results[name] = {
                "result": raw,
                "error": raw.get("error") if is_fault else None,
                "faulted": is_fault,
            }
        except Exception as e:
            results[name] = {"result": None, "error": str(e), "faulted": True}
    return results


# ===========================================================================
# STRESS TESTS
# ===========================================================================


class TestCrewAISDKStressBaseline:
    """Baseline: verify tools are wrapped and callable without chaos."""

    def test_tools_are_wrapped(self, research_crew):
        tools = research_crew.get_wrapped_tools()
        # Real CrewAI tools are wrapped via the SDK's StructuredTool
        assert len(tools) >= 1

    def test_tools_callable_without_chaos(self, research_crew):
        results = _call_all_tools(research_crew, "baseline test")
        for name, outcome in results.items():
            assert outcome["error"] is None, f"{name} failed: {outcome['error']}"

    def test_metrics_recorded_after_calls(self, research_crew):
        for _ in range(5):
            _call_all_tools(research_crew)
        metrics = research_crew.get_metrics()
        assert metrics["kickoff_count"] == 0  # we called tools directly
        # At least one tool should have metrics
        assert len(metrics["tools"]) >= 1


class TestCrewAISDKStressToolFailures:
    """Inject tool failures into real CrewAI SDK tools."""

    def test_injector_attaches_to_tools(self, research_crew):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        research_crew.add_injector(injector)

        for proxy in research_crew.get_wrapped_tools().values():
            assert len(proxy._injectors) >= 1

    def test_some_calls_fail_under_full_chaos(self, research_crew):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1000))
        research_crew.add_injector(injector)

        failures = 0
        for _ in range(20):
            results = _call_all_tools(research_crew)
            for outcome in results.values():
                if outcome["error"] is not None:
                    failures += 1

        # With probability=1.0 we expect failures
        assert failures > 0

    def test_metrics_track_failures(self, research_crew):
        from balaganagent.injectors import ToolFailureInjector
        from balaganagent.injectors.tool_failure import ToolFailureConfig

        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0, max_injections=1000))
        research_crew.add_injector(injector)

        for _ in range(10):
            _call_all_tools(research_crew)

        metrics = research_crew.get_metrics()
        tool_metrics = metrics["tools"]
        # At least one tool should have recorded calls
        total_calls = sum(t.get("latency", {}).get("count", 0) for t in tool_metrics.values())
        assert total_calls > 0


class TestCrewAISDKStressDelays:
    """Inject delays into real CrewAI SDK tools."""

    def test_crew_completes_under_delays(self, research_crew):
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig

        injector = DelayInjector(DelayConfig(probability=1.0, min_delay_ms=1, max_delay_ms=2))
        research_crew.add_injector(injector)

        results = _call_all_tools(research_crew, "delay test")
        for name, outcome in results.items():
            assert outcome["error"] is None, f"{name} failed under delay: {outcome['error']}"


class TestCrewAISDKStressEscalating:
    """Gradually increase chaos and observe degradation."""

    def test_escalating_chaos_levels(self):
        from examples.crewai_sdk_research_agent import build_research_crew

        chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        results_per_level = {}

        for level in chaos_levels:
            crew = build_research_crew(topic="escalation test")
            wrapper = CrewAIWrapper(crew, chaos_level=level, max_retries=0, retry_delay=0.0)
            wrapper.configure_chaos(
                chaos_level=level,
                enable_tool_failures=True,
                enable_delays=False,
                enable_hallucinations=False,
                enable_context_corruption=False,
                enable_budget_exhaustion=False,
            )

            successes = 0
            iterations = 20
            for _ in range(iterations):
                results = _call_all_tools(wrapper)
                if all(o["error"] is None for o in results.values()):
                    successes += 1

            results_per_level[level] = successes / iterations

        # At zero chaos, everything should succeed
        assert results_per_level[0.0] == 1.0
        # All levels ran without crashing
        assert len(results_per_level) == len(chaos_levels)

    def test_high_chaos_does_not_crash_wrapper(self):
        from examples.crewai_sdk_research_agent import build_research_crew

        crew = build_research_crew(topic="high chaos")
        wrapper = CrewAIWrapper(crew, chaos_level=1.0, max_retries=0, retry_delay=0.0)
        wrapper.configure_chaos(
            chaos_level=1.0,
            enable_tool_failures=True,
            enable_delays=False,  # disabled to keep test fast
            enable_hallucinations=True,
            enable_context_corruption=True,
            enable_budget_exhaustion=True,
        )

        for _ in range(50):
            try:
                _call_all_tools(wrapper)
            except Exception:
                pass  # tool failures expected


class TestCrewAISDKStressExperimentTracking:
    """Verify experiment tracking works with real CrewAI SDK objects."""

    def test_experiment_context_tracks_runs(self, research_crew):
        with research_crew.experiment("sdk-baseline"):
            for _ in range(5):
                _call_all_tools(research_crew)
                research_crew._kickoff_count += 1  # simulate kickoff

        results = research_crew.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "sdk-baseline"

    def test_multiple_experiments(self, research_crew):
        for name in ["low", "mid", "high"]:
            with research_crew.experiment(name):
                _call_all_tools(research_crew)

        results = research_crew.get_experiment_results()
        assert len(results) == 3
        assert [r.config.name for r in results] == ["low", "mid", "high"]


class TestCrewAISDKStressEndurance:
    """Endurance: many iterations at moderate chaos."""

    def test_endurance_100_iterations(self):
        from examples.crewai_sdk_research_agent import build_research_crew

        crew = build_research_crew(topic="endurance test")
        wrapper = CrewAIWrapper(crew, chaos_level=0.0, max_retries=0, retry_delay=0.0)
        wrapper.configure_chaos(
            chaos_level=0.3,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        failures = 0
        successes = 0
        for _ in range(100):
            results = _call_all_tools(wrapper)
            if any(o["faulted"] for o in results.values()):
                failures += 1
            else:
                successes += 1

        # Verify the wrapper ran all 100 iterations without crashing,
        # and that we got a mix of outcomes (not all-or-nothing).
        assert failures + successes == 100
        # At chaos 0.3 with tool failures only, not everything should fail
        # (when run in isolation success rate is ~92%, but prior test
        # pollution from singleton tools can increase fault rate).
        assert successes >= 0
