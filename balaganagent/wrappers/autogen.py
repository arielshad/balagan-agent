"""AutoGen wrapper for chaos injection.

This module provides chaos engineering capabilities for Microsoft AutoGen agents.
It wraps AutoGen function_map functions and enables fault injection during agent
conversations.

Example usage:
    from autogen import AssistantAgent, UserProxyAgent
    from balaganagent.wrappers.autogen import AutoGenWrapper

    # Create your agents
    assistant = AssistantAgent("assistant", llm_config=config)
    user_proxy = UserProxyAgent("user_proxy")

    # Wrap with chaos
    wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.initiate_chat("Hello, agent!")
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


@dataclass
class AutoGenFunctionCall:
    """Record of an AutoGen function call."""

    function_name: str
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


class AutoGenFunctionProxy:
    """
    Proxy for AutoGen function_map functions that enables chaos injection.

    AutoGen agents use a function_map dictionary to define callable functions.
    This proxy wraps those functions to inject faults.
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Initialize the function proxy.

        Args:
            func: The function to wrap
            name: Function name
            chaos_level: Chaos level (0.0 = no chaos, 1.0 = full chaos)
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self._func = func
        self._function_name = name
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._injectors: list[BaseInjector] = []
        self._call_history: list[AutoGenFunctionCall] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

    @property
    def function_name(self) -> str:
        return self._function_name

    def add_injector(self, injector: BaseInjector):
        """Add a fault injector."""
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        """Remove a fault injector."""
        self._injectors.remove(injector)

    def clear_injectors(self):
        """Remove all injectors."""
        self._injectors.clear()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the function with chaos injection."""
        call = AutoGenFunctionCall(
            function_name=self._function_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )

        context = {
            "function_name": self._function_name,
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
                    if injector.should_inject(self._function_name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type
                        self._mttr.record_failure(self._function_name, fault_type)

                        result, details = injector.inject(self._function_name, context)
                        if result is not None:
                            call.end_time = time.time()
                            call.fault_injected = fault_type
                            call.result = result
                            self._call_history.append(call)
                            self._metrics.record_operation(
                                self._function_name,
                                call.duration_ms,
                                success=False,
                                fault_type=fault_type,
                            )
                            return result

                # Execute the actual function
                result = self._func(*args, **kwargs)

                call.end_time = time.time()
                call.result = result
                call.retries = retries

                if fault_injected:
                    self._mttr.record_recovery(
                        self._function_name,
                        fault_injected,
                        recovery_method="retry",
                        retries=retries,
                        success=True,
                    )

                self._call_history.append(call)
                self._metrics.record_operation(
                    self._function_name,
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
            self._function_name,
            call.duration_ms,
            success=False,
            retries=retries,
            fault_type=fault_injected,
        )

        if fault_injected:
            self._mttr.record_recovery(
                self._function_name,
                fault_injected,
                recovery_method="retry",
                retries=retries,
                success=False,
            )

        raise last_error  # type: ignore

    def get_call_history(self) -> list[AutoGenFunctionCall]:
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


class AutoGenWrapper:
    """
    Wrapper for AutoGen agents that enables chaos engineering.

    This wrapper intercepts function calls from the agent's function_map
    and injects faults according to the configured chaos level.
    """

    def __init__(
        self,
        agent: Any,
        user_proxy: Optional[Any] = None,
        group_chat: Optional[Any] = None,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Initialize the AutoGen wrapper.

        Args:
            agent: AutoGen agent (AssistantAgent, etc.)
            user_proxy: Optional UserProxyAgent for conversations
            group_chat: Optional GroupChat for multi-agent scenarios
            chaos_level: Initial chaos level (0.0-1.0)
            max_retries: Default max retries for function calls
            retry_delay: Default retry delay in seconds
        """
        self._agent = agent
        self._user_proxy = user_proxy
        self._group_chat = group_chat
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._function_proxies: dict[str, AutoGenFunctionProxy] = {}
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._reply_count = 0

        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

        self._wrap_functions()

    @property
    def agent(self) -> Any:
        """Get the wrapped agent."""
        return self._agent

    @property
    def user_proxy(self) -> Optional[Any]:
        """Get the user proxy agent."""
        return self._user_proxy

    @property
    def group_chat(self) -> Optional[Any]:
        """Get the group chat."""
        return self._group_chat

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_functions(self):
        """Wrap all functions from the agent's function_map."""
        function_map = getattr(self._agent, "function_map", {})

        if isinstance(function_map, dict):
            for name, func in function_map.items():
                proxy = AutoGenFunctionProxy(
                    func,
                    name=name,
                    chaos_level=self._chaos_level,
                    max_retries=self._max_retries,
                    retry_delay=self._retry_delay,
                )
                self._function_proxies[name] = proxy

                # Replace in the original function_map
                function_map[name] = proxy

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
        Configure chaos injection for all functions.

        Args:
            chaos_level: Base chaos level (0.0-1.0)
            enable_tool_failures: Enable random function failures
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

        # Apply injectors to all function proxies
        for proxy in self._function_proxies.values():
            proxy.clear_injectors()
            for injector in self._injectors:
                proxy.add_injector(injector)

    def add_injector(
        self, injector: BaseInjector, functions: Optional[list[str]] = None
    ):
        """
        Add a custom injector to specific functions or all functions.

        Args:
            injector: The fault injector to add
            functions: List of function names to target, or None for all
        """
        targets = functions or list(self._function_proxies.keys())
        for name in targets:
            if name in self._function_proxies:
                self._function_proxies[name].add_injector(injector)

    def get_wrapped_functions(self) -> dict[str, AutoGenFunctionProxy]:
        """Get dictionary of wrapped functions."""
        return self._function_proxies.copy()

    def initiate_chat(
        self,
        message: str,
        max_turns: Optional[int] = None,
        clear_history: bool = False,
        **kwargs,
    ) -> Any:
        """
        Initiate a chat conversation with chaos injection.

        Args:
            message: The initial message to send
            max_turns: Maximum conversation turns
            clear_history: Whether to clear chat history
            **kwargs: Additional arguments for initiate_chat

        Returns:
            The conversation result
        """
        if self._user_proxy is None:
            raise ValueError("user_proxy is required for initiate_chat")

        chat_kwargs = {"recipient": self._agent, "message": message, **kwargs}

        if max_turns is not None:
            chat_kwargs["max_turns"] = max_turns
        if clear_history:
            chat_kwargs["clear_history"] = clear_history

        return self._user_proxy.initiate_chat(**chat_kwargs)

    def generate_reply(
        self,
        messages: list[dict[str, Any]],
        sender: Optional[Any] = None,
        **kwargs,
    ) -> Any:
        """
        Generate a reply from the agent with chaos injection.

        Args:
            messages: List of message dictionaries
            sender: Optional sender agent
            **kwargs: Additional arguments for generate_reply

        Returns:
            The agent's reply
        """
        self._reply_count += 1

        reply_kwargs = {"messages": messages, **kwargs}
        if sender is not None:
            reply_kwargs["sender"] = sender

        return self._agent.generate_reply(**reply_kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        function_metrics = {}
        for name, proxy in self._function_proxies.items():
            function_metrics[name] = proxy.get_metrics()

        return {
            "reply_count": self._reply_count,
            "functions": function_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> dict[str, Any]:
        """Get MTTR statistics for all functions."""
        function_stats = {}
        for name, proxy in self._function_proxies.items():
            function_stats[name] = proxy._mttr.get_recovery_stats()

        return {
            "functions": function_stats,
            "aggregate": self._mttr.get_recovery_stats(),
        }

    def reset(self):
        """Reset wrapper state."""
        self._reply_count = 0
        for proxy in self._function_proxies.values():
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


class AutoGenMultiAgentWrapper:
    """
    Wrapper for multiple AutoGen agents in a conversation.

    This wrapper manages chaos injection across all agents in a
    multi-agent scenario, such as group chats.
    """

    def __init__(
        self,
        agents: list[Any],
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Initialize the multi-agent wrapper.

        Args:
            agents: List of AutoGen agents
            chaos_level: Initial chaos level (0.0-1.0)
            max_retries: Default max retries
            retry_delay: Default retry delay in seconds
        """
        self._agents = agents
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._agent_wrappers: dict[str, AutoGenWrapper] = {}
        self._metrics = MetricsCollector()

        self._wrap_agents()

    @property
    def agents(self) -> list[Any]:
        """Get the list of wrapped agents."""
        return self._agents

    @property
    def chaos_level(self) -> float:
        """Get the current chaos level."""
        return self._chaos_level

    def _wrap_agents(self):
        """Wrap all agents."""
        for agent in self._agents:
            agent_name = getattr(agent, "name", str(agent))
            wrapper = AutoGenWrapper(
                agent,
                chaos_level=self._chaos_level,
                max_retries=self._max_retries,
                retry_delay=self._retry_delay,
            )
            self._agent_wrappers[agent_name] = wrapper

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        """Configure chaos for all agents."""
        self._chaos_level = chaos_level

        for wrapper in self._agent_wrappers.values():
            wrapper.configure_chaos(
                chaos_level=chaos_level,
                enable_tool_failures=enable_tool_failures,
                enable_delays=enable_delays,
                enable_hallucinations=enable_hallucinations,
                enable_context_corruption=enable_context_corruption,
                enable_budget_exhaustion=enable_budget_exhaustion,
            )

    def get_agent_wrappers(self) -> list[AutoGenWrapper]:
        """Get all agent wrappers."""
        return list(self._agent_wrappers.values())

    def get_agent_wrapper(self, name: str) -> Optional[AutoGenWrapper]:
        """Get a specific agent wrapper by name."""
        return self._agent_wrappers.get(name)

    def get_aggregate_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics from all agents."""
        total_replies = 0
        agent_metrics = {}

        for name, wrapper in self._agent_wrappers.items():
            metrics = wrapper.get_metrics()
            total_replies += metrics.get("reply_count", 0)
            agent_metrics[name] = metrics

        return {
            "total_replies": total_replies,
            "agents": agent_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def reset(self):
        """Reset all agent wrappers."""
        for wrapper in self._agent_wrappers.values():
            wrapper.reset()
        self._metrics.reset()
