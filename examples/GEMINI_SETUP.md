# CrewAI + Gemini 3.0 Flash Setup Guide

This guide explains how to use the Gemini-powered CrewAI research agent example.

## Overview

The [crewai_gemini_research_agent.py](crewai_gemini_research_agent.py) example demonstrates:

- **Google Gemini 2.0 Flash** integration via LangChain
- **Environment-based configuration** using python-dotenv
- **Two-agent sequential workflow** (Researcher → Writer)
- **Full TDD test coverage** with mocked LLMs

## Quick Start

### 1. Install Dependencies

```bash
# Install with Gemini support
pip install -e ".[crewai-gemini]"

# Or install packages individually
pip install crewai langchain-google-genai python-dotenv
```

### 2. Configure Environment

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your Google API key
echo "GOOGLE_API_KEY=your_api_key_here" >> .env
```

Get your API key from: https://aistudio.google.com/app/apikey

### 3. Run the Example

```bash
# From Python
python examples/crewai_gemini_research_agent.py "chaos engineering"

# Or import and use
python -c "
from examples.crewai_gemini_research_agent import build_research_crew

crew = build_research_crew(topic='distributed systems')
result = crew.kickoff()
print(result.raw)
"
```

## Usage Examples

### Basic Usage

```python
from examples.crewai_gemini_research_agent import build_research_crew

# Uses Gemini Flash from environment
crew = build_research_crew(topic="artificial intelligence")
result = crew.kickoff()
print(result.raw)
```

### Custom Model Configuration

```python
from examples.crewai_gemini_research_agent import build_research_crew, get_gemini_llm

# Use a different model or temperature
llm = get_gemini_llm(
    model="gemini-pro",  # or "gemini-2.0-flash-exp"
    temperature=0.3
)

crew = build_research_crew(topic="machine learning", llm=llm)
result = crew.kickoff()
```

### Individual Agent Creation

```python
from examples.crewai_gemini_research_agent import (
    create_researcher_agent,
    create_writer_agent,
    create_research_task,
    create_report_task,
    get_gemini_llm
)

# Create custom LLM
llm = get_gemini_llm(temperature=0.5)

# Build agents
researcher = create_researcher_agent(llm=llm)
writer = create_writer_agent(llm=llm)

# Create tasks
research = create_research_task(researcher, topic="quantum computing")
report = create_report_task(writer, research)

# Build custom crew
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, writer],
    tasks=[research, report],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
```

## Stress Testing with AgentChaos

```python
from agentchaos.wrappers.crewai import CrewAIWrapper
from examples.crewai_gemini_research_agent import build_research_crew

# Build and wrap the crew
crew = build_research_crew(topic="reliability engineering")
wrapper = CrewAIWrapper(crew, chaos_level=0.3)

# Configure chaos
wrapper.configure_chaos(
    chaos_level=0.3,
    enable_tool_failures=True,
    enable_delays=True,
)

# Run experiment
with wrapper.experiment("moderate-chaos"):
    for i in range(10):
        try:
            result = wrapper.kickoff()
            print(f"✅ Run {i+1}: Success")
        except Exception as e:
            print(f"❌ Run {i+1}: {e}")

# Analyze results
metrics = wrapper.get_metrics()
print(f"Total runs: {metrics['kickoff_count']}")
print(f"Tool calls: {sum(t['latency']['count'] for t in metrics['tools'].values())}")
```

## Running Tests

```bash
# Run all Gemini tests
pytest tests/test_crewai_gemini_agent.py -v

# Run specific test class
pytest tests/test_crewai_gemini_agent.py::TestGeminiLLMConfiguration -v

# Run with coverage
pytest tests/test_crewai_gemini_agent.py --cov=examples.crewai_gemini_research_agent
```

All tests use mocked LLMs - no API key needed for testing!

## Architecture

### Agents

1. **Senior Research Analyst**
   - Role: Find comprehensive information
   - Tools: `search_web`, `summarize_text`
   - LLM: Gemini 2.0 Flash

2. **Technical Writer**
   - Role: Write clear, concise reports
   - Tools: `summarize_text`, `save_report`
   - LLM: Gemini 2.0 Flash

### Tools

All tools are deterministic for testability:

- `search_web(query)` - Returns simulated search results
- `summarize_text(text)` - Extracts first 3 sentences
- `save_report(content)` - Returns word count confirmation

### Process

Sequential execution:
1. Researcher gathers and summarizes information
2. Writer uses research to create polished report
3. Report is saved and returned

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key (primary) |
| `GEMINI_TOKEN` | No | Alternative name for API key |

The code checks `GOOGLE_API_KEY` first, then falls back to `GEMINI_TOKEN`.

## Troubleshooting

### "Google API key not found"

- Ensure `.env` file exists in project root
- Check that `GOOGLE_API_KEY` or `GEMINI_TOKEN` is set
- Verify the API key is valid (get one from https://aistudio.google.com)

### "ModuleNotFoundError: No module named 'langchain_google_genai'"

```bash
pip install langchain-google-genai
```

### Tests failing with "Model must be a non-empty string"

This happens when mocking the LLM incorrectly. Mock must have a `model` attribute:

```python
mock_llm = MagicMock()
mock_llm.model = "gemini-2.0-flash-exp"
```

## Differences from Base Example

The Gemini version differs from [crewai_sdk_research_agent.py](crewai_sdk_research_agent.py):

| Feature | Base Example | Gemini Example |
|---------|--------------|----------------|
| LLM | Not specified (uses default) | Google Gemini 2.0 Flash |
| Config | Hardcoded | Environment variables |
| API Key | OPENAI_API_KEY | GOOGLE_API_KEY or GEMINI_TOKEN |
| Dependencies | crewai only | crewai + langchain-google-genai + python-dotenv |

## Next Steps

- **Add more agents**: Extend with editor, fact-checker, etc.
- **Hierarchical process**: Add a manager agent to coordinate
- **Real tools**: Replace simulated tools with actual APIs
- **Planning mode**: Enable `planning=True` in Crew
- **YAML configs**: Move agent/task definitions to config files

See [examples/README.md](README.md) for more patterns and examples.
