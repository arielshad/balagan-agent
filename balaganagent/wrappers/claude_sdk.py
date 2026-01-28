"""Claude Agent SDK wrapper for chaos injection.

This module provides chaos engineering capabilities for agents built with the
Claude Agent SDK. It wraps agent tools and enables fault injection during
agent execution.

Example usage:
    from claude_agent_sdk import Agent, tool
    from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper

    agent = Agent(name="researcher", tools=[search, summarize])

    # Wrap with chaos
    wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.run("Research AI safety")
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

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
class ClaudeAgentSDKToolCall:
    """Record of a Claude Agent SDK tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


class ClaudeAgentSDKToolProxy:
    """
    Proxy for Claude Agent SDK tool functions that enables chaos injection.

    Claude Agent SDK agents expose tools as callables (functions decorated with
    ``@tool`` or plain functions). This proxy wraps those functions to inject
    faults during execution.
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._func = func
        self._tool_name = name
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._call_history: list[ClaudeAgentSDKToolCall] = []
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
        call = ClaudeAgentSDKToolCall(
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
                    if self.verbose:
                        self._logger.recovery(self._tool_name, retries, True)

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
            if self.verbose:
                self._logger.recovery(self._tool_name, retries, False)

        if self.verbose and last_error is not None:
            self._logger.tool_error(last_error, call.duration_ms)

        assert last_error is not None, "last_error should not be None after all retries exhausted"
        raise last_error

    def get_call_history(self) -> list[ClaudeAgentSDKToolCall]:
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


class ClaudeAgentSDKWrapper:
    """
    Wrapper for Claude Agent SDK agents that enables chaos engineering.

    This wrapper intercepts tool calls from the agent and injects faults
    according to the configured chaos level. It supports agents that expose
    tools as either a list of objects (with ``name``/``func`` attributes) or
    a dict mapping names to callables.
    """

    def __init__(
        self,
        agent: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._agent = agent
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._tool_proxies: dict[str, ClaudeAgentSDKToolProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._run_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        self._wrap_tools()

    @property
    def agent(self) -> Any:
        """Get the wrapped agent."""
        return self._agent

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_tools(self):
        """Wrap all tools from the agent."""
        tools = getattr(self._agent, "tools", [])

        if isinstance(tools, dict):
            for name, func in tools.items():
                self._add_tool_proxy(name, func)
        elif isinstance(tools, (list, tuple)):
            for tool in tools:
                tool_name = getattr(tool, "name", str(tool))
                tool_func = getattr(tool, "func", tool)
                self._add_tool_proxy(tool_name, tool_func)

    def _add_tool_proxy(self, name: str, func: Callable):
        """Create and register a tool proxy."""
        if name not in self._tool_proxies:
            proxy = ClaudeAgentSDKToolProxy(
                func,
                name=name,
                chaos_level=self._chaos_level,
                max_retries=self._max_retries,
                retry_delay=self._retry_delay,
                verbose=self.verbose,
            )
            self._tool_proxies[name] = proxy

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        """Configure chaos injection for all tools."""
        from ..injectors.budget import BudgetExhaustionConfig
        from ..injectors.context import ContextCorruptionConfig
        from ..injectors.delay import DelayConfig
        from ..injectors.hallucination import HallucinationConfig
        from ..injectors.tool_failure import ToolFailureConfig

        self._chaos_level = chaos_level
        self._injectors.clear()
        base_prob = 0.1 * chaos_level

        if enable_tool_failures:
            self._injectors.append(ToolFailureInjector(ToolFailureConfig(probability=base_prob)))

        if enable_delays:
            self._injectors.append(DelayInjector(DelayConfig(probability=base_prob * 2)))

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

    def add_injector(self, injector: BaseInjector, tools: Optional[list[str]] = None):
        """Add a custom injector to specific tools or all tools."""
        targets = tools or list(self._tool_proxies.keys())
        for name in targets:
            if name in self._tool_proxies:
                self._tool_proxies[name].add_injector(injector)

    def get_wrapped_tools(self) -> dict[str, ClaudeAgentSDKToolProxy]:
        """Get dictionary of wrapped tools."""
        return self._tool_proxies.copy()

    def run(self, prompt: str, **kwargs: Any) -> Any:
        """
        Execute the agent with chaos injection active on its tools.

        Args:
            prompt: The prompt / task for the agent
            **kwargs: Additional arguments passed to agent.run()

        Returns:
            The agent's output
        """
        self._run_count += 1
        return self._agent.run(prompt, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        return {
            "run_count": self._run_count,
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
        self._run_count = 0
        for proxy in self._tool_proxies.values():
            proxy.reset()
        self._metrics.reset()
        self._mttr.reset()

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """Context manager for running chaos experiments."""
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
