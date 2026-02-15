# Integrations

BalaganAgent provides first-class wrappers for major AI agent frameworks. Each wrapper intercepts tool calls and injects chaos transparently.

## CrewAI

```python
from crewai import Agent, Task, Crew
from balaganagent.wrappers.crewai import CrewAIWrapper

# Your existing CrewAI setup
crew = Crew(agents=[agent], tasks=[task])

# Add chaos testing (3 lines)
wrapper = CrewAIWrapper(crew, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.kickoff()

# Check metrics
metrics = wrapper.get_metrics()
print(f"Success rate: {metrics['aggregate']['operations']['success_rate']:.1%}")
```

For a full walkthrough, see the [CrewAI Integration Guide](https://github.com/arielshad/balagan-agent/blob/main/CREWAI_INTEGRATION_GUIDE.md).

## AutoGen

```python
from balaganagent.wrappers.autogen import AutoGenWrapper

wrapper = AutoGenWrapper(autogen_agent, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True)
result = wrapper.run(task)
```

## LangChain

```python
from balaganagent.wrappers.langchain import LangChainWrapper

wrapper = LangChainWrapper(chain, chaos_level=0.5)
wrapper.configure_chaos(enable_hallucinations=True)
result = wrapper.invoke(input_data)
```

## LangGraph

```python
from langgraph.graph import StateGraph
from balaganagent.wrappers.langgraph import LangGraphWrapper

# Build and compile your graph
graph = StateGraph(AgentState)
# ... add nodes, edges, tool nodes ...
compiled = graph.compile()

# Add chaos testing (3 lines)
wrapper = LangGraphWrapper(compiled, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.invoke({"messages": [HumanMessage(content="Hello")]})

# Check metrics
metrics = wrapper.get_metrics()
print(f"Success rate: {metrics['aggregate']['operations']['success_rate']:.1%}")
```

### Node-Level Chaos (LangGraph-specific)

```python
from balaganagent.injectors import DelayInjector
from balaganagent.injectors.delay import DelayConfig

# Wrap specific nodes for chaos injection
wrapper.wrap_node("tool_executor")
wrapper.add_injector(
    DelayInjector(DelayConfig(probability=0.5, min_delay_ms=100, max_delay_ms=500)),
    nodes=["tool_executor"],
)
```

## Claude Agent SDK

```python
from balaganagent.wrappers.claude_sdk import ClaudeSDKWrapper

wrapper = ClaudeSDKWrapper(agent, chaos_level=0.5)
wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)
result = wrapper.run(task)
```

You can also use **chaos hooks** for deeper integration:

```python
from balaganagent.hooks.chaos_hooks import ChaosHooks

hooks = ChaosHooks(chaos_level=0.75)
# Attach hooks to your Claude SDK agent
agent.add_hooks(hooks)
```

## Custom Agents

Wrap any Python object that exposes tool methods:

```python
from balaganagent import AgentWrapper

wrapper = AgentWrapper(my_agent)
wrapper.configure_chaos(chaos_level=0.5)
result = wrapper.call_tool("my_tool", *args)
```

## Install extras

```bash
# Individual frameworks
pip install balagan-agent[crewai]
pip install balagan-agent[autogen]
pip install balagan-agent[langchain]
pip install balagan-agent[claude-agent-sdk]
pip install balagan-agent[langgraph]

# All wrappers
pip install balagan-agent[all-wrappers]
```
