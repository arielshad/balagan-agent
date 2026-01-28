# BalaganAgent Examples

Example implementations demonstrating BalaganAgent with different agent frameworks and LLM providers.

## CrewAI Examples

### 1. Basic Research Agent (Mock LLM)

**File:** [crewai_sdk_research_agent.py](crewai_sdk_research_agent.py)

A two-agent research crew demonstrating TDD principles with deterministic tools that don't require a real LLM.

**Features:**
- Sequential process: Researcher → Writer
- Deterministic tools for testing without API calls
- Tool factories to avoid singleton mutation
- Full test coverage (unit + stress tests)

**Agents:**
- **Senior Research Analyst** - Uses `search_web` and `summarize_text` tools
- **Technical Writer** - Uses `summarize_text` and `save_report` tools

**Installation:**
```bash
pip install -e ".[crewai]"
```

**Usage:**
```python
from examples.crewai_sdk_research_agent import build_research_crew

crew = build_research_crew(topic="quantum computing")
# Note: Requires OPENAI_API_KEY or mocked LLM for real execution
```

**Tests:**
- Unit tests: [tests/test_crewai_sdk_agent.py](../tests/test_crewai_sdk_agent.py)
- Stress tests: [tests/test_crewai_sdk_stress.py](../tests/test_crewai_sdk_stress.py)

---

### 2. Gemini-Powered Research Agent

**File:** [crewai_gemini_research_agent.py](crewai_gemini_research_agent.py)

Same two-agent research crew powered by Google's Gemini 3.0 Flash via LangChain integration.

**Features:**
- Uses Google Gemini 2.0 Flash (or configurable model)
- Environment variables loaded from `.env` file
- Same tool architecture as base example
- Full LLM integration for real agent orchestration

**Agents:**
- **Senior Research Analyst** - Gemini-powered researcher
- **Technical Writer** - Gemini-powered writer

**Installation:**
```bash
# Install with Gemini support
pip install -e ".[crewai-gemini]"

# Or install individually
pip install crewai langchain-google-genai python-dotenv
```

**Configuration:**

1. Create a `.env` file (or copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. Add your Google API key:
   ```bash
   GOOGLE_API_KEY=your_api_key_here
   ```

   Get your API key from: https://aistudio.google.com/app/apikey

**Usage:**

```python
from examples.crewai_gemini_research_agent import build_research_crew

# Uses Gemini Flash from environment
crew = build_research_crew(topic="chaos engineering")
result = crew.kickoff()
print(result.raw)
```

**CLI Usage:**
```bash
# Run from command line
python examples/crewai_gemini_research_agent.py "artificial intelligence"
```

**Custom LLM Configuration:**
```python
from examples.crewai_gemini_research_agent import build_research_crew, get_gemini_llm

# Use a different model or temperature
llm = get_gemini_llm(model="gemini-pro", temperature=0.5)
crew = build_research_crew(topic="machine learning", llm=llm)
```

**Tests:**
- Unit tests: [tests/test_crewai_gemini_agent.py](../tests/test_crewai_gemini_agent.py)
- All tests use mocked LLMs to avoid API calls

---

### 3. Chaos Engineering Example

**File:** [crewai_gemini_chaos_example.py](crewai_gemini_chaos_example.py)

A comprehensive chaos engineering demonstration that applies BalaganAgent to the Gemini-powered research agent, showing how agents behave under various failure conditions.

**Chaos Scenarios:**
1. **Tool Failures** - Random 50% failure rate on all tools
2. **Latency Injection** - 1-3 second delays on tool calls
3. **Partial Failures** - Primary tool (search_web) fails 70% of the time
4. **Data Corruption** - Tools return garbled/malformed outputs
5. **Stress Test** - Combined failures + latency under high load

**Features:**
- Real-time chaos statistics and metrics
- Multiple scenario configurations
- Command-line interface for easy testing
- Detailed output showing agent resilience

**Installation:**
```bash
# Install the main package with CrewAI and Gemini support
pip install -e ".[crewai-gemini]"
```

**Configuration:**
Same as Gemini example - requires `.env` file with `GOOGLE_API_KEY`.

**Usage:**

```bash
# Run tool failure scenario (default)
python examples/crewai_gemini_chaos_example.py

# Run specific scenario
python examples/crewai_gemini_chaos_example.py --scenario latency
python examples/crewai_gemini_chaos_example.py --scenario stress

# Run all scenarios
python examples/crewai_gemini_chaos_example.py --scenario all

# Custom topic
python examples/crewai_gemini_chaos_example.py --scenario failures --topic "distributed systems"
```

**Programmatic Usage:**
```python
from examples.crewai_gemini_chaos_example import (
    scenario_tool_failures,
    scenario_latency_injection,
    scenario_stress_test,
)

# Run individual scenarios
scenario_tool_failures(topic="quantum computing")
scenario_latency_injection(topic="blockchain")
scenario_stress_test(topic="artificial intelligence")
```

**Expected Output:**
```
🌪️  BalaganAgent — CrewAI Research Agent Chaos Testing
======================================================================

🔧 SCENARIO 1: Tool Failures (50% failure rate)
======================================================================
Topic: quantum computing
Testing: How agents handle when tools randomly fail

Starting chaotic execution...
✅ Execution completed in 12.34s

Agent Output:
----------------------------------------------------------------------
[Research report generated despite tool failures...]
----------------------------------------------------------------------

📊 Chaos Statistics:
Total tool calls: 15
Failed calls: 7
Success rate: 53.3%
```

**Key Insights:**
- Shows agent resilience under degraded conditions
- Measures impact of different failure types on output quality
- Helps identify critical dependencies and bottlenecks
- Validates graceful degradation strategies

---

## Stress Testing with BalaganAgent

Both examples can be stress-tested with BalaganAgent to inject chaos and measure reliability:

```python
from balaganagent.wrappers.crewai import CrewAIWrapper
from examples.crewai_gemini_research_agent import build_research_crew

# Build and wrap the crew
crew = build_research_crew(topic="distributed systems")
wrapper = CrewAIWrapper(crew, chaos_level=0.3)

# Configure chaos injectors
wrapper.configure_chaos(
    chaos_level=0.3,
    enable_tool_failures=True,
    enable_delays=True,
    enable_hallucinations=False,
)

# Run experiments
with wrapper.experiment("moderate-chaos"):
    for _ in range(10):
        try:
            result = wrapper.kickoff()
            print(f"✅ Success: {result.raw[:100]}...")
        except Exception as e:
            print(f"❌ Failure: {e}")

# Analyze results
metrics = wrapper.get_metrics()
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Mean latency: {metrics['tools']['search_web']['latency']['mean_ms']:.0f}ms")
```

## Meeting Notes Agent

**File:** [meeting_notes_agent.py](meeting_notes_agent.py)

A practical example demonstrating a meeting notes processing crew.

See the file for details.

---

## Environment Variables

Common environment variables used across examples:

| Variable | Required For | Description |
|----------|--------------|-------------|
| `GOOGLE_API_KEY` | Gemini examples | Google Gemini API key |
| `GEMINI_TOKEN` | Gemini examples | Alternative to GOOGLE_API_KEY |
| `OPENAI_API_KEY` | OpenAI examples | OpenAI API key (for base example if not mocked) |

**Note:** Test files use fake API keys via fixtures - no real API keys needed for testing.

---

## Running Tests

```bash
# Run all example tests
pytest tests/test_crewai_*.py -v

# Run specific example tests
pytest tests/test_crewai_gemini_agent.py -v

# Run stress tests
pytest tests/test_crewai_sdk_stress.py -v
```

## Contributing

When adding new examples:

1. Follow the TDD pattern (write tests first)
2. Create both unit tests and stress tests
3. Use tool factories to avoid singleton mutation
4. Document required dependencies in `pyproject.toml`
5. Add environment variable documentation
6. Update this README
