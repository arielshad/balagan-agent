# Development Guide

Welcome to BalaganAgent development! This guide will help you set up your environment and contribute to the project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Development Workflow](#development-workflow)
- [CLI Development](#cli-development)
- [Adding New Features](#adding-new-features)
- [Testing with Agent Frameworks](#testing-with-agent-frameworks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python**: 3.10 or higher
- **Git**: For version control
- **Virtual Environment**: Recommended (venv or conda)
- **Make** (optional): For convenience commands

### Verify Prerequisites

```bash
python --version  # Should be 3.10+
git --version
```

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/arielshad/balagan-agent.git
cd balagan-agent
```

### 2. Create Virtual Environment

```bash
# Using venv (recommended)
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Or install with all optional dependencies for testing all wrappers
pip install -e ".[dev,all-wrappers]"
```

### 4. Verify Installation

```bash
# Run tests to verify setup
pytest tests/ -v

# Check CLI works
balaganagent --version
```

## Project Structure

```
balaganagent/
├── __init__.py              # Main exports
├── engine.py                # Chaos engine core
├── experiment.py            # Experiment definitions
├── wrapper.py               # Agent wrapper base
├── runner.py                # Experiment runner
├── reporting.py             # Report generation
├── cli.py                   # Command-line interface
├── verbose.py               # Logging utilities
├── injectors/               # Fault injection modules
│   ├── base.py              # Base injector interface
│   ├── tool_failure.py      # Tool failure injection
│   ├── delay.py             # Latency injection
│   ├── hallucination.py     # Data corruption
│   ├── context.py           # Context corruption
│   └── budget.py            # Budget exhaustion
├── metrics/                 # Metrics collection
│   ├── collector.py         # General metrics
│   ├── mttr.py              # MTTR calculation
│   ├── recovery.py          # Recovery quality
│   └── reliability.py       # Reliability scoring
└── wrappers/                # Agent framework integrations
    ├── crewai.py            # CrewAI integration
    ├── autogen.py           # AutoGen integration
    └── langchain.py         # LangChain integration

tests/
├── test_*.py                # Unit tests
├── bdd/                     # BDD tests (Gherkin)
└── e2e/                     # End-to-end tests
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=balaganagent --cov-report=html

# Run with verbose output
pytest -v
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/test_*.py

# BDD tests
pytest tests/bdd/

# End-to-end tests
pytest tests/e2e/

# Specific test file
pytest tests/test_engine.py -v

# Specific test
pytest tests/test_engine.py::test_chaos_level -v
```

### Test with Different Frameworks

```bash
# Install specific framework dependencies first
pip install -e ".[crewai]"
pytest tests/test_crewai_wrapper.py

pip install -e ".[autogen]"
pytest tests/test_autogen_wrapper.py

pip install -e ".[langchain]"
pytest tests/test_langchain_wrapper.py
```

### Async Tests

BalaganAgent uses pytest-asyncio for async tests:

```bash
# Async tests run automatically
pytest tests/test_async*.py -v
```

## Code Quality

### Formatting with Black

```bash
# Format all code
black balaganagent/ tests/

# Check without modifying
black --check balaganagent/ tests/

# Format specific file
black balaganagent/engine.py
```

### Linting with Ruff

```bash
# Lint all code
ruff check balaganagent/ tests/

# Auto-fix issues
ruff check --fix balaganagent/ tests/

# Check specific file
ruff check balaganagent/engine.py
```

### Type Checking with Mypy

```bash
# Type check entire project
mypy balaganagent/

# Check specific file
mypy balaganagent/engine.py

# Strict mode
mypy --strict balaganagent/
```

### Pre-commit Checks

Before committing, run:

```bash
# Format code
black balaganagent/ tests/

# Lint
ruff check --fix balaganagent/ tests/

# Type check
mypy balaganagent/

# Run tests
pytest
```

## Development Workflow

### Branching Strategy

- `main`: Stable release branch
- `develop`: Development branch (if used)
- `feat/feature-name`: Feature branches
- `fix/bug-name`: Bug fix branches
- `docs/topic`: Documentation branches

### Creating a Feature

```bash
# Create and switch to feature branch
git checkout -b feat/my-new-feature

# Make changes, commit often
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feat/my-new-feature
```

### Commit Messages

Use conventional commits:

```
feat: add new hallucination type
fix: resolve timeout handling bug
docs: update README examples
test: add coverage for delay injector
refactor: simplify metrics collection
chore: update dependencies
```

### Pull Request Process

1. Create feature branch from `main`
2. Make your changes with tests
3. Ensure all tests pass
4. Ensure code quality checks pass
5. Update documentation if needed
6. Create pull request
7. Address review feedback
8. Squash and merge when approved

## CLI Development

### Running CLI Locally

```bash
# Run from source
python -m balaganagent.cli demo --chaos-level 0.5

# Or use installed command
balaganagent demo --chaos-level 0.5
```

### Adding CLI Commands

Edit `balaganagent/cli.py`:

```python
@click.command()
@click.option('--param', help='Description')
def new_command(param):
    """Command description."""
    # Implementation
    pass

# Register in CLI group
cli.add_command(new_command)
```

### Testing CLI

```bash
# Test CLI commands
python -m balaganagent.cli --help
python -m balaganagent.cli demo --help

# Test with different options
python -m balaganagent.cli demo --chaos-level 0.5 --verbose
```

## Adding New Features

### Adding a New Injector

1. Create file in `balaganagent/injectors/`:

```python
# balaganagent/injectors/my_injector.py
from dataclasses import dataclass
from .base import Injector, InjectorConfig

@dataclass
class MyInjectorConfig(InjectorConfig):
    probability: float = 0.1
    # Add config fields

class MyInjector(Injector):
    def __init__(self, config: MyInjectorConfig):
        self.config = config

    def should_inject(self) -> bool:
        # Injection logic
        pass

    def inject(self, *args, **kwargs):
        # Fault injection logic
        pass
```

2. Register in `balaganagent/injectors/__init__.py`:

```python
from .my_injector import MyInjector, MyInjectorConfig
```

3. Add tests in `tests/test_my_injector.py`

4. Update documentation

### Adding a New Wrapper

1. Create file in `balaganagent/wrappers/`:

```python
# balaganagent/wrappers/myframework.py
from balaganagent.wrapper import AgentWrapper

class MyFrameworkWrapper(AgentWrapper):
    def __init__(self, agent, chaos_level: float = 1.0):
        super().__init__(agent, chaos_level)

    def kickoff(self, *args, **kwargs):
        # Framework-specific execution
        pass
```

2. Add optional dependency in `pyproject.toml`:

```toml
[project.optional-dependencies]
myframework = [
    "myframework>=1.0.0",
]
```

3. Add tests in `tests/test_myframework_wrapper.py`

4. Create integration guide

### Adding Metrics

1. Create metric in `balaganagent/metrics/`:

```python
# balaganagent/metrics/my_metric.py
class MyMetric:
    def __init__(self):
        self.data = []

    def record(self, value):
        self.data.append(value)

    def calculate(self):
        # Calculation logic
        pass
```

2. Integrate with `MetricsCollector`

3. Add tests

4. Update reporting

## Testing with Agent Frameworks

### CrewAI Testing

```bash
# Install CrewAI dependencies
pip install -e ".[crewai]"

# Set up API keys (if needed)
export OPENAI_API_KEY="your-key"

# Run CrewAI tests
pytest tests/test_crewai_wrapper.py -v

# Run with Gemini
pip install -e ".[crewai-gemini]"
export GOOGLE_API_KEY="your-key"
pytest tests/test_crewai_gemini_agent.py -v
```

### AutoGen Testing

```bash
pip install -e ".[autogen]"
pytest tests/test_autogen_wrapper.py -v
```

### LangChain Testing

```bash
pip install -e ".[langchain]"
pytest tests/test_langchain_wrapper.py -v
```

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify installation
pip list | grep balagan-agent
```

### Test Failures

```bash
# Run specific failing test with verbose output
pytest tests/test_file.py::test_name -vv

# Check test logs
pytest tests/ -v --log-cli-level=DEBUG
```

### Type Checking Issues

```bash
# Ignore specific errors (add to code)
# type: ignore[error-code]

# Update type stubs
pip install types-*
```

### Coverage Issues

```bash
# Generate coverage report
pytest --cov=balaganagent --cov-report=term-missing

# View HTML report
pytest --cov=balaganagent --cov-report=html
open htmlcov/index.html
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Dependency Conflicts

```bash
# Update dependencies
pip install --upgrade pip
pip install --upgrade -e ".[dev]"

# Clear cache
pip cache purge
```

## Resources

- [Contributing Guide](CONTRIBUTING.md) - Contribution guidelines
- [Security Policy](SECURITY.md) - Security and vulnerability reporting
- [Changelog](CHANGELOG.md) - Version history
- [Issue Tracker](https://github.com/arielshad/balagan-agent/issues)
- [Discussions](https://github.com/arielshad/balagan-agent/discussions)

## Getting Help

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Code Review**: Request reviews on your PRs

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to improve agent reliability!

---

Happy coding! If you find any issues with this guide, please open an issue or PR.
