# BalaganAgent + Research Agent Integration Example

This example demonstrates how to integrate the **BalaganAgent chaos testing framework** with the **Claude Agent SDK research agent** system (`research_agent/agent.py`).

## Overview

The example shows how to:
1. **Wrap research tools** with chaos injection for failure testing
2. **Run research workflows** with controlled failure injection
3. **Analyze resilience** at different chaos levels
4. **Measure MTTR** (Mean Time To Recovery) and reliability metrics
5. **Identify breaking points** where the system fails

## Quick Start

### Basic Chaos Test
```bash
python3 examples/balagan_research_agent_example.py
```

### Test Escalating Chaos Levels
```bash
python3 examples/balagan_research_agent_example.py --test-mode escalating
```

### Test Individual Tool Failures
```bash
python3 examples/balagan_research_agent_example.py --test-mode targeted
```

### Measure Recovery Time (MTTR)
```bash
python3 examples/balagan_research_agent_example.py --test-mode mttr
```

### Find System Breaking Points
```bash
python3 examples/balagan_research_agent_example.py --test-mode resilience
```

### Run All Tests
```bash
python3 examples/balagan_research_agent_example.py --test-mode all --topic "quantum computing"
```

## Command-Line Options

```
--topic TEXT              Research topic (default: "artificial intelligence")
--chaos-level FLOAT       Base chaos level 0.0-2.0 (default: 0.5)
--test-mode {basic,escalating,targeted,mttr,resilience,all}
                         Which chaos test to run (default: basic)
--output-dir TEXT        Directory for output files (default: chaos_reports)
--quiet                  Suppress verbose output
```

## What Each Test Does

### 1. Basic Chaos Injection (`basic`)

Runs a complete research workflow with chaos enabled:
- **Search Phase**: Queries for information on a topic
- **Summarize Phase**: Condenses the findings
- **Report Phase**: Generates a markdown report

Outputs:
- Success/failure status for each phase
- Operation metrics (total operations, success rate, latency)
- MTTR stats if recovery events occurred

```bash
python3 examples/balagan_research_agent_example.py --test-mode basic
```

### 2. Escalating Chaos Levels (`escalating`)

Tests the same workflow at increasing chaos intensities:
- 0.0 (no chaos, baseline)
- 0.25 (low chaos)
- 0.5 (medium chaos)
- 0.75 (high chaos)
- 1.0 (maximum chaos)

Shows how performance degrades with increasing failure rates:
```
Level      Phases    Success Rate
0.00       3/3       100%           ✓ ACCEPTABLE
0.25       3/3       100%           ✓ ACCEPTABLE
0.50       3/3       100%           ✓ ACCEPTABLE
0.75       3/3       100%           ✓ ACCEPTABLE
1.00       3/3       100%           ✓ ACCEPTABLE
```

### 3. Targeted Tool Failures (`targeted`)

Injects failures on individual tools to isolate failure modes:
- `search_web`: Tests when information gathering fails
- `summarize_text`: Tests when summarization fails
- `save_report`: Tests when report generation fails

Helps identify which tool failures are most critical:
```
Injecting 50% failure rate on search_web:
  Success rate: 50% (5/10)

Injecting 50% failure rate on summarize_text:
  Success rate: 50% (5/10)

Injecting 50% failure rate on save_report:
  Success rate: 50% (5/10)
```

### 4. MTTR Analysis (`mttr`)

Analyzes Mean Time To Recovery with built-in retries:
- Measures how long it takes the system to recover from failures
- Tests retry mechanisms under 40% failure rate
- Calculates min/max/mean recovery times

Useful for understanding system resilience and recovery patterns.

### 5. Resilience Patterns (`resilience`)

Tests at progressively higher chaos levels to find breaking points:
- 0.3, 0.5, 0.7, 0.9, 1.2, 1.5
- Identifies where success rate drops below acceptable thresholds
- Shows system degradation patterns

```
Chaos Level     Workflow Success          Status
0.3             5/5 (100%)           ✓ ACCEPTABLE
0.5             5/5 (100%)           ✓ ACCEPTABLE
0.7             5/5 (100%)           ✓ ACCEPTABLE
0.9             5/5 (100%)           ✓ ACCEPTABLE
1.2             5/5 (100%)           ✓ ACCEPTABLE
1.5             5/5 (100%)           ✓ ACCEPTABLE

✓ System resilient across all tested chaos levels
```

## Understanding the Metrics

### Operations Metrics
- **Total operations**: Number of tool calls made
- **Success rate**: Percentage of successful operations
- **Avg latency**: Average execution time in milliseconds

### MTTR (Mean Time To Recovery)
- **Recovery events**: Number of times the system recovered from failures
- **MTTR (seconds)**: Average time to recover from a failure
- **Min/Max recovery time**: Fastest and slowest recovery times

## Integration with research_agent/agent.py

This example shows how to add chaos testing to the Claude Agent SDK research agent. The integration pattern:

```python
from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_research_tools import get_research_tools

# 1. Create wrapper with tools and chaos level
wrapper = ClaudeAgentSDKWrapper(
    tools=get_research_tools(mode="mock"),
    chaos_level=0.5
)

# 2. Configure which types of chaos to inject
wrapper.configure_chaos(
    chaos_level=0.5,
    enable_tool_failures=True,      # Inject tool failures
    enable_delays=True,              # Inject latency
    enable_hallucinations=False,     # Don't hallucinate (keep data accurate)
    enable_context_corruption=False, # Don't corrupt context
    enable_budget_exhaustion=False,  # Don't exhaust budget
)

# 3. Get wrapped tools and use them normally
tools = wrapper.get_wrapped_tools()
result = tools["search_web"]({"query": "AI safety"})

# 4. Collect metrics
metrics = wrapper.get_metrics()
mttr = wrapper.get_mttr_stats()
```

## Using with Claude Agent SDK

To integrate this pattern with the full Claude Agent SDK multi-agent system:

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper

# Wrap your tools with chaos
wrapper = ClaudeAgentSDKWrapper(tools=your_tools, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True)

# Create MCP server from wrapped tools
mcp_server = wrapper.create_mcp_server(name="research-tools", version="1.0.0")

# Use with Claude Agent SDK
options = ClaudeAgentOptions(
    mcp_servers={"tools": mcp_server},
    allowed_tools=["mcp__tools__search_web", "mcp__tools__summarize_text"],
)

async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt="Research AI safety")
```

## Chaos Levels Explained

Chaos level controls the probability of failures:

- **0.0**: No chaos, baseline behavior
- **0.25**: Light chaos (25% expected failure rate)
- **0.5**: Moderate chaos (50% expected failure rate) - good for testing
- **0.75**: High chaos (75% expected failure rate)
- **1.0**: Extreme chaos (100% expected failure rate)
- **>1.0**: Multiple failures per operation possible

## Advanced Usage

### Targeted Tool Failure Injection

Inject failures on specific tools only:

```python
from balaganagent.injectors import ToolFailureInjector
from balaganagent.injectors.tool_failure import ToolFailureConfig

wrapper = ClaudeAgentSDKWrapper(tools=tools, chaos_level=0.5)

# 50% failure rate on search_web only
injector = ToolFailureInjector(ToolFailureConfig(probability=0.5))
wrapper.add_injector(injector, tools=["search_web"])

tools = wrapper.get_wrapped_tools()
```

### Named Experiments

Track experiments separately:

```python
with wrapper.experiment("my-test"):
    wrapper.record_query()
    # Run your workflow...

results = wrapper.get_experiment_results()
for result in results:
    print(f"Experiment: {result.config.name}")
    print(f"Success rate: {result.metrics['aggregate']['operations']['success_rate']:.1%}")
```

## Example Output

When running `balagan_research_agent_example.py --test-mode resilience`:

```
######################################################################
#  BALAGAN AGENT + RESEARCH AGENT CHAOS TESTING
######################################################################

======================================================================
EXAMPLE 5: Resilience Patterns
======================================================================
Testing to find resilience breaking points

Chaos Level     Workflow Success          Status
-------------------------------------------------------
0.3             5/5 (100%)           ✓ ACCEPTABLE
0.5             5/5 (100%)           ✓ ACCEPTABLE
0.7             5/5 (100%)           ✓ ACCEPTABLE
0.9             5/5 (100%)           ✓ ACCEPTABLE
1.2             5/5 (100%)           ✓ ACCEPTABLE
1.5             5/5 (100%)           ✓ ACCEPTABLE

✓ System resilient across all tested chaos levels

######################################################################
#  CHAOS TESTING COMPLETED
######################################################################
```

## Output Files

Generated files are saved to the `chaos_reports/` directory:
- `report_<topic>_chaos.md`: Markdown research reports from basic test

## Related Examples

- **claude_sdk_research_agent.py**: Simple research workflow with optional chaos
- **claude_sdk_research_chaos_example.py**: Detailed chaos testing examples
- **claude_sdk_agent.py**: Basic Claude Agent SDK integration
- **research_agent/agent.py**: Full multi-agent interactive research system

## Troubleshooting

### No metric data collected

Metrics are collected per experiment. Make sure to use:
```python
with wrapper.experiment("test-name"):
    wrapper.record_query()
    # Run your code...
```

### All tests pass but metrics show 0%

This is expected when using mock tools without real failures. The mock tools always succeed unless chaos is explicitly configured.

### High failure rates at low chaos levels

This may indicate the tools are already failing. Check your tool implementation and error handling.

## Learn More

- [BalaganAgent Documentation](https://github.com/arielshad/balagan-agent)
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
