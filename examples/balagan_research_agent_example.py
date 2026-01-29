"""Example of using BalaganAgent chaos testing with research_agent multi-agent system.

This example demonstrates how to integrate the BalaganAgent chaos framework with the
Claude Agent SDK's multi-agent research_agent system. It shows:

1. Wrapping research tools with chaos injection
2. Running the research workflow with failure injection
3. Analyzing resilience metrics across different chaos levels
4. Measuring MTTR (Mean Time To Recovery) and reliability

The research_agent workflow:
1. Gather research information via search
2. Summarize findings
3. Generate and save a research report

With chaos injection:
- Tool failures can be injected at configurable rates
- Delays can simulate network latency
- Reliability metrics are collected automatically
- MTTR helps identify recovery patterns

Usage:
    # Run basic chaos workflow
    python balagan_research_agent_example.py

    # Run with specific topic
    python balagan_research_agent_example.py --topic "quantum computing"

    # Run with custom chaos level (0.0-2.0)
    python balagan_research_agent_example.py --chaos-level 0.75

Dependencies:
    - balaganagent (chaos framework)
    - claude-agent-sdk (Claude SDK integration)
    - python-dotenv (environment variables)
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from balaganagent.injectors import ToolFailureInjector
from balaganagent.injectors.tool_failure import ToolFailureConfig
from examples.claude_sdk_research_tools import get_research_tools


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ChaosResearchConfig:
    """Configuration for chaos-testing research agent."""

    topic: str = "artificial intelligence"
    chaos_level: float = 0.5
    output_dir: str = "chaos_reports"
    verbose: bool = True
    test_mode: str = "basic"  # basic | escalating | targeted | mttr | resilience

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> ChaosResearchConfig:
        """Create config from parsed CLI arguments."""
        return cls(
            topic=args.topic,
            chaos_level=args.chaos_level,
            output_dir=args.output_dir,
            verbose=not args.quiet,
            test_mode=args.test_mode,
        )


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool = True):
    """Print message if verbose."""
    if verbose:
        print(msg)


def _create_output_dir(output_dir: str):
    """Create output directory if it doesn't exist."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)


# ---------------------------------------------------------------------------
# Example 1: Basic Chaos Injection
# ---------------------------------------------------------------------------


def example_basic_chaos(config: ChaosResearchConfig):
    """Run research workflow with chaos injection enabled.

    This example shows the simplest way to add chaos testing to a research workflow:
    1. Create wrapper with tools and chaos level
    2. Configure chaos parameters (which types of failures to inject)
    3. Get wrapped tools and use them normally
    4. Collect metrics after execution
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 1: Basic Chaos Injection", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Topic: {config.topic}", config.verbose)
    _log(f"Chaos Level: {config.chaos_level}\n", config.verbose)

    # Create wrapper and configure chaos
    wrapper = ClaudeAgentSDKWrapper(
        tools=get_research_tools(mode="mock"),
        chaos_level=config.chaos_level
    )

    wrapper.configure_chaos(
        chaos_level=config.chaos_level,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=False,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    tools = wrapper.get_wrapped_tools()

    # Run research workflow
    results = {
        "success": True,
        "phases": {}
    }

    _log("Running research workflow phases...\n", config.verbose)

    # Phase 1: Search
    _log("Phase 1: Searching for information", config.verbose)
    search_text = None
    try:
        with wrapper.experiment(f"basic-chaos-{config.chaos_level}"):
            wrapper.record_query()
            result = tools["search_web"]({"query": config.topic})
            if isinstance(result, dict) and "content" in result:
                search_text = result["content"][0]["text"]
            else:
                search_text = str(result)
            results["phases"]["search"] = "✓ Success"
            _log("  ✓ Search completed\n", config.verbose)
    except Exception as e:
        results["phases"]["search"] = f"✗ Failed: {str(e)[:50]}"
        results["success"] = False
        _log(f"  ✗ Search failed: {e}\n", config.verbose)
        return results

    # Phase 2: Summarize
    _log("Phase 2: Summarizing findings", config.verbose)
    summary_text = None
    try:
        result = tools["summarize_text"]({"text": search_text or "research findings"})
        if isinstance(result, dict) and "content" in result:
            summary_text = result["content"][0]["text"]
        else:
            summary_text = str(result)
        results["phases"]["summary"] = "✓ Success"
        _log("  ✓ Summarization completed\n", config.verbose)
    except Exception as e:
        results["phases"]["summary"] = f"✗ Failed: {str(e)[:50]}"
        results["success"] = False
        _log(f"  ✗ Summarization failed: {e}\n", config.verbose)
        return results

    # Phase 3: Generate Report
    _log("Phase 3: Generating report", config.verbose)
    try:
        report_content = (
            f"# Research Report: {config.topic}\n\n"
            f"## Search Results\n\n{search_text or 'No search results'}\n\n"
            f"## Summary\n\n{summary_text or 'No summary'}\n"
        )

        report_filename = os.path.join(
            config.output_dir,
            f"report_{config.topic.replace(' ', '_')}_chaos.md"
        )

        result = tools["save_report"](
            {"content": report_content, "filename": report_filename}
        )
        if isinstance(result, dict) and "content" in result:
            report_msg = result["content"][0]["text"]
        else:
            report_msg = str(result)
        results["phases"]["report"] = "✓ Success"
        _log(f"  ✓ {report_msg}\n", config.verbose)
    except Exception as e:
        results["phases"]["report"] = f"✗ Failed: {str(e)[:50]}"
        results["success"] = False
        _log(f"  ✗ Report generation failed: {e}\n", config.verbose)
        return results

    # Collect and display metrics
    metrics = wrapper.get_metrics()
    mttr = wrapper.get_mttr_stats()

    _log("Results:", config.verbose)
    for phase, status in results["phases"].items():
        _log(f"  {phase}: {status}", config.verbose)

    ops = metrics["aggregate"]["operations"]
    _log("\nMetrics:", config.verbose)
    _log(f"  Total operations: {ops['total']}", config.verbose)
    _log(f"  Success rate: {ops['success_rate']:.1%}", config.verbose)
    _log(f"  Avg latency: {ops.get('avg_latency_ms', 0):.1f}ms", config.verbose)

    if mttr["aggregate"].get("recovery_events"):
        _log(f"  Recovery events: {mttr['aggregate']['recovery_events']}", config.verbose)
        _log(f"  MTTR: {mttr['aggregate'].get('mttr_seconds', 0):.2f}s", config.verbose)

    _log("", config.verbose)
    return results


# ---------------------------------------------------------------------------
# Example 2: Escalating Chaos Levels
# ---------------------------------------------------------------------------


def example_escalating_chaos(config: ChaosResearchConfig):
    """Test research workflow at increasing chaos levels.

    This example shows how reliability metrics change as chaos intensity increases.
    It helps identify at what point the system starts to fail.
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 2: Escalating Chaos Levels", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Topic: {config.topic}\n", config.verbose)

    chaos_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    results_by_level = {}

    _log(f"{'Level':<10} {'Phases':<30} {'Success Rate':<15}", config.verbose)
    _log("-" * 55, config.verbose)

    for level in chaos_levels:
        wrapper = ClaudeAgentSDKWrapper(
            tools=get_research_tools(mode="mock"),
            chaos_level=level
        )

        wrapper.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=True,
        )

        tools = wrapper.get_wrapped_tools()

        successes = 0
        total_phases = 3

        with wrapper.experiment(f"escalating-{level}"):
            wrapper.record_query()

            try:
                tools["search_web"]({"query": config.topic})
                successes += 1
            except Exception:
                pass

            try:
                tools["summarize_text"]({"text": "research findings"})
                successes += 1
            except Exception:
                pass

            try:
                tools["save_report"]({"content": "report content"})
                successes += 1
            except Exception:
                pass

        metrics = wrapper.get_metrics()
        ops = metrics["aggregate"]["operations"]
        success_rate = ops["success_rate"]

        phase_status = f"{successes}/{total_phases}"
        results_by_level[level] = success_rate

        status_icon = "✓" if success_rate > 0.5 else "⚠" if success_rate > 0.2 else "✗"

        _log(
            f"{level:<10.2f} {phase_status:<30} {success_rate:<15.1%} {status_icon}",
            config.verbose
        )

    _log("", config.verbose)
    return results_by_level


# ---------------------------------------------------------------------------
# Example 3: Targeted Tool Failures
# ---------------------------------------------------------------------------


def example_targeted_failures(config: ChaosResearchConfig):
    """Inject failures on specific tools to isolate failure modes.

    This example shows how to test the impact of individual tool failures,
    which helps understand critical dependencies.
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 3: Targeted Tool Failures", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Testing failure isolation on individual tools\n", config.verbose)

    tools_to_test = ["search_web", "summarize_text", "save_report"]
    results_by_tool = {}

    for target_tool in tools_to_test:
        _log(f"Injecting 50% failure rate on {target_tool}:", config.verbose)

        wrapper = ClaudeAgentSDKWrapper(
            tools=get_research_tools(mode="mock"),
            chaos_level=0.5
        )

        # Inject 50% failure rate on this specific tool only
        injector = ToolFailureInjector(ToolFailureConfig(probability=0.5))
        wrapper.add_injector(injector, tools=[target_tool])

        tools = wrapper.get_wrapped_tools()

        successes = 0
        for i in range(10):
            try:
                if target_tool == "search_web":
                    tools[target_tool]({"query": f"query {i}"})
                elif target_tool == "summarize_text":
                    tools[target_tool]({"text": f"text {i}"})
                else:  # save_report
                    tools[target_tool]({"content": f"content {i}"})

                successes += 1
            except Exception:
                pass

        success_rate = successes / 10
        results_by_tool[target_tool] = success_rate

        _log(f"  Success rate: {success_rate:.1%} ({successes}/10)", config.verbose)

    _log("", config.verbose)
    return results_by_tool


# ---------------------------------------------------------------------------
# Example 4: MTTR Analysis
# ---------------------------------------------------------------------------


def example_mttr_analysis(config: ChaosResearchConfig):
    """Analyze Mean Time To Recovery (MTTR) with retries.

    This example shows how the built-in retry mechanism helps the system
    recover from transient failures.
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 4: MTTR (Mean Time To Recovery) Analysis", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Running searches with 40% failure rate (max 3 retries each)\n", config.verbose)

    wrapper = ClaudeAgentSDKWrapper(
        tools=get_research_tools(mode="mock"),
        chaos_level=0.7
    )

    # Inject 40% failure rate with retries enabled
    injector = ToolFailureInjector(ToolFailureConfig(probability=0.4))
    wrapper.add_injector(injector, tools=["search_web"])

    tools = wrapper.get_wrapped_tools()

    successes = 0
    for i in range(20):
        try:
            tools["search_web"]({"query": f"topic {i}"})
            successes += 1
        except Exception:
            pass

    # Analyze MTTR
    mttr_stats = wrapper.get_mttr_stats()
    aggregate_mttr = mttr_stats["aggregate"]

    _log("MTTR Results:", config.verbose)
    if aggregate_mttr.get("recovery_events"):
        _log(f"  Total recovery events: {aggregate_mttr['recovery_events']}", config.verbose)
        _log(f"  Mean Time To Recovery: {aggregate_mttr.get('mttr_seconds', 0):.2f}s", config.verbose)
        _log(f"  Min recovery time: {aggregate_mttr.get('min_recovery_seconds', 0):.2f}s", config.verbose)
        _log(f"  Max recovery time: {aggregate_mttr.get('max_recovery_seconds', 0):.2f}s", config.verbose)
    else:
        _log("  No recovery events recorded", config.verbose)

    _log(f"\nSuccess rate: {successes}/20 ({successes/20:.1%})", config.verbose)
    _log("", config.verbose)

    return aggregate_mttr


# ---------------------------------------------------------------------------
# Example 5: Resilience Patterns
# ---------------------------------------------------------------------------


def example_resilience_patterns(config: ChaosResearchConfig):
    """Identify resilience patterns and breaking points.

    This example tests at progressively higher chaos levels to find where
    the system starts to fail consistently.
    """
    _log("\n" + "=" * 70, config.verbose)
    _log("EXAMPLE 5: Resilience Patterns", config.verbose)
    _log("=" * 70, config.verbose)
    _log(f"Testing to find resilience breaking points\n", config.verbose)

    chaos_levels = [0.3, 0.5, 0.7, 0.9, 1.2, 1.5]
    breaking_point = None

    _log(f"{'Chaos Level':<15} {'Workflow Success':<25} {'Status':<15}", config.verbose)
    _log("-" * 55, config.verbose)

    for level in chaos_levels:
        wrapper = ClaudeAgentSDKWrapper(
            tools=get_research_tools(mode="mock"),
            chaos_level=level
        )

        wrapper.configure_chaos(
            chaos_level=level,
            enable_tool_failures=True,
            enable_delays=True,
        )

        tools = wrapper.get_wrapped_tools()

        # Try to complete full workflow 5 times
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

        if success_rate > 0.8:
            status = "✓ ACCEPTABLE"
        elif success_rate > 0.5:
            status = "⚠ DEGRADED"
        else:
            status = "✗ UNACCEPTABLE"
            if breaking_point is None:
                breaking_point = level

        _log(f"{level:<15.1f} {successes}/{max_attempts} ({success_rate:<15.0%}) {status}", config.verbose)

    if breaking_point:
        _log(f"\n⚠️  Breaking point detected at chaos level {breaking_point}", config.verbose)
    else:
        _log(f"\n✓ System resilient across all tested chaos levels", config.verbose)

    _log("", config.verbose)
    return breaking_point


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def main():
    """Run selected chaos testing example."""
    args = parse_args()
    config = ChaosResearchConfig.from_args(args)

    # Create output directory
    _create_output_dir(config.output_dir)

    _log("\n" + "#" * 70, config.verbose)
    _log("#  BALAGAN AGENT + RESEARCH AGENT CHAOS TESTING", config.verbose)
    _log("#" * 70, config.verbose)

    try:
        if config.test_mode == "basic":
            example_basic_chaos(config)
        elif config.test_mode == "escalating":
            example_escalating_chaos(config)
        elif config.test_mode == "targeted":
            example_targeted_failures(config)
        elif config.test_mode == "mttr":
            example_mttr_analysis(config)
        elif config.test_mode == "resilience":
            example_resilience_patterns(config)
        elif config.test_mode == "all":
            example_basic_chaos(config)
            example_escalating_chaos(config)
            example_targeted_failures(config)
            example_mttr_analysis(config)
            example_resilience_patterns(config)
        else:
            _log(f"Unknown test mode: {config.test_mode}", config.verbose)
            return 1

        _log("#" * 70, config.verbose)
        _log("#  CHAOS TESTING COMPLETED", config.verbose)
        _log("#" * 70 + "\n", config.verbose)

        return 0

    except Exception as e:
        _log(f"\n❌ Error: {e}", True)
        import traceback
        traceback.print_exc()
        return 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="BalaganAgent chaos testing with research_agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Run basic chaos test\n"
            "  python balagan_research_agent_example.py\n\n"
            "  # Run escalating chaos levels\n"
            "  python balagan_research_agent_example.py --test-mode escalating\n\n"
            "  # Run all tests with custom topic\n"
            "  python balagan_research_agent_example.py --test-mode all "
            "--topic 'machine learning' --chaos-level 0.75\n\n"
            "  # Analyze resilience patterns\n"
            "  python balagan_research_agent_example.py --test-mode resilience\n"
        ),
    )

    parser.add_argument(
        "--topic",
        type=str,
        default="artificial intelligence",
        help="Research topic (default: 'artificial intelligence')",
    )

    parser.add_argument(
        "--chaos-level",
        type=float,
        default=0.5,
        help="Base chaos level: 0.0-2.0 (default: 0.5)",
    )

    parser.add_argument(
        "--test-mode",
        choices=["basic", "escalating", "targeted", "mttr", "resilience", "all"],
        default="basic",
        help="Which chaos test to run (default: basic)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="chaos_reports",
        help="Directory for output (default: chaos_reports)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )

    return parser.parse_args()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
