"""Chaos testing examples for Claude Agent SDK research agent.

This example demonstrates how to stress-test the research agent with different
levels of chaos injection. It shows:

1. Escalating chaos levels - Test reliability at different failure rates
2. Targeted tool failures - Inject failures on specific tools
3. MTTR measurement - Calculate mean time to recovery
4. Recovery patterns - Analyze how the agent recovers from failures

No API key is required — all examples use deterministic mock tools.

Usage:
    python claude_sdk_research_chaos_example.py
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balaganagent.injectors import ToolFailureInjector
from balaganagent.injectors.tool_failure import ToolFailureConfig
from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_research_tools import get_research_tools


# ---------------------------------------------------------------------------
# Example 1: Escalating Chaos Levels
# ---------------------------------------------------------------------------


def example_escalating_chaos():
    """Test research agent reliability under increasing chaos levels.

    This example runs the research workflow at different chaos levels:
    - 0.0: No chaos (baseline)
    - 0.25: Low chaos (minimal failures)
    - 0.5: Medium chaos (50% expected failure rate on failures)
    - 0.75: High chaos (severe failures)
    - 1.0: Maximum chaos (extreme failures)

    Shows how agent resilience degradates with increasing failure rates.
    """
    print("\n" + "=" * 70)
    print("Example 1: Escalating Chaos Levels")
    print("=" * 70 + "\n")

    topic = "artificial intelligence safety"
    chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    results = {}

    for level in chaos_levels:
        print(f"\n--- Chaos Level {level} ---")

        # Create wrapper and configure chaos
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=level)
        wrapper.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=False,
        )

        tools = wrapper.get_wrapped_tools()

        # Simulate research workflow
        attempt = 0
        successes = 0
        max_attempts = 3  # Try each phase up to 3 times

        with wrapper.experiment(f"escalating-chaos-{level}"):
            wrapper.record_query()

            # Phase 1: Search
            for attempt_num in range(1, max_attempts + 1):
                try:
                    result = tools["search_web"]({"query": topic})
                    successes += 1
                    print(f"  Search (attempt {attempt_num}): ✓")
                    break
                except Exception as e:
                    print(f"  Search (attempt {attempt_num}): ✗ {str(e)[:40]}")

            # Phase 2: Summarize
            for attempt_num in range(1, max_attempts + 1):
                try:
                    result = tools["summarize_text"]({"text": f"Research on {topic}"})
                    successes += 1
                    print(f"  Summarize (attempt {attempt_num}): ✓")
                    break
                except Exception as e:
                    print(f"  Summarize (attempt {attempt_num}): ✗ {str(e)[:40]}")

            # Phase 3: Save report
            for attempt_num in range(1, max_attempts + 1):
                try:
                    result = tools["save_report"]({"content": f"Report on {topic}"})
                    successes += 1
                    print(f"  Save report (attempt {attempt_num}): ✓")
                    break
                except Exception as e:
                    print(f"  Save report (attempt {attempt_num}): ✗ {str(e)[:40]}")

        # Collect metrics
        metrics = wrapper.get_metrics()
        mttr = wrapper.get_mttr_stats()

        ops = metrics["aggregate"]["operations"]
        print(f"\n  Metrics:")
        print(f"    Total operations: {ops['total']}")
        print(f"    Success rate: {ops['success_rate']:.1%}")
        print(f"    Average latency: {ops.get('avg_latency_ms', 0):.1f}ms")

        if mttr["aggregate"].get("recovery_events"):
            print(f"    MTTR: {mttr['aggregate'].get('mttr_seconds', 0):.2f}s")

        results[level] = {"metrics": metrics, "mttr": mttr}

    # Print summary table
    print(f"\n{'=' * 70}")
    print("Summary Table")
    print(f"{'=' * 70}\n")

    print(f"{'Level':<10} {'Success Rate':<20} {'Avg Latency':<20} {'Status':<15}")
    print("-" * 65)

    for level in chaos_levels:
        result = results[level]
        ops = result["metrics"]["aggregate"]["operations"]
        success_rate = ops["success_rate"]
        avg_latency = ops.get("avg_latency_ms", 0)

        status = "✓ OK" if success_rate > 0.5 else "⚠ DEGRADED" if success_rate > 0.2 else "✗ FAILED"

        print(
            f"{level:<10.2f} {success_rate:<20.1%} "
            f"{avg_latency:<20.1f}ms {status:<15}"
        )

    print()


# ---------------------------------------------------------------------------
# Example 2: Targeted Tool-Specific Failures
# ---------------------------------------------------------------------------


def example_targeted_tool_failures():
    """Inject failures on specific tools to isolate failure modes.

    This example injects failures only on the search_web tool to see how
    the agent behaves when search fails but other tools work normally.
    """
    print("\n" + "=" * 70)
    print("Example 2: Targeted Tool-Specific Failures")
    print("=" * 70 + "\n")

    tools_to_test = ["search_web", "summarize_text", "save_report"]

    print("Testing failure isolation on individual tools:\n")

    for target_tool in tools_to_test:
        print(f"--- Injecting 50% failures on {target_tool} ---\n")

        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)

        # Inject 50% failure rate on target tool only
        injector = ToolFailureInjector(ToolFailureConfig(probability=0.5))
        wrapper.add_injector(injector, tools=[target_tool])

        tools = wrapper.get_wrapped_tools()

        # Run 10 calls to the target tool
        successes = 0
        failures = 0

        for i in range(10):
            try:
                if target_tool == "search_web":
                    tools[target_tool]({"query": f"query {i}"})
                elif target_tool == "summarize_text":
                    tools[target_tool]({"text": f"text {i}"})
                else:  # save_report
                    tools[target_tool]({"content": f"content {i}"})

                successes += 1
                print(f"  Call {i + 1}: ✓")
            except Exception as e:
                failures += 1
                print(f"  Call {i + 1}: ✗")

        print(f"\nResults: {successes} successes, {failures} failures")
        print(f"Success rate: {successes / 10:.1%}\n")


# ---------------------------------------------------------------------------
# Example 3: MTTR (Mean Time To Recovery) Analysis
# ---------------------------------------------------------------------------


def example_mttr_analysis():
    """Analyze Mean Time To Recovery (MTTR) with retries.

    This example shows how the built-in retry mechanism helps the agent
    recover from transient failures, and how MTTR is calculated.
    """
    print("\n" + "=" * 70)
    print("Example 3: MTTR (Mean Time To Recovery) Analysis")
    print("=" * 70 + "\n")

    wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.7)

    # Inject 40% failure rate with retries enabled
    injector = ToolFailureInjector(ToolFailureConfig(probability=0.4))
    wrapper.add_injector(injector, tools=["search_web"])

    tools = wrapper.get_wrapped_tools()

    print("Running 20 searches with 40% failure rate (max 3 retries each):\n")

    for i in range(20):
        try:
            result = tools["search_web"]({"query": f"topic {i}"})
            print(f"  Search {i + 1}: ✓")
        except Exception as e:
            print(f"  Search {i + 1}: ✗ (exhausted retries)")

    # Analyze MTTR
    mttr_stats = wrapper.get_mttr_stats()
    search_mttr = mttr_stats["tools"].get("search_web", {})
    aggregate_mttr = mttr_stats["aggregate"]

    print(f"\n{'=' * 70}")
    print("MTTR Analysis")
    print(f"{'=' * 70}\n")

    if aggregate_mttr.get("recovery_events"):
        print(f"Total recovery events: {aggregate_mttr['recovery_events']}")
        print(f"Mean Time To Recovery: {aggregate_mttr.get('mttr_seconds', 0):.2f}s")
        print(f"Min recovery time: {aggregate_mttr.get('min_recovery_seconds', 0):.2f}s")
        print(f"Max recovery time: {aggregate_mttr.get('max_recovery_seconds', 0):.2f}s")
    else:
        print("No recovery events recorded")

    if search_mttr.get("recovery_events"):
        print(f"\nTool-specific (search_web):")
        print(f"  Recovery events: {search_mttr['recovery_events']}")
        print(f"  MTTR: {search_mttr.get('mttr_seconds', 0):.2f}s")

    print()


# ---------------------------------------------------------------------------
# Example 4: Resilience Patterns
# ---------------------------------------------------------------------------


def example_resilience_patterns():
    """Identify resilience patterns and breaking points.

    This example tests the agent at progressively higher chaos levels
    and identifies where it starts to fail consistently.
    """
    print("\n" + "=" * 70)
    print("Example 4: Resilience Patterns")
    print("=" * 70 + "\n")

    print("Testing to find resilience breaking points:\n")

    chaos_levels = [0.3, 0.5, 0.7, 0.9, 1.2, 1.5]
    breaking_point = None

    for level in chaos_levels:
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=level)
        wrapper.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=False,
        )

        tools = wrapper.get_wrapped_tools()

        # Try to complete full workflow
        successes = 0
        max_attempts = 5

        for _ in range(max_attempts):
            try:
                tools["search_web"]({"query": "test"})
                tools["summarize_text"]({"text": "test"})
                tools["save_report"]({"content": "test"})
                successes += 1
            except Exception:
                pass

        success_rate = successes / max_attempts
        print(f"Chaos level {level:>4.1f}: {success_rate:>4.0%} success rate", end="")

        if success_rate > 0.8:
            print(" ✓ ACCEPTABLE")
        elif success_rate > 0.5:
            print(" ⚠ DEGRADED")
        else:
            print(" ✗ UNACCEPTABLE")
            if breaking_point is None:
                breaking_point = level

    if breaking_point:
        print(f"\n⚠️  Breaking point detected at chaos level {breaking_point}")
    else:
        print("\n✓ Agent resilient across all tested chaos levels")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    """Run all chaos testing examples."""
    print("\n" + "#" * 70)
    print("#  CLAUDE AGENT SDK RESEARCH - CHAOS TESTING EXAMPLES")
    print("#" * 70)

    try:
        example_escalating_chaos()
        example_targeted_tool_failures()
        example_mttr_analysis()
        example_resilience_patterns()

        print("\n" + "#" * 70)
        print("#  ALL EXAMPLES COMPLETED")
        print("#" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
