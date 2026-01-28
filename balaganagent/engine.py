"""Core chaos engine for orchestrating experiments."""

import random
import time
from typing import Any, Callable, Optional

from .experiment import Experiment, ExperimentConfig, ExperimentResult
from .injectors import (
    BaseInjector,
    BudgetExhaustionInjector,
    ContextCorruptionInjector,
    DelayInjector,
    HallucinationInjector,
    ToolFailureInjector,
)
from .injectors.budget import BudgetExhaustionConfig
from .injectors.context import ContextCorruptionConfig
from .injectors.delay import DelayConfig
from .injectors.hallucination import HallucinationConfig
from .injectors.tool_failure import ToolFailureConfig
from .verbose import get_logger


class ChaosEngine:
    """
    Core chaos engineering engine for AI agents.

    The ChaosEngine orchestrates chaos experiments by:
    1. Managing fault injectors
    2. Intercepting tool calls
    3. Injecting faults based on configuration
    4. Collecting metrics
    5. Generating reports

    Usage:
        engine = ChaosEngine()
        engine.configure(chaos_level=0.5)

        # Wrap an agent's tool
        wrapped_tool = engine.wrap_tool(original_tool)

        # Run experiment
        with engine.experiment("test-resilience") as exp:
            result = wrapped_tool("some_input")

        report = engine.get_report()
    """

    def __init__(
        self,
        chaos_level: float = 1.0,
        seed: Optional[int] = None,
        verbose: bool = False,
    ):
        self.chaos_level = chaos_level
        self.seed = seed
        self.verbose = verbose
        self._rng = random.Random(seed)
        self._logger = get_logger()

        # Initialize injectors
        self._injectors: dict[str, BaseInjector] = {}
        self._active_experiment: Optional[Experiment] = None
        self._completed_experiments: list[ExperimentResult] = []

        # Callbacks
        self._on_fault_injected: list[Callable] = []
        self._on_operation_complete: list[Callable] = []

        self._initialize_default_injectors()

    def _initialize_default_injectors(self):
        """Initialize default fault injectors."""
        base_probability = 0.1 * self.chaos_level

        self._injectors["tool_failure"] = ToolFailureInjector(
            ToolFailureConfig(probability=base_probability, seed=self._rng.randint(0, 2**31))
        )

        self._injectors["delay"] = DelayInjector(
            DelayConfig(probability=base_probability * 2, seed=self._rng.randint(0, 2**31))
        )

        self._injectors["hallucination"] = HallucinationInjector(
            HallucinationConfig(
                probability=base_probability * 0.5, seed=self._rng.randint(0, 2**31)
            )
        )

        self._injectors["context_corruption"] = ContextCorruptionInjector(
            ContextCorruptionConfig(
                probability=base_probability * 0.3, seed=self._rng.randint(0, 2**31)
            )
        )

        self._injectors["budget_exhaustion"] = BudgetExhaustionInjector(
            BudgetExhaustionConfig(
                probability=1.0, seed=self._rng.randint(0, 2**31)
            )  # Always check budgets
        )

    def configure(
        self,
        chaos_level: Optional[float] = None,
        tool_failure_config: Optional[ToolFailureConfig] = None,
        delay_config: Optional[DelayConfig] = None,
        hallucination_config: Optional[HallucinationConfig] = None,
        context_corruption_config: Optional[ContextCorruptionConfig] = None,
        budget_exhaustion_config: Optional[BudgetExhaustionConfig] = None,
    ):
        """Configure the chaos engine."""
        if chaos_level is not None:
            self.chaos_level = chaos_level
            # Reinitialize with new chaos level
            self._initialize_default_injectors()

        if tool_failure_config:
            self._injectors["tool_failure"] = ToolFailureInjector(tool_failure_config)

        if delay_config:
            self._injectors["delay"] = DelayInjector(delay_config)

        if hallucination_config:
            self._injectors["hallucination"] = HallucinationInjector(hallucination_config)

        if context_corruption_config:
            self._injectors["context_corruption"] = ContextCorruptionInjector(
                context_corruption_config
            )

        if budget_exhaustion_config:
            self._injectors["budget_exhaustion"] = BudgetExhaustionInjector(
                budget_exhaustion_config
            )

    def add_injector(self, name: str, injector: BaseInjector):
        """Add a custom injector."""
        self._injectors[name] = injector

    def remove_injector(self, name: str):
        """Remove an injector."""
        self._injectors.pop(name, None)

    def get_injector(self, name: str) -> Optional[BaseInjector]:
        """Get an injector by name."""
        return self._injectors.get(name)

    def enable_injector(self, name: str):
        """Enable an injector."""
        if name in self._injectors:
            self._injectors[name].config.enabled = True

    def disable_injector(self, name: str):
        """Disable an injector."""
        if name in self._injectors:
            self._injectors[name].config.enabled = False

    def wrap_tool(
        self,
        tool_func: Callable,
        tool_name: Optional[str] = None,
        inject_on_input: bool = False,
        inject_on_output: bool = True,
    ) -> Callable:
        """
        Wrap a tool function with chaos injection.

        Args:
            tool_func: The tool function to wrap
            tool_name: Name for the tool (defaults to function name)
            inject_on_input: Whether to inject faults on input
            inject_on_output: Whether to inject faults on output

        Returns:
            Wrapped function with chaos injection
        """
        name = tool_name or tool_func.__name__

        def wrapped(*args, **kwargs):
            start_time = time.time()
            context = {
                "tool_name": name,
                "args": args,
                "kwargs": kwargs,
                "timestamp": start_time,
            }

            # Verbose logging: tool call
            if self.verbose:
                self._logger.tool_call(name, args, kwargs)

            # Check if we're in an experiment
            if self._active_experiment:
                op = self._active_experiment.operation(name)
                op.__enter__()

            try:
                # Input injection
                if inject_on_input:
                    args, kwargs = self._inject_on_input(name, args, kwargs, context)

                # Check budget before execution
                budget_injector = self._injectors.get("budget_exhaustion")
                if budget_injector and budget_injector.should_inject(name):
                    result, details = budget_injector.inject(name, context)
                    if result is not None:  # Budget exceeded
                        self._notify_fault("budget_exhaustion", name, details)
                        if self._active_experiment:
                            op.record_fault("budget_exhaustion")
                            op.record_failure("Budget exhausted")
                            op.__exit__(None, None, None)
                        return result

                # Apply delay if configured
                delay_injector = self._injectors.get("delay")
                if delay_injector and delay_injector.should_inject(name):
                    delay_ms, details = delay_injector.inject(name, context)
                    self._notify_fault("delay", name, details)
                    if self._active_experiment:
                        op.record_fault("delay")

                # Check for tool failure
                failure_injector = self._injectors.get("tool_failure")
                if failure_injector and failure_injector.should_inject(name):
                    result, details = failure_injector.inject(name, context)
                    self._notify_fault("tool_failure", name, details)
                    if self._active_experiment:
                        op.record_fault("tool_failure")
                        op.record_failure(details.get("error_message", "Tool failure"))
                        op.__exit__(None, None, None)
                    return result

                # Execute the actual tool
                result = tool_func(*args, **kwargs)

                # Output injection
                if inject_on_output:
                    result = self._inject_on_output(name, result, context)

                # Verbose logging: success
                if self.verbose:
                    duration_ms = (time.time() - start_time) * 1000
                    self._logger.tool_result(result, duration_ms)

                if self._active_experiment:
                    op.record_success()
                    op.__exit__(None, None, None)

                return result

            except Exception as e:
                # Verbose logging: error
                if self.verbose:
                    duration_ms = (time.time() - start_time) * 1000
                    self._logger.tool_error(e, duration_ms)

                if self._active_experiment:
                    op.record_failure(str(e))
                    op.__exit__(type(e), e, e.__traceback__)
                raise

        wrapped.__name__ = name
        wrapped.__doc__ = tool_func.__doc__
        wrapped._original = tool_func
        wrapped._chaos_wrapped = True

        return wrapped

    def _inject_on_input(
        self,
        tool_name: str,
        args: tuple,
        kwargs: dict,
        context: dict,
    ) -> tuple[tuple, dict]:
        """Inject faults on input."""
        # Context corruption on input
        corruption_injector = self._injectors.get("context_corruption")
        if corruption_injector and corruption_injector.should_inject(tool_name):
            context["data"] = {"args": args, "kwargs": kwargs}
            corrupted, details = corruption_injector.inject(tool_name, context)
            self._notify_fault("context_corruption", tool_name, details)

            if isinstance(corrupted, dict):
                args = corrupted.get("args", args)
                kwargs = corrupted.get("kwargs", kwargs)

        return args, kwargs

    def _inject_on_output(
        self,
        tool_name: str,
        result: Any,
        context: dict,
    ) -> Any:
        """Inject faults on output."""
        # Hallucination injection
        hallucination_injector = self._injectors.get("hallucination")
        if hallucination_injector and hallucination_injector.should_inject(tool_name):
            context["data"] = result
            corrupted, details = hallucination_injector.inject(tool_name, context)
            self._notify_fault("hallucination", tool_name, details)
            return corrupted

        return result

    def _notify_fault(self, fault_type: str, tool_name: str, details: dict):
        """Notify listeners of a fault injection."""
        # Verbose logging: fault injection
        if self.verbose:
            self._logger.fault_injected(fault_type, tool_name, details)

        for callback in self._on_fault_injected:
            try:
                callback(fault_type, tool_name, details)
            except Exception:
                pass  # Don't let callback errors affect operation

    def on_fault_injected(self, callback: Callable):
        """Register a callback for fault injection events."""
        self._on_fault_injected.append(callback)

    def on_operation_complete(self, callback: Callable):
        """Register a callback for operation completion events."""
        self._on_operation_complete.append(callback)

    def experiment(self, name: str, **config_kwargs) -> "ExperimentContextManager":
        """
        Create an experiment context manager.

        Usage:
            with engine.experiment("test") as exp:
                # Run operations
                pass
            result = exp.result
        """
        # Use provided chaos_level or fall back to engine's default
        chaos_level = config_kwargs.pop("chaos_level", self.chaos_level)
        config = ExperimentConfig(name=name, chaos_level=chaos_level, **config_kwargs)
        return ExperimentContextManager(self, config)

    def start_experiment(self, config: ExperimentConfig) -> Experiment:
        """Start a new experiment."""
        if self._active_experiment:
            raise RuntimeError("An experiment is already running")

        # Verbose logging: experiment start
        if self.verbose:
            self._logger.experiment_start(config.name, config.chaos_level)

        experiment = Experiment(config)
        experiment.start()
        self._active_experiment = experiment

        # Reset injectors for fresh experiment
        for injector in self._injectors.values():
            injector.reset()

        return experiment

    def end_experiment(self) -> ExperimentResult:
        """End the current experiment and return results."""
        if not self._active_experiment:
            raise RuntimeError("No experiment is running")

        result = self._active_experiment.complete()

        # Verbose logging: experiment end
        if self.verbose:
            duration = result.end_time - result.start_time if result.end_time else 0
            self._logger.experiment_end(result.config.name, duration, result.success_rate)

        self._completed_experiments.append(result)
        self._active_experiment = None

        return result

    def get_experiment_results(self) -> list[ExperimentResult]:
        """Get all completed experiment results."""
        return self._completed_experiments.copy()

    def get_injection_stats(self) -> dict[str, Any]:
        """Get statistics about injected faults."""
        stats = {}
        for name, injector in self._injectors.items():
            events = injector.get_events()
            stats[name] = {
                "total_injections": len(events),
                "events": [
                    {
                        "timestamp": e.timestamp,
                        "target": e.target,
                        "details": e.details,
                    }
                    for e in events[-10:]  # Last 10 events
                ],
            }
        return stats

    def reset(self):
        """Reset the engine state."""
        for injector in self._injectors.values():
            injector.reset()
        self._active_experiment = None
        self._completed_experiments.clear()


class ExperimentContextManager:
    """Context manager for running experiments."""

    def __init__(self, engine: ChaosEngine, config: ExperimentConfig):
        self.engine = engine
        self.config = config
        self.experiment: Optional[Experiment] = None
        self.result: Optional[ExperimentResult] = None

    def __enter__(self) -> Experiment:
        self.experiment = self.engine.start_experiment(self.config)
        return self.experiment

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.experiment:
                self.experiment.abort(str(exc_val))
        self.result = self.engine.end_experiment()
        return False  # Don't suppress exceptions
