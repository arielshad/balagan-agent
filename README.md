# AgentChaos

**Chaos Engineering for AI Agents**

Everyone demos agents. Nobody stress-tests them.

AgentChaos is a reliability testing framework that stress-tests AI agents through controlled fault injection—because your agent will fail in production, and you should know how it handles it.

## Why AgentChaos?

AI agents are entering production environments, but there's zero reliability discipline. AgentChaos brings the battle-tested principles of chaos engineering (think Chaos Monkey, Gremlin) to the world of AI agents.

**The Problem:**
- Agents fail silently in production
- Tool calls time out, return garbage, or hallucinate
- Context gets corrupted, budgets get exhausted
- Nobody knows until users complain

**The Solution:**
- Inject failures in development, not production
- Measure recovery time (MTTR)
- Score reliability like we score SLAs
- Find breaking points before users do

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

### Installation

```bash
pip install agentchaos
```

### Basic Usage

```python
from agentchaos import ChaosEngine, AgentWrapper

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
from agentchaos import ChaosEngine
from agentchaos.runner import scenario, ExperimentRunner

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
agentchaos demo --chaos-level 0.5

# Initialize a new project
agentchaos init my-chaos-tests

# Run a scenario file
agentchaos run scenarios/search_test.json --chaos-level 0.75

# Run stress tests
agentchaos stress scenarios/critical_path.json --iterations 100
```

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
from agentchaos.injectors import ToolFailureInjector
from agentchaos.injectors.tool_failure import ToolFailureConfig, FailureMode

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
from agentchaos.injectors import DelayInjector
from agentchaos.injectors.delay import DelayConfig, DelayPattern, LatencySimulator

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
from agentchaos.injectors import HallucinationInjector
from agentchaos.injectors.hallucination import HallucinationConfig, HallucinationType

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
from agentchaos.injectors import BudgetExhaustionInjector
from agentchaos.injectors.budget import BudgetExhaustionConfig

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
from agentchaos.metrics import MTTRCalculator

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
from agentchaos.metrics import ReliabilityScorer

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
from agentchaos.reporting import ReportGenerator

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
  AGENTCHAOS EXPERIMENT REPORT
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
agentchaos/
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

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.

---

*"Hope is not a strategy. Test your agents."*
