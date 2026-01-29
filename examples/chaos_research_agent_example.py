"""Chaos testing the Claude Agent SDK research agent with BalaganAgent.

This example demonstrates two-level chaos injection on the multi-agent
research system from ``claude-agent-sdk-demos/research_agent/``:

- **Level 1 (hooks)**: Injects tool failures, delays, hallucinations,
  and context corruption into built-in SDK tools (WebSearch, Write, etc.)
- **Level 2 (client)**: Injects prompt corruption, query delays, and
  API failures at the ClaudeSDKClient level.

Usage::

    # Basic chaos test
    python examples/chaos_research_agent_example.py

    # Higher chaos level
    python examples/chaos_research_agent_example.py --chaos-level 0.8

    # Run all test modes
    python examples/chaos_research_agent_example.py --test-mode all

Dependencies:
    - balaganagent
    - claude-agent-sdk
    - python-dotenv
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balaganagent.wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Config:
    topic: str = "artificial intelligence"
    chaos_level: float = 0.5
    test_mode: str = "basic"  # basic | escalating | all
    verbose: bool = True


def _log(msg: str, verbose: bool = True):
    if verbose:
        print(msg)


# ---------------------------------------------------------------------------
# Example 1: Basic hook-level chaos (no API key needed — mock mode)
# ---------------------------------------------------------------------------


def example_basic_hook_chaos(config: Config):
    """Demonstrate ChaosHookEngine with simulated hook calls.

    This runs without an API key by simulating the hook call cycle
    that the SDK would perform during agent execution.
    """
    from balaganagent.hooks import ChaosHookEngine

    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 1: Hook-Based Tool Chaos (simulated)", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Chaos Level: {config.chaos_level}\n", config.verbose)

    engine = ChaosHookEngine(chaos_level=config.chaos_level)
    engine.configure_chaos(
        chaos_level=config.chaos_level,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=True,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    # Simulate SDK tool calls by invoking hooks directly
    tools_to_simulate = [
        ("WebSearch", {"query": config.topic}),
        ("Write", {"file_path": "/tmp/notes.md", "content": "Research notes..."}),
        ("Read", {"file_path": "/tmp/notes.md"}),
        ("Bash", {"command": "echo 'generating chart...'"}),
        ("Write", {"file_path": "/tmp/report.pdf", "content": "Final report..."}),
    ]

    successes = 0
    failures = 0

    with engine.experiment(f"hook-chaos-{config.chaos_level}"):
        for i, (tool_name, tool_input) in enumerate(tools_to_simulate):
            tool_use_id = f"tool_{i}"
            hook_input = {"tool_name": tool_name, "tool_input": tool_input}

            # PreToolUse
            pre_result = asyncio.get_event_loop().run_until_complete(
                engine.pre_tool_use_hook(hook_input, tool_use_id, None)
            )

            if not pre_result.get("continue_", True):
                failures += 1
                fault = pre_result.get("tool_response", {}).get("fault_type", "unknown")
                _log(f"  {tool_name}: BLOCKED ({fault})", config.verbose)
                continue

            # Simulate tool execution (would normally happen in the SDK)
            tool_response = {"type": "text", "text": f"Result from {tool_name}"}

            # PostToolUse
            post_input = {"tool_name": tool_name, "tool_response": tool_response}
            post_result = asyncio.get_event_loop().run_until_complete(
                engine.post_tool_use_hook(post_input, tool_use_id, None)
            )

            if "tool_response" in post_result and post_result["tool_response"] != tool_response:
                _log(f"  {tool_name}: SUCCESS (output corrupted by hallucination)", config.verbose)
            else:
                _log(f"  {tool_name}: SUCCESS", config.verbose)
            successes += 1

    metrics = engine.get_metrics()
    _log(f"\nResults: {successes}/{successes + failures} succeeded", config.verbose)
    _log(f"Metrics: {metrics.get('operations', {})}", config.verbose)
    _log("", config.verbose)


# ---------------------------------------------------------------------------
# Example 2: Escalating chaos levels
# ---------------------------------------------------------------------------


def example_escalating_chaos(config: Config):
    """Test hook-based chaos at escalating levels."""
    from balaganagent.hooks import ChaosHookEngine

    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 2: Escalating Hook Chaos Levels", config.verbose)
    _log("=" * 70 + "\n", config.verbose)

    chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    tools = [
        ("WebSearch", {"query": "test"}),
        ("Write", {"file_path": "/tmp/test.md", "content": "test"}),
        ("Read", {"file_path": "/tmp/test.md"}),
    ]

    _log(f"{'Level':<10} {'Success':<15} {'Rate':<10}", config.verbose)
    _log("-" * 35, config.verbose)

    for level in chaos_levels:
        engine = ChaosHookEngine(chaos_level=level)
        engine.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=False,  # Skip delays for speed
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        successes = 0
        total = len(tools) * 5  # 5 rounds

        for _round in range(5):
            for i, (tool_name, tool_input) in enumerate(tools):
                tool_use_id = f"tool_{_round}_{i}"
                hook_input = {"tool_name": tool_name, "tool_input": tool_input}

                pre_result = asyncio.get_event_loop().run_until_complete(
                    engine.pre_tool_use_hook(hook_input, tool_use_id, None)
                )

                if pre_result.get("continue_", True):
                    post_input = {"tool_name": tool_name, "tool_response": {"text": "ok"}}
                    asyncio.get_event_loop().run_until_complete(
                        engine.post_tool_use_hook(post_input, tool_use_id, None)
                    )
                    successes += 1

        rate = successes / total if total > 0 else 0
        _log(f"{level:<10.2f} {successes}/{total:<13} {rate:<10.1%}", config.verbose)

    _log("", config.verbose)


# ---------------------------------------------------------------------------
# Example 3: Full integration (requires API key)
# ---------------------------------------------------------------------------


async def example_full_integration(config: Config):
    """Full two-level chaos integration with the real research agent.

    Requires ANTHROPIC_API_KEY to be set.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _log("\nSkipping full integration (no ANTHROPIC_API_KEY set)", config.verbose)
        _log("Set ANTHROPIC_API_KEY to run this example.\n", config.verbose)
        return

    try:
        from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition, HookMatcher
    except ImportError:
        _log("\nSkipping full integration (claude-agent-sdk not installed)\n", config.verbose)
        return

    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 3: Full Two-Level Chaos Integration", config.verbose)
    _log("=" * 70, config.verbose)

    # Load prompts from research agent
    prompts_dir = Path(__file__).parent.parent / "claude-agent-sdk-demos" / "research_agent" / "prompts"

    def load_prompt(filename: str) -> str:
        with open(prompts_dir / filename, "r") as f:
            return f.read().strip()

    # Set up chaos integration
    chaos = ClaudeSDKChaosIntegration(
        chaos_level=config.chaos_level,
        exclude_tools=["Task"],  # Don't inject chaos on Task (subagent spawning)
        client_chaos_config={
            "prompt_corruption_rate": 0.1,
            "query_delay_range": (0.0, 1.0),
            "api_failure_rate": 0.05,
        },
    )
    chaos.configure_chaos(
        chaos_level=config.chaos_level,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=True,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    # Build agent definitions (same as research_agent/agent.py)
    agents = {
        "researcher": AgentDefinition(
            description="Research agent that searches the web for information.",
            tools=["WebSearch", "Write"],
            prompt=load_prompt("researcher.txt"),
            model="haiku",
        ),
        "data-analyst": AgentDefinition(
            description="Data analyst that creates charts and analysis.",
            tools=["Glob", "Read", "Bash", "Write"],
            prompt=load_prompt("data_analyst.txt"),
            model="haiku",
        ),
        "report-writer": AgentDefinition(
            description="Report writer that creates PDF reports.",
            tools=["Skill", "Write", "Glob", "Read", "Bash"],
            prompt=load_prompt("report_writer.txt"),
            model="haiku",
        ),
    }

    # Build options with chaos hooks merged in
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        setting_sources=["project"],
        system_prompt=load_prompt("lead_agent.txt"),
        allowed_tools=["Task"],
        agents=agents,
        hooks=chaos.get_hooks(),
        model="haiku",
    )

    # Run experiment
    with chaos.experiment("research-agent-resilience"):
        try:
            async with chaos.create_client(options, inject_hooks=False) as client:
                await client.query(prompt=f"Research {config.topic} and create a brief report")
                async for msg in client.receive_response():
                    if hasattr(msg, "content"):
                        for block in getattr(msg, "content", []):
                            if hasattr(block, "text"):
                                _log(block.text, config.verbose)
        except (RuntimeError, TimeoutError) as e:
            _log(f"\nClient-level chaos triggered: {e}", config.verbose)

    # Report
    report = chaos.get_report()
    _log("\n--- Chaos Report ---", config.verbose)
    for exp in report["experiments"]:
        _log(f"Experiment: {exp['name']}", config.verbose)
        _log(f"  Status: {exp['status']}", config.verbose)
        _log(f"  Duration: {exp['duration_seconds']:.1f}s", config.verbose)

    metrics = report["metrics"]
    _log(f"\nTool-level metrics: {metrics.get('tool_level', {})}", config.verbose)
    _log(f"Tool MTTR: {metrics.get('tool_mttr', {})}", config.verbose)
    _log("", config.verbose)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Chaos test the research agent")
    parser.add_argument("--topic", default="artificial intelligence")
    parser.add_argument("--chaos-level", type=float, default=0.5)
    parser.add_argument(
        "--test-mode",
        choices=["basic", "escalating", "full", "all"],
        default="basic",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    config = Config(
        topic=args.topic,
        chaos_level=args.chaos_level,
        test_mode=args.test_mode,
        verbose=not args.quiet,
    )

    _log("\n" + "#" * 70, config.verbose)
    _log("#  BALAGAN AGENT - RESEARCH AGENT CHAOS TESTING (HOOKS)", config.verbose)
    _log("#" * 70, config.verbose)

    if config.test_mode in ("basic", "all"):
        example_basic_hook_chaos(config)
    if config.test_mode in ("escalating", "all"):
        example_escalating_chaos(config)
    if config.test_mode in ("full", "all"):
        asyncio.run(example_full_integration(config))

    _log("#" * 70, config.verbose)
    _log("#  CHAOS TESTING COMPLETED", config.verbose)
    _log("#" * 70 + "\n", config.verbose)


if __name__ == "__main__":
    main()
