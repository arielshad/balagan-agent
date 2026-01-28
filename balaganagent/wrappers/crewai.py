"""CrewAI wrapper for chaos injection.

This module provides chaos engineering capabilities for CrewAI agents and crews.
It wraps CrewAI tools and enables fault injection during crew execution.

Example usage:
    from crewai import Agent, Task, Crew
    from balaganagent.wrappers.crewai import CrewAIWrapper

    # Create your crew
    crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])

    # Wrap with chaos
    wrapper = CrewAIWrapper(crew, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.kickoff()
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Optional

from ..experiment import Experiment, ExperimentConfig, ExperimentResult
from ..injectors import (
    BaseInjector,
    BudgetExhaustionInjector,
    ContextCorruptionInjector,
    DelayInjector,
    HallucinationInjector,
    ToolFailureInjector,
)
from ..metrics import MetricsCollector, MTTRCalculator
from ..verbose import get_logger


@dataclass
class CrewAIToolCall:
    """Record of a CrewAI tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0
    agent_name: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


class CrewAIToolProxy:
    """
    Proxy for CrewAI tool objects that enables chaos injection.

    CrewAI tools have a specific structure with `name` and `func` attributes.
    This proxy wraps the tool's function to inject faults.
    """

    def __init__(
        self,
        tool: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        """
        Initialize the tool proxy.

        Args:
            tool: CrewAI tool object with `name` and `func` attributes
            chaos_level: Chaos level (0.0 = no chaos, 1.0 = full chaos)
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
            verbose: Enable verbose logging
        """
        self._tool = tool
        self._tool_name = getattr(tool, "name", str(tool))
        self._func = getattr(tool, "func", tool)
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._call_history: list[CrewAIToolCall] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

    @property
    def tool_name(self) -> str:
        return self._tool_name

    def add_injector(self, injector: BaseInjector):
        """Add a fault injector to this tool proxy."""
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        """Remove a fault injector."""
        self._injectors.remove(injector)

    def clear_injectors(self):
        """Remove all injectors."""
        self._injectors.clear()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with chaos injection."""
        call = CrewAIToolCall(
            tool_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )

        context = {
            "tool_name": self._tool_name,
            "args": args,
            "kwargs": kwargs,
        }

        # Verbose logging: tool call
        if self.verbose:
            self._logger.tool_call(self._tool_name, args, kwargs)

        retries = 0
        last_error = None
        fault_injected = None

        while retries <= self._max_retries:
            try:
                # Check injectors before call
                for injector in self._injectors:
                    if injector.should_inject(self._tool_name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type
                        self._mttr.record_failure(self._tool_name, fault_type)

                        result, details = injector.inject(self._tool_name, context)
                        if result is not None:
                            call.end_time = time.time()
                            call.fault_injected = fault_type
                            call.result = result
                            self._call_history.append(call)
                            self._metrics.record_operation(
                                self._tool_name,
                                call.duration_ms,
                                success=False,
                                fault_type=fault_type,
                            )
                            return result

                # Execute the actual tool function
                result = self._func(*args, **kwargs)

                call.end_time = time.time()
                call.result = result
                call.retries = retries

                if fault_injected:
                    self._mttr.record_recovery(
                        self._tool_name,
                        fault_injected,
                        recovery_method="retry",
                        retries=retries,
                        success=True,
                    )
                    # Verbose logging: recovery
                    if self.verbose:
                        self._logger.recovery(self._tool_name, retries, True)

                # Verbose logging: result
                if self.verbose:
                    self._logger.tool_result(result, call.duration_ms)

                self._call_history.append(call)
                self._metrics.record_operation(
                    self._tool_name,
                    call.duration_ms,
                    success=True,
                    retries=retries,
                    fault_type=fault_injected,
                )

                return result

            except Exception as e:
                last_error = e
                retries += 1
                call.retries = retries

                if retries <= self._max_retries:
                    # Verbose logging: retry
                    if self.verbose:
                        self._logger.retry(retries, self._max_retries, self._retry_delay)
                    time.sleep(self._retry_delay)
                else:
                    break

        # All retries exhausted
        call.end_time = time.time()
        call.error = str(last_error)
        self._call_history.append(call)

        self._metrics.record_operation(
            self._tool_name,
            call.duration_ms,
            success=False,
            retries=retries,
            fault_type=fault_injected,
        )

        if fault_injected:
            self._mttr.record_recovery(
                self._tool_name,
                fault_injected,
                recovery_method="retry",
                retries=retries,
                success=False,
            )
            # Verbose logging: failed recovery
            if self.verbose:
                self._logger.recovery(self._tool_name, retries, False)

        # Verbose logging: error
        if self.verbose:
            self._logger.tool_error(last_error, call.duration_ms)

        raise last_error  # type: ignore

    def get_call_history(self) -> list[CrewAIToolCall]:
        """Get call history."""
        return self._call_history.copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics summary."""
        return self._metrics.get_summary()

    def reset(self):
        """Reset proxy state."""
        self._call_history.clear()
        self._metrics.reset()
        self._mttr.reset()
        for injector in self._injectors:
            injector.reset()


class CrewAIWrapper:
    """
    Wrapper for CrewAI Crew objects that enables chaos engineering.

    This wrapper intercepts tool calls from all agents in the crew
    and injects faults according to the configured chaos level.
    """

    def __init__(
        self,
        crew: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        """
        Initialize the CrewAI wrapper.

        Args:
            crew: CrewAI Crew object
            chaos_level: Initial chaos level (0.0-1.0)
            max_retries: Default max retries for tool calls
            retry_delay: Default retry delay in seconds
            verbose: Enable verbose logging
        """
        self._crew = crew
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._tool_proxies: dict[str, CrewAIToolProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._kickoff_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        self._wrap_tools()

    @property
    def crew(self) -> Any:
        """Get the wrapped crew."""
        return self._crew

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_tools(self):
        """Wrap all tools from all agents in the crew."""
        agents = getattr(self._crew, "agents", [])

        for agent in agents:
            agent_tools = getattr(agent, "tools", [])

            for tool in agent_tools:
                tool_name = getattr(tool, "name", str(tool))

                if tool_name not in self._tool_proxies:
                    proxy = CrewAIToolProxy(
                        tool,
                        chaos_level=self._chaos_level,
                        max_retries=self._max_retries,
                        retry_delay=self._retry_delay,
                        verbose=self.verbose,
                    )
                    self._tool_proxies[tool_name] = proxy

                    # Replace the tool's func with our proxy
                    if hasattr(tool, "func"):
                        tool.func = proxy

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        """
        Configure chaos injection for all tools.

        Args:
            chaos_level: Base chaos level (0.0-1.0)
            enable_tool_failures: Enable random tool failures
            enable_delays: Enable artificial delays
            enable_hallucinations: Enable data corruption
            enable_context_corruption: Enable input corruption
            enable_budget_exhaustion: Enable budget/rate limit simulation
        """
        from ..injectors.budget import BudgetExhaustionConfig
        from ..injectors.context import ContextCorruptionConfig
        from ..injectors.delay import DelayConfig
        from ..injectors.hallucination import HallucinationConfig
        from ..injectors.tool_failure import ToolFailureConfig

        self._chaos_level = chaos_level
        self._injectors.clear()
        base_prob = 0.1 * chaos_level

        if enable_tool_failures:
            self._injectors.append(
                ToolFailureInjector(ToolFailureConfig(probability=base_prob))
            )

        if enable_delays:
            self._injectors.append(
                DelayInjector(DelayConfig(probability=base_prob * 2))
            )

        if enable_hallucinations:
            self._injectors.append(
                HallucinationInjector(HallucinationConfig(probability=base_prob * 0.5))
            )

        if enable_context_corruption:
            self._injectors.append(
                ContextCorruptionInjector(ContextCorruptionConfig(probability=base_prob * 0.3))
            )

        if enable_budget_exhaustion:
            self._injectors.append(
                BudgetExhaustionInjector(BudgetExhaustionConfig(probability=1.0))
            )

        # Apply injectors to all tool proxies
        for proxy in self._tool_proxies.values():
            proxy.clear_injectors()
            for injector in self._injectors:
                proxy.add_injector(injector)

    def add_injector(
        self, injector: BaseInjector, tools: Optional[list[str]] = None
    ):
        """
        Add a custom injector to specific tools or all tools.

        Args:
            injector: The fault injector to add
            tools: List of tool names to target, or None for all tools
        """
        targets = tools or list(self._tool_proxies.keys())
        for name in targets:
            if name in self._tool_proxies:
                self._tool_proxies[name].add_injector(injector)

    def get_wrapped_tools(self) -> dict[str, CrewAIToolProxy]:
        """Get dictionary of wrapped tools."""
        return self._tool_proxies.copy()

    def kickoff(self, inputs: Optional[dict[str, Any]] = None) -> Any:
        """
        Execute the crew with chaos injection.

        Args:
            inputs: Optional input dictionary for the crew

        Returns:
            The crew's output
        """
        self._kickoff_count += 1

        if inputs is not None:
            return self._crew.kickoff(inputs=inputs)
        return self._crew.kickoff()

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        return {
            "kickoff_count": self._kickoff_count,
            "tools": tool_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> dict[str, Any]:
        """Get MTTR statistics for all tools."""
        tool_stats = {}
        for name, proxy in self._tool_proxies.items():
            tool_stats[name] = proxy._mttr.get_recovery_stats()

        return {
            "tools": tool_stats,
            "aggregate": self._mttr.get_recovery_stats(),
        }

    def reset(self):
        """Reset wrapper state."""
        self._kickoff_count = 0
        for proxy in self._tool_proxies.values():
            proxy.reset()
        self._metrics.reset()
        self._mttr.reset()

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """
        Context manager for running chaos experiments.

        Args:
            name: Experiment name
            **config_kwargs: Additional experiment configuration

        Yields:
            Experiment object
        """
        config = ExperimentConfig(name=name, **config_kwargs)
        exp = Experiment(config)

        self._experiments.append(exp)
        self._current_experiment = exp

        try:
            exp.start()
            yield exp
        except Exception as e:
            exp.abort(str(e))
            raise
        finally:
            if exp.status.value == "running":
                result = exp.complete()
                self._experiment_results.append(result)
            self._current_experiment = None

    def get_experiment_results(self) -> list[ExperimentResult]:
        """Get all experiment results."""
        return self._experiment_results.copy()
