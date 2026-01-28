"""Agent wrapper and tool proxy for chaos injection."""

import functools
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, TypeVar

from .injectors import (
    BaseInjector,
    BudgetExhaustionInjector,
    ContextCorruptionInjector,
    DelayInjector,
    HallucinationInjector,
    ToolFailureInjector,
)
from .metrics import MetricsCollector, MTTRCalculator
from .verbose import get_logger


class ToolProtocol(Protocol):
    """Protocol for tool functions."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


T = TypeVar("T", bound=ToolProtocol)


@dataclass
class ToolCall:
    """Record of a tool call."""

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


class ToolProxy:
    """
    Proxy wrapper for individual tools that enables chaos injection.

    Usage:
        def my_tool(query: str) -> str:
            return f"Result for {query}"

        proxy = ToolProxy(my_tool)
        proxy.add_injector(ToolFailureInjector())

        # This may now fail randomly
        result = proxy("test query")
    """

    def __init__(
        self,
        tool: Callable,
        name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        verbose: bool = False,
    ):
        self.tool = tool
        self.name = name or tool.__name__
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._call_history: list[ToolCall] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

        # Callbacks
        self._before_call: list[Callable] = []
        self._after_call: list[Callable] = []
        self._on_error: list[Callable] = []
        self._on_retry: list[Callable] = []

    def add_injector(self, injector: BaseInjector):
        """Add a fault injector."""
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        """Remove a fault injector."""
        self._injectors.remove(injector)

    def clear_injectors(self):
        """Remove all injectors."""
        self._injectors.clear()

    def before_call(self, callback: Callable):
        """Register a before-call callback."""
        self._before_call.append(callback)

    def after_call(self, callback: Callable):
        """Register an after-call callback."""
        self._after_call.append(callback)

    def on_error(self, callback: Callable):
        """Register an error callback."""
        self._on_error.append(callback)

    def on_retry(self, callback: Callable):
        """Register a retry callback."""
        self._on_retry.append(callback)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with chaos injection."""
        call = ToolCall(
            tool_name=self.name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )

        context = {
            "tool_name": self.name,
            "args": args,
            "kwargs": kwargs,
        }

        # Verbose logging: tool call
        if self.verbose:
            self._logger.tool_call(self.name, args, kwargs)

        # Notify before-call callbacks
        for callback in self._before_call:
            try:
                callback(self.name, args, kwargs)
            except Exception:
                pass

        retries = 0
        last_error = None
        fault_injected = None

        while retries <= self.max_retries:
            try:
                # Check injectors before call
                for injector in self._injectors:
                    if injector.should_inject(self.name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type

                        # Record failure for MTTR
                        self._mttr.record_failure(self.name, fault_type)

                        result, details = injector.inject(self.name, context)

                        # If injector raised an exception, it will propagate
                        # If it returned a result, that's our "failed" response
                        if result is not None:
                            call.end_time = time.time()
                            call.fault_injected = fault_type
                            call.result = result
                            self._call_history.append(call)

                            self._metrics.record_operation(
                                self.name,
                                call.duration_ms,
                                success=False,
                                fault_type=fault_type,
                            )

                            return result

                # Execute the actual tool
                result = self.tool(*args, **kwargs)

                call.end_time = time.time()
                call.result = result
                call.retries = retries

                if fault_injected:
                    # Record recovery if we had a fault but succeeded
                    self._mttr.record_recovery(
                        self.name,
                        fault_injected,
                        recovery_method="retry",
                        retries=retries,
                        success=True,
                    )
                    # Verbose logging: recovery
                    if self.verbose:
                        self._logger.recovery(self.name, retries, True)

                # Verbose logging: result
                if self.verbose:
                    self._logger.tool_result(result, call.duration_ms)

                self._call_history.append(call)

                self._metrics.record_operation(
                    self.name,
                    call.duration_ms,
                    success=True,
                    retries=retries,
                    fault_type=fault_injected,
                )

                # Notify after-call callbacks
                for callback in self._after_call:
                    try:
                        callback(self.name, result, call.duration_ms)
                    except Exception:
                        pass

                return result

            except Exception as e:
                last_error = e
                retries += 1
                call.retries = retries

                # Notify error callbacks
                for callback in self._on_error:
                    try:
                        callback(self.name, e, retries)
                    except Exception:
                        pass

                if retries <= self.max_retries:
                    # Verbose logging: retry
                    if self.verbose:
                        self._logger.retry(retries, self.max_retries, self.retry_delay_seconds)

                    # Notify retry callbacks
                    for callback in self._on_retry:
                        try:
                            callback(self.name, retries, self.retry_delay_seconds)
                        except Exception:
                            pass

                    time.sleep(self.retry_delay_seconds)
                else:
                    break

        # All retries exhausted
        call.end_time = time.time()
        call.error = str(last_error)
        self._call_history.append(call)

        self._metrics.record_operation(
            self.name,
            call.duration_ms,
            success=False,
            retries=retries,
            fault_type=fault_injected,
        )

        if fault_injected:
            self._mttr.record_recovery(
                self.name,
                fault_injected,
                recovery_method="retry",
                retries=retries,
                success=False,
            )
            # Verbose logging: failed recovery
            if self.verbose:
                self._logger.recovery(self.name, retries, False)

        # Verbose logging: error
        if self.verbose and last_error is not None:
            self._logger.tool_error(last_error, call.duration_ms)

        assert last_error is not None, "last_error should not be None after all retries exhausted"
        raise last_error

    def get_call_history(self) -> list[ToolCall]:
        """Get call history."""
        return self._call_history.copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics summary."""
        return self._metrics.get_summary()

    def get_mttr_stats(self) -> dict[str, Any]:
        """Get MTTR statistics."""
        return self._mttr.get_recovery_stats()

    def reset(self):
        """Reset proxy state."""
        self._call_history.clear()
        self._metrics.reset()
        self._mttr.reset()
        for injector in self._injectors:
            injector.reset()


class AgentWrapper:
    """
    Wraps an entire agent to enable chaos testing.

    Works with any agent that exposes tools as callable attributes
    or a tools dictionary.

    Usage:
        class MyAgent:
            def search(self, query): ...
            def calculate(self, expr): ...

        agent = MyAgent()
        wrapper = AgentWrapper(agent)
        wrapper.configure_chaos(chaos_level=0.5)

        # Tools are now wrapped with chaos injection
        result = wrapper.agent.search("test")
    """

    def __init__(
        self,
        agent: Any,
        tool_names: Optional[list[str]] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        verbose: bool = False,
    ):
        self._original_agent = agent
        self._tool_names = tool_names
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self.verbose = verbose

        self._tool_proxies: dict[str, ToolProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

        self._wrap_tools()

    def _wrap_tools(self):
        """Wrap agent tools with proxies."""
        tools_to_wrap = self._tool_names

        # Auto-discover tools if not specified
        if tools_to_wrap is None:
            tools_to_wrap = []

            # Check for tools dict
            if hasattr(self._original_agent, "tools"):
                tools = getattr(self._original_agent, "tools")
                if isinstance(tools, dict):
                    tools_to_wrap.extend(tools.keys())

            # Check for callable attributes
            for name in dir(self._original_agent):
                if name.startswith("_"):
                    continue
                attr = getattr(self._original_agent, name, None)
                if callable(attr) and name not in tools_to_wrap:
                    tools_to_wrap.append(name)

        # Create proxies
        for name in tools_to_wrap:
            tool = self._get_tool(name)
            if tool is not None:
                proxy = ToolProxy(
                    tool,
                    name=name,
                    max_retries=self._max_retries,
                    retry_delay_seconds=self._retry_delay_seconds,
                    verbose=self.verbose,
                )
                self._tool_proxies[name] = proxy

    def _get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool from the agent."""
        # Try tools dict first
        if hasattr(self._original_agent, "tools"):
            tools = getattr(self._original_agent, "tools")
            if isinstance(tools, dict) and name in tools:
                from typing import cast
                return cast(Callable[..., Any], tools[name])

        # Try as attribute
        return getattr(self._original_agent, name, None)

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
        from .injectors.budget import BudgetExhaustionConfig
        from .injectors.context import ContextCorruptionConfig
        from .injectors.delay import DelayConfig
        from .injectors.hallucination import HallucinationConfig
        from .injectors.tool_failure import ToolFailureConfig

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

        # Add injectors to all proxies
        for proxy in self._tool_proxies.values():
            proxy.clear_injectors()
            for injector in self._injectors:
                proxy.add_injector(injector)

    def add_injector(self, injector: BaseInjector, tools: Optional[list[str]] = None):
        """Add an injector to specific tools or all tools."""
        targets = tools or list(self._tool_proxies.keys())
        for name in targets:
            if name in self._tool_proxies:
                self._tool_proxies[name].add_injector(injector)

    def get_proxy(self, name: str) -> Optional[ToolProxy]:
        """Get a tool proxy by name."""
        return self._tool_proxies.get(name)

    def call_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Call a tool through its proxy."""
        proxy = self._tool_proxies.get(name)
        if proxy is None:
            raise ValueError(f"Unknown tool: {name}")
        return proxy(*args, **kwargs)

    @property
    def agent(self) -> Any:
        """Get a proxy object that looks like the original agent."""
        return _AgentProxy(self)

    def get_metrics(self) -> dict[str, Any]:
        """Get combined metrics from all tools."""
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        return {
            "tools": tool_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> dict[str, Any]:
        """Get combined MTTR stats from all tools."""
        tool_stats = {}
        for name, proxy in self._tool_proxies.items():
            tool_stats[name] = proxy.get_mttr_stats()

        return {
            "tools": tool_stats,
            "aggregate": self._mttr.get_recovery_stats(),
        }

    def reset(self):
        """Reset all proxies and metrics."""
        for proxy in self._tool_proxies.values():
            proxy.reset()
        self._metrics.reset()
        self._mttr.reset()


class _AgentProxy:
    """Internal proxy that mimics the original agent interface."""

    def __init__(self, wrapper: AgentWrapper):
        self._wrapper = wrapper

    def __getattr__(self, name: str) -> Any:
        proxy = self._wrapper.get_proxy(name)
        if proxy is not None:
            return proxy

        # Fall back to original agent
        return getattr(self._wrapper._original_agent, name)


def chaos_tool(
    probability: float = 0.1,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    enable_delays: bool = True,
    enable_failures: bool = True,
    verbose: bool = False,
) -> Callable[[T], T]:
    """
    Decorator to add chaos injection to a tool function.

    Usage:
        @chaos_tool(probability=0.2)
        def my_tool(query: str) -> str:
            return f"Result: {query}"
    """

    def decorator(func: T) -> T:
        from .injectors.delay import DelayConfig
        from .injectors.tool_failure import ToolFailureConfig

        proxy = ToolProxy(
            func,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay,
            verbose=verbose,
        )

        if enable_failures:
            proxy.add_injector(ToolFailureInjector(ToolFailureConfig(probability=probability)))

        if enable_delays:
            proxy.add_injector(DelayInjector(DelayConfig(probability=probability)))

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return proxy(*args, **kwargs)

        wrapper._proxy = proxy  # type: ignore
        return wrapper  # type: ignore

    return decorator
