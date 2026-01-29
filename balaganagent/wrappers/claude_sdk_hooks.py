"""Unified chaos integration for Claude Agent SDK agents using built-in tools.

Combines hook-based tool chaos (Level 1) and client-level chaos (Level 2)
into a single integration class.

Usage::

    from balaganagent.wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration

    chaos = ClaudeSDKChaosIntegration(chaos_level=0.5)
    chaos.configure_chaos(enable_tool_failures=True, enable_delays=True)

    options = ClaudeAgentOptions(
        ...,
        hooks=chaos.merge_hooks(existing_hooks),
    )

    with chaos.experiment("resilience-test"):
        async with chaos.create_client(options) as client:
            await client.query(prompt="...")
            async for msg in client.receive_response():
                ...

    report = chaos.get_report()
"""

from contextlib import contextmanager
from typing import Any, Optional

from ..experiment import Experiment, ExperimentConfig, ExperimentResult
from ..hooks.chaos_hooks import ChaosHookEngine
from .claude_sdk_client import ChaosClaudeSDKClient


class ClaudeSDKChaosIntegration:
    """Unified chaos integration combining hook-level and client-level chaos.

    This is the recommended entry point for chaos-testing Claude Agent SDK
    agents that use built-in tools (WebSearch, Write, Read, Bash, etc.).
    """

    def __init__(
        self,
        chaos_level: float = 0.5,
        target_tools: Optional[list[str]] = None,
        exclude_tools: Optional[list[str]] = None,
        client_chaos_config: Optional[dict[str, Any]] = None,
    ):
        self._hook_engine = ChaosHookEngine(
            chaos_level=chaos_level,
            target_tools=target_tools,
            exclude_tools=exclude_tools,
        )
        self._client_config = client_chaos_config or {}
        self._experiment_results: list[ExperimentResult] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure_chaos(self, **kwargs):
        """Configure tool-level chaos. Passed through to ``ChaosHookEngine``."""
        self._hook_engine.configure_chaos(**kwargs)

    def configure_client_chaos(
        self,
        prompt_corruption_rate: float = 0.0,
        query_delay_range: tuple[float, float] = (0.0, 0.0),
        api_failure_rate: float = 0.0,
        timeout_rate: float = 0.0,
    ):
        """Configure client-level chaos parameters."""
        self._client_config = {
            "prompt_corruption_rate": prompt_corruption_rate,
            "query_delay_range": query_delay_range,
            "api_failure_rate": api_failure_rate,
            "timeout_rate": timeout_rate,
        }

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def get_hooks(self) -> dict:
        """Return chaos hook matchers for ``ClaudeAgentOptions(hooks=...)``."""
        return self._hook_engine.get_hook_matchers()

    def merge_hooks(self, existing_hooks: Optional[dict] = None) -> dict:
        """Merge chaos hooks with existing hooks.

        Args:
            existing_hooks: Existing hooks dict from ``ClaudeAgentOptions``.

        Returns:
            Merged hooks dict with chaos hooks appended.
        """
        chaos_hooks = self._hook_engine.get_hooks_for_options()
        if not existing_hooks:
            return chaos_hooks

        merged = dict(existing_hooks)
        for key, matchers in chaos_hooks.items():
            merged.setdefault(key, []).extend(matchers)
        return merged

    # ------------------------------------------------------------------
    # Client creation
    # ------------------------------------------------------------------

    def create_client(
        self,
        options: Any,
        inject_hooks: bool = True,
    ) -> ChaosClaudeSDKClient:
        """Create a ``ChaosClaudeSDKClient`` with chaos hooks injected.

        Args:
            options: ``ClaudeAgentOptions`` instance.
            inject_hooks: If True, merge chaos hooks into options.hooks
                before creating the client.

        Returns:
            A ``ChaosClaudeSDKClient`` ready for use as an async context manager.
        """
        if inject_hooks and hasattr(options, "hooks"):
            options.hooks = self.merge_hooks(getattr(options, "hooks", None))

        return ChaosClaudeSDKClient(
            options=options,
            chaos_level=self._hook_engine.chaos_level,
            **self._client_config,
        )

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """Context manager for a named chaos experiment.

        Wraps ``ChaosHookEngine.experiment`` and collects results.
        """
        config = ExperimentConfig(name=name, **config_kwargs)
        exp = Experiment(config)
        self._hook_engine._current_experiment = exp
        self._hook_engine._experiments.append(exp)

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
            self._hook_engine._current_experiment = None

    def get_experiment_results(self) -> list[ExperimentResult]:
        return self._experiment_results.copy()

    # ------------------------------------------------------------------
    # Metrics / reporting
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict[str, Any]:
        """Get combined metrics from both levels."""
        return {
            "tool_level": self._hook_engine.get_metrics(),
            "tool_mttr": self._hook_engine.get_mttr_stats(),
        }

    def get_report(self) -> dict[str, Any]:
        """Generate a summary report of all experiments and metrics."""
        return {
            "experiments": [
                {
                    "name": r.config.name if hasattr(r, "config") else str(r),
                    "status": r.status.value if hasattr(r, "status") else "unknown",
                    "duration_seconds": r.duration_seconds if hasattr(r, "duration_seconds") else 0,
                }
                for r in self._experiment_results
            ],
            "metrics": self.get_metrics(),
        }

    def reset(self):
        """Reset all state."""
        self._hook_engine.reset()
        self._experiment_results.clear()
