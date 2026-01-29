# BalaganAgent — agents.md

> Chaos Engineering for AI Agents. Stress-test your agents before production breaks them.

## What This Project Does

BalaganAgent is a reliability testing framework that injects controlled failures into AI agent tool calls to measure how agents handle faults, recover from errors, and degrade gracefully. It provides SRE-grade reliability metrics (MTTR, availability scores, error budgets) for AI agents.

## Key Concepts

- **Chaos Engine**: Orchestrates fault injection experiments against agents
- **Fault Injectors**: Pluggable modules that inject specific failure types (tool failures, delays, hallucinations, context corruption, budget exhaustion)
- **Framework Wrappers**: Adapters that integrate chaos testing with CrewAI, AutoGen, LangChain, and Claude Agent SDK
- **Metrics Collectors**: Track MTTR, recovery quality, reliability scores, and operation success rates
- **Experiments**: Configurable test runs with defined chaos levels and target parameters

## Project Structure

```
balaganagent/
├── engine.py              # Core chaos orchestrator
├── wrapper.py             # Base agent wrapper (tool interception)
├── experiment.py          # Experiment config and results
├── runner.py              # Scenario runner and stress testing
├── reporting.py           # Report generation (JSON/MD/HTML/terminal)
├── cli.py                 # CLI: run, stress, demo, init
├── verbose.py             # Logging utilities
├── injectors/
│   ├── base.py            # BaseInjector ABC, FaultType enum
│   ├── tool_failure.py    # Tool failure modes (timeout, 429, 503, etc.)
│   ├── delay.py           # Latency injection (fixed, random, spike)
│   ├── hallucination.py   # Data corruption (wrong values, fabrication)
│   ├── context.py         # Context corruption (truncation, reorder)
│   └── budget.py          # Resource exhaustion (tokens, cost, rate)
├── metrics/
│   ├── collector.py       # General metrics collection
│   ├── mttr.py            # Mean Time To Recovery
│   ├── recovery.py        # Recovery quality analysis
│   └── reliability.py     # SRE-grade reliability scoring
└── wrappers/
    ├── crewai.py          # CrewAI integration
    ├── autogen.py         # Microsoft AutoGen integration
    ├── langchain.py       # LangChain integration
    └── claude_sdk.py      # Claude Agent SDK integration

examples/                  # Usage examples for all frameworks
tests/                     # Unit, BDD, and E2E tests
claude-agent-sdk-demos/    # Claude Agent SDK demo agents
```

## How to Use BalaganAgent

### 1. Wrap an agent with chaos
```python
from balaganagent.wrappers.crewai import CrewAIWrapper

wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(
    enable_tool_failures=True,
    enable_delays=True,
    enable_hallucinations=True
)
```

### 2. Run experiments
```python
result = wrapper.kickoff()
metrics = wrapper.get_metrics()
```

### 3. Analyze reliability
Metrics include: success rate, MTTR, recovery quality, SRE reliability grade (99.999% to 90%), error budget consumption.

### 4. Generate reports
```python
from balaganagent.reporting import Reporter
reporter = Reporter(results)
reporter.generate("markdown")  # or "json", "html", "terminal"
```

## Supported Frameworks

| Framework | Wrapper Class | Import Path |
|-----------|--------------|-------------|
| CrewAI | `CrewAIWrapper` | `balaganagent.wrappers.crewai` |
| AutoGen | `AutoGenWrapper` | `balaganagent.wrappers.autogen` |
| LangChain | `LangChainAgentWrapper` | `balaganagent.wrappers.langchain` |
| Claude Agent SDK | `ClaudeAgentSDKWrapper` | `balaganagent.wrappers.claude_sdk` |

## Fault Injection Types

| Type | Module | What It Does |
|------|--------|-------------|
| Tool Failure | `injectors/tool_failure.py` | Exceptions, timeouts, empty responses, HTTP errors (429/401/404/503) |
| Delay | `injectors/delay.py` | Fixed/random/spike/degrading latency |
| Hallucination | `injectors/hallucination.py` | Wrong values, fabricated data, contradictions, fake references |
| Context Corruption | `injectors/context.py` | Truncation, reordering, noise, encoding issues |
| Budget Exhaustion | `injectors/budget.py` | Token limits, cost caps, rate limiting, call quotas |

## Installation

```bash
pip install balagan-agent
pip install balagan-agent[crewai]      # With CrewAI support
pip install balagan-agent[langchain]   # With LangChain support
pip install balagan-agent[dev]         # Development dependencies
```

## CLI Usage

```bash
balaganagent run <scenario>            # Run a chaos scenario
balaganagent stress <scenario>         # Stress test at escalating levels
balaganagent demo --chaos-level 0.5    # Run demo experiment
balaganagent init                      # Initialize new project
```
