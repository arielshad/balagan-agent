"""Experiment runner for chaos testing."""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .engine import ChaosEngine
from .experiment import ExperimentResult
from .metrics import (
    MetricsCollector,
    MTTRCalculator,
    RecoveryQualityAnalyzer,
    ReliabilityScorer,
)
from .verbose import get_logger
from .wrapper import AgentWrapper


@dataclass
class Scenario:
    """A test scenario to run against an agent."""

    name: str
    description: str
    operations: list[dict[str, Any]]
    expected_results: Optional[dict[str, Any]] = None
    chaos_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            operations=data["operations"],
            expected_results=data.get("expected_results"),
            chaos_config=data.get("chaos_config", {}),
        )

    @classmethod
    def from_file(cls, path: str) -> "Scenario":
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class RunResult:
    """Result of a single scenario run."""

    scenario_name: str
    experiment_result: ExperimentResult
    metrics: dict[str, Any]
    mttr_stats: dict[str, Any]
    reliability_report: dict[str, Any]
    recovery_quality: dict[str, Any]
    duration_seconds: float
    passed: bool
    failure_reason: Optional[str] = None


class ExperimentRunner:
    """
    Runs chaos experiments against AI agents.

    Supports:
    - Single scenario runs
    - Multi-scenario test suites
    - Parallel execution
    - Result aggregation
    - Report generation

    Usage:
        runner = ExperimentRunner(agent_wrapper)
        result = runner.run_scenario(scenario)
        report = runner.generate_report()
    """

    def __init__(
        self,
        agent_wrapper: Optional[AgentWrapper] = None,
        chaos_engine: Optional[ChaosEngine] = None,
        verbose: bool = False,
    ):
        self.agent_wrapper = agent_wrapper
        self.verbose = verbose
        self._logger = get_logger()

        # Create or use provided chaos engine with verbose setting
        if chaos_engine is None:
            self.chaos_engine = ChaosEngine(verbose=verbose)
        else:
            self.chaos_engine = chaos_engine

        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._recovery_analyzer = RecoveryQualityAnalyzer()
        self._reliability_scorer = ReliabilityScorer()

        self._results: list[RunResult] = []
        self._start_time: Optional[float] = None

    def set_agent(self, agent: Any, tool_names: Optional[list[str]] = None):
        """Set the agent to test."""
        self.agent_wrapper = AgentWrapper(agent, tool_names, verbose=self.verbose)

    def run_scenario(
        self,
        scenario: Scenario,
        chaos_level: Optional[float] = None,
    ) -> RunResult:
        """Run a single scenario."""
        if self.agent_wrapper is None:
            raise RuntimeError("No agent configured. Call set_agent() first.")

        start_time = time.time()

        # Configure chaos
        chaos_config = scenario.chaos_config.copy()
        if chaos_level is not None:
            chaos_config["chaos_level"] = chaos_level

        # Verbose logging: scenario start
        if self.verbose:
            self._logger.section(f"Scenario: {scenario.name}")
            if scenario.description:
                self._logger.log(scenario.description, "dim")
            self._logger.log(f"Operations: {len(scenario.operations)}", "cyan")

        self.agent_wrapper.configure_chaos(**chaos_config)

        failure_reason = None
        passed = True

        with self.chaos_engine.experiment(scenario.name, **chaos_config) as experiment:
            try:
                # Execute operations
                for operation in scenario.operations:
                    tool_name = operation["tool"]
                    args = operation.get("args", [])
                    kwargs = operation.get("kwargs", {})

                    with experiment.operation(tool_name) as op:
                        try:
                            result = self.agent_wrapper.call_tool(tool_name, *args, **kwargs)

                            # Record metrics
                            self._reliability_scorer.record_operation(
                                success=True,
                                latency_ms=time.time() - start_time,
                            )

                            op.record_success()

                        except Exception as e:
                            op.record_failure(str(e))
                            self._reliability_scorer.record_operation(
                                success=False,
                                latency_ms=time.time() - start_time,
                            )

                # Validate expected results if provided
                if scenario.expected_results:
                    # Basic validation - can be extended
                    pass

            except Exception as e:
                passed = False
                failure_reason = str(e)

        end_time = time.time()
        experiment_result = self.chaos_engine.end_experiment() if self.chaos_engine._active_experiment else experiment.complete()

        # Gather metrics
        result = RunResult(
            scenario_name=scenario.name,
            experiment_result=experiment_result,
            metrics=self.agent_wrapper.get_metrics(),
            mttr_stats=self.agent_wrapper.get_mttr_stats(),
            reliability_report=self._reliability_scorer.calculate_score().__dict__,
            recovery_quality=self._recovery_analyzer.get_summary(),
            duration_seconds=end_time - start_time,
            passed=passed,
            failure_reason=failure_reason,
        )

        # Verbose logging: scenario completion
        if self.verbose:
            status = "✓ PASSED" if passed else "✗ FAILED"
            color = "green" if passed else "red"
            self._logger.log(f"{status} - {scenario.name} ({result.duration_seconds:.2f}s)", color)
            if failure_reason:
                self._logger.log(f"  Reason: {failure_reason}", "red", level=1)

            # Log metrics
            self._logger.metric("Success Rate", f"{experiment_result.success_rate:.1%}")
            self._logger.metric("Recovery Rate", f"{experiment_result.recovery_rate:.1%}")
            self._logger.metric("Faults Injected", experiment_result.faults_injected)

        self._results.append(result)
        return result

    def run_suite(
        self,
        scenarios: list[Scenario],
        chaos_level: Optional[float] = None,
        stop_on_failure: bool = False,
    ) -> list[RunResult]:
        """Run multiple scenarios."""
        self._start_time = time.time()
        results = []

        for scenario in scenarios:
            result = self.run_scenario(scenario, chaos_level)
            results.append(result)

            if stop_on_failure and not result.passed:
                break

        return results

    def run_stress_test(
        self,
        scenario: Scenario,
        iterations: int = 100,
        chaos_levels: Optional[list[float]] = None,
    ) -> dict[str, Any]:
        """
        Run a stress test with increasing chaos levels.

        Returns statistics about agent behavior under increasing chaos.
        """
        if chaos_levels is None:
            chaos_levels = [0.1, 0.25, 0.5, 0.75, 1.0]

        stress_results = {
            "scenario": scenario.name,
            "iterations_per_level": iterations,
            "levels": {},
        }

        for level in chaos_levels:
            # Verbose logging: stress test level start
            if self.verbose:
                self._logger.section(f"Stress Test Level: {level}")
                self._logger.log(f"Running {iterations} iterations...", "cyan")

            level_results = []

            for i in range(iterations):
                if self.verbose and i > 0 and i % 10 == 0:
                    self._logger.log(f"  Progress: {i}/{iterations} iterations completed", "dim")

                result = self.run_scenario(scenario, chaos_level=level)
                level_results.append({
                    "passed": result.passed,
                    "duration": result.duration_seconds,
                    "success_rate": result.experiment_result.success_rate,
                    "recovery_rate": result.experiment_result.recovery_rate,
                })

            # Aggregate level results
            passed_count = sum(1 for r in level_results if r["passed"])
            avg_duration = sum(r["duration"] for r in level_results) / len(level_results)
            avg_success_rate = sum(r["success_rate"] for r in level_results) / len(level_results)

            stress_results["levels"][str(level)] = {
                "pass_rate": passed_count / iterations,
                "avg_duration_seconds": avg_duration,
                "avg_success_rate": avg_success_rate,
                "iterations": len(level_results),
            }

            # Verbose logging: level summary
            if self.verbose:
                pass_rate = passed_count / iterations
                color = "green" if pass_rate > 0.9 else "yellow" if pass_rate > 0.7 else "red"
                self._logger.log(f"Level {level} complete: {pass_rate:.1%} pass rate", color)

        return stress_results

    def get_results(self) -> list[RunResult]:
        """Get all run results."""
        return self._results.copy()

    def get_aggregate_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics across all runs."""
        if not self._results:
            return {}

        total_duration = sum(r.duration_seconds for r in self._results)
        passed_count = sum(1 for r in self._results if r.passed)
        total_operations = sum(
            r.experiment_result.total_operations for r in self._results
        )
        successful_operations = sum(
            r.experiment_result.successful_operations for r in self._results
        )
        faults_injected = sum(
            r.experiment_result.faults_injected for r in self._results
        )

        return {
            "total_runs": len(self._results),
            "passed_runs": passed_count,
            "failed_runs": len(self._results) - passed_count,
            "pass_rate": passed_count / len(self._results),
            "total_duration_seconds": total_duration,
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "operation_success_rate": (
                successful_operations / total_operations if total_operations > 0 else 0
            ),
            "total_faults_injected": faults_injected,
        }

    def reset(self):
        """Reset runner state."""
        self._results.clear()
        self._metrics.reset()
        self._mttr.reset()
        self._recovery_analyzer.reset()
        self._reliability_scorer.reset()
        self._start_time = None
        if self.agent_wrapper:
            self.agent_wrapper.reset()


class ScenarioBuilder:
    """Builder for creating test scenarios."""

    def __init__(self, name: str):
        self._name = name
        self._description = ""
        self._operations: list[dict[str, Any]] = []
        self._expected_results: dict[str, Any] = {}
        self._chaos_config: dict[str, Any] = {}

    def description(self, desc: str) -> "ScenarioBuilder":
        self._description = desc
        return self

    def call(
        self,
        tool_name: str,
        *args: Any,
        expected: Any = None,
        **kwargs: Any,
    ) -> "ScenarioBuilder":
        """Add a tool call to the scenario."""
        operation = {
            "tool": tool_name,
            "args": list(args),
            "kwargs": kwargs,
        }
        if expected is not None:
            operation["expected"] = expected
        self._operations.append(operation)
        return self

    def with_chaos(
        self,
        level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ) -> "ScenarioBuilder":
        """Configure chaos settings."""
        self._chaos_config = {
            "chaos_level": level,
            "enable_tool_failures": enable_tool_failures,
            "enable_delays": enable_delays,
            "enable_hallucinations": enable_hallucinations,
            "enable_context_corruption": enable_context_corruption,
            "enable_budget_exhaustion": enable_budget_exhaustion,
        }
        return self

    def expect(self, key: str, value: Any) -> "ScenarioBuilder":
        """Add an expected result."""
        self._expected_results[key] = value
        return self

    def build(self) -> Scenario:
        """Build the scenario."""
        return Scenario(
            name=self._name,
            description=self._description,
            operations=self._operations,
            expected_results=self._expected_results if self._expected_results else None,
            chaos_config=self._chaos_config,
        )


def scenario(name: str) -> ScenarioBuilder:
    """Create a new scenario builder."""
    return ScenarioBuilder(name)
