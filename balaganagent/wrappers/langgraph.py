"""LangGraph wrapper for chaos injection.

This module provides chaos engineering capabilities for LangGraph state graphs.
It wraps LangGraph compiled graphs and their tools/nodes to enable fault injection
during graph execution.

Example usage:
    from langgraph.graph import StateGraph
    from balaganagent.wrappers.langgraph import LangGraphWrapper

    # Build and compile your graph
    graph = StateGraph(AgentState)
    # ... add nodes and edges ...
    compiled = graph.compile()

    # Wrap with chaos
    wrapper = LangGraphWrapper(compiled, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.invoke({"messages": [HumanMessage(content="Hello")]})
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterator, Optional

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
from ..verbose import get_logger


@dataclass
class LangGraphToolCall:
    """Record of a LangGraph tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0
    node_name: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class LangGraphNodeEvent:
    """Record of a LangGraph node execution."""

    node_name: str
    start_time: float
    end_time: Optional[float] = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


class LangGraphToolProxy:
    """
    Proxy for LangGraph tool objects that enables chaos injection.

    LangGraph tools are LangChain-compatible BaseTool objects with `name`
    and `func` attributes. This proxy wraps the tool's function to inject
    faults, record call history, and collect metrics.
    """

    def __init__(
        self,
        tool: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._tool = tool
        self._tool_name = getattr(tool, "name", str(tool))
        self._func = getattr(tool, "func", tool)
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._call_history: list[LangGraphToolCall] = []
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
        call = LangGraphToolCall(
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

                        if self.verbose:
                            self._logger.info(
                                f"[LangGraph] Injecting {fault_type} on {self._tool_name}"
                            )

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

                self._call_history.append(call)
                self._metrics.record_operation(
                    self._tool_name,
                    call.duration_ms,
                    success=True,
                    retries=retries,
                    fault_type=fault_injected,
                )

                if self.verbose:
                    self._logger.info(
                        f"[LangGraph] {self._tool_name} completed in {call.duration_ms:.1f}ms"
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

        raise last_error  # type: ignore

    def get_call_history(self) -> list[LangGraphToolCall]:
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


class LangGraphNodeProxy:
    """
    Proxy for a LangGraph node function that enables chaos injection.

    LangGraph nodes are functions that take state (TypedDict) and return
    updated state. This proxy wraps those functions to inject delays,
    failures, or other faults at the node execution level.

    Node-level chaos is orthogonal to tool-level chaos: tool chaos affects
    individual tool calls within a node, while node chaos affects the
    entire node's execution.
    """

    def __init__(
        self,
        func: Callable,
        node_name: str,
        chaos_level: float = 0.0,
        verbose: bool = False,
    ):
        self._func = func
        self._node_name = node_name
        self._chaos_level = chaos_level
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._event_history: list[LangGraphNodeEvent] = []
        self._metrics = MetricsCollector()

    @property
    def node_name(self) -> str:
        return self._node_name

    def add_injector(self, injector: BaseInjector):
        """Add a fault injector to this node proxy."""
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        """Remove a fault injector."""
        self._injectors.remove(injector)

    def clear_injectors(self):
        """Remove all injectors."""
        self._injectors.clear()

    def __call__(self, state: Any) -> Any:
        """Execute the node function with chaos injection."""
        event = LangGraphNodeEvent(
            node_name=self._node_name,
            start_time=time.time(),
        )

        # Check injectors before execution
        for injector in self._injectors:
            if injector.should_inject(self._node_name):
                fault_type = injector.fault_type.value
                event.fault_injected = fault_type

                if self.verbose:
                    self._logger.info(
                        f"[LangGraph] Injecting {fault_type} on node '{self._node_name}'"
                    )

                result, details = injector.inject(
                    self._node_name,
                    {"node_name": self._node_name, "state": state},
                )

                # Delay injections add latency but don't block execution —
                # the delay already happened inside inject() via time.sleep
                if injector.fault_type == FaultType.DELAY:
                    continue

                if result is not None:
                    event.end_time = time.time()
                    event.error = f"Fault injected: {fault_type}"
                    self._event_history.append(event)
                    self._metrics.record_operation(
                        self._node_name,
                        event.duration_ms,
                        success=False,
                        fault_type=fault_type,
                    )
                    raise RuntimeError(
                        f"Chaos fault injected on node '{self._node_name}': {fault_type}"
                    )

        try:
            result = self._func(state)
            event.end_time = time.time()
            self._event_history.append(event)
            self._metrics.record_operation(
                self._node_name,
                event.duration_ms,
                success=True,
            )

            if self.verbose:
                self._logger.info(
                    f"[LangGraph] Node '{self._node_name}' completed "
                    f"in {event.duration_ms:.1f}ms"
                )

            return result
        except Exception as e:
            event.end_time = time.time()
            event.error = str(e)
            self._event_history.append(event)
            self._metrics.record_operation(
                self._node_name,
                event.duration_ms,
                success=False,
            )
            raise

    def get_event_history(self) -> list[LangGraphNodeEvent]:
        """Get node event history."""
        return self._event_history.copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get node metrics summary."""
        return self._metrics.get_summary()

    def reset(self):
        """Reset node proxy state."""
        self._event_history.clear()
        self._metrics.reset()


class LangGraphWrapper:
    """
    Wrapper for LangGraph CompiledGraph that enables chaos engineering.

    This wrapper intercepts tool calls and optionally node executions
    from the compiled graph and injects faults according to the
    configured chaos level.
    """

    def __init__(
        self,
        compiled_graph: Any,
        tools: Optional[list[Any]] = None,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._compiled_graph = compiled_graph
        self._explicit_tools = tools
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._tool_proxies: dict[str, LangGraphToolProxy] = {}
        self._node_proxies: dict[str, LangGraphNodeProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._invoke_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        self._wrap_tools()

    @property
    def compiled_graph(self) -> Any:
        """Get the wrapped compiled graph."""
        return self._compiled_graph

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_tools(self):
        """Discover and wrap all tools from the compiled graph.

        LangGraph tools can be discovered from:
        1. Explicitly passed tools list
        2. ToolNode instances in the graph's nodes
        3. The graph's tools attribute
        """
        tools_to_wrap: list[Any] = []

        # 1. Use explicitly provided tools if any
        if self._explicit_tools:
            tools_to_wrap.extend(self._explicit_tools)

        # 2. Discover from graph nodes — look for ToolNode instances
        nodes = getattr(self._compiled_graph, "nodes", {})
        for node_name, node_func in nodes.items():
            # Check if node is a ToolNode (has .tools attribute)
            node_tools = getattr(node_func, "tools", None)
            if node_tools and isinstance(node_tools, (list, tuple)):
                tools_to_wrap.extend(node_tools)
            # Also check tools_by_name dict
            tools_by_name = getattr(node_func, "tools_by_name", None)
            if tools_by_name and isinstance(tools_by_name, dict):
                tools_to_wrap.extend(tools_by_name.values())

        # 3. Fallback: check compiled graph's tools
        graph_tools = getattr(self._compiled_graph, "tools", None)
        if graph_tools and isinstance(graph_tools, (list, tuple)):
            tools_to_wrap.extend(graph_tools)

        # Wrap each discovered tool
        for tool in tools_to_wrap:
            tool_name = getattr(tool, "name", str(tool))

            if tool_name not in self._tool_proxies:
                proxy = LangGraphToolProxy(
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

    def wrap_node(
        self,
        node_name: str,
        injectors: Optional[list[BaseInjector]] = None,
    ) -> Optional[LangGraphNodeProxy]:
        """Wrap a specific graph node with chaos injection.

        Node-level wrapping is opt-in because not all nodes should be
        chaos-injected (e.g., the LLM router node should typically
        remain stable).

        Args:
            node_name: The name of the node in the graph
            injectors: Optional list of injectors for this node

        Returns:
            The LangGraphNodeProxy if the node was found, None otherwise
        """
        nodes = getattr(self._compiled_graph, "nodes", {})
        if node_name not in nodes:
            return None

        original_func = nodes[node_name]
        proxy = LangGraphNodeProxy(
            func=original_func,
            node_name=node_name,
            chaos_level=self._chaos_level,
            verbose=self.verbose,
        )
        if injectors:
            for inj in injectors:
                proxy.add_injector(inj)

        self._node_proxies[node_name] = proxy
        nodes[node_name] = proxy
        return proxy

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

    def add_injector(
        self,
        injector: BaseInjector,
        tools: Optional[list[str]] = None,
        nodes: Optional[list[str]] = None,
    ):
        """
        Add a custom injector to specific tools, nodes, or all tools.

        Args:
            injector: The fault injector to add
            tools: List of tool names to target, or None for all tools
            nodes: List of node names to target (must be explicit)
        """
        # Apply to tools (default: all tools)
        tool_targets = tools or list(self._tool_proxies.keys())
        for name in tool_targets:
            if name in self._tool_proxies:
                self._tool_proxies[name].add_injector(injector)

        # Apply to nodes (must be explicit)
        if nodes:
            for name in nodes:
                if name in self._node_proxies:
                    self._node_proxies[name].add_injector(injector)

    def get_wrapped_tools(self) -> dict[str, LangGraphToolProxy]:
        """Get dictionary of wrapped tools."""
        return self._tool_proxies.copy()

    def get_wrapped_nodes(self) -> dict[str, LangGraphNodeProxy]:
        """Get dictionary of wrapped nodes."""
        return self._node_proxies.copy()

    def invoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Invoke the graph with chaos injection.

        Args:
            input_data: Input state dictionary for the graph
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The graph's output state
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        return self._compiled_graph.invoke(input_data, **kwargs)

    async def ainvoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Async invoke the graph with chaos injection.

        Args:
            input_data: Input state dictionary for the graph
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The graph's output state
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        return await self._compiled_graph.ainvoke(input_data, **kwargs)

    def stream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> Iterator[Any]:
        """
        Stream responses from the graph (node-by-node).

        Args:
            input_data: Input state dictionary
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Yields:
            Node output chunks
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        yield from self._compiled_graph.stream(input_data, **kwargs)

    async def astream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> AsyncIterator[Any]:
        """
        Async stream responses from the graph.

        Args:
            input_data: Input state dictionary
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Yields:
            Node output chunks
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        async for chunk in self._compiled_graph.astream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list[dict], config: Optional[dict] = None, **kwargs) -> list[Any]:
        """
        Batch invoke the graph.

        Args:
            inputs: List of input state dictionaries
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            List of graph output states
        """
        self._invoke_count += len(inputs)

        if config is not None:
            kwargs["config"] = config

        from typing import cast

        return cast(list[Any], self._compiled_graph.batch(inputs, **kwargs))

    async def abatch(
        self, inputs: list[dict], config: Optional[dict] = None, **kwargs
    ) -> list[Any]:
        """
        Async batch invoke the graph.

        Args:
            inputs: List of input state dictionaries
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            List of graph output states
        """
        self._invoke_count += len(inputs)

        if config is not None:
            kwargs["config"] = config

        from typing import cast

        return cast(list[Any], await self._compiled_graph.abatch(inputs, **kwargs))

    def get_state(self, config: Optional[dict] = None) -> Any:
        """Get the current graph state."""
        return self._compiled_graph.get_state(config or {})

    def update_state(self, config: dict, values: dict, **kwargs) -> Any:
        """Update the graph state."""
        return self._compiled_graph.update_state(config, values, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        node_metrics = {}
        for name, proxy in self._node_proxies.items():
            node_metrics[name] = proxy.get_metrics()

        return {
            "invoke_count": self._invoke_count,
            "tools": tool_metrics,
            "nodes": node_metrics,
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
        self._invoke_count = 0
        for proxy in self._tool_proxies.values():
            proxy.reset()
        for proxy in self._node_proxies.values():
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
