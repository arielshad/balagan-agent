#!/usr/bin/env python3
"""Chaos-testing Claude Agent SDK custom tools with BalaganAgent.

This example shows how to:
1. Define custom tools following the Claude Agent SDK ``@tool`` convention.
2. Wrap them with ``ClaudeAgentSDKWrapper`` for chaos injection.
3. Run chaos experiments and inspect reliability metrics.

No API key is required — all tools are deterministic stubs.

In production you would pass the wrapped tools to
``create_sdk_mcp_server()`` and then to ``query()`` or
``ClaudeSDKClient`` via ``ClaudeAgentOptions.mcp_servers``.
"""

from __future__ import annotations

import os
import sys

# Allow running this file directly from the examples/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_agent import get_tool_list


def example_basic_chaos():
    """Wrap custom tools with chaos and invoke them."""
    print("\n" + "=" * 60)
    print("Example 1: Basic chaos injection on SDK custom tools")
    print("=" * 60 + "\n")

    wrapper = ClaudeAgentSDKWrapper(tools=get_tool_list(), chaos_level=0.5)
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
            tools["search_web"]({"query": f"topic {i}"})
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
    print("Example 2: Named chaos experiment")
    print("=" * 60 + "\n")

    wrapper = ClaudeAgentSDKWrapper(tools=get_tool_list(), chaos_level=0.0)

    with wrapper.experiment("claude-sdk-chaos"):
        wrapper.record_query()
        tools = wrapper.get_wrapped_tools()
        result = tools["search_web"]({"query": "artificial intelligence"})
        print(f"search_web result: {result['content'][0]['text'][:60]}...")

    results = wrapper.get_experiment_results()
    print(f"\nExperiment '{results[0].config.name}' completed.")


def example_targeted_failure():
    """Inject targeted tool failures."""
    print("\n" + "=" * 60)
    print("Example 3: Targeted tool-failure injection")
    print("=" * 60 + "\n")

    from balaganagent.injectors import ToolFailureInjector
    from balaganagent.injectors.tool_failure import ToolFailureConfig

    wrapper = ClaudeAgentSDKWrapper(tools=get_tool_list())
    injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
    wrapper.add_injector(injector, tools=["search_web"])

    tools = wrapper.get_wrapped_tools()

    result = tools["search_web"]({"query": "test"})
    print(f"search_web (100% failure injector): {result}")

    result = tools["save_report"]({"content": "hello world"})
    print(f"save_report (no injector):          {result['content'][0]['text']}")

    print("\n--- These wrapped tools are ready for create_sdk_mcp_server() ---")
    wrapped_list = wrapper.get_wrapped_tool_list()
    print(f"Wrapped tool count: {len(wrapped_list)}")


def main():
    print("\n" + "#" * 60)
    print("#  CLAUDE AGENT SDK + BALAGANAGENT CHAOS EXAMPLES")
    print("#" * 60)

    example_basic_chaos()
    example_experiment()
    example_targeted_failure()

    print("\n" + "#" * 60)
    print("#  ALL EXAMPLES COMPLETED")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
