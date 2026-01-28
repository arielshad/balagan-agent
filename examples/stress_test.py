#!/usr/bin/env python3
"""
Stress testing example for BalaganAgent.

This example demonstrates how to run stress tests
to find the breaking point of an agent.
"""

from balaganagent import AgentWrapper, ExperimentRunner
from balaganagent.runner import scenario


class RobustAgent:
    """An agent with built-in retry logic."""

    def __init__(self):
        self.call_count = 0

    def reliable_search(self, query: str) -> dict:
        """A search that should handle failures gracefully."""
        self.call_count += 1
        return {
            "query": query,
            "results": [f"Result for {query}"],
            "call_number": self.call_count,
        }

    def flaky_process(self, data: str) -> dict:
        """A process that might fail under load."""
        return {"processed": data, "status": "complete"}


def run_stress_test():
    """Run a comprehensive stress test."""
    print("\n" + "=" * 60)
    print("BALAGANAGENT STRESS TEST")
    print("=" * 60 + "\n")

    agent = RobustAgent()
    runner = ExperimentRunner()
    runner.set_agent(agent)

    # Create stress test scenario
    stress_scenario = (
        scenario("stress-test")
        .description("Stress test with increasing chaos levels")
        .call("reliable_search", "stress query 1")
        .call("reliable_search", "stress query 2")
        .call("flaky_process", "data chunk 1")
        .call("flaky_process", "data chunk 2")
        .with_chaos(level=1.0)
        .build()
    )

    # Run stress test with multiple chaos levels
    print("Running stress test across chaos levels...")
    print("This tests how the agent performs as chaos increases.\n")

    results = runner.run_stress_test(
        stress_scenario,
        iterations=50,
        chaos_levels=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
    )

    # Print results
    print("\nSTRESS TEST RESULTS")
    print("-" * 60)
    print(f"{'Chaos Level':<15} {'Pass Rate':<15} {'Avg Success':<15} {'Avg Duration'}")
    print("-" * 60)

    for level, data in results["levels"].items():
        print(
            f"{level:<15} "
            f"{data['pass_rate']:<15.1%} "
            f"{data['avg_success_rate']:<15.1%} "
            f"{data['avg_duration_seconds']:.3f}s"
        )

    print("-" * 60)

    # Find breaking point
    breaking_point = None
    for level, data in results["levels"].items():
        if data["pass_rate"] < 0.5:
            breaking_point = level
            break

    if breaking_point:
        print(f"\n⚠️  Breaking point detected at chaos level: {breaking_point}")
        print("   Agent reliability drops below 50% at this level.")
    else:
        print("\n✓ Agent maintained >50% reliability across all chaos levels!")

    return results


def run_endurance_test():
    """Run a longer endurance test at a fixed chaos level."""
    print("\n" + "=" * 60)
    print("ENDURANCE TEST")
    print("=" * 60 + "\n")

    agent = RobustAgent()
    runner = ExperimentRunner()
    runner.set_agent(agent)

    # Create endurance scenario
    endurance_scenario = (
        scenario("endurance-test")
        .description("Long-running endurance test")
        .call("reliable_search", "endurance query")
        .call("flaky_process", "endurance data")
        .with_chaos(level=0.5)  # Moderate chaos
        .build()
    )

    print("Running 200 iterations at chaos level 0.5...")
    print("This tests sustained performance under moderate chaos.\n")

    results = []
    for i in range(200):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/200 iterations")

        result = runner.run_scenario(endurance_scenario, chaos_level=0.5)
        results.append(result.passed)

    # Calculate rolling success rate
    window_size = 20
    rolling_rates = []
    for i in range(len(results) - window_size + 1):
        window = results[i : i + window_size]
        rate = sum(window) / len(window)
        rolling_rates.append(rate)

    # Print summary
    total_passed = sum(results)
    print(f"\nENDURANCE TEST RESULTS")
    print("-" * 40)
    print(f"Total Iterations: {len(results)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {len(results) - total_passed}")
    print(f"Overall Pass Rate: {total_passed / len(results):.1%}")
    print(f"Min Rolling Rate (20): {min(rolling_rates):.1%}")
    print(f"Max Rolling Rate (20): {max(rolling_rates):.1%}")

    # Check for degradation
    first_half = results[: len(results) // 2]
    second_half = results[len(results) // 2 :]
    first_rate = sum(first_half) / len(first_half)
    second_rate = sum(second_half) / len(second_half)

    if second_rate < first_rate * 0.9:
        print(f"\n⚠️  Performance degradation detected!")
        print(f"   First half: {first_rate:.1%}, Second half: {second_rate:.1%}")
    else:
        print(f"\n✓ No significant performance degradation detected.")


if __name__ == "__main__":
    run_stress_test()
    run_endurance_test()
