"""Chaos injection via Claude Agent SDK PreToolUse/PostToolUse hooks.

This module provides ``ChaosHookEngine`` — a chaos engine that plugs into the
SDK's hook system to inject faults into *built-in* tools (WebSearch, Write,
Read, Bash, Glob, Task, etc.) without needing custom ``@tool`` functions.

Usage::

    from balaganagent.hooks import ChaosHookEngine

    engine = ChaosHookEngine(chaos_level=0.5)
    engine.configure_chaos(enable_tool_failures=True, enable_delays=True)

    options = ClaudeAgentOptions(
        ...,
        hooks=engine.get_hook_matchers(),
    )
"""

import asyncio
import time
from contextlib import contextmanager
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
from ..injectors.base import FaultType
from ..metrics import MetricsCollector, MTTRCalculator


class ChaosHookEngine:
    """Chaos engine that injects faults via SDK PreToolUse/PostToolUse hooks.

    Unlike ``ClaudeAgentSDKWrapper`` which wraps custom ``@tool`` functions,
    this engine works with *any* tool (including built-in SDK tools) by
    intercepting calls at the hook level.

    The engine produces ``HookMatcher``-compatible hook dicts via
    :meth:`get_hook_matchers` that can be passed directly to
    ``ClaudeAgentOptions(hooks=...)``.
    """

    def __init__(
        self,
        chaos_level: float = 0.5,
        target_tools: Optional[list[str]] = None,
        exclude_tools: Optional[list[str]] = None,
    ):
        self._chaos_level = chaos_level
        self._target_tools = target_tools
        self._exclude_tools = exclude_tools or []
        self._injectors: list[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

        # Track timing across pre/post hooks keyed by tool_use_id
        self._pending_calls: dict[str, dict[str, Any]] = {}

        # Track last fault per tool for MTTR recovery detection
        self._last_fault: dict[str, str] = {}

        # Experiment support
        self._experiments: list[Experiment] = []
        self._experiment_results: list[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def chaos_level(self) -> float:
        return self._chaos_level

    # ------------------------------------------------------------------
    # Chaos configuration
    # ------------------------------------------------------------------

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        """Configure chaos injection. Mirrors ``ClaudeAgentSDKWrapper.configure_chaos``."""
        from ..injectors.budget import BudgetExhaustionConfig
        from ..injectors.context import ContextCorruptionConfig
        from ..injectors.delay import DelayConfig
        from ..injectors.hallucination import HallucinationConfig
        from ..injectors.tool_failure import ToolFailureConfig

        self._chaos_level = chaos_level
        self._injectors.clear()
        base_prob = 0.1 * chaos_level

        if enable_tool_failures:
            cfg = ToolFailureConfig(probability=base_prob)
            if self._target_tools:
                cfg.target_tools = list(self._target_tools)
            cfg.exclude_tools = list(self._exclude_tools)
            self._injectors.append(ToolFailureInjector(cfg))

        if enable_delays:
            cfg = DelayConfig(probability=base_prob * 2)
            if self._target_tools:
                cfg.target_tools = list(self._target_tools)
            cfg.exclude_tools = list(self._exclude_tools)
            self._injectors.append(DelayInjector(cfg))

        if enable_hallucinations:
            cfg = HallucinationConfig(probability=base_prob * 0.5)
            if self._target_tools:
                cfg.target_tools = list(self._target_tools)
            cfg.exclude_tools = list(self._exclude_tools)
            self._injectors.append(HallucinationInjector(cfg))

        if enable_context_corruption:
            cfg = ContextCorruptionConfig(probability=base_prob * 0.3)
            if self._target_tools:
                cfg.target_tools = list(self._target_tools)
            cfg.exclude_tools = list(self._exclude_tools)
            self._injectors.append(ContextCorruptionInjector(cfg))

        if enable_budget_exhaustion:
            cfg = BudgetExhaustionConfig(probability=base_prob)
            if self._target_tools:
                cfg.target_tools = list(self._target_tools)
            cfg.exclude_tools = list(self._exclude_tools)
            self._injectors.append(BudgetExhaustionInjector(cfg))

    def add_injector(self, injector: BaseInjector):
        """Add a custom injector."""
        self._injectors.append(injector)

    # ------------------------------------------------------------------
    # Hook callbacks
    # ------------------------------------------------------------------

    async def pre_tool_use_hook(self, hook_input: dict, tool_use_id: str, context: Any) -> dict:
        """PreToolUse hook — runs before every tool invocation.

        Can:
        - Block the call by returning ``{'continue_': False, 'tool_response': ...}``
        - Add a delay before the call proceeds
        - Corrupt tool input args
        """
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})

        # Record start time
        self._pending_calls[tool_use_id] = {
            "tool_name": tool_name,
            "start_time": time.time(),
        }

        ctx = {"tool_name": tool_name, "args": (tool_input,), "kwargs": {}}

        for injector in self._injectors:
            if not injector.should_inject(tool_name):
                continue

            fault_type = injector.fault_type.value

            # Delay: sleep then continue
            if injector.fault_type == FaultType.DELAY:
                result, details = injector.inject(tool_name, ctx)
                # The delay injector typically returns the delay amount
                delay_seconds = details.get("delay_seconds", 0.5)
                await asyncio.sleep(delay_seconds)
                self._metrics.record_operation(
                    tool_name, delay_seconds * 1000, success=True, fault_type=fault_type
                )
                continue

            # Context corruption: modify tool_input
            if injector.fault_type == FaultType.CONTEXT_CORRUPTION:
                result, details = injector.inject(tool_name, ctx)
                if isinstance(result, dict):
                    # Return modified input
                    self._metrics.record_operation(
                        tool_name, 0, success=True, fault_type=fault_type
                    )
                    return {"continue_": True, "tool_input": result}
                continue

            # Tool failure / budget exhaustion: block the call
            if injector.fault_type in (FaultType.TOOL_FAILURE, FaultType.BUDGET_EXHAUSTION):
                error_msg = f"Chaos injection: {fault_type}"
                try:
                    result, details = injector.inject(tool_name, ctx)
                    error_msg = details.get("error", error_msg)
                except Exception as e:
                    # ToolFailureInjector may raise exceptions — catch and convert
                    error_msg = str(e)

                duration = (time.time() - self._pending_calls[tool_use_id]["start_time"]) * 1000
                self._metrics.record_operation(
                    tool_name, duration, success=False, fault_type=fault_type
                )
                self._mttr.record_failure(tool_name, fault_type)
                self._last_fault[tool_name] = fault_type
                self._pending_calls.pop(tool_use_id, None)

                return {
                    "continue_": False,
                    "tool_response": {
                        "type": "error",
                        "error": error_msg,
                        "chaos_injected": True,
                        "fault_type": fault_type,
                    },
                }

        return {"continue_": True}

    async def post_tool_use_hook(self, hook_input: dict, tool_use_id: str, context: Any) -> dict:
        """PostToolUse hook — runs after every tool invocation.

        Can:
        - Corrupt tool output (hallucination injection)
        - Record timing metrics and MTTR recovery
        """
        pending = self._pending_calls.pop(tool_use_id, None)
        if not pending:
            return {"continue_": True}

        tool_name = pending["tool_name"]
        duration = (time.time() - pending["start_time"]) * 1000
        tool_response = hook_input.get("tool_response")

        # Check for hallucination injection on the output
        ctx = {"tool_name": tool_name, "result": tool_response}
        for injector in self._injectors:
            if injector.fault_type != FaultType.HALLUCINATION:
                continue
            if not injector.should_inject(tool_name):
                continue

            result, details = injector.inject(tool_name, ctx)
            if result is not None:
                self._metrics.record_operation(
                    tool_name, duration, success=True, fault_type="hallucination"
                )
                # Record recovery from previous fault if any
                if tool_name in self._last_fault:
                    self._mttr.record_recovery(
                        tool_name, self._last_fault.pop(tool_name),
                        recovery_method="retry", retries=0, success=True,
                    )
                return {"continue_": True, "tool_response": result}

        # Normal success — record metrics
        self._metrics.record_operation(tool_name, duration, success=True)

        # Record MTTR recovery if this tool had a previous fault
        if tool_name in self._last_fault:
            self._mttr.record_recovery(
                tool_name, self._last_fault.pop(tool_name),
                recovery_method="retry", retries=0, success=True,
            )

        return {"continue_": True}

    # ------------------------------------------------------------------
    # Hook matcher generation
    # ------------------------------------------------------------------

    def get_hook_matchers(self) -> dict:
        """Return a hooks dict for ``ClaudeAgentOptions(hooks=...)``.

        Returns a dict with ``PreToolUse`` and ``PostToolUse`` keys, each
        containing a list with a single ``HookMatcher``-style dict.

        Note: The caller should import ``HookMatcher`` from ``claude_agent_sdk``
        and wrap these if needed, or pass the raw async callables.
        """
        return {
            "PreToolUse": [{"matcher": None, "hooks": [self.pre_tool_use_hook]}],
            "PostToolUse": [{"matcher": None, "hooks": [self.post_tool_use_hook]}],
        }

    def get_hooks_for_options(self) -> dict:
        """Return hooks formatted to merge with existing hooks lists.

        Usage::

            existing_hooks = {...}
            chaos_hooks = engine.get_hooks_for_options()
            # Merge:
            for key in chaos_hooks:
                existing_hooks.setdefault(key, []).extend(chaos_hooks[key])
        """
        return self.get_hook_matchers()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics.get_summary()

    def get_mttr_stats(self) -> dict[str, Any]:
        return self._mttr.get_recovery_stats()

    def reset(self):
        self._metrics.reset()
        self._mttr.reset()
        self._pending_calls.clear()
        self._last_fault.clear()
        for injector in self._injectors:
            injector.reset()

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """Context manager for a named chaos experiment."""
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
