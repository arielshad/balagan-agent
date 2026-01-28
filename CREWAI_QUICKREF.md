# CrewAI + AgentChaos Quick Reference

**One-page cheatsheet for chaos testing your CrewAI agents**

---

## Installation
```bash
pip install agentchaos crewai
```

---

## Basic Integration (3 Lines)

```python
from agentchaos.wrappers.crewai import CrewAIWrapper

wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.kickoff()
```

---

## Common Patterns

### Pattern 1: Light Testing (Development)
```python
wrapper = CrewAIWrapper(crew, chaos_level=0.25, verbose=False)
wrapper.configure_chaos(
    enable_tool_failures=True,
    enable_delays=False,
)
```

### Pattern 2: Standard Testing (Pre-Production)
```python
wrapper = CrewAIWrapper(crew, chaos_level=0.5, verbose=True)
wrapper.configure_chaos(
    enable_tool_failures=True,
    enable_delays=True,
    enable_budget_exhaustion=True,
)
```

### Pattern 3: Stress Testing (Find Limits)
```python
wrapper = CrewAIWrapper(crew, chaos_level=2.0, verbose=True)
wrapper.configure_chaos(
    enable_tool_failures=True,
    enable_delays=True,
    enable_hallucinations=True,
    enable_context_corruption=True,
)
```

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chaos_level` | 0.0 | Base chaos intensity (0.0-2.0+) |
| `max_retries` | 3 | Retry attempts for failed tools |
| `retry_delay` | 0.1 | Seconds between retries |
| `verbose` | False | Show detailed logs |

**Chaos Level Guide:**
- `0.25` = 2.5% failure rate (light)
- `0.5` = 5% failure rate (moderate)
- `1.0` = 10% failure rate (standard)
- `2.0` = 20% failure rate (stress test)

---

## Check Results

```python
# Get metrics
metrics = wrapper.get_metrics()

# Success rate
for tool_name, tool_metrics in metrics['tools'].items():
    ops = tool_metrics.get('operations', {})
    total = ops.get('total', 0)
    failed = ops.get('failed', 0)
    success_rate = ((total - failed) / total) * 100 if total > 0 else 0
    print(f"{tool_name}: {success_rate:.1f}% success")

# Recovery stats (MTTR)
mttr_stats = wrapper.get_mttr_stats()
for tool_name, stats in mttr_stats['tools'].items():
    if stats.get('recovery_count', 0) > 0:
        print(f"{tool_name}: {stats['mttr_seconds']:.2f}s recovery time")
```

---

## Enable Verbose Logging

```python
from agentchaos import set_verbose

# Global
set_verbose(True)

# Or per-wrapper
wrapper = CrewAIWrapper(crew, verbose=True)
```

---

## Multiple Test Runs

```python
wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True)

for i in range(10):
    result = wrapper.kickoff()
    wrapper.reset()  # Reset for next run
```

---

## Custom Injectors

```python
from agentchaos.injectors import ToolFailureInjector
from agentchaos.injectors.tool_failure import ToolFailureConfig

# Create wrapper
wrapper = CrewAIWrapper(crew, chaos_level=0.0)

# Add custom injector to specific tools
injector = ToolFailureInjector(ToolFailureConfig(probability=0.3))
wrapper.add_injector(injector, tools=["search_tool", "scrape_tool"])
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Too many failures | Lower `chaos_level` or increase `max_retries` |
| No faults injected | Check `chaos_level > 0` and `configure_chaos()` called |
| Crew never completes | Increase `max_retries` or lower `chaos_level` |
| Want verbose logs | Set `verbose=True` or call `set_verbose(True)` |

---

## Pytest Integration

```python
def test_crew_resilience():
    crew = create_my_crew()
    wrapper = CrewAIWrapper(crew, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True)

    result = wrapper.kickoff()
    assert result is not None

    metrics = wrapper.get_metrics()
    # Add your assertions
```

---

## Complete Example

```python
from crewai import Agent, Task, Crew
from agentchaos.wrappers.crewai import CrewAIWrapper

# 1. Create your crew (as usual)
agent = Agent(role="Researcher", goal="Find info", tools=[search_tool])
task = Task(description="Research AI trends", agent=agent)
crew = Crew(agents=[agent], tasks=[task])

# 2. Wrap with chaos
wrapper = CrewAIWrapper(crew, chaos_level=0.5, verbose=True)
wrapper.configure_chaos(
    enable_tool_failures=True,
    enable_delays=True,
)

# 3. Run
result = wrapper.kickoff()

# 4. Check metrics
metrics = wrapper.get_metrics()
print(f"Kickoffs: {metrics['kickoff_count']}")
for tool_name, tool_metrics in metrics['tools'].items():
    ops = tool_metrics.get('operations', {})
    print(f"{tool_name}: {ops.get('total', 0)} calls, "
          f"{ops.get('failed', 0)} failures")
```

---

📖 **Full Guide:** [CREWAI_INTEGRATION_GUIDE.md](CREWAI_INTEGRATION_GUIDE.md)
🐛 **Issues:** [GitHub Issues](https://github.com/anthropics/agent-chaos/issues)
⭐ **Star the repo!**
