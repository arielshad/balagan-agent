#!/usr/bin/env python3
"""Command-line interface for AgentChaos."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .engine import ChaosEngine
from .runner import ExperimentRunner, Scenario, scenario
from .reporting import ReportGenerator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="agentchaos",
        description="Chaos engineering framework for AI agents",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"agentchaos {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run chaos experiments")
    run_parser.add_argument(
        "scenario",
        help="Path to scenario file (JSON) or scenario name",
    )
    run_parser.add_argument(
        "--agent",
        "-a",
        help="Path to agent module (module:class format)",
    )
    run_parser.add_argument(
        "--chaos-level",
        "-c",
        type=float,
        default=1.0,
        help="Chaos level (0.0 to 2.0, default: 1.0)",
    )
    run_parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=1,
        help="Number of iterations",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        help="Output file for report",
    )
    run_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown", "html", "terminal"],
        default="terminal",
        help="Output format",
    )

    # Stress command
    stress_parser = subparsers.add_parser("stress", help="Run stress tests")
    stress_parser.add_argument(
        "scenario",
        help="Path to scenario file",
    )
    stress_parser.add_argument(
        "--agent",
        "-a",
        help="Path to agent module",
    )
    stress_parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=100,
        help="Iterations per chaos level",
    )
    stress_parser.add_argument(
        "--levels",
        "-l",
        nargs="+",
        type=float,
        default=[0.1, 0.25, 0.5, 0.75, 1.0],
        help="Chaos levels to test",
    )
    stress_parser.add_argument(
        "--output",
        "-o",
        help="Output file for results",
    )

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run a demo experiment")
    demo_parser.add_argument(
        "--chaos-level",
        "-c",
        type=float,
        default=0.5,
        help="Chaos level for demo",
    )

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new chaos test project")
    init_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to initialize",
    )

    args = parser.parse_args()

    if args.command == "run":
        run_experiment(args)
    elif args.command == "stress":
        run_stress_test(args)
    elif args.command == "demo":
        run_demo(args)
    elif args.command == "init":
        init_project(args)
    else:
        parser.print_help()
        sys.exit(1)


def run_experiment(args):
    """Run chaos experiment."""
    print(f"Running chaos experiment with level {args.chaos_level}")

    # Load scenario
    scenario_path = Path(args.scenario)
    if scenario_path.exists():
        scen = Scenario.from_file(str(scenario_path))
    else:
        print(f"Error: Scenario file not found: {args.scenario}")
        sys.exit(1)

    # Load agent if specified
    agent = None
    if args.agent:
        agent = load_agent(args.agent)

    if agent is None:
        # Use mock agent for demo
        agent = MockAgent()

    # Run experiment
    runner = ExperimentRunner()
    runner.set_agent(agent)

    results = []
    for i in range(args.iterations):
        print(f"  Iteration {i + 1}/{args.iterations}...")
        result = runner.run_scenario(scen, chaos_level=args.chaos_level)
        results.append(result)

    # Generate report
    report_gen = ReportGenerator()
    report = report_gen.generate_from_results(
        [r.experiment_result for r in results],
        aggregate_metrics=runner.get_aggregate_metrics(),
    )

    # Output report
    if args.format == "terminal":
        print(report_gen.to_terminal(report))
    elif args.format == "json":
        output = report_gen.to_json(report)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)
    elif args.format == "markdown":
        output = report_gen.to_markdown(report)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)
    elif args.format == "html":
        output = report_gen.to_html(report)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Report saved to {args.output}")
        else:
            print(output)


def run_stress_test(args):
    """Run stress test."""
    print(f"Running stress test with levels: {args.levels}")

    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        print(f"Error: Scenario file not found: {args.scenario}")
        sys.exit(1)

    scen = Scenario.from_file(str(scenario_path))

    agent = None
    if args.agent:
        agent = load_agent(args.agent)
    if agent is None:
        agent = MockAgent()

    runner = ExperimentRunner()
    runner.set_agent(agent)

    results = runner.run_stress_test(
        scen,
        iterations=args.iterations,
        chaos_levels=args.levels,
    )

    # Output results
    output = json.dumps(results, indent=2)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Results saved to {args.output}")
    else:
        print(output)


def run_demo(args):
    """Run demo experiment."""
    print(f"\n{'='*60}")
    print("  AGENTCHAOS DEMO")
    print(f"{'='*60}\n")
    print(f"Running demo with chaos level: {args.chaos_level}\n")

    # Create mock agent
    agent = MockAgent()

    # Create demo scenario
    demo_scenario = (
        scenario("demo-scenario")
        .description("Demo chaos experiment")
        .call("search", "test query")
        .call("calculate", "2 + 2")
        .call("fetch_data", "users/123")
        .with_chaos(level=args.chaos_level)
        .build()
    )

    # Run experiment
    runner = ExperimentRunner()
    runner.set_agent(agent)

    print("Running experiment...")
    result = runner.run_scenario(demo_scenario, chaos_level=args.chaos_level)

    # Generate and print report
    report_gen = ReportGenerator()
    report = report_gen.generate_from_results(
        [result.experiment_result],
        aggregate_metrics=runner.get_aggregate_metrics(),
    )

    print(report_gen.to_terminal(report))


def init_project(args):
    """Initialize a new chaos test project."""
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)

    # Create sample scenario
    sample_scenario = {
        "name": "sample-scenario",
        "description": "A sample chaos test scenario",
        "operations": [
            {"tool": "search", "args": ["test query"]},
            {"tool": "process", "args": [], "kwargs": {"data": "sample"}},
        ],
        "chaos_config": {
            "chaos_level": 0.5,
            "enable_tool_failures": True,
            "enable_delays": True,
            "enable_hallucinations": True,
        },
    }

    scenario_file = directory / "scenarios" / "sample.json"
    scenario_file.parent.mkdir(parents=True, exist_ok=True)
    scenario_file.write_text(json.dumps(sample_scenario, indent=2))

    # Create sample agent
    agent_code = '''"""Sample agent for chaos testing."""


class SampleAgent:
    """A sample agent with tools to test."""

    def search(self, query: str) -> dict:
        """Search for something."""
        return {"results": [f"Result for: {query}"], "count": 1}

    def process(self, data: str = "") -> dict:
        """Process some data."""
        return {"processed": True, "input": data}

    def fetch_data(self, resource_id: str) -> dict:
        """Fetch data from a resource."""
        return {"id": resource_id, "data": {"key": "value"}}
'''

    agent_file = directory / "agent.py"
    agent_file.write_text(agent_code)

    # Create config
    config = {
        "default_chaos_level": 0.5,
        "default_iterations": 10,
        "output_directory": "reports",
    }

    config_file = directory / "agentchaos.json"
    config_file.write_text(json.dumps(config, indent=2))

    print(f"Initialized AgentChaos project in {directory}")
    print(f"  Created: {scenario_file}")
    print(f"  Created: {agent_file}")
    print(f"  Created: {config_file}")
    print()
    print("To run the sample scenario:")
    print(f"  cd {directory}")
    print("  agentchaos run scenarios/sample.json --agent agent:SampleAgent")


def load_agent(agent_spec: str):
    """Load an agent from a module specification."""
    try:
        if ":" in agent_spec:
            module_path, class_name = agent_spec.rsplit(":", 1)
        else:
            module_path = agent_spec
            class_name = None

        # Handle file paths
        if module_path.endswith(".py"):
            import importlib.util

            spec = importlib.util.spec_from_file_location("agent_module", module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module from {module_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            import importlib

            module = importlib.import_module(module_path)

        if class_name:
            agent_class = getattr(module, class_name)
            return agent_class()
        else:
            # Try to find an agent class
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and name.endswith("Agent"):
                    return obj()

        raise ValueError(f"No agent class found in {module_path}")

    except Exception as e:
        print(f"Error loading agent: {e}")
        return None


class MockAgent:
    """Mock agent for demos and testing."""

    def search(self, query: str) -> dict:
        return {"results": [f"Result 1 for {query}", f"Result 2 for {query}"], "count": 2}

    def calculate(self, expression: str) -> dict:
        try:
            # Safe eval for basic math
            result = eval(expression, {"__builtins__": {}}, {})
            return {"expression": expression, "result": result}
        except Exception:
            return {"expression": expression, "error": "Could not evaluate"}

    def fetch_data(self, resource_id: str) -> dict:
        return {"id": resource_id, "data": {"name": "Sample", "value": 42}}


if __name__ == "__main__":
    main()
