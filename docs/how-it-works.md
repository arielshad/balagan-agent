# How It Works

BalaganAgent injects controlled failures into your agent's tool calls, then measures how well the agent recovers.

## Architecture

```
Your Agent  →  BalaganAgent Wrapper  →  Chaos Engine  →  Injectors
                                              ↓
                                        Metrics Collector
                                              ↓
                                        Report Generator
```

## Chaos Levels

The `chaos_level` parameter controls fault injection probability:

| Level | Base Failure Rate | Use Case |
|-------|------------------|----------|
| 0.0   | 0%  | Baseline (no chaos) |
| 0.25  | 2.5%  | Light testing |
| 0.5   | 5%  | Moderate chaos |
| 1.0   | 10% | Standard chaos |
| 2.0   | 20% | Stress testing |

## Fault Injectors

### Tool Failure Injector

Simulates tool failure modes: exceptions, timeouts, empty responses, malformed data, rate limits, auth failures, service unavailable.

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

Simulates network latency: fixed, uniform random, exponential, spike, degrading, jitter patterns.

```python
from balaganagent.injectors import DelayInjector
from balaganagent.injectors.delay import DelayConfig, DelayPattern, LatencySimulator

# Use a preset
injector = LatencySimulator.create("poor")

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

Corrupts data to test detection: wrong values, fabricated data, contradictions, confident-wrong, partial truth, outdated info, nonexistent references.

```python
from balaganagent.injectors import HallucinationInjector
from balaganagent.injectors.hallucination import HallucinationConfig, HallucinationType

injector = HallucinationInjector(HallucinationConfig(
    probability=0.05,
    severity=0.5,
    hallucination_types=[
        HallucinationType.WRONG_VALUE,
        HallucinationType.FABRICATED_DATA,
    ]
))
```

### Context Corruption Injector

Corrupts agent context: truncation, reordering, duplicates, dropped entries, noise injection, encoding issues, stale data, circular references, overflow.

### Budget Exhaustion Injector

Simulates resource limits: token limits, time limits, cost caps, call limits, rate limits, memory limits, concurrent limits.

```python
from balaganagent.injectors import BudgetExhaustionInjector
from balaganagent.injectors.budget import BudgetExhaustionConfig

injector = BudgetExhaustionInjector(BudgetExhaustionConfig(
    token_limit=10000,
    cost_limit_dollars=1.00,
    rate_limit_per_minute=60,
    fail_hard=True,
))
```

## Metrics

### MTTR (Mean Time To Recovery)

How fast does your agent recover from a fault?

```python
from balaganagent.metrics import MTTRCalculator

calc = MTTRCalculator()
calc.record_failure("search", "timeout")
# ... agent recovers ...
calc.record_recovery("search", "timeout", retries=2)

stats = calc.get_recovery_stats()
print(f"MTTR: {stats['mttr_seconds']:.2f}s")
```

### Reliability Scorer

SRE-grade scoring with SLO tracking:

```python
from balaganagent.metrics import ReliabilityScorer

scorer = ReliabilityScorer(slos={
    "availability": 0.99,
    "latency_p99_ms": 2000,
})

for result in agent_results:
    scorer.record_operation(
        success=result.success,
        latency_ms=result.latency,
    )

report = scorer.calculate_score()
print(f"Grade: {report.grade.value}")
print(f"Error Budget Remaining: {report.error_budget_remaining:.1%}")
```

## Reports

Generate reports in four formats:

```python
from balaganagent.reporting import ReportGenerator

gen = ReportGenerator()
report = gen.generate_from_results(results, metrics)

gen.save(report, "report.json", format="json")
gen.save(report, "report.md", format="markdown")
gen.save(report, "report.html", format="html")
print(gen.to_terminal(report))
```

## Scenarios

Define experiments in code or JSON:

```json
{
  "name": "critical-path-test",
  "description": "Test the critical user journey",
  "operations": [
    {"tool": "authenticate", "args": ["user123"]},
    {"tool": "fetch_profile", "args": ["user123"]},
    {"tool": "search", "args": ["recent orders"]}
  ],
  "chaos_config": {
    "chaos_level": 0.5,
    "enable_tool_failures": true,
    "enable_delays": true
  }
}
```
