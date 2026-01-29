"""Claude Agent SDK wrapper for chaos injection.

This module provides chaos engineering capabilities for agents built with the
Claude Agent SDK (``claude-agent-sdk``).  The SDK exposes two main entry
points — ``query()`` for one-shot prompts and ``ClaudeSDKClient`` for
bidirectional conversations — and custom tools defined via the ``@tool``
decorator + ``create_sdk_mcp_server()``.

BalaganAgent intercepts **custom tool functions** before they are registered
with the SDK so that every invocation passes through the chaos engine.  The
wrapper also collects per-tool metrics, MTTR stats and supports named
experiments.

Example usage::

    from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions
    from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper

    @tool("search", "Search the web", {"query": str})
    async def search(args):
        return {"content": [{"type": "text", "text": f"Results for {args['query']}"}]}

    # Wrap tools with chaos *before* creating the MCP server
    wrapper = ClaudeAgentSDKWrapper(tools=[search], chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True)

    # Build SDK server from the chaos-wrapped tools
    server = wrapper.create_mcp_server(name="my-tools", version="1.0.0")

    options = ClaudeAgentOptions(
        mcp_servers={"tools": server},
        allowed_tools=["mcp__tools__search"],
    )
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
from ..injectors.base import FaultType
from ..metrics import MetricsCollector, MTTRCalculator


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
    """Proxy for a Claude Agent SDK ``@tool`` function with chaos injection.

    In the real SDK a custom tool is an async callable that receives an
    ``args`` dict and returns an MCP-style result dict.  This proxy wraps
    that callable so injectors can intercept every invocation.
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        self._func = func
        self._tool_name = name
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._injectors: list[BaseInjector] = []
        self._call_history: list[ClaudeAgentSDKToolCall] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

        # Preserve the original tool metadata so the SDK still recognises it
        for attr in ("__name__", "__doc__", "__module__", "__qualname__"):
            try:
                setattr(self, attr, getattr(func, attr))
            except AttributeError:
                pass

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

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with chaos injection (sync path)."""
        call = ClaudeAgentSDKToolCall(
            tool_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )
        context = {"tool_name": self._tool_name, "args": args, "kwargs": kwargs}

        retries = 0
        last_error: Optional[Exception] = None
        fault_injected: Optional[str] = None

        while retries <= self._max_retries:
            try:
                # Check injectors before call
                for injector in self._injectors:
                    if injector.should_inject(self._tool_name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type
                        self._mttr.record_failure(self._tool_name, fault_type)

                        result, _details = injector.inject(self._tool_name, context)
                        # inject() either raises directly (EXCEPTION/TIMEOUT
                        # modes) or returns a fault result for non-raising
                        # modes.  For tool-failure injectors the non-raising
                        # modes (EMPTY_RESPONSE, MALFORMED_RESPONSE, etc.)
                        # should still surface as exceptions so callers can
                        # detect and retry.
                        if fault_type == FaultType.TOOL_FAILURE.value:
                            from ..injectors.tool_failure import (
                                ToolFailureException,
                            )

                            raise ToolFailureException(
                                _details.get("error_message", "Injected fault"),
                                _details.get("failure_mode", fault_type),
                                self._tool_name,
                            )
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

                # Execute the real tool function
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

        assert last_error is not None
        raise last_error

    # ------------------------------------------------------------------
    # History / metrics
    # ------------------------------------------------------------------

    def get_call_history(self) -> list[ClaudeAgentSDKToolCall]:
        return self._call_history.copy()

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics.get_summary()

    def reset(self):
        self._call_history.clear()
        self._metrics.reset()
        self._mttr.reset()
        for injector in self._injectors:
            injector.reset()


@dataclass
class _ToolRecord:
    """Internal record of an original tool and its proxy."""

    name: str
    original: Callable
    proxy: ClaudeAgentSDKToolProxy


class ClaudeAgentSDKWrapper:
    """Chaos wrapper for Claude Agent SDK custom tools.

    The Claude Agent SDK defines agents via ``query()`` or
    ``ClaudeSDKClient``, and custom tools via ``@tool`` +
    ``create_sdk_mcp_server()``.  This wrapper sits between
    the tool definitions and the MCP server creation so that
    every tool invocation flows through BalaganAgent injectors.

    Usage::

        wrapper = ClaudeAgentSDKWrapper(tools=[search, save], chaos_level=0.5)
        wrapper.configure_chaos(enable_tool_failures=True)
        wrapped_tools = wrapper.get_wrapped_tools()
        # pass wrapped_tools to create_sdk_mcp_server(...)
    """

    def __init__(
        self,
        tools: Optional[list[Any]] = None,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._tool_records: dict[str, _ToolRecord] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._query_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        if tools:
            self._register_tools(tools)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def chaos_level(self) -> float:
        return self._chaos_level

    @property
    def query_count(self) -> int:
        return self._query_count

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self, tools: list[Any]):
        """Register tools, which may be callables, dicts, or objects with name/func."""
        for t in tools:
            if isinstance(t, dict):
                name = t.get("name", str(t))
                func = t.get("func", t)
            elif hasattr(t, "name") and hasattr(t, "func"):
                name = t.name
                func = t.func
            elif callable(t):
                name = getattr(t, "__name__", str(t))
                func = t
            else:
                continue

            proxy = ClaudeAgentSDKToolProxy(
                func,
                name=name,
                chaos_level=self._chaos_level,
                max_retries=self._max_retries,
                retry_delay=self._retry_delay,
            )
            self._tool_records[name] = _ToolRecord(name=name, original=func, proxy=proxy)

    def add_tool(self, func: Callable, name: Optional[str] = None):
        """Register a single tool after construction."""
        tool_name = name or getattr(func, "__name__", str(func))
        self._register_tools([{"name": tool_name, "func": func}])

    # ------------------------------------------------------------------
    # Chaos configuration
    # ------------------------------------------------------------------

    def configure_chaos(
        self,
        chaos_level: Optional[float] = None,
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

        if chaos_level is not None:
            self._chaos_level = chaos_level
        self._injectors.clear()
        base_prob = min(self._chaos_level * self._chaos_level, 0.9)

        if enable_tool_failures:
            self._injectors.append(ToolFailureInjector(ToolFailureConfig(probability=base_prob)))
        if enable_delays:
            self._injectors.append(DelayInjector(DelayConfig(probability=min(base_prob * 2, 1.0))))
        if enable_hallucinations:
            self._injectors.append(
                HallucinationInjector(HallucinationConfig(probability=min(base_prob * 0.5, 1.0)))
            )
        if enable_context_corruption:
            self._injectors.append(
                ContextCorruptionInjector(
                    ContextCorruptionConfig(probability=min(base_prob * 0.3, 1.0))
                )
            )
        if enable_budget_exhaustion:
            self._injectors.append(
                BudgetExhaustionInjector(BudgetExhaustionConfig(probability=1.0))
            )

        for rec in self._tool_records.values():
            rec.proxy.clear_injectors()
            for injector in self._injectors:
                rec.proxy.add_injector(injector)

    def add_injector(self, injector: BaseInjector, tools: Optional[list[str]] = None):
        """Add a custom injector to specific tools or all tools."""
        targets = tools or list(self._tool_records.keys())
        for name in targets:
            if name in self._tool_records:
                self._tool_records[name].proxy.add_injector(injector)

    # ------------------------------------------------------------------
    # Wrapped-tool access
    # ------------------------------------------------------------------

    def get_wrapped_tools(self) -> dict[str, ClaudeAgentSDKToolProxy]:
        """Return a dict mapping tool names to chaos-wrapped proxies.

        Pass these to ``create_sdk_mcp_server(tools=...)`` to register
        chaos-wrapped tools with the Claude Agent SDK.
        """
        return {name: rec.proxy for name, rec in self._tool_records.items()}

    def get_wrapped_tool_list(self) -> list[ClaudeAgentSDKToolProxy]:
        """Return a list of chaos-wrapped tool proxies.

        This is the format expected by ``create_sdk_mcp_server(tools=[...])``.
        """
        return [rec.proxy for rec in self._tool_records.values()]

    # ------------------------------------------------------------------
    # Query tracking
    # ------------------------------------------------------------------

    def record_query(self):
        """Record that a query was sent to the agent."""
        self._query_count += 1

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict[str, Any]:
        tool_metrics = {}
        for name, rec in self._tool_records.items():
            tool_metrics[name] = rec.proxy.get_metrics()
        return {
            "query_count": self._query_count,
            "tools": tool_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> dict[str, Any]:
        tool_stats = {}
        for name, rec in self._tool_records.items():
            tool_stats[name] = rec.proxy._mttr.get_recovery_stats()
        return {
            "tools": tool_stats,
            "aggregate": self._mttr.get_recovery_stats(),
        }

    def reset(self):
        self._query_count = 0
        for rec in self._tool_records.values():
            rec.proxy.reset()
        self._metrics.reset()
        self._mttr.reset()

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """Context manager for running a named chaos experiment."""
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
        return self._experiment_results.copy()
