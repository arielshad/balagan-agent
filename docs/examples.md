# Examples

All examples live in the [`examples/`](https://github.com/arielshad/balagan-agent/tree/main/examples) directory.

## Basic Usage

Wrap an agent and inject chaos:

```python
from balaganagent import ChaosEngine, AgentWrapper

class MyAgent:
    def search(self, query: str) -> dict:
        return {"results": ["result1", "result2"]}

agent = MyAgent()
wrapper = AgentWrapper(agent)
wrapper.configure_chaos(chaos_level=0.5)

result = wrapper.call_tool("search", "test query")
```

**File:** [`examples/basic_usage.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/basic_usage.py)

## Stress Testing

Run experiments at multiple chaos levels to find your agent's breaking point:

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

**File:** [`examples/stress_test.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/stress_test.py)

## CrewAI Integration

```python
from balaganagent.wrappers.crewai import CrewAIWrapper

wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.kickoff()
```

**Files:**

- [`examples/crewai_gemini_research_agent.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/crewai_gemini_research_agent.py)
- [`examples/crewai_gemini_chaos_example.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/crewai_gemini_chaos_example.py)

## Claude Agent SDK

```python
from balaganagent.wrappers.claude_sdk import ClaudeSDKWrapper

wrapper = ClaudeSDKWrapper(agent, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True)
result = wrapper.run(task)
```

**Files:**

- [`examples/claude_sdk_agent.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/claude_sdk_agent.py)
- [`examples/claude_sdk_chaos_example.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/claude_sdk_chaos_example.py)

## Meeting Notes Agent

A real-world agent example with chaos testing:

**File:** [`examples/meeting_notes_agent.py`](https://github.com/arielshad/balagan-agent/blob/main/examples/meeting_notes_agent.py)

## Running Examples

```bash
# Clone the repo
git clone https://github.com/arielshad/balagan-agent.git
cd balagan-agent

# Install with dev dependencies
pip install -e ".[dev]"

# Run any example
python examples/basic_usage.py
python examples/stress_test.py
```
