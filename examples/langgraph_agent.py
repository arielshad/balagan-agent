#!/usr/bin/env python3
"""
LangGraph chaos engineering example for BalaganAgent.

This example demonstrates how to:
1. Create a LangGraph state graph with tools (mocked)
2. Wrap the compiled graph with chaos injection
3. Run chaos experiments
4. Inject chaos at the node level
5. Analyze reliability metrics

Requires: pip install balagan-agent[langgraph]
"""

from balaganagent.wrappers.langgraph import LangGraphWrapper


# --- Mock objects for demonstration (replace with real LangGraph in production) ---


class MockTool:
    """Mock LangChain/LangGraph tool."""

    def __init__(self, name, func=None):
        self.name = name
        self.func = func or (lambda *a, **kw: f"{name} result")


class MockToolNode:
    """Mock LangGraph ToolNode."""

    def __init__(self, tools):
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}

    def __call__(self, state):
        return state


class MockCompiledGraph:
    """Mock LangGraph CompiledGraph."""

    def __init__(self, nodes=None, tools=None):
        self.nodes = nodes or {}
        self.tools = tools

    def invoke(self, input_data, **kwargs):
        state = dict(input_data)
        for node_func in self.nodes.values():
            result = node_func(state)
            if result is not None:
                state = result
        return state

    def stream(self, input_data, **kwargs):
        for node_name in self.nodes:
            yield {node_name: {"messages": [f"Output from {node_name}"]}}


# --- Examples ---


def example_basic_chaos():
    """Example: Basic LangGraph wrapping with chaos."""
    print("=" * 60)
    print("Example 1: Basic LangGraph Chaos Testing")
    print("=" * 60)

    # Create tools
    search_tool = MockTool("search", lambda q: f"Search results for: {q}")
    calc_tool = MockTool("calculator", lambda x: "42")

    # Build graph with a ToolNode
    tool_node = MockToolNode([search_tool, calc_tool])

    def agent_node(state):
        return {"messages": state.get("messages", []) + ["Agent processed"]}

    graph = MockCompiledGraph(nodes={"agent": agent_node, "tools": tool_node})

    # Wrap with chaos
    wrapper = LangGraphWrapper(graph, chaos_level=0.5)
    wrapper.configure_chaos(
        enable_tool_failures=True,
        enable_delays=True,
        enable_hallucinations=False,
    )

    # Run
    result = wrapper.invoke({"messages": ["Hello, search for AI agents"]})
    print(f"Result: {result}")

    # Check metrics
    metrics = wrapper.get_metrics()
    print(f"Invoke count: {metrics['invoke_count']}")
    print(f"Tools wrapped: {list(metrics['tools'].keys())}")
    print()


def example_node_level_chaos():
    """Example: Injecting chaos at specific graph nodes."""
    print("=" * 60)
    print("Example 2: Node-Level Chaos Injection")
    print("=" * 60)

    from balaganagent.injectors import DelayInjector
    from balaganagent.injectors.delay import DelayConfig

    def retriever_node(state):
        return {"messages": state.get("messages", []) + ["Retrieved documents"]}

    def generator_node(state):
        return {"messages": state.get("messages", []) + ["Generated response"]}

    graph = MockCompiledGraph(nodes={"retriever": retriever_node, "generator": generator_node})

    wrapper = LangGraphWrapper(graph, chaos_level=0.0)

    # Wrap specific node with delay injection
    proxy = wrapper.wrap_node("retriever")
    wrapper.add_injector(
        DelayInjector(DelayConfig(probability=0.5, min_delay_ms=100, max_delay_ms=500)),
        nodes=["retriever"],
    )

    print(f"Wrapped nodes: {list(wrapper.get_wrapped_nodes().keys())}")
    print(f"Node proxy: {proxy.node_name}")

    # Execute node directly to see chaos
    result = proxy({"messages": ["test"]})
    print(f"Node result: {result}")

    events = proxy.get_event_history()
    print(f"Node events: {len(events)}")
    for event in events:
        print(f"  - {event.node_name}: {event.duration_ms:.1f}ms, success={event.success}")
    print()


def example_experiment_tracking():
    """Example: Running a chaos experiment with a LangGraph agent."""
    print("=" * 60)
    print("Example 3: Experiment Tracking")
    print("=" * 60)

    graph = MockCompiledGraph()
    wrapper = LangGraphWrapper(graph, chaos_level=0.0)

    # Run experiment
    with wrapper.experiment("langgraph-reliability-test"):
        for i in range(5):
            wrapper.invoke({"messages": [f"Query {i}"]})

    results = wrapper.get_experiment_results()
    print(f"Experiments completed: {len(results)}")
    for result in results:
        print(f"  - {result.config.name}: status={result.status}")

    metrics = wrapper.get_metrics()
    print(f"Total invocations: {metrics['invoke_count']}")
    print()


def main():
    """Run all LangGraph examples."""
    print()
    print("BalaganAgent - LangGraph Chaos Engineering Examples")
    print("===================================================")
    print()

    example_basic_chaos()
    example_node_level_chaos()
    example_experiment_tracking()

    print("All examples completed!")


if __name__ == "__main__":
    main()
