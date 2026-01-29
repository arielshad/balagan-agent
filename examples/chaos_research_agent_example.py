"""Chaos testing the Claude Agent SDK research agent with BalaganAgent.

This example uses the actual research agent from
``claude-agent-sdk-demos/research_agent/agent.py`` and injects chaos at
two levels:

- **Level 1 (hooks)**: Injects tool failures, delays, hallucinations into
  built-in SDK tools (WebSearch, Write, Read, Bash, etc.) via PreToolUse/
  PostToolUse hooks.
- **Level 2 (client)**: Injects prompt corruption, query delays, and API
  failures at the ClaudeSDKClient level.

Usage::

    # Simulated hook chaos (no API key needed)
    python examples/chaos_research_agent_example.py

    # Escalating chaos levels
    python examples/chaos_research_agent_example.py --test-mode escalating

    # Full integration with real agent (requires ANTHROPIC_API_KEY)
    python examples/chaos_research_agent_example.py --test-mode full

    # All modes
    python examples/chaos_research_agent_example.py --test-mode all
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root and claude-agent-sdk-demos to path so we can import both
# balaganagent and research_agent
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEMOS_DIR = _PROJECT_ROOT / "claude-agent-sdk-demos"
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_DEMOS_DIR))

from balaganagent.hooks import ChaosHookEngine
from balaganagent.wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration
from research_agent.agent import build_agents, build_options


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Config:
    topic: str = "artificial intelligence"
    chaos_level: float = 0.5
    test_mode: str = "basic"  # basic | escalating | full | all
    verbose: bool = True


def _log(msg: str, verbose: bool = True):
    if verbose:
        print(msg)


# ---------------------------------------------------------------------------
# Helper: collect the tool names the research agent actually uses
# ---------------------------------------------------------------------------


def _get_research_agent_tools() -> list[tuple[str, dict]]:
    """Return (tool_name, sample_input) for every tool the research agent uses.

    The tool names come from the real ``build_agents()`` definitions, so this
    stays in sync with any changes to the research agent.
    """
    agents = build_agents()
    seen: dict[str, dict] = {}
    # Example inputs keyed by tool name
    sample_inputs = {
        "WebSearch": {"query": "artificial intelligence breakthroughs"},
        "Write": {"file_path": "/tmp/notes.md", "content": "Research notes..."},
        "Read": {"file_path": "/tmp/notes.md"},
        "Glob": {"pattern": "files/research_notes/*.md"},
        "Bash": {"command": "echo 'generating chart...'"},
        "Skill": {"skill": "pdf"},
        "Task": {"prompt": "research topic", "subagent_type": "researcher"},
    }
    for agent_def in agents.values():
        for tool_name in agent_def.tools:
            if tool_name not in seen:
                seen[tool_name] = sample_inputs.get(tool_name, {})
    return list(seen.items())


# ---------------------------------------------------------------------------
# Example 1: Hook-level chaos using research agent tool definitions
# ---------------------------------------------------------------------------


def example_basic_hook_chaos(config: Config):
    """Inject chaos into the exact tools the research agent uses.

    Simulates the hook call cycle the SDK performs during agent execution,
    using the real tool list from ``research_agent.agent.build_agents()``.
    No API key required.
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 1: Hook-Based Chaos on Research Agent Tools", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Chaos Level: {config.chaos_level}", config.verbose)

    # Get the real tool list from the research agent
    tools = _get_research_agent_tools()
    _log(f"Tools under test: {[t for t, _ in tools]}\n", config.verbose)

    engine = ChaosHookEngine(
        chaos_level=config.chaos_level,
        exclude_tools=["Task"],  # Don't chaos subagent spawning
    )
    engine.configure_chaos(
        chaos_level=config.chaos_level,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=True,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    successes = 0
    failures = 0

    with engine.experiment(f"hook-chaos-{config.chaos_level}"):
        for i, (tool_name, tool_input) in enumerate(tools):
            tool_use_id = f"tool_{i}"
            hook_input = {"tool_name": tool_name, "tool_input": tool_input}

            pre_result = asyncio.get_event_loop().run_until_complete(
                engine.pre_tool_use_hook(hook_input, tool_use_id, None)
            )

            if not pre_result.get("continue_", True):
                failures += 1
                fault = pre_result.get("tool_response", {}).get("fault_type", "unknown")
                _log(f"  {tool_name}: BLOCKED ({fault})", config.verbose)
                continue

            tool_response = {"type": "text", "text": f"Result from {tool_name}"}
            post_input = {"tool_name": tool_name, "tool_response": tool_response}
            post_result = asyncio.get_event_loop().run_until_complete(
                engine.post_tool_use_hook(post_input, tool_use_id, None)
            )

            if "tool_response" in post_result and post_result["tool_response"] != tool_response:
                _log(f"  {tool_name}: SUCCESS (output corrupted)", config.verbose)
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
    """Test research agent tools at escalating chaos levels."""
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 2: Escalating Chaos on Research Agent Tools", config.verbose)
    _log("=" * 70 + "\n", config.verbose)

    tools = _get_research_agent_tools()
    # Filter out Task since we exclude it from chaos
    tools = [(name, inp) for name, inp in tools if name != "Task"]

    chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]

    _log(f"Tools: {[t for t, _ in tools]}", config.verbose)
    _log(f"{'Level':<10} {'Success':<15} {'Rate':<10}", config.verbose)
    _log("-" * 35, config.verbose)

    for level in chaos_levels:
        engine = ChaosHookEngine(chaos_level=level, exclude_tools=["Task"])
        engine.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        successes = 0
        rounds = 5
        total = len(tools) * rounds

        for r in range(rounds):
            for i, (tool_name, tool_input) in enumerate(tools):
                tool_use_id = f"tool_{r}_{i}"
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
# Example 3: Full integration with the real research agent (requires API key)
# ---------------------------------------------------------------------------


async def example_full_integration(config: Config):
    """Run the actual research agent with two-level chaos.

    Uses ``build_agents()`` and ``build_options()`` from the research agent,
    injecting chaos hooks and wrapping the client.

    Requires ``ANTHROPIC_API_KEY`` to be set.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _log("\nSkipping full integration (no ANTHROPIC_API_KEY set)", config.verbose)
        _log("Set ANTHROPIC_API_KEY to run this example.\n", config.verbose)
        return

    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 3: Full Two-Level Chaos on Research Agent", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Topic: {config.topic}", config.verbose)
    _log(f"Chaos Level: {config.chaos_level}\n", config.verbose)

    # Set up chaos integration
    chaos = ClaudeSDKChaosIntegration(
        chaos_level=config.chaos_level,
        exclude_tools=["Task"],
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

    # Build options from the real research agent, with chaos hooks merged in
    agents = build_agents()
    options = build_options(agents=agents, hooks=chaos.get_hooks())

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
    parser = argparse.ArgumentParser(
        description="Chaos test the research agent from claude-agent-sdk-demos"
    )
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
    _log("#  BALAGAN AGENT - RESEARCH AGENT CHAOS TESTING", config.verbose)
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
