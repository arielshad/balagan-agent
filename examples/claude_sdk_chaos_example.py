#!/usr/bin/env python3
"""Chaos-testing a Claude Agent SDK agent with BalaganAgent.

This example shows how to:
1. Build an agent following Claude Agent SDK conventions.
2. Wrap it with ``ClaudeAgentSDKWrapper`` for chaos injection.
3. Run chaos experiments and inspect reliability metrics.

No external API keys are required — all tools are deterministic.
"""

from __future__ import annotations

from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_agent import build_research_agent


def example_basic_chaos():
    """Wrap an agent with chaos and call its tools."""
    print("\n" + "=" * 60)
    print("Example 1: Basic chaos injection on Claude Agent SDK agent")
    print("=" * 60 + "\n")

    agent = build_research_agent()
    wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.5)

    wrapper.configure_chaos(
        chaos_level=0.5,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=False,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    tools = wrapper.get_wrapped_tools()
    print("Making 10 search_web calls with chaos injection...")
    for i in range(10):
        try:
            tools["search_web"](f"query {i}")
            print(f"  Call {i + 1}: Success")
        except Exception as e:
            print(f"  Call {i + 1}: Failed - {e}")

    metrics = wrapper.get_metrics()
    print("\nMetrics:")
    for name, m in metrics.get("tools", {}).items():
        ops = m.get("operations", {})
        print(
            f"  {name}: total={ops.get('total', 0)}, "
            f"success_rate={ops.get('success_rate', 0):.1%}"
        )


def example_experiment():
    """Run a named chaos experiment."""
    print("\n" + "=" * 60)
    print("Example 2: Chaos experiment with Claude Agent SDK agent")
    print("=" * 60 + "\n")

    agent = build_research_agent()
    wrapper = ClaudeAgentSDKWrapper(agent, chaos_level=0.0)

    with wrapper.experiment("claude-sdk-chaos"):
        result = wrapper.run("artificial intelligence")
        print(f"Agent output: {result}")

    results = wrapper.get_experiment_results()
    print(f"\nExperiment '{results[0].config.name}' completed.")


def example_tool_failure_injection():
    """Inject targeted tool failures."""
    print("\n" + "=" * 60)
    print("Example 3: Targeted tool-failure injection")
    print("=" * 60 + "\n")

    from balaganagent.injectors import ToolFailureInjector
    from balaganagent.injectors.tool_failure import ToolFailureConfig

    agent = build_research_agent()
    wrapper = ClaudeAgentSDKWrapper(agent)

    injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
    wrapper.add_injector(injector, tools=["search_web"])

    tools = wrapper.get_wrapped_tools()
    result = tools["search_web"]("test")
    print(f"search_web (100% failure injector): {result}")

    result = tools["save_report"]("hello world")
    print(f"save_report (no injector):          {result}")


def main():
    print("\n" + "#" * 60)
    print("#  CLAUDE AGENT SDK + BALAGANAGENT CHAOS EXAMPLES")
    print("#" * 60)

    example_basic_chaos()
    example_experiment()
    example_tool_failure_injection()

    print("\n" + "#" * 60)
    print("#  ALL EXAMPLES COMPLETED")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
