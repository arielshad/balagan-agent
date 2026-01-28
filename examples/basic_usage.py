#!/usr/bin/env python3
"""
Basic usage example for BalaganAgent.

This example demonstrates how to:
1. Create a simple agent with tools
2. Wrap the agent with chaos injection
3. Run chaos experiments
4. Generate reliability reports
"""

from balaganagent import ChaosEngine, AgentWrapper, ExperimentRunner
from balaganagent.runner import scenario
from balaganagent.reporting import ReportGenerator


# Define a simple agent with tools
class SimpleAgent:
    """A simple agent with common tools."""

    def search(self, query: str) -> dict:
        """Search for information."""
        return {
            "query": query,
            "results": [
                {"title": f"Result 1 for {query}", "score": 0.95},
                {"title": f"Result 2 for {query}", "score": 0.87},
            ],
            "total": 2,
        }

    def calculate(self, expression: str) -> dict:
        """Perform a calculation."""
        # Simple safe evaluation
        allowed_chars = set("0123456789+-*/.(). ")
        if all(c in allowed_chars for c in expression):
            try:
                result = eval(expression)
                return {"expression": expression, "result": result}
            except Exception as e:
                return {"expression": expression, "error": str(e)}
        return {"expression": expression, "error": "Invalid expression"}

    def fetch_data(self, resource_id: str) -> dict:
        """Fetch data from a resource."""
        return {
            "id": resource_id,
            "data": {
                "name": f"Resource {resource_id}",
                "created_at": "2024-01-15T10:00:00Z",
                "status": "active",
            },
        }


def example_basic_wrapping():
    """Example: Basic agent wrapping with chaos injection."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Agent Wrapping")
    print("=" * 60 + "\n")

    # Create agent and wrapper
    agent = SimpleAgent()
    wrapper = AgentWrapper(agent)

    # Configure chaos (50% chaos level = 5% base failure rate)
    wrapper.configure_chaos(
        chaos_level=0.5,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=False,  # Disable for this example
    )

    # Make calls through the wrapper
    print("Making 10 search calls with chaos injection...")
    for i in range(10):
        try:
            result = wrapper.call_tool("search", f"query {i}")
            print(f"  Call {i + 1}: Success - {len(result.get('results', []))} results")
        except Exception as e:
            print(f"  Call {i + 1}: Failed - {e}")

    # Print metrics
    print("\nMetrics Summary:")
    metrics = wrapper.get_metrics()
    for tool_name, tool_metrics in metrics.get("tools", {}).items():
        ops = tool_metrics.get("operations", {})
        print(f"  {tool_name}:")
        print(f"    Total: {ops.get('total', 0)}")
        print(f"    Success Rate: {ops.get('success_rate', 0):.1%}")


def example_experiment_runner():
    """Example: Using the experiment runner with scenarios."""
    print("\n" + "=" * 60)
    print("Example 2: Experiment Runner with Scenarios")
    print("=" * 60 + "\n")

    # Create agent
    agent = SimpleAgent()

    # Create a scenario using the builder
    test_scenario = (
        scenario("search-reliability-test")
        .description("Test search tool reliability under chaos")
        .call("search", "artificial intelligence")
        .call("search", "machine learning")
        .call("search", "neural networks")
        .call("calculate", "2 + 2")
        .call("calculate", "10 * 5")
        .call("fetch_data", "user-123")
        .with_chaos(
            level=0.75,
            enable_tool_failures=True,
            enable_delays=True,
        )
        .build()
    )

    # Create runner and execute
    runner = ExperimentRunner()
    runner.set_agent(agent)

    print("Running scenario...")
    result = runner.run_scenario(test_scenario)

    # Print results
    print(f"\nScenario: {result.scenario_name}")
    print(f"Passed: {result.passed}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Operations: {result.experiment_result.total_operations}")
    print(f"Success Rate: {result.experiment_result.success_rate:.1%}")
    print(f"Recovery Rate: {result.experiment_result.recovery_rate:.1%}")
    print(f"Faults Injected: {result.experiment_result.faults_injected}")


def example_chaos_engine():
    """Example: Direct chaos engine usage."""
    print("\n" + "=" * 60)
    print("Example 3: Direct Chaos Engine Usage")
    print("=" * 60 + "\n")

    # Create chaos engine
    engine = ChaosEngine(chaos_level=1.0, seed=42)

    # Define a simple tool function
    def my_tool(x: int, y: int) -> int:
        return x + y

    # Wrap with chaos injection
    chaotic_tool = engine.wrap_tool(my_tool)

    # Run an experiment
    print("Running experiment with wrapped tool...")
    with engine.experiment("addition-test") as exp:
        for i in range(20):
            with exp.operation(f"add_{i}") as op:
                try:
                    result = chaotic_tool(i, i + 1)
                    print(f"  {i} + {i + 1} = {result}")
                    op.record_success()
                except Exception as e:
                    print(f"  {i} + {i + 1} = FAILED ({e})")
                    op.record_failure(str(e))

    # Get results
    result = engine.get_experiment_results()[-1]
    print(f"\nExperiment Results:")
    print(f"  Total Operations: {result.total_operations}")
    print(f"  Successful: {result.successful_operations}")
    print(f"  Failed: {result.failed_operations}")
    print(f"  Success Rate: {result.success_rate:.1%}")


def example_report_generation():
    """Example: Generating comprehensive reports."""
    print("\n" + "=" * 60)
    print("Example 4: Report Generation")
    print("=" * 60 + "\n")

    # Run a quick experiment
    agent = SimpleAgent()
    runner = ExperimentRunner()
    runner.set_agent(agent)

    # Create and run scenario
    test_scenario = (
        scenario("report-demo")
        .description("Demo scenario for report generation")
        .call("search", "test")
        .call("calculate", "1 + 1")
        .call("fetch_data", "demo-123")
        .with_chaos(level=0.5)
        .build()
    )

    result = runner.run_scenario(test_scenario)

    # Generate report
    report_gen = ReportGenerator()
    report = report_gen.generate_from_results(
        [result.experiment_result],
        aggregate_metrics=runner.get_aggregate_metrics(),
    )

    # Print terminal report
    print(report_gen.to_terminal(report))

    # You could also save in other formats:
    # report_gen.save(report, "report.json", format="json")
    # report_gen.save(report, "report.md", format="markdown")
    # report_gen.save(report, "report.html", format="html")


def main():
    """Run all examples."""
    print("\n" + "#" * 60)
    print("#  BALAGANAGENT EXAMPLES")
    print("#" * 60)

    example_basic_wrapping()
    example_experiment_runner()
    example_chaos_engine()
    example_report_generation()

    print("\n" + "#" * 60)
    print("#  ALL EXAMPLES COMPLETED")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
