# FAQ

## General

### What is BalaganAgent?

BalaganAgent is a chaos engineering framework for AI agents. It injects controlled failures (tool errors, latency, hallucinations, context corruption, budget exhaustion) into your agent's tool calls, then measures recovery time (MTTR) and reliability.

### Is this for production use?

No. BalaganAgent is designed for **development and CI testing**. You run chaos experiments against your agents in dev/staging to find failure modes before they hit production.

### Does it cost money?

BalaganAgent is free and open source (Apache 2.0). If your agent calls paid APIs (like LLMs), those API costs still apply during chaos experiments, but BalaganAgent itself is free.

### What does "balagan" mean?

"Balagan" (בלגן) is a Hebrew word meaning chaos or mess. It captures the spirit of controlled chaos testing.

## Technical

### Which agent frameworks are supported?

- **CrewAI** — full wrapper + integration guide
- **Microsoft AutoGen** — full wrapper
- **LangChain** — full wrapper
- **Claude Agent SDK** — full wrapper + hooks
- **Custom agents** — wrap any Python class

### How do I add a custom injector?

Subclass `BaseInjector` from `balaganagent.injectors.base`:

```python
from balaganagent.injectors.base import BaseInjector, InjectorConfig

class MyInjector(BaseInjector):
    def inject(self, tool_name, args, kwargs):
        # Your fault injection logic
        ...
```

See the [Contributing Guide](https://github.com/arielshad/balagan-agent/blob/main/CONTRIBUTING.md) for full details.

### What metrics does it collect?

- **MTTR** — Mean Time To Recovery (seconds)
- **Recovery quality** — did the agent recover correctly or just fail gracefully?
- **Reliability score** — SRE-grade (five nines to one nine)
- **Error budget tracking** — know when to freeze changes
- **Success rate, failure distributions, latency analysis**

### Can I use it in CI/CD?

Yes. Use the CLI to run experiments and assert on results:

```bash
balaganagent run scenarios/critical.json --format json -o results.json
# Then parse results.json in your CI pipeline
```

### What Python versions are supported?

Python 3.10, 3.11, and 3.12.

## Troubleshooting

### `balaganagent: command not found`

Make sure you installed with pip and the install location is on your PATH:

```bash
pip install balagan-agent
python -m balaganagent --version
```

### Import errors with framework wrappers

Install the optional dependencies for your framework:

```bash
pip install balagan-agent[crewai]
pip install balagan-agent[langchain]
pip install balagan-agent[autogen]
pip install balagan-agent[claude-agent-sdk]
```
