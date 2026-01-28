"""LangChain wrapper for chaos injection.

This module provides chaos engineering capabilities for LangChain agents and chains.
It wraps LangChain tools and enables fault injection during agent execution.

Example usage:
    from langchain.agents import AgentExecutor
    from balaganagent.wrappers.langchain import LangChainAgentWrapper

    # Create your agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools)

    # Wrap with chaos
    wrapper = LangChainAgentWrapper(agent_executor, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.invoke({"input": "Hello"})
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Optional

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


@dataclass
class LangChainToolCall:
    """Record of a LangChain tool call."""

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


@dataclass
class CallbackEvent:
    """Record of a callback event."""

    event_type: str
    timestamp: float
    data: dict


class LangChainToolProxy:
    """
    Proxy for LangChain tool objects that enables chaos injection.

    LangChain tools have a specific structure with `name` and `func` attributes.
    This proxy wraps the tool's function to inject faults.
    """

    def __init__(
        self,
        tool: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Initialize the tool proxy.

        Args:
            tool: LangChain tool object with `name` and `func` attributes
            chaos_level: Chaos level (0.0 = no chaos, 1.0 = full chaos)
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self._tool = tool
        self._tool_name = getattr(tool, "name", str(tool))
        self._func = getattr(tool, "func", tool)
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._injectors: list[BaseInjector] = []
        self._call_history: list[LangChainToolCall] = []
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
        call = LangChainToolCall(
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

    def get_call_history(self) -> list[LangChainToolCall]:
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


class ChaosCallbackHandler:
    """
    LangChain callback handler that records events and can inject chaos.

    This handler integrates with LangChain's callback system to track
    LLM calls, tool usage, and chain execution.
    """

    def __init__(self, chaos_level: float = 0.0):
        """
        Initialize the callback handler.

        Args:
            chaos_level: Chaos level for injection (0.0-1.0)
        """
        self.chaos_level = chaos_level
        self._events: list[CallbackEvent] = []
        self._tool_calls = 0
        self._llm_calls = 0
        self._chain_runs = 0

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        """Called when LLM starts."""
        self._llm_calls += 1
        self._events.append(
            CallbackEvent(
                event_type="llm_start",
                timestamp=time.time(),
                data={"serialized": serialized, "prompts": prompts},
            )
        )

    def on_llm_end(self, response, **kwargs):
        """Called when LLM ends."""
        self._events.append(
            CallbackEvent(
                event_type="llm_end",
                timestamp=time.time(),
                data={"response": str(response)},
            )
        )

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Called when tool starts."""
        self._tool_calls += 1
        self._events.append(
            CallbackEvent(
                event_type="tool_start",
                timestamp=time.time(),
                data={"serialized": serialized, "input": input_str},
            )
        )

    def on_tool_end(self, output: str, **kwargs):
        """Called when tool ends."""
        self._events.append(
            CallbackEvent(
                event_type="tool_end",
                timestamp=time.time(),
                data={"output": output},
            )
        )

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs):
        """Called when chain starts."""
        self._chain_runs += 1
        self._events.append(
            CallbackEvent(
                event_type="chain_start",
                timestamp=time.time(),
                data={"serialized": serialized, "inputs": inputs},
            )
        )

    def on_chain_end(self, outputs: dict, **kwargs):
        """Called when chain ends."""
        self._events.append(
            CallbackEvent(
                event_type="chain_end",
                timestamp=time.time(),
                data={"outputs": outputs},
            )
        )

    def get_events(self) -> list[CallbackEvent]:
        """Get all recorded events."""
        return self._events.copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get callback metrics."""
        return {
            "tool_calls": self._tool_calls,
            "llm_calls": self._llm_calls,
            "chain_runs": self._chain_runs,
            "total_events": len(self._events),
        }

    def reset(self):
        """Reset callback state."""
        self._events.clear()
        self._tool_calls = 0
        self._llm_calls = 0
        self._chain_runs = 0


class LangChainAgentWrapper:
    """
    Wrapper for LangChain AgentExecutor that enables chaos engineering.

    This wrapper intercepts tool calls from the agent and injects faults
    according to the configured chaos level.
    """

    def __init__(
        self,
        agent_executor: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Initialize the LangChain agent wrapper.

        Args:
            agent_executor: LangChain AgentExecutor object
            chaos_level: Initial chaos level (0.0-1.0)
            max_retries: Default max retries for tool calls
            retry_delay: Default retry delay in seconds
        """
        self._agent_executor = agent_executor
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._tool_proxies: dict[str, LangChainToolProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._invoke_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        self._wrap_tools()

    @property
    def agent_executor(self) -> Any:
        """Get the wrapped agent executor."""
        return self._agent_executor

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_tools(self):
        """Wrap all tools from the agent."""
        tools = getattr(self._agent_executor, "tools", [])

        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))

            if tool_name not in self._tool_proxies:
                proxy = LangChainToolProxy(
                    tool,
                    chaos_level=self._chaos_level,
                    max_retries=self._max_retries,
                    retry_delay=self._retry_delay,
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

    def get_wrapped_tools(self) -> dict[str, LangChainToolProxy]:
        """Get dictionary of wrapped tools."""
        return self._tool_proxies.copy()

    def invoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Invoke the agent with chaos injection.

        Args:
            input_data: Input dictionary for the agent
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The agent's output
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        return self._agent_executor.invoke(input_data, **kwargs)

    async def ainvoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Async invoke the agent with chaos injection.

        Args:
            input_data: Input dictionary for the agent
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The agent's output
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        return await self._agent_executor.ainvoke(input_data, **kwargs)

    def stream(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Iterator[Any]:
        """
        Stream responses from the agent.

        Args:
            input_data: Input dictionary for the agent
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Yields:
            Response chunks
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        yield from self._agent_executor.stream(input_data, **kwargs)

    async def astream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> AsyncIterator[Any]:
        """
        Async stream responses from the agent.

        Args:
            input_data: Input dictionary for the agent
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Yields:
            Response chunks
        """
        self._invoke_count += 1

        if config is not None:
            kwargs["config"] = config

        async for chunk in self._agent_executor.astream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list[dict], config: Optional[dict] = None, **kwargs) -> list[Any]:
        """
        Batch invoke the agent.

        Args:
            inputs: List of input dictionaries
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            List of agent outputs
        """
        self._invoke_count += len(inputs)

        if config is not None:
            kwargs["config"] = config

        return self._agent_executor.batch(inputs, **kwargs)

    async def abatch(
        self, inputs: list[dict], config: Optional[dict] = None, **kwargs
    ) -> list[Any]:
        """
        Async batch invoke the agent.

        Args:
            inputs: List of input dictionaries
            config: Optional config dictionary
            **kwargs: Additional keyword arguments

        Returns:
            List of agent outputs
        """
        self._invoke_count += len(inputs)

        if config is not None:
            kwargs["config"] = config

        return await self._agent_executor.abatch(inputs, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        return {
            "invoke_count": self._invoke_count,
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
        self._invoke_count = 0
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


class LangChainChainWrapper:
    """
    Wrapper for LangChain chains (LCEL) that enables chaos engineering.

    This wrapper works with any Runnable chain and can inject faults
    during chain execution.
    """

    def __init__(
        self,
        chain: Any,
        chaos_level: float = 0.0,
    ):
        """
        Initialize the chain wrapper.

        Args:
            chain: LangChain chain/Runnable object
            chaos_level: Initial chaos level (0.0-1.0)
        """
        self._chain = chain
        self._chaos_level = chaos_level
        self._invoke_count = 0
        self._metrics = MetricsCollector()
        self._injectors: list[BaseInjector] = []

    @property
    def chain(self) -> Any:
        """Get the wrapped chain."""
        return self._chain

    @property
    def chaos_level(self) -> float:
        """Get current chaos level."""
        return self._chaos_level

    def invoke(self, input_data: dict, **kwargs) -> Any:
        """Invoke the chain."""
        self._invoke_count += 1
        return self._chain.invoke(input_data, **kwargs)

    def stream(self, input_data: dict, **kwargs) -> Iterator[Any]:
        """Stream from the chain."""
        self._invoke_count += 1
        yield from self._chain.stream(input_data, **kwargs)

    def batch(self, inputs: list[dict], **kwargs) -> list[Any]:
        """Batch invoke the chain."""
        self._invoke_count += len(inputs)
        return self._chain.batch(inputs, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics."""
        return {
            "invoke_count": self._invoke_count,
            "aggregate": self._metrics.get_summary(),
        }

    def reset(self):
        """Reset wrapper state."""
        self._invoke_count = 0
        self._metrics.reset()
