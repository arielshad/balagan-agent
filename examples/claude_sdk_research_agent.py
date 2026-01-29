"""Research agent built with Claude Agent SDK and BalaganAgent chaos framework.

This example demonstrates a research workflow with optional chaos injection:
1. Search web for information on a topic
2. Summarize findings
3. Generate and save a research report

The agent can run in three modes:
- mock: Deterministic tools (no API keys needed)
- production: Real Claude Agent SDK integration
- chaos: Mock tools with failure injection for reliability testing

Usage:
    # Mock mode (default)
    python claude_sdk_research_agent.py --topic "AI safety"

    # With chaos testing
    python claude_sdk_research_agent.py --topic "AI safety" --chaos --chaos-level 0.5

    # Production mode with real Claude SDK
    export ANTHROPIC_API_KEY=sk-ant-...
    python claude_sdk_research_agent.py --topic "AI safety" --mode production

Dependencies:
    - balagan-agent (for chaos wrapper)
    - claude-agent-sdk (for production mode)
    - python-dotenv (for environment variables)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_research_tools import get_research_tools


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ResearchConfig:
    """Configuration for research agent."""

    topic: str = "artificial intelligence"
    mode: str = "mock"  # mock | production
    use_chaos: bool = False
    chaos_level: float = 0.5
    output_dir: str = "reports"
    verbose: bool = True

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> ResearchConfig:
        """Create config from parsed CLI arguments."""
        return cls(
            topic=args.topic,
            mode=args.mode,
            use_chaos=args.chaos,
            chaos_level=args.chaos_level,
            output_dir=args.output_dir,
            verbose=not args.quiet,
        )


# ---------------------------------------------------------------------------
# Research Workflow
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool = True):
    """Print message if verbose."""
    if verbose:
        print(msg)


async def run_research_agent(config: ResearchConfig) -> dict:
    """Execute research agent workflow with optional chaos injection.

    Workflow:
    1. Get research tools
    2. Optionally wrap with chaos injection
    3. Execute tool sequence:
       - search_web: Gather information
       - summarize_text: Condense findings
       - save_report: Generate report

    Args:
        config: Research agent configuration

    Returns:
        Dict with results, metrics, and experiment data
    """
    _log(f"\n{'=' * 60}", config.verbose)
    _log(f"🔍 Research Agent", config.verbose)
    _log(f"{'=' * 60}", config.verbose)
    _log(f"Topic: {config.topic}", config.verbose)
    _log(f"Mode: {config.mode}", config.verbose)
    _log(f"Chaos: {config.use_chaos} (level={config.chaos_level})", config.verbose)
    _log(f"{'=' * 60}\n", config.verbose)

    # Step 1: Get tools
    _log("📦 Loading research tools...", config.verbose)
    tools = get_research_tools(mode=config.mode)
    tool_dict = {t["name"]: t["func"] for t in tools}

    # Step 2: Setup wrapper and chaos
    wrapper: Optional[ClaudeAgentSDKWrapper] = None
    wrapped_tools = tool_dict

    if config.use_chaos:
        _log("⚡ Configuring chaos injection...", config.verbose)
        wrapper = ClaudeAgentSDKWrapper(tools=tools, chaos_level=config.chaos_level)
        wrapper.configure_chaos(
            chaos_level=config.chaos_level,
            enable_tool_failures=True,
            enable_delays=True,
            enable_hallucinations=False,  # Keep research data accurate
            enable_context_corruption=False,
            enable_budget_exhaustion=False,
        )
        wrapped_tools = wrapper.get_wrapped_tools()
        _log(f"✓ Chaos configured (level={config.chaos_level})", config.verbose)

    # Create output directory if needed
    if config.output_dir and not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir, exist_ok=True)

    # Step 3: Execute research workflow
    _log("\n📋 Starting research workflow...\n", config.verbose)

    results = {"tool_outputs": {}, "success": True, "errors": []}

    try:
        # Phase 1: Search
        _log("1️⃣  Searching for information...", config.verbose)
        try:
            search_result = wrapped_tools["search_web"]({"query": config.topic})
            search_text = search_result["content"][0]["text"]
            results["tool_outputs"]["search"] = search_text
            _log("   ✓ Search complete\n", config.verbose)
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            results["errors"].append(error_msg)
            results["success"] = False
            _log(f"   ✗ {error_msg}\n", config.verbose)
            raise

        # Phase 2: Summarize
        _log("2️⃣  Summarizing findings...", config.verbose)
        try:
            summary_result = wrapped_tools["summarize_text"]({"text": search_text})
            summary_text = summary_result["content"][0]["text"]
            results["tool_outputs"]["summary"] = summary_text
            _log("   ✓ Summary complete\n", config.verbose)
        except Exception as e:
            error_msg = f"Summarization failed: {str(e)}"
            results["errors"].append(error_msg)
            results["success"] = False
            _log(f"   ✗ {error_msg}\n", config.verbose)
            raise

        # Phase 3: Generate report
        _log("3️⃣  Generating report...", config.verbose)
        try:
            report_content = (
                f"# Research Report: {config.topic}\n\n"
                f"## Search Results\n\n{search_text}\n\n"
                f"## Summary\n\n{summary_text}\n"
            )

            report_filename = os.path.join(config.output_dir, f"report_{config.topic.replace(' ', '_')}.md")

            report_result = wrapped_tools["save_report"](
                {"content": report_content, "filename": report_filename}
            )
            report_msg = report_result["content"][0]["text"]
            results["tool_outputs"]["report"] = report_msg
            _log(f"   ✓ {report_msg}\n", config.verbose)
        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            results["errors"].append(error_msg)
            results["success"] = False
            _log(f"   ✗ {error_msg}\n", config.verbose)
            raise

    except Exception as e:
        results["success"] = False

    # Step 4: Collect metrics
    if wrapper:
        wrapper.record_query()
        results["metrics"] = wrapper.get_metrics()
        results["mttr"] = wrapper.get_mttr_stats()
        results["experiment"] = wrapper.get_experiment_results()

    # Step 5: Print summary
    _log(f"\n{'=' * 60}", config.verbose)
    if results["success"]:
        _log("✅ Research completed successfully!", config.verbose)
    else:
        _log("❌ Research encountered errors", config.verbose)
        for error in results["errors"]:
            _log(f"   - {error}", config.verbose)

    if wrapper:
        metrics = results["metrics"]["aggregate"]
        _log(f"\n📊 Metrics:", config.verbose)
        _log(f"   Total operations: {metrics.get('operations', {}).get('total', 0)}", config.verbose)
        _log(f"   Success rate: {metrics.get('operations', {}).get('success_rate', 0):.1%}", config.verbose)

    _log(f"{'=' * 60}\n", config.verbose)

    return results


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Research agent with Claude Agent SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Run with mock tools (no API key needed)\n"
            "  python claude_sdk_research_agent.py --topic 'quantum computing'\n\n"
            "  # Run with chaos testing\n"
            "  python claude_sdk_research_agent.py --topic 'AI safety' --chaos --chaos-level 0.75\n\n"
            "  # Production mode (requires ANTHROPIC_API_KEY)\n"
            "  python claude_sdk_research_agent.py --mode production --topic 'AI safety'\n"
        ),
    )

    parser.add_argument(
        "--topic",
        type=str,
        default="artificial intelligence safety",
        help="Research topic (default: 'artificial intelligence safety')",
    )

    parser.add_argument(
        "--mode",
        choices=["mock", "production"],
        default="mock",
        help="Agent mode (default: mock)",
    )

    parser.add_argument(
        "--chaos",
        action="store_true",
        help="Enable chaos testing with fault injection",
    )

    parser.add_argument(
        "--chaos-level",
        type=float,
        default=0.5,
        help="Chaos level: 0.0-2.0 (default: 0.5)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory for report output (default: reports)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    config = ResearchConfig.from_args(args)

    try:
        result = await run_research_agent(config)
        return 0 if result["success"] else 1
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
