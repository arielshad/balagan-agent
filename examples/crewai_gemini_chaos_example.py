"""BalaganAgent Example — Testing CrewAI Gemini Research Agent with Chaos Engineering.

This script demonstrates how to apply chaos engineering to the CrewAI research agent
using the BalaganAgent framework. It shows various failure scenarios and how agents
handle degraded conditions.

Key Chaos Scenarios:
  1. Tool Failures — Random failures in search_web, summarize_text, or save_report
  2. Latency Injection — Simulating slow tool responses
  3. Partial Failures — Some tools work, others fail intermittently
  4. Data Corruption — Tools return malformed or incomplete data

Dependencies:
  - balaganagent
  - crewai>=0.28.0
  - langchain-google-genai
  - python-dotenv

Usage:
  python examples/crewai_gemini_chaos_example.py
  python examples/crewai_gemini_chaos_example.py --scenario latency
  python examples/crewai_gemini_chaos_example.py --scenario all
  python examples/crewai_gemini_chaos_example.py --scenario failures --verbose
"""

from __future__ import annotations

import argparse
import sys
import time

# Import the research agent components
from crewai_gemini_research_agent import (
    build_research_crew,
    get_gemini_llm,
)

try:
    from balaganagent import set_verbose
    from balaganagent.wrappers.crewai import CrewAIWrapper
except ImportError:
    print("❌ BalaganAgent not installed. Install with: pip install -e .")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Chaos Scenario Configurations
# ---------------------------------------------------------------------------


def scenario_tool_failures(topic: str = "quantum computing", verbose: bool = False):
    """Scenario 1: Random tool failures.

    Tests how the agent handles when tools randomly fail 50% of the time.
    The agent should either retry, use alternative approaches, or gracefully degrade.
    """
    print("\n" + "=" * 70)
    print("🔧 SCENARIO 1: Tool Failures (50% failure rate)")
    print("=" * 70)
    print(f"Topic: {topic}")
    print("Testing: How agents handle when tools randomly fail")
    if verbose:
        print("Verbose mode: ON")
    print()

    try:
        llm = get_gemini_llm()
        crew = build_research_crew(topic=topic, llm=llm)

        # Wrap with BalaganAgent - configure 50% tool failure rate
        wrapper = CrewAIWrapper(crew, chaos_level=0.5, verbose=verbose)
        wrapper.configure_chaos(
            chaos_level=5.0,  # High chaos level for 50% failure rate
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        print("Starting chaotic execution...")
        start_time = time.time()

        result = wrapper.kickoff()

        elapsed = time.time() - start_time

        print(f"\n✅ Execution completed in {elapsed:.2f}s")
        print("\nAgent Output:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        # Show chaos statistics
        metrics = wrapper.get_metrics()
        print("\n📊 Chaos Statistics:")
        print(f"Kickoff count: {metrics['kickoff_count']}")

        # Calculate aggregate success rate
        total_calls = 0
        total_failures = 0
        for tool_name, tool_metrics in metrics["tools"].items():
            ops = tool_metrics.get("operations", {})
            total_calls += ops.get("total", 0)
            total_failures += ops.get("failed", 0)

        if total_calls > 0:
            success_rate = ((total_calls - total_failures) / total_calls) * 100
            print(f"Total tool calls: {total_calls}")
            print(f"Failed calls: {total_failures}")
            print(f"Success rate: {success_rate:.1f}%")

    except Exception as e:
        print(f"\n❌ Crew failed to complete: {e}")
        print("This shows the agent couldn't handle this chaos level!")


def scenario_latency_injection(topic: str = "blockchain", verbose: bool = False):
    """Scenario 2: Latency injection.

    Tests how the agent performs when tools have artificial delays.
    Useful for understanding timeout behavior and user experience degradation.
    """
    print("\n" + "=" * 70)
    print("⏱️  SCENARIO 2: Latency Injection (1-3 second delays)")
    print("=" * 70)
    print(f"Topic: {topic}")
    print("Testing: Agent performance with slow tool responses")
    if verbose:
        print("Verbose mode: ON")
    print()

    try:
        llm = get_gemini_llm()
        crew = build_research_crew(topic=topic, llm=llm)

        # Wrap with BalaganAgent - add delays
        wrapper = CrewAIWrapper(crew, chaos_level=0.3, verbose=verbose)
        wrapper.configure_chaos(
            chaos_level=3.0,  # High chaos level for frequent delays
            enable_tool_failures=False,
            enable_delays=True,  # Enable latency injection
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        print("Starting chaotic execution with latency...")
        start_time = time.time()

        result = wrapper.kickoff()

        elapsed = time.time() - start_time

        print(f"\n✅ Execution completed in {elapsed:.2f}s (with artificial delays)")
        print("\nAgent Output:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        metrics = wrapper.get_metrics()
        print("\n📊 Performance Impact:")
        print(f"Total execution time: {elapsed:.2f}s")

        # Calculate average latency
        total_latency = 0.0
        total_calls = 0
        for tool_name, tool_metrics in metrics["tools"].items():
            latency = tool_metrics.get("latency", {})
            count = tool_metrics.get("operations", {}).get("total", 0)
            mean_ms = latency.get("mean_ms", 0)
            total_latency += mean_ms * count
            total_calls += count

        if total_calls > 0:
            avg_latency = total_latency / total_calls
            print(f"Average latency per call: {avg_latency:.0f}ms")

    except Exception as e:
        print(f"\n❌ Crew failed: {e}")


def scenario_partial_failures(topic: str = "machine learning", verbose: bool = False):
    """Scenario 3: Partial/intermittent failures.

    Some tools work reliably, others fail intermittently.
    Tests agent's ability to work with partially degraded tooling.
    """
    print("\n" + "=" * 70)
    print("⚡ SCENARIO 3: Partial Failures (search_web fails 70%)")
    print("=" * 70)
    print(f"Topic: {topic}")
    print("Testing: Agent adaptation when primary tool is unreliable")
    if verbose:
        print("Verbose mode: ON")
    print()

    try:
        llm = get_gemini_llm()
        crew = build_research_crew(topic=topic, llm=llm)

        # Wrap with high chaos for partial degradation
        # This simulates the primary research tool being unreliable
        wrapper = CrewAIWrapper(crew, chaos_level=0.7, verbose=verbose)
        wrapper.configure_chaos(
            chaos_level=7.0,  # Very high chaos level
            enable_tool_failures=True,
            enable_delays=False,
            enable_hallucinations=False,
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )

        print("Starting execution with partial tool degradation...")
        start_time = time.time()

        result = wrapper.kickoff()

        elapsed = time.time() - start_time

        print(f"\n✅ Execution completed in {elapsed:.2f}s")
        print("\nAgent Output:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        metrics = wrapper.get_metrics()
        print("\n📊 Chaos Statistics:")

        # Show per-tool failure rates
        for tool_name, tool_metrics in metrics["tools"].items():
            ops = tool_metrics.get("operations", {})
            total = ops.get("total", 0)
            failed = ops.get("failed", 0)
            if total > 0:
                failure_rate = (failed / total) * 100
                print(f"  {tool_name}: {total} calls, {failed} failures ({failure_rate:.1f}%)")

    except Exception as e:
        print(f"\n❌ Crew failed: {e}")


def scenario_data_corruption(topic: str = "cybersecurity", verbose: bool = False):
    """Scenario 4: Data corruption.

    Tools return incomplete or malformed data instead of failing cleanly.
    Tests agent's ability to handle garbage inputs and validate tool outputs.
    """
    print("\n" + "=" * 70)
    print("🗑️  SCENARIO 4: Data Corruption (garbled outputs)")
    print("=" * 70)
    print(f"Topic: {topic}")
    print("Testing: Agent resilience to malformed tool outputs")
    if verbose:
        print("Verbose mode: ON")
    print()

    try:
        llm = get_gemini_llm()
        crew = build_research_crew(topic=topic, llm=llm)

        # Wrap with BalaganAgent - enable hallucinations (data corruption)
        wrapper = CrewAIWrapper(crew, chaos_level=0.3, verbose=verbose)
        wrapper.configure_chaos(
            chaos_level=3.0,
            enable_tool_failures=False,
            enable_delays=False,
            enable_hallucinations=True,  # Return corrupted/hallucinated data
            enable_context_corruption=True,  # Also corrupt inputs
            enable_budget_exhaustion=False,
        )

        print("Starting execution with data corruption...")
        start_time = time.time()

        result = wrapper.kickoff()

        elapsed = time.time() - start_time

        print(f"\n✅ Execution completed in {elapsed:.2f}s")
        print("\nAgent Output:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        metrics = wrapper.get_metrics()
        print("\n📊 Chaos Statistics:")

        # Count corrupted operations
        corrupted_count = 0
        for tool_name, tool_metrics in metrics["tools"].items():
            faults = tool_metrics.get("faults", {})
            corrupted_count += faults.get("hallucination", 0)
            corrupted_count += faults.get("context_corruption", 0)

        print(f"Corrupted operations: {corrupted_count}")

    except Exception as e:
        print(f"\n❌ Crew failed: {e}")


def scenario_stress_test(topic: str = "artificial intelligence", verbose: bool = False):
    """Scenario 5: Stress test with multiple chaos factors.

    Combines failures, latency, and high load to see breaking points.
    """
    print("\n" + "=" * 70)
    print("💥 SCENARIO 5: Stress Test (combined chaos factors)")
    print("=" * 70)
    print(f"Topic: {topic}")
    print("Testing: Agent under maximum stress")
    if verbose:
        print("Verbose mode: ON")
    print()

    try:
        llm = get_gemini_llm()
        crew = build_research_crew(topic=topic, llm=llm)

        # Maximum chaos: enable all injectors
        wrapper = CrewAIWrapper(crew, chaos_level=0.4, verbose=verbose)
        wrapper.configure_chaos(
            chaos_level=4.0,  # High chaos across all dimensions
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=True,
            enable_context_corruption=True,
            enable_budget_exhaustion=True,
        )

        print("Starting stress test...")
        start_time = time.time()

        result = wrapper.kickoff()

        elapsed = time.time() - start_time

        print(f"\n✅ Stress test completed in {elapsed:.2f}s")
        print("\nAgent Output:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        metrics = wrapper.get_metrics()
        print("\n📊 Stress Test Results:")

        # Calculate aggregate statistics
        total_calls = 0
        total_failures = 0
        total_latency = 0.0
        fault_counts: dict[str, int] = {}

        for tool_name, tool_metrics in metrics["tools"].items():
            ops = tool_metrics.get("operations", {})
            total_calls += ops.get("total", 0)
            total_failures += ops.get("failed", 0)

            latency = tool_metrics.get("latency", {})
            mean_ms = latency.get("mean_ms", 0)
            count = ops.get("total", 0)
            total_latency += mean_ms * count

            faults = tool_metrics.get("faults", {})
            for fault_type, count in faults.items():
                fault_counts[fault_type] = fault_counts.get(fault_type, 0) + count

        print(f"Total tool calls: {total_calls}")
        print(f"Failed calls: {total_failures}")
        if total_calls > 0:
            survival_rate = ((total_calls - total_failures) / total_calls) * 100
            print(f"Agent survival rate: {survival_rate:.1f}%")
            print(f"Total latency added: {total_latency / 1000:.2f}s")

        print("\nFault breakdown:")
        for fault_type, count in sorted(fault_counts.items()):
            print(f"  {fault_type}: {count}")

    except Exception as e:
        print(f"\n❌ Stress test failed: {e}")
        print("Agent reached breaking point under stress!")


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------


def main():
    """Run chaos engineering scenarios on CrewAI research agent."""
    parser = argparse.ArgumentParser(
        description="Test CrewAI research agent with chaos engineering"
    )
    parser.add_argument(
        "--scenario",
        choices=["failures", "latency", "partial", "corruption", "stress", "all"],
        default="failures",
        help="Which chaos scenario to run (default: failures)",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Research topic (default: varies by scenario)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output showing tool calls, faults, and retries",
    )

    args = parser.parse_args()

    # Enable verbose mode globally if requested
    if args.verbose:
        set_verbose(True)

    print("\n" + "=" * 70)
    print("🌪️  BalaganAgent — CrewAI Research Agent Chaos Testing")
    print("=" * 70)

    try:
        # Verify API key is set
        get_gemini_llm()

        scenarios = {
            "failures": (scenario_tool_failures, "quantum computing"),
            "latency": (scenario_latency_injection, "blockchain"),
            "partial": (scenario_partial_failures, "machine learning"),
            "corruption": (scenario_data_corruption, "cybersecurity"),
            "stress": (scenario_stress_test, "artificial intelligence"),
        }

        if args.scenario == "all":
            print("\n🎯 Running ALL chaos scenarios...\n")
            for name, (func, default_topic) in scenarios.items():
                topic = args.topic or default_topic
                func(topic, verbose=args.verbose)
                time.sleep(1)  # Brief pause between scenarios
        else:
            func, default_topic = scenarios[args.scenario]
            topic = args.topic or default_topic
            func(topic, verbose=args.verbose)

        print("\n" + "=" * 70)
        print("✅ Chaos testing completed!")
        print("=" * 70)
        print("\n💡 Key Insights:")
        print("  • Agents can continue operating under tool failures")
        print("  • Latency affects user experience but not correctness")
        print("  • Partial degradation reveals dependency patterns")
        print("  • Data validation is crucial for corrupted outputs")
        print()

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure your .env file contains:")
        print("  GOOGLE_API_KEY=your_api_key_here")
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Dependency error: {e}")
        print("\nInstall required packages:")
        print("  pip install balaganagent crewai langchain-google-genai python-dotenv")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
