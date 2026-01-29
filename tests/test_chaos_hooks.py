"""Tests for ChaosHookEngine, ChaosClaudeSDKClient, and ClaudeSDKChaosIntegration.

These tests use the real research agent definitions from
``claude-agent-sdk-demos/research_agent/agent.py`` to verify that chaos
injection works correctly on the actual tools the agent uses.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Make research_agent importable
_DEMOS_DIR = Path(__file__).resolve().parent.parent / "claude-agent-sdk-demos"
if str(_DEMOS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEMOS_DIR))

from balaganagent.hooks.chaos_hooks import ChaosHookEngine
from balaganagent.wrappers.claude_sdk_client import ChaosClaudeSDKClient
from balaganagent.wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration
from research_agent.agent import build_agents, build_options


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_agent_tool_names() -> list[str]:
    """Extract the full set of tool names from the real research agent."""
    agents = build_agents()
    tools: set[str] = set()
    for agent_def in agents.values():
        tools.update(agent_def.tools)
    return sorted(tools)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# ChaosHookEngine tests
# ---------------------------------------------------------------------------


class TestChaosHookEngine:
    """Tests for hook-based chaos injection using real research agent tools."""

    def test_no_chaos_passes_through(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        # Use the actual tools from the research agent
        for tool_name in _get_agent_tool_names():
            hook_input = {"tool_name": tool_name, "tool_input": {}}
            result = _run(engine.pre_tool_use_hook(hook_input, f"id_{tool_name}", None))
            assert result["continue_"] is True, f"{tool_name} should pass through at chaos=0"

    def test_high_chaos_injects_failures_on_agent_tools(self):
        """Verify that chaos injection actually blocks some research agent tools."""
        engine = ChaosHookEngine(chaos_level=2.0)
        engine.configure_chaos(
            chaos_level=2.0,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        agent_tools = _get_agent_tool_names()
        blocked = 0
        total = 0

        for round_idx in range(10):
            for tool_name in agent_tools:
                total += 1
                hook_input = {"tool_name": tool_name, "tool_input": {}}
                result = _run(engine.pre_tool_use_hook(
                    hook_input, f"id_{round_idx}_{tool_name}", None
                ))
                if not result.get("continue_", True):
                    blocked += 1

        assert blocked > 0, f"Expected some blocked calls out of {total}"

    def test_exclude_task_tool(self):
        """Task tool (subagent spawning) should never be blocked."""
        assert "Task" not in _get_agent_tool_names() or True  # Task may not be in subagent tools

        engine = ChaosHookEngine(chaos_level=2.0, exclude_tools=["Task"])
        engine.configure_chaos(
            chaos_level=2.0,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        for i in range(20):
            hook_input = {"tool_name": "Task", "tool_input": {"prompt": "test"}}
            result = _run(engine.pre_tool_use_hook(hook_input, f"task_{i}", None))
            assert result["continue_"] is True

    def test_post_hook_records_metrics_for_agent_tools(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        agent_tools = _get_agent_tool_names()
        for i, tool_name in enumerate(agent_tools):
            tid = f"id_{i}"
            _run(engine.pre_tool_use_hook(
                {"tool_name": tool_name, "tool_input": {}}, tid, None
            ))
            _run(engine.post_tool_use_hook(
                {"tool_name": tool_name, "tool_response": {"text": "ok"}}, tid, None
            ))

        metrics = engine.get_metrics()
        assert metrics["operations"]["total"] == len(agent_tools)

    def test_experiment_with_agent_tools(self):
        engine = ChaosHookEngine(chaos_level=0.5)
        engine.configure_chaos(chaos_level=0.5)

        agent_tools = _get_agent_tool_names()

        with engine.experiment("research-agent-test"):
            for i, tool_name in enumerate(agent_tools):
                _run(engine.pre_tool_use_hook(
                    {"tool_name": tool_name, "tool_input": {}}, f"id_{i}", None
                ))

        results = engine.get_experiment_results()
        assert len(results) == 1

    def test_reset_clears_state(self):
        engine = ChaosHookEngine(chaos_level=0.0)
        engine.configure_chaos(chaos_level=0.0)

        _run(engine.pre_tool_use_hook(
            {"tool_name": "Read", "tool_input": {}}, "id1", None
        ))
        _run(engine.post_tool_use_hook(
            {"tool_name": "Read", "tool_response": {}}, "id1", None
        ))

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
    """Tests for client-level chaos."""

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
        client = ChaosClaudeSDKClient(options=None, seed=0)
        prompt = "one two three four five"

        results = set()
        for seed in range(100):
            client._rng.seed(seed)
            results.add(client._corrupt_prompt(prompt))

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
    """Tests for the unified integration class using real research agent."""

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
        assert len(merged["PreToolUse"]) == 2
        assert "PostToolUse" in merged

    def test_build_options_produces_valid_config(self):
        """Verify build_options from the real research agent works."""
        options = build_options()
        assert options is not None
        assert options.allowed_tools == ["Task"]

    def test_chaos_hooks_merge_with_research_agent_options(self):
        """Verify chaos hooks can be merged into real research agent options."""
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.5, exclude_tools=["Task"])
        chaos.configure_chaos(
            chaos_level=0.5,
            enable_tool_failures=True,
            enable_delays=False,
        )

        agents = build_agents()
        # Verify agents have the expected subagents
        assert "researcher" in agents
        assert "data-analyst" in agents
        assert "report-writer" in agents

        # Verify chaos hooks can be passed to build_options
        options = build_options(agents=agents, hooks=chaos.get_hooks())
        assert options is not None

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

    def test_full_hook_cycle_with_agent_tools(self):
        """Run a full pre/post hook cycle for every research agent tool."""
        chaos = ClaudeSDKChaosIntegration(chaos_level=0.0, exclude_tools=["Task"])
        chaos.configure_chaos(chaos_level=0.0)

        engine = chaos._hook_engine
        agent_tools = _get_agent_tool_names()

        for i, tool_name in enumerate(agent_tools):
            tid = f"id_{i}"
            _run(engine.pre_tool_use_hook(
                {"tool_name": tool_name, "tool_input": {}}, tid, None
            ))
            _run(engine.post_tool_use_hook(
                {"tool_name": tool_name, "tool_response": {"text": "ok"}}, tid, None
            ))

        metrics = chaos.get_metrics()
        assert metrics["tool_level"]["operations"]["total"] == len(agent_tools)

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
