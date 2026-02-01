# BalaganAgent

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/balagan-agent.svg)](https://pypi.org/project/balagan-agent/)
[![Python versions](https://img.shields.io/pypi/pyversions/balagan-agent.svg)](https://pypi.org/project/balagan-agent/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://github.com/arielshad/balagan-agent/workflows/Tests/badge.svg)](https://github.com/arielshad/balagan-agent/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Downloads](https://img.shields.io/pypi/dm/balagan-agent.svg)](https://pypi.org/project/balagan-agent/)
[![GitHub stars](https://img.shields.io/github/stars/arielshad/balagan-agent.svg?style=social)](https://github.com/arielshad/balagan-agent)

**Chaos Engineering for AI Agents**

Everyone demos agents. Nobody stress-tests them.

[Quick Start](#quick-start) •
[Features](#features) •
[Docs](https://arielshad.github.io/balagan-agent/) •
[Examples](#examples) •
[Contributing](#contributing)

</div>

BalaganAgent is a reliability testing framework that stress-tests AI agents through controlled fault injection—because your agent will fail in production, and you should know how it handles it.

> **Latest: v0.4.0** — [Changelog](CHANGELOG.md) · [Full Documentation](https://arielshad.github.io/balagan-agent/)

```bash
pip install balagan-agent        # Install
balaganagent demo --chaos-level 0.5  # Run your first experiment in 60 seconds
```

---

## Table of Contents

- [Why BalaganAgent?](#why-balaganagent)
- [Features](#features)
- [Quick Start](#quick-start)
- [Use Cases](#use-cases)
- [Chaos Levels](#chaos-levels)
- [Fault Injectors](#fault-injectors)
- [Metrics](#metrics)
- [Reports](#reports)
- [Project Structure](#project-structure)
- [Community](#community)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Why BalaganAgent?

AI agents are entering production environments, but there's zero reliability discipline. BalaganAgent brings the battle-tested principles of chaos engineering (think Chaos Monkey, Gremlin) to the world of AI agents.

### The Problem
- Agents fail silently in production
- Tool calls time out, return garbage, or hallucinate
- Context gets corrupted, budgets get exhausted
- Nobody knows until users complain

### The Solution
- Inject failures in development, not production
- Measure recovery time (MTTR)
- Score reliability like we score SLAs
- Find breaking points before users do

### Industry Adoption

BalaganAgent is designed for teams that take AI reliability seriously:
- Production AI systems requiring SLO compliance
- Enterprise deployments with strict reliability requirements
- Development teams practicing chaos engineering
- Organizations building mission-critical AI agents

## Features

### Fault Injection
- **Tool Failures**: Exceptions, timeouts, empty responses, malformed data, rate limits
- **Delays**: Fixed, random, spike patterns, degrading latency
- **Hallucinations**: Wrong values, fabricated data, contradictions, fake references
- **Context Corruption**: Truncation, reordering, noise injection, encoding issues
- **Budget Exhaustion**: Token limits, cost caps, rate limiting, call quotas

### Metrics & Analysis
- **MTTR** (Mean Time To Recovery): How fast does your agent recover?
- **Recovery Quality**: Did it recover correctly or just fail gracefully?
- **Reliability Score**: SRE-grade scoring (five nines to one nine)
- **Error Budget Tracking**: Know when to freeze changes

### Reports
- Terminal output with colors
- JSON for programmatic analysis
- Markdown for documentation
- HTML dashboards

## Quick Start

Get up and running in minutes.

### Installation

```bash
pip install balagan-agent
```

Verify installation:

```bash
balaganagent --version
```

### CrewAI Integration

**Using CrewAI?** Check out our [CrewAI Integration Guide](CREWAI_INTEGRATION_GUIDE.md) for a complete step-by-step walkthrough!

Quick example:
```python
from balaganagent.wrappers.crewai import CrewAIWrapper

# Your existing CrewAI setup
crew = Crew(agents=[agent], tasks=[task])

# Add chaos testing (3 lines!)
wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.kickoff()

# Check metrics
metrics = wrapper.get_metrics()
print(f"Success rate: {metrics['aggregate']['operations']['success_rate']:.1%}")
```

[→ Full CrewAI Integration Guide](CREWAI_INTEGRATION_GUIDE.md)

### Basic Usage

```python
from balaganagent import ChaosEngine, AgentWrapper

# Your agent with tools
class MyAgent:
    def search(self, query: str) -> dict:
        return {"results": [...]}

    def calculate(self, expr: str) -> float:
        return eval(expr)

# Wrap it with chaos
agent = MyAgent()
wrapper = AgentWrapper(agent)
wrapper.configure_chaos(chaos_level=0.5)  # 50% chaos intensity

# Now calls might fail randomly!
result = wrapper.call_tool("search", "test query")
```

### Run an Experiment

```python
from balaganagent import ChaosEngine
from balaganagent.runner import scenario, ExperimentRunner

# Define a test scenario
test = (
    scenario("search-reliability")
    .description("Test search under chaos")
    .call("search", "AI safety")
    .call("search", "machine learning")
    .call("calculate", "2 + 2")
    .with_chaos(level=0.75)
    .build()
)

# Run it
runner = ExperimentRunner()
runner.set_agent(MyAgent())
result = runner.run_scenario(test)

print(f"Success Rate: {result.experiment_result.success_rate:.1%}")
print(f"MTTR: {result.mttr_stats['mttr_seconds']:.2f}s")
```

### CLI Usage

```bash
# Run a demo
balaganagent demo --chaos-level 0.5

# Initialize a new project
balaganagent init my-chaos-tests

# Run a scenario file
balaganagent run scenarios/search_test.json --chaos-level 0.75

# Run stress tests
balaganagent stress scenarios/critical_path.json --iterations 100
```

## Use Cases

BalaganAgent helps you answer critical questions about your agents:

- **Pre-Production Validation**: Will my agent handle API timeouts gracefully?
- **Integration Testing**: Does my agent recover when tools return malformed data?
- **Load Testing**: How does performance degrade under high failure rates?
- **Reliability Engineering**: What's my agent's actual MTTR and recovery rate?
- **SLO Compliance**: Can I maintain 99.9% availability under chaos?
- **Regression Testing**: Did my recent changes break failure handling?

## Chaos Levels

The `chaos_level` parameter controls fault injection probability:

| Level | Base Failure Rate | Use Case |
|-------|------------------|----------|
| 0.0 | 0% | Baseline (no chaos) |
| 0.25 | 2.5% | Light testing |
| 0.5 | 5% | Moderate chaos |
| 1.0 | 10% | Standard chaos |
| 2.0 | 20% | Stress testing |

## Fault Injectors

### Tool Failure Injector

Simulates various tool failure modes:

```python
from balaganagent.injectors import ToolFailureInjector
from balaganagent.injectors.tool_failure import ToolFailureConfig, FailureMode

injector = ToolFailureInjector(ToolFailureConfig(
    probability=0.1,
    failure_modes=[
        FailureMode.TIMEOUT,
        FailureMode.RATE_LIMIT,
        FailureMode.SERVICE_UNAVAILABLE,
    ]
))
```

### Delay Injector

Simulates network latency patterns:

```python
from balaganagent.injectors import DelayInjector
from balaganagent.injectors.delay import DelayConfig, DelayPattern, LatencySimulator

# Use presets
injector = LatencySimulator.create("poor")  # High latency, high jitter

# Or configure manually
injector = DelayInjector(DelayConfig(
    pattern=DelayPattern.SPIKE,
    min_delay_ms=50,
    max_delay_ms=200,
    spike_probability=0.1,
    spike_multiplier=10,
))
```

### Hallucination Injector

Corrupts data to test agent's ability to detect bad information:

```python
from balaganagent.injectors import HallucinationInjector
from balaganagent.injectors.hallucination import HallucinationConfig, HallucinationType

injector = HallucinationInjector(HallucinationConfig(
    probability=0.05,
    severity=0.5,  # 0=subtle, 1=obvious
    hallucination_types=[
        HallucinationType.WRONG_VALUE,
        HallucinationType.FABRICATED_DATA,
        HallucinationType.NONEXISTENT_REFERENCE,
    ]
))
```

### Budget Exhaustion Injector

Tests behavior when resources run out:

```python
from balaganagent.injectors import BudgetExhaustionInjector
from balaganagent.injectors.budget import BudgetExhaustionConfig

injector = BudgetExhaustionInjector(BudgetExhaustionConfig(
    token_limit=10000,
    cost_limit_dollars=1.00,
    rate_limit_per_minute=60,
    fail_hard=True,  # Raise exception vs return error
))
```

## Metrics

### MTTR Calculator

```python
from balaganagent.metrics import MTTRCalculator

calc = MTTRCalculator()

# Record failure and recovery
calc.record_failure("search", "timeout")
# ... agent recovers ...
calc.record_recovery("search", "timeout", retries=2)

stats = calc.get_recovery_stats()
print(f"MTTR: {stats['mttr_seconds']:.2f}s")
print(f"Recovery Rate: {stats['recovery_rate']:.1%}")
```

### Reliability Scorer

```python
from balaganagent.metrics import ReliabilityScorer

scorer = ReliabilityScorer(slos={
    "availability": 0.99,
    "latency_p99_ms": 2000,
})

# Record operations
for result in agent_results:
    scorer.record_operation(
        success=result.success,
        latency_ms=result.latency,
    )

report = scorer.calculate_score()
print(f"Grade: {report.grade.value}")
print(f"Availability: {report.availability:.3%}")
print(f"Error Budget Remaining: {report.error_budget_remaining:.1%}")
```

## Scenarios

Scenarios can be defined in code or JSON:

```json
{
  "name": "critical-path-test",
  "description": "Test the critical user journey",
  "operations": [
    {"tool": "authenticate", "args": ["user123"]},
    {"tool": "fetch_profile", "args": ["user123"]},
    {"tool": "search", "args": ["recent orders"]},
    {"tool": "process_request", "kwargs": {"action": "refund"}}
  ],
  "chaos_config": {
    "chaos_level": 0.5,
    "enable_tool_failures": true,
    "enable_delays": true,
    "enable_budget_exhaustion": true
  }
}
```

## Stress Testing

Find your agent's breaking point:

```python
runner = ExperimentRunner()
runner.set_agent(agent)

results = runner.run_stress_test(
    scenario,
    iterations=100,
    chaos_levels=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
)

for level, data in results["levels"].items():
    print(f"Chaos {level}: {data['pass_rate']:.1%} pass rate")
```

## Reports

Generate reports in multiple formats:

```python
from balaganagent.reporting import ReportGenerator

gen = ReportGenerator()
report = gen.generate_from_results(results, metrics)

# Terminal (with colors)
print(gen.to_terminal(report))

# Save as files
gen.save(report, "report.json", format="json")
gen.save(report, "report.md", format="markdown")
gen.save(report, "report.html", format="html")
```

## Example Output

```
============================================================
  BALAGANAGENT EXPERIMENT REPORT
============================================================

  Generated: 2024-01-15T10:30:00
  Status: WARNING

SUMMARY
  Experiments: 5 (Completed: 4, Failed: 1)
  Operations:  150 (Success Rate: 87.3%)
  Faults:      23 injected

RELIABILITY
  Score: 0.82
  Grade: 99%
  MTTR:  1.3s

EXPERIMENTS
  search-reliability [completed]
    Duration: 12.34s | Success: 90.0% | Recovery: 85.0%

  calculate-stress [completed]
    Duration: 8.21s | Success: 95.0% | Recovery: 100.0%

RECOMMENDATIONS
  1. Recovery rate is 85.0%. Agents should implement better recovery mechanisms.
  2. Most frequent fault type: tool_failure. Focus testing on this failure mode.

============================================================
```

## Project Structure

```
balaganagent/
├── __init__.py          # Main exports
├── engine.py            # Chaos engine core
├── experiment.py        # Experiment definitions
├── wrapper.py           # Agent wrapping
├── runner.py            # Experiment runner
├── reporting.py         # Report generation
├── cli.py               # Command-line interface
├── injectors/           # Fault injectors
│   ├── base.py          # Base injector class
│   ├── tool_failure.py  # Tool failure injection
│   ├── delay.py         # Latency injection
│   ├── hallucination.py # Data corruption
│   ├── context.py       # Context corruption
│   └── budget.py        # Budget exhaustion
└── metrics/             # Metrics collection
    ├── collector.py     # General metrics
    ├── mttr.py          # MTTR calculation
    ├── recovery.py      # Recovery quality
    └── reliability.py   # Reliability scoring
```

## Documentation

- **[Full Docs (GitHub Pages)](https://arielshad.github.io/balagan-agent/)** - How it works, integrations, CLI reference, FAQ
- **[Development Guide](DEVELOPMENT.md)** - Set up your development environment
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to BalaganAgent
- **[Security Policy](SECURITY.md)** - Vulnerability reporting process
- **[Changelog](CHANGELOG.md)** - Version history and release notes
- **[CrewAI Integration](CREWAI_INTEGRATION_GUIDE.md)** - Step-by-step CrewAI setup

## Examples

Check out real-world examples:

- [Meeting Notes Agent](tests/test_meeting_notes_agent.py) - Real agent under chaos
- [CrewAI Integration](tests/test_crewai_wrapper.py) - CrewAI with chaos testing
- [Stress Testing](tests/test_crewai_sdk_stress.py) - Finding breaking points
- [BDD Scenarios](tests/bdd/) - Behavior-driven chaos scenarios

## Community

- **GitHub Discussions**: [Ask questions and share ideas](https://github.com/arielshad/balagan-agent/discussions)
- **Issue Tracker**: [Report bugs and request features](https://github.com/arielshad/balagan-agent/issues)
- **Linkedin**: Follow for updates [ariel-shadkhan](https://www.linkedin.com/in/ariel-shadkhan/)


## Contributing

We welcome contributions of all kinds! Whether it's:

- Bug reports and feature requests
- Code contributions (new injectors, wrappers, metrics)
- Documentation improvements
- Example agents and scenarios
- Blog posts and tutorials

Please read our [Contributing Guide](CONTRIBUTING.md) and [Development Guide](DEVELOPMENT.md) to get started.

### Contributors

Thanks to all our contributors!

<a href="https://github.com/arielshad/balagan-agent/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=arielshad/balagan-agent" />
</a>

## Roadmap

### Current (v0.1.x)
- ✅ Core chaos engine
- ✅ Basic injectors (tool failure, delay, hallucination, context, budget)
- ✅ CrewAI, AutoGen, LangChain wrappers
- ✅ MTTR and reliability metrics
- ✅ Multi-format reporting

### Coming Soon (v0.2.x)
- 🔄 Real-time chaos injection during agent execution
- 🔄 Advanced metrics (latency percentiles, error budgets)
- 🔄 Chaos schedules and campaigns
- 🔄 Web dashboard for visualization
- 🔄 More agent framework integrations (LangGraph, AutoGPT)

### Future (v0.3.x+)
- 📋 Distributed chaos experiments
- 📋 ML-powered failure prediction
- 📋 Custom injector plugins
- 📋 Production chaos (with safeguards)
- 📋 Cost impact analysis

Have an idea? [Open a discussion](https://github.com/arielshad/balagan-agent/discussions)!

## Comparison

### BalaganAgent vs Manual Testing

| Aspect | Manual Testing | BalaganAgent |
|--------|----------------|--------------|
| Coverage | Limited scenarios | Comprehensive failure modes |
| Consistency | Varies by tester | Reproducible experiments |
| Metrics | Manual tracking | Automated MTTR, recovery rate |
| Scale | Time-consuming | Run 100s of tests easily |
| Integration | N/A | Built-in CI/CD support |

### BalaganAgent vs Traditional Chaos Tools

Tools like Chaos Monkey and Gremlin are infrastructure-focused. BalaganAgent is purpose-built for AI agents:

- **Agent-aware**: Understands LLMs, tools, context, prompts
- **Semantic failures**: Injects hallucinations, not just network errors
- **Agent metrics**: MTTR, recovery quality, reliability scoring
- **Framework integration**: Works with CrewAI, AutoGen, LangChain

## Credits

Built with inspiration from:
- [Chaos Monkey](https://netflix.github.io/chaosmonkey/) - Netflix's pioneering chaos engineering
- [Gremlin](https://www.gremlin.com/) - Enterprise chaos engineering platform
- [pytest](https://pytest.org/) - Python testing framework
- The entire chaos engineering community

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details

## Star History

<a href="https://star-history.com/#arielshad/balagan-agent&Date">
  <img src="https://api.star-history.com/svg?repos=arielshad/balagan-agent&type=Date" alt="Star History Chart" width="600">
</a>

---

<div align="center">

**"Hope is not a strategy. Test your agents."**

Made with ❤️ by the reliability community

[⭐ Star on GitHub](https://github.com/arielshad/balagan-agent) • [📦 PyPI Package](https://pypi.org/project/balagan-agent/) • [🐛 Report Bug](https://github.com/arielshad/balagan-agent/issues) • [💡 Request Feature](https://github.com/arielshad/balagan-agent/discussions)

</div>
