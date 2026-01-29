"""Tests for ChaosHookEngine and ChaosClaudeSDKClient."""

import asyncio
import pytest

from balaganagent.hooks.chaos_hooks import ChaosHookEngine
from balaganagent.wrappers.claude_sdk_client import ChaosClaudeSDKClient
from balaganagent.wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration


# ---------------------------------------------------------------------------
# ChaosHookEngine tests
# ---------------------------------------------------------------------------


class TestChaosHookEngine:
    """Tests for hook-based chaos injection."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_no_chaos_passes_through(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        hook_input = {"tool_name": "WebSearch", "tool_input": {"query": "test"}}
        result = self._run(engine.pre_tool_use_hook(hook_input, "id1", None))
        assert result["continue_"] is True

    def test_high_chaos_injects_failures(self):
        engine = ChaosHookEngine(chaos_level=2.0)
        engine.configure_chaos(
            chaos_level=2.0,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        blocked = 0
        for i in range(50):
            hook_input = {"tool_name": "WebSearch", "tool_input": {"query": f"q{i}"}}
            result = self._run(engine.pre_tool_use_hook(hook_input, f"id_{i}", None))
            if not result.get("continue_", True):
                blocked += 1

        # With chaos_level=2.0, base_prob=0.2 for tool failures
        # Over 50 calls we should see some blocked
        assert blocked > 0

    def test_post_hook_records_metrics(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        # Pre hook to register the call
        hook_input = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test"}}
        self._run(engine.pre_tool_use_hook(hook_input, "id1", None))

        # Post hook
        post_input = {"tool_name": "Read", "tool_response": {"text": "content"}}
        result = self._run(engine.post_tool_use_hook(post_input, "id1", None))
        assert result["continue_"] is True

        metrics = engine.get_metrics()
        assert metrics["operations"]["total"] >= 1

    def test_exclude_tools(self):
        engine = ChaosHookEngine(chaos_level=2.0, exclude_tools=["Task"])
        engine.configure_chaos(
            chaos_level=2.0,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        # Task tool should never be blocked
        for i in range(20):
            hook_input = {"tool_name": "Task", "tool_input": {"prompt": "test"}}
            result = self._run(engine.pre_tool_use_hook(hook_input, f"task_{i}", None))
            assert result["continue_"] is True

    def test_experiment_context_manager(self):
        engine = ChaosHookEngine(chaos_level=0.5)
        engine.configure_chaos(chaos_level=0.5)

        with engine.experiment("test-experiment"):
            hook_input = {"tool_name": "Write", "tool_input": {"file_path": "/tmp/test"}}
            self._run(engine.pre_tool_use_hook(hook_input, "id1", None))

        results = engine.get_experiment_results()
        assert len(results) == 1

    def test_reset_clears_state(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        hook_input = {"tool_name": "Read", "tool_input": {}}
        self._run(engine.pre_tool_use_hook(hook_input, "id1", None))
        self._run(engine.post_tool_use_hook({"tool_name": "Read", "tool_response": {}}, "id1", None))

        engine.reset()
        metrics = engine.get_metrics()
        assert metrics["operations"]["total"] == 0

    def test_get_hook_matchers_structure(self):
        engine = ChaosHookEngine()
        matchers = engine.get_hook_matchers()

        assert "PreToolUse" in matchers
        assert "PostToolUse" in matchers
        assert len(matchers["PreToolUse"]) == 1
        assert len(matchers["PostToolUse"]) == 1
        assert callable(matchers["PreToolUse"][0]["hooks"][0])
        assert callable(matchers["PostToolUse"][0]["hooks"][0])


# ---------------------------------------------------------------------------
# ChaosClaudeSDKClient tests
# ---------------------------------------------------------------------------


class TestChaosClaudeSDKClient:
    """Tests for client-level chaos (without real SDK)."""

    def test_prompt_corruption(self):
        client = ChaosClaudeSDKClient(
            options=None,
            prompt_corruption_rate=1.0,
            seed=42,
        )
        original = "Research quantum computing advances"
        corrupted = client._corrupt_prompt(original)
        assert corrupted != original

    def test_prompt_corruption_strategies(self):
        """Verify all corruption strategies produce different output."""
        client = ChaosClaudeSDKClient(options=None, seed=0)
        prompt = "one two three four five"

        results = set()
        for seed in range(100):
            client._rng.seed(seed)
            results.add(client._corrupt_prompt(prompt))

        # Should have multiple distinct corruptions
        assert len(results) > 1

    def test_metrics_tracking(self):
        client = ChaosClaudeSDKClient(options=None)
        assert client.query_count == 0
        metrics = client.get_metrics()
        assert metrics["query_count"] == 0

    def test_reset(self):
        client = ChaosClaudeSDKClient(options=None)
        client._query_count = 5
        client.reset()
        assert client.query_count == 0


# ---------------------------------------------------------------------------
# ClaudeSDKChaosIntegration tests
# ---------------------------------------------------------------------------


class TestClaudeSDKChaosIntegration:
    """Tests for the unified integration class."""

    def test_merge_hooks_with_none(self):
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.5)
        merged = chaos.merge_hooks(None)
        assert "PreToolUse" in merged
        assert "PostToolUse" in merged

    def test_merge_hooks_with_existing(self):
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.5)

        async def existing_hook(hi, tid, ctx):
            return {"continue_": True}

        existing = {
            "PreToolUse": [{"matcher": None, "hooks": [existing_hook]}],
        }

        merged = chaos.merge_hooks(existing)
        # Should have both the existing and chaos hooks
        assert len(merged["PreToolUse"]) == 2
        assert "PostToolUse" in merged

    def test_configure_chaos(self):
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.5)
        chaos.configure_chaos(
            chaos_level=0.8,
            enable_tool_failures=True,
            enable_delays=False,
        )
        assert chaos._hook_engine.chaos_level == 0.8

    def test_configure_client_chaos(self):
        chaos = ClaudeSDKChaosIntegration()
        chaos.configure_client_chaos(
            prompt_corruption_rate=0.2,
            api_failure_rate=0.1,
        )
        assert chaos._client_config["prompt_corruption_rate"] == 0.2
        assert chaos._client_config["api_failure_rate"] == 0.1

    def test_get_report_empty(self):
        chaos = ClaudeSDKChaosIntegration()
        report = chaos.get_report()
        assert "experiments" in report
        assert "metrics" in report
        assert len(report["experiments"]) == 0

    def test_reset(self):
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.5)
        chaos.configure_chaos(chaos_level=0.5)
        chaos.reset()
        metrics = chaos.get_metrics()
        assert metrics["tool_level"]["operations"]["total"] == 0
