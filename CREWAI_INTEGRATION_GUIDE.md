# CrewAI Chaos Testing Integration Guide

**A step-by-step guide to stress-test your existing CrewAI agents with AgentChaos**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Start (5 minutes)](#quick-start-5-minutes)
4. [Step-by-Step Integration](#step-by-step-integration)
5. [Common Scenarios](#common-scenarios)
6. [Advanced Configuration](#advanced-configuration)
7. [Verbose Mode & Debugging](#verbose-mode--debugging)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start, make sure you have:
- ✅ Python 3.8 or higher
- ✅ An existing CrewAI project with agents and tasks
- ✅ Basic understanding of your agent's tools and workflows

---

## Installation

```bash
# Install AgentChaos
pip install agentchaos

# If you don't have CrewAI yet
pip install crewai
```

---

## Quick Start (5 minutes)

### Your Existing CrewAI Code

```python
from crewai import Agent, Task, Crew

# Your existing setup
agent = Agent(
    role="Research Analyst",
    goal="Find accurate information",
    tools=[search_tool, summarize_tool]
)

task = Task(
    description="Research quantum computing",
    agent=agent
)

crew = Crew(agents=[agent], tasks=[task])

# Normal execution
result = crew.kickoff()
```

### Add Chaos Testing (3 lines!)

```python
from agentchaos.wrappers.crewai import CrewAIWrapper

# Wrap your crew with chaos
wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

# Run with chaos injection
result = wrapper.kickoff()

# Check metrics
metrics = wrapper.get_metrics()
print(f"Success rate: {metrics['aggregate']['operations']['success_rate']:.1%}")
```

That's it! Your crew now runs with chaos injection. 🎉

---

## Step-by-Step Integration

### Step 1: Import the CrewAI Wrapper

Add this import at the top of your file:

```python
from agentchaos.wrappers.crewai import CrewAIWrapper
```

### Step 2: Create Your Crew (as usual)

Keep your existing CrewAI code unchanged:

```python
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool, WebsiteSearchTool

# Create your tools
search = SerperDevTool()
scraper = WebsiteSearchTool()

# Create your agents
researcher = Agent(
    role="Senior Researcher",
    goal="Find and verify information",
    tools=[search, scraper],
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Create engaging content",
    tools=[],
    verbose=True
)

# Create tasks
research_task = Task(
    description="Research the latest AI trends",
    agent=researcher,
    expected_output="A detailed research report"
)

write_task = Task(
    description="Write an article based on research",
    agent=writer,
    expected_output="A well-written article"
)

# Create crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True
)
```

### Step 3: Wrap Your Crew with AgentChaos

Wrap the crew before running it:

```python
# Wrap with chaos
wrapper = CrewAIWrapper(
    crew,
    chaos_level=0.5,       # 50% chaos intensity
    max_retries=3,         # Retry failed tools up to 3 times
    retry_delay=0.5,       # Wait 0.5s between retries
    verbose=True           # Enable verbose logging
)
```

**What does each parameter do?**
- `chaos_level`: Controls how often faults are injected (0.0 = none, 1.0 = standard, 2.0+ = stress test)
- `max_retries`: How many times to retry a failed tool call
- `retry_delay`: Seconds to wait between retries
- `verbose`: Show detailed logs of tool calls, failures, and recoveries

### Step 4: Configure Chaos Types

Choose which types of chaos to inject:

```python
wrapper.configure_chaos(
    chaos_level=0.5,                    # Base chaos level
    enable_tool_failures=True,          # Tools randomly fail
    enable_delays=True,                 # Tools take longer to respond
    enable_hallucinations=False,        # Tools return corrupted data
    enable_context_corruption=False,    # Tool inputs get corrupted
    enable_budget_exhaustion=False,     # Simulate rate limits
)
```

**Recommended for beginners:**
- Start with just `enable_tool_failures=True`
- Add `enable_delays=True` once you're comfortable
- Add others gradually as you build confidence

### Step 5: Run Your Crew with Chaos

Execute your crew normally - chaos happens automatically:

```python
# Run with chaos injection
result = wrapper.kickoff()

# Or with inputs
result = wrapper.kickoff(inputs={"topic": "artificial intelligence"})

print(result.raw)  # Your crew's output
```

### Step 6: Analyze the Results

Check how your crew performed under chaos:

```python
# Get metrics
metrics = wrapper.get_metrics()

print(f"\nChaos Test Results:")
print(f"Total kickoffs: {metrics['kickoff_count']}")
print(f"Tools tested: {len(metrics['tools'])}")

# Per-tool statistics
for tool_name, tool_metrics in metrics['tools'].items():
    ops = tool_metrics.get('operations', {})
    total = ops.get('total', 0)
    failed = ops.get('failed', 0)

    if total > 0:
        success_rate = ((total - failed) / total) * 100
        print(f"\n{tool_name}:")
        print(f"  Total calls: {total}")
        print(f"  Failures: {failed}")
        print(f"  Success rate: {success_rate:.1f}%")

# MTTR (Mean Time To Recovery) statistics
mttr_stats = wrapper.get_mttr_stats()
print(f"\nRecovery Statistics:")
for tool_name, stats in mttr_stats['tools'].items():
    if stats.get('recovery_count', 0) > 0:
        print(f"{tool_name}: {stats['mttr_seconds']:.2f}s average recovery time")
```

---

## Common Scenarios

### Scenario 1: Light Testing (Development)

Perfect for daily development - catches obvious issues without being disruptive:

```python
wrapper = CrewAIWrapper(crew, chaos_level=0.25, verbose=False)
wrapper.configure_chaos(
    chaos_level=0.25,              # 2.5% base failure rate
    enable_tool_failures=True,
    enable_delays=False,           # Don't slow down development
    enable_hallucinations=False,
    enable_context_corruption=False,
    enable_budget_exhaustion=False,
)

result = wrapper.kickoff()
```

### Scenario 2: Moderate Testing (Pre-Production)

Good balance for pre-production testing:

```python
wrapper = CrewAIWrapper(crew, chaos_level=0.5, verbose=True)
wrapper.configure_chaos(
    chaos_level=0.5,               # 5% base failure rate
    enable_tool_failures=True,
    enable_delays=True,
    enable_hallucinations=False,
    enable_context_corruption=False,
    enable_budget_exhaustion=True, # Test rate limits
)

result = wrapper.kickoff()
```

### Scenario 3: Stress Testing (Find Breaking Points)

Find out when your agent completely breaks:

```python
wrapper = CrewAIWrapper(crew, chaos_level=2.0, verbose=True)
wrapper.configure_chaos(
    chaos_level=2.0,               # 20% base failure rate
    enable_tool_failures=True,
    enable_delays=True,
    enable_hallucinations=True,    # Corrupted data
    enable_context_corruption=True, # Corrupted inputs
    enable_budget_exhaustion=True,
)

try:
    result = wrapper.kickoff()
    print("✅ Crew survived stress test!")
except Exception as e:
    print(f"❌ Crew failed under stress: {e}")
```

### Scenario 4: Specific Tool Testing

Test only certain tools that are critical or unreliable:

```python
from agentchaos.injectors import ToolFailureInjector
from agentchaos.injectors.tool_failure import ToolFailureConfig

# Create wrapper without auto-configuration
wrapper = CrewAIWrapper(crew, chaos_level=0.0)

# Add injector only to specific tools
injector = ToolFailureInjector(ToolFailureConfig(probability=0.3))
wrapper.add_injector(injector, tools=["search_tool", "scrape_tool"])

result = wrapper.kickoff()
```

### Scenario 5: Multiple Test Runs

Run your crew multiple times to get statistically significant results:

```python
wrapper = CrewAIWrapper(crew, chaos_level=0.5, verbose=False)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

successful_runs = 0
total_runs = 10

for i in range(total_runs):
    print(f"Run {i+1}/{total_runs}...")
    try:
        result = wrapper.kickoff()
        successful_runs += 1
        print(f"  ✓ Success")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Reset metrics for next run
    wrapper.reset()

success_rate = (successful_runs / total_runs) * 100
print(f"\nOverall Success Rate: {success_rate:.1f}%")
```

---

## Advanced Configuration

### Custom Injectors

Create your own fault injection patterns:

```python
from agentchaos.injectors.tool_failure import ToolFailureInjector, ToolFailureConfig, FailureMode

# Configure specific failure types
custom_injector = ToolFailureInjector(ToolFailureConfig(
    probability=0.15,
    failure_modes=[
        FailureMode.TIMEOUT,        # Simulate timeouts
        FailureMode.RATE_LIMIT,     # Simulate API rate limits
        FailureMode.EMPTY_RESPONSE, # Return empty data
    ]
))

wrapper = CrewAIWrapper(crew)
wrapper.add_injector(custom_injector)
```

### Latency Simulation

Simulate different network conditions:

```python
from agentchaos.injectors import DelayInjector
from agentchaos.injectors.delay import DelayConfig, DelayPattern

# Simulate poor network with spikes
delay_injector = DelayInjector(DelayConfig(
    probability=0.8,              # 80% of calls get delayed
    pattern=DelayPattern.SPIKE,   # Random latency spikes
    min_delay_ms=100,
    max_delay_ms=500,
    spike_probability=0.2,        # 20% of delays are severe
    spike_multiplier=10,          # 10x slower during spikes
))

wrapper = CrewAIWrapper(crew)
wrapper.add_injector(delay_injector)
```

### Experiment Context

Track experiments formally for better reporting:

```python
wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

# Use experiment context
with wrapper.experiment("production-readiness-test") as exp:
    result = wrapper.kickoff()

# Get experiment results
experiments = wrapper.get_experiment_results()
for exp_result in experiments:
    print(f"\nExperiment: {exp_result.config.name}")
    print(f"Success Rate: {exp_result.success_rate:.1%}")
    print(f"Duration: {exp_result.duration_seconds:.2f}s")
```

---

## Verbose Mode & Debugging

### Enable Verbose Logging

See exactly what's happening during chaos testing:

```python
from agentchaos import set_verbose

# Enable globally
set_verbose(True)

# Or per-wrapper
wrapper = CrewAIWrapper(crew, verbose=True)
```

**Example verbose output:**
```
  0.123s   🔧 Tool call: search_tool('quantum computing')
  0.156s     💥 FAULT INJECTED: tool_failure on search_tool
  0.156s        Details: error_type=service_unavailable
  0.156s     🔄 Retry 1/3 (waiting 0.5s...)
  0.678s   ✓ Result: {...} (522.34ms)
```

### Verbose CLI Usage

If running from a script:

```bash
python my_chaos_test.py --verbose
```

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--verbose', '-v', action='store_true')
args = parser.parse_args()

if args.verbose:
    set_verbose(True)

wrapper = CrewAIWrapper(crew, verbose=args.verbose)
```

---

## Best Practices

### 1. Start Small, Scale Up

```python
# Week 1: Just tool failures, low chaos
wrapper.configure_chaos(chaos_level=0.25, enable_tool_failures=True)

# Week 2: Add delays
wrapper.configure_chaos(chaos_level=0.5, enable_tool_failures=True, enable_delays=True)

# Week 3: Full chaos
wrapper.configure_chaos(chaos_level=1.0, enable_tool_failures=True,
                       enable_delays=True, enable_hallucinations=True)
```

### 2. Run Chaos Tests in CI/CD

```python
# tests/test_crew_resilience.py
import pytest
from agentchaos.wrappers.crewai import CrewAIWrapper

def test_crew_handles_tool_failures():
    """Test crew can handle 50% tool failure rate."""
    crew = create_my_crew()
    wrapper = CrewAIWrapper(crew, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True)

    # Should not raise exception
    result = wrapper.kickoff()
    assert result is not None

    # Should maintain reasonable success rate
    metrics = wrapper.get_metrics()
    # ... add assertions based on your requirements

def test_crew_stress_limit():
    """Find the chaos level where crew starts failing."""
    crew = create_my_crew()

    for chaos_level in [0.5, 1.0, 1.5, 2.0]:
        wrapper = CrewAIWrapper(crew, chaos_level=chaos_level)
        wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

        try:
            result = wrapper.kickoff()
            print(f"✓ Survived chaos level {chaos_level}")
        except Exception as e:
            print(f"✗ Failed at chaos level {chaos_level}")
            assert chaos_level >= 1.5, "Crew should survive at least 1.0 chaos"
            break
```

### 3. Monitor Key Metrics

```python
def assert_reliability_standards(metrics):
    """Ensure crew meets reliability standards."""

    # Calculate aggregate success rate
    total_calls = 0
    total_failures = 0

    for tool_name, tool_metrics in metrics['tools'].items():
        ops = tool_metrics.get('operations', {})
        total_calls += ops.get('total', 0)
        total_failures += ops.get('failed', 0)

    if total_calls > 0:
        success_rate = ((total_calls - total_failures) / total_calls)

        # Assert minimum standards
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95% threshold"

        # Check MTTR
        mttr_stats = wrapper.get_mttr_stats()
        for tool_name, stats in mttr_stats['tools'].items():
            if 'mttr_seconds' in stats:
                assert stats['mttr_seconds'] < 5.0, f"{tool_name} MTTR too high"

metrics = wrapper.get_metrics()
assert_reliability_standards(metrics)
```

### 4. Document Your Findings

```python
# Save results for analysis
import json
from datetime import datetime

metrics = wrapper.get_metrics()
mttr_stats = wrapper.get_mttr_stats()

report = {
    "timestamp": datetime.now().isoformat(),
    "chaos_level": wrapper.chaos_level,
    "metrics": metrics,
    "mttr": mttr_stats,
}

with open(f"chaos_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
    json.dump(report, f, indent=2)
```

### 5. Test Critical Paths First

Focus on the most important workflows:

```python
# Identify critical paths in your crew
critical_tasks = ["user_authentication", "payment_processing", "data_retrieval"]

# Create a crew with only critical tasks
critical_crew = Crew(agents=agents, tasks=critical_tasks_only)

# Test with higher chaos
wrapper = CrewAIWrapper(critical_crew, chaos_level=1.0)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

result = wrapper.kickoff()

# Critical paths should have stricter requirements
metrics = wrapper.get_metrics()
# ... validate with higher standards
```

---

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'agentchaos'"

**Solution:**
```bash
pip install agentchaos
# Or if developing locally:
pip install -e .
```

### Problem: "CrewAIWrapper.__init__() got an unexpected keyword argument 'verbose'"

**Solution:** You have an older version. Update to the latest:
```bash
pip install --upgrade agentchaos
```

### Problem: Crew fails immediately with chaos enabled

**Diagnosis:**
```python
# Test with zero chaos first
wrapper = CrewAIWrapper(crew, chaos_level=0.0, verbose=True)
result = wrapper.kickoff()  # Should work

# Gradually increase chaos
for level in [0.1, 0.25, 0.5]:
    wrapper = CrewAIWrapper(crew, chaos_level=level, verbose=True)
    try:
        result = wrapper.kickoff()
        print(f"✓ Level {level} OK")
    except Exception as e:
        print(f"✗ Failed at level {level}: {e}")
        break
```

### Problem: No faults are being injected

**Check:**
```python
# Verify chaos is configured
wrapper = CrewAIWrapper(crew, chaos_level=1.0, verbose=True)  # verbose=True!
wrapper.configure_chaos(enable_tool_failures=True)

result = wrapper.kickoff()

# Check metrics - should see some failures
metrics = wrapper.get_metrics()
print(json.dumps(metrics, indent=2))
```

### Problem: Too many failures, crew never completes

**Solution:** Lower chaos level or increase retries:
```python
wrapper = CrewAIWrapper(
    crew,
    chaos_level=0.25,    # Lower this
    max_retries=5,       # Increase this
    retry_delay=0.5
)
```

### Problem: Want to exclude certain tools from chaos

**Solution:**
```python
# Create wrapper without auto-chaos
wrapper = CrewAIWrapper(crew, chaos_level=0.0)

# Get all wrapped tools
all_tools = wrapper.get_wrapped_tools()

# Add injector only to specific tools (exclude critical ones)
from agentchaos.injectors import ToolFailureInjector
from agentchaos.injectors.tool_failure import ToolFailureConfig

injector = ToolFailureInjector(ToolFailureConfig(probability=0.3))

# Only inject into non-critical tools
non_critical_tools = ["search_tool", "scrape_tool"]  # Exclude "payment_tool"
wrapper.add_injector(injector, tools=non_critical_tools)
```

---

## Example: Complete Integration

Here's a complete example putting it all together:

```python
"""
chaos_test.py - Chaos testing for my CrewAI research agent
"""

import sys
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool

from agentchaos import set_verbose
from agentchaos.wrappers.crewai import CrewAIWrapper


def create_research_crew(topic: str) -> Crew:
    """Create a research crew."""
    search_tool = SerperDevTool()

    researcher = Agent(
        role="Senior Researcher",
        goal="Find accurate, up-to-date information",
        tools=[search_tool],
        backstory="Expert at finding reliable sources"
    )

    task = Task(
        description=f"Research {topic} and provide a comprehensive summary",
        agent=researcher,
        expected_output="A detailed research report"
    )

    return Crew(agents=[researcher], tasks=[task])


def run_chaos_test(topic: str, chaos_level: float = 0.5, verbose: bool = False):
    """Run a chaos test on the research crew."""
    print(f"\n{'='*70}")
    print(f"🌪️  Chaos Testing: {topic}")
    print(f"{'='*70}")
    print(f"Chaos Level: {chaos_level}")
    print(f"Verbose: {verbose}\n")

    # Enable verbose logging if requested
    if verbose:
        set_verbose(True)

    # Create crew
    crew = create_research_crew(topic)

    # Wrap with chaos
    wrapper = CrewAIWrapper(crew, chaos_level=chaos_level, verbose=verbose)
    wrapper.configure_chaos(
        chaos_level=chaos_level,
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=False,
        enable_context_corruption=False,
        enable_budget_exhaustion=False,
    )

    # Run with chaos
    try:
        result = wrapper.kickoff()
        print(f"\n✅ Crew completed successfully!\n")
        print("Result:")
        print("-" * 70)
        print(result.raw)
        print("-" * 70)

        # Show metrics
        metrics = wrapper.get_metrics()
        print(f"\n📊 Chaos Test Metrics:")
        print(f"Kickoff count: {metrics['kickoff_count']}")

        for tool_name, tool_metrics in metrics['tools'].items():
            ops = tool_metrics.get('operations', {})
            total = ops.get('total', 0)
            failed = ops.get('failed', 0)

            if total > 0:
                success_rate = ((total - failed) / total) * 100
                print(f"\n{tool_name}:")
                print(f"  Total calls: {total}")
                print(f"  Failures: {failed}")
                print(f"  Success rate: {success_rate:.1f}%")

        # MTTR stats
        mttr_stats = wrapper.get_mttr_stats()
        print(f"\n⏱️  Recovery Statistics:")
        for tool_name, stats in mttr_stats['tools'].items():
            if stats.get('recovery_count', 0) > 0:
                print(f"{tool_name}: {stats['mttr_seconds']:.2f}s average recovery time")

        return True

    except Exception as e:
        print(f"\n❌ Crew failed: {e}")
        print("This shows the crew couldn't handle this chaos level!")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Chaos test CrewAI research agent")
    parser.add_argument("--topic", default="quantum computing", help="Research topic")
    parser.add_argument("--chaos-level", type=float, default=0.5, help="Chaos level (0.0-2.0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    success = run_chaos_test(args.topic, args.chaos_level, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

**Run it:**
```bash
# Basic test
python chaos_test.py

# Custom topic and chaos level
python chaos_test.py --topic "machine learning" --chaos-level 1.0

# With verbose logging
python chaos_test.py --verbose

# Stress test
python chaos_test.py --chaos-level 2.0 --verbose
```

---

## What's Next?

1. **Start testing your crew** with the Quick Start example
2. **Gradually increase chaos** from 0.25 → 0.5 → 1.0
3. **Monitor metrics** and fix issues you discover
4. **Add to CI/CD** to prevent regressions
5. **Share your results** with the team

---

## Need Help?

- 📖 Read the [main README](README.md) for more details
- 💬 Ask questions in [GitHub Issues](https://github.com/anthropics/agent-chaos/issues)
- 🐛 Report bugs in [GitHub Issues](https://github.com/anthropics/agent-chaos/issues)
- ⭐ Star the repo if this helped you!

---

*"Your agents will fail in production. Test them first."* 🧪
