"""Tests for Claude Agent SDK research agent.

Test coverage includes:
- Unit tests for individual tools
- Integration tests for the research workflow
- Chaos testing for reliability under failures
- MTTR calculation and recovery patterns
"""

from __future__ import annotations

import os
import tempfile

import pytest

from balaganagent.injectors import ToolFailureInjector
from balaganagent.injectors.tool_failure import ToolFailureConfig
from balaganagent.wrappers.claude_sdk import ClaudeAgentSDKWrapper
from examples.claude_sdk_research_agent import ResearchConfig, run_research_agent
from examples.claude_sdk_research_tools import get_research_tools

# ---------------------------------------------------------------------------
# Unit Tests: Individual Tools
# ---------------------------------------------------------------------------


class TestResearchTools:
    """Test individual research tools."""

    def test_search_web_deterministic(self):
        """search_web returns consistent results (deterministic)."""
        tools = get_research_tools(mode="mock")
        search = next(t["func"] for t in tools if t["name"] == "search_web")

        result1 = search({"query": "AI safety"})
        result2 = search({"query": "AI safety"})

        assert result1 == result2
        assert "content" in result1
        assert len(result1["content"]) > 0
        assert result1["content"][0]["type"] == "text"

    def test_search_web_includes_query_in_result(self):
        """search_web includes the query in the result."""
        tools = get_research_tools(mode="mock")
        search = next(t["func"] for t in tools if t["name"] == "search_web")

        query = "machine learning"
        result = search({"query": query})

        result_text = result["content"][0]["text"]
        assert query in result_text

    def test_search_web_handles_empty_query(self):
        """search_web handles empty query gracefully."""
        tools = get_research_tools(mode="mock")
        search = next(t["func"] for t in tools if t["name"] == "search_web")

        result = search({"query": ""})

        assert "content" in result
        assert result["content"][0]["type"] == "text"

    def test_summarize_text_reduces_length(self):
        """summarize_text produces shorter output."""
        tools = get_research_tools(mode="mock")
        summarize = next(t["func"] for t in tools if t["name"] == "summarize_text")

        long_text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        result = summarize({"text": long_text})

        summary_text = result["content"][0]["text"]
        assert len(summary_text) < len(long_text)
        # Should keep first few sentences
        assert "Sentence one" in summary_text

    def test_summarize_text_handles_empty(self):
        """summarize_text handles empty text."""
        tools = get_research_tools(mode="mock")
        summarize = next(t["func"] for t in tools if t["name"] == "summarize_text")

        result = summarize({"text": ""})

        assert "content" in result
        assert result["content"][0]["type"] == "text"

    def test_save_report_creates_file(self):
        """save_report creates a file in the specified location."""
        tools = get_research_tools(mode="mock")
        save = next(t["func"] for t in tools if t["name"] == "save_report")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_report.md")
            result = save({"content": "Test report content", "filename": filepath})

            # Check file was created
            assert os.path.exists(filepath)

            # Check content
            with open(filepath, "r") as f:
                content = f.read()
                assert "Test report content" in content

            # Check result message
            assert "content" in result
            assert "Report saved" in result["content"][0]["text"]

    def test_save_report_default_filename(self):
        """save_report generates default filename when not specified."""
        tools = get_research_tools(mode="mock")
        save = next(t["func"] for t in tools if t["name"] == "save_report")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                save({"content": "Test content"})

                # Check that some file was created
                files = os.listdir(".")
                assert len(files) > 0
                assert files[0].startswith("research_report_")

            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# Unit Tests: Tool Factories
# ---------------------------------------------------------------------------


class TestToolFactories:
    """Test tool factory functions."""

    def test_get_research_tools_mock_mode(self):
        """get_research_tools returns three tools in mock mode."""
        tools = get_research_tools(mode="mock")

        assert len(tools) == 3
        assert tools[0]["name"] == "search_web"
        assert tools[1]["name"] == "summarize_text"
        assert tools[2]["name"] == "save_report"

    def test_get_research_tools_callable(self):
        """get_research_tools returns callable functions."""
        tools = get_research_tools(mode="mock")

        for tool in tools:
            assert callable(tool["func"])
            assert "func" in tool
            assert "name" in tool

    def test_get_research_tools_fresh_instances(self):
        """get_research_tools returns fresh instances each call."""
        tools1 = get_research_tools(mode="mock")
        tools2 = get_research_tools(mode="mock")

        # Different instances
        assert tools1[0]["func"] is not tools2[0]["func"]
        # But same behavior
        result1 = tools1[0]["func"]({"query": "test"})
        result2 = tools2[0]["func"]({"query": "test"})
        assert result1 == result2

    def test_get_research_tools_invalid_mode(self):
        """get_research_tools raises error for invalid mode."""
        with pytest.raises(ValueError):
            get_research_tools(mode="invalid_mode")


# ---------------------------------------------------------------------------
# Integration Tests: Chaos Wrapper
# ---------------------------------------------------------------------------


class TestChaosWrapperIntegration:
    """Test integration with BalaganAgent chaos wrapper."""

    def test_chaos_wrapper_wraps_tools(self):
        """ClaudeAgentSDKWrapper wraps research tools."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)

        tools = wrapper.get_wrapped_tools()

        assert "search_web" in tools
        assert "summarize_text" in tools
        assert "save_report" in tools
        assert callable(tools["search_web"])

    def test_chaos_wrapper_returns_list(self):
        """get_wrapped_tool_list returns proper format."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)

        tool_list = wrapper.get_wrapped_tool_list()

        assert isinstance(tool_list, list)
        assert len(tool_list) == 3
        assert all(callable(t) for t in tool_list)

    def test_chaos_wrapper_no_chaos_baseline(self):
        """Tools work without chaos (baseline test)."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.0)

        tools = wrapper.get_wrapped_tools()

        # All tools should work
        result1 = tools["search_web"]({"query": "test"})
        result2 = tools["summarize_text"]({"text": "test text"})

        assert "content" in result1
        assert "content" in result2

    def test_chaos_wrapper_preserves_tool_names(self):
        """Wrapped tools preserve their names."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)

        tools = wrapper.get_wrapped_tools()

        assert hasattr(tools["search_web"], "__name__")
        assert tools["search_web"].__name__ == "search_web"


# ---------------------------------------------------------------------------
# Integration Tests: Research Workflow
# ---------------------------------------------------------------------------


class TestResearchWorkflow:
    """Test the research agent workflow."""

    @pytest.mark.asyncio
    async def test_research_workflow_mock_mode(self):
        """Research workflow completes in mock mode."""
        config = ResearchConfig(topic="test topic", mode="mock", use_chaos=False, verbose=False)

        result = await run_research_agent(config)

        assert result["success"]
        assert "tool_outputs" in result
        assert "search" in result["tool_outputs"]
        assert "summary" in result["tool_outputs"]
        assert "report" in result["tool_outputs"]

    @pytest.mark.asyncio
    async def test_research_workflow_has_proper_structure(self):
        """Research workflow returns properly structured results."""
        config = ResearchConfig(topic="test", mode="mock", use_chaos=False, verbose=False)

        result = await run_research_agent(config)

        assert "tool_outputs" in result
        assert "success" in result
        assert "errors" in result
        assert isinstance(result["tool_outputs"], dict)
        assert isinstance(result["errors"], list)

    @pytest.mark.asyncio
    async def test_research_workflow_saves_report(self):
        """Research workflow saves a report file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                topic="quantum computing",
                mode="mock",
                use_chaos=False,
                output_dir=tmpdir,
                verbose=False,
            )

            await run_research_agent(config)

            # Check that a file was created
            files = os.listdir(tmpdir)
            assert len(files) > 0
            assert any(f.endswith(".md") for f in files)


# ---------------------------------------------------------------------------
# Chaos Tests: Reliability Under Failures
# ---------------------------------------------------------------------------


class TestChaosReliability:
    """Test research agent reliability under chaos injection."""

    def test_research_under_low_chaos(self):
        """Research completes with low chaos (0.25)."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.25)
        wrapper.configure_chaos(
            enable_tool_failures=True, enable_delays=True, enable_hallucinations=False
        )

        tools = wrapper.get_wrapped_tools()

        # Should mostly succeed at low chaos
        successes = 0
        for _ in range(5):
            try:
                tools["search_web"]({"query": "test"})
                successes += 1
            except Exception:
                pass

        assert successes >= 3  # At least 60% success

    def test_research_under_medium_chaos(self):
        """Research shows degradation under medium chaos (0.5)."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)
        wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

        tools = wrapper.get_wrapped_tools()

        successes = 0
        for _ in range(10):
            try:
                tools["search_web"]({"query": "test"})
                successes += 1
            except Exception:
                pass

        # Some should still work despite chaos
        assert successes > 0

    def test_research_under_high_chaos(self):
        """Research significantly degrades under high chaos (1.0)."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=1.0)
        wrapper.configure_chaos(enable_tool_failures=True, enable_delays=False)

        tools = wrapper.get_wrapped_tools()

        successes = 0
        for _ in range(10):
            try:
                tools["search_web"]({"query": "test"})
                successes += 1
            except Exception:
                pass

        # Success rate should be lower
        assert successes <= 7

    def test_targeted_failure_injection(self):
        """Can inject failures on specific tools."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)

        # Inject 100% failure on search_web
        injector = ToolFailureInjector(ToolFailureConfig(probability=1.0))
        wrapper.add_injector(injector, tools=["search_web"])

        tools = wrapper.get_wrapped_tools()

        # search_web should always fail
        with pytest.raises(Exception):
            tools["search_web"]({"query": "test"})

        # Other tools should work (no injector on them)
        result = tools["summarize_text"]({"text": "test"})
        assert "content" in result


# ---------------------------------------------------------------------------
# Chaos Tests: MTTR and Recovery
# ---------------------------------------------------------------------------


class TestChaosMetrics:
    """Test metrics collection under chaos."""

    def test_metrics_collection(self):
        """Wrapper collects metrics from tools."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)
        wrapper.configure_chaos(enable_tool_failures=True)

        tools = wrapper.get_wrapped_tools()

        # Make some calls
        for _ in range(5):
            try:
                tools["search_web"]({"query": "test"})
            except Exception:
                pass

        metrics = wrapper.get_metrics()

        assert "tools" in metrics
        assert "search_web" in metrics["tools"]
        assert "operations" in metrics["tools"]["search_web"]

    def test_mttr_calculation(self):
        """MTTR is calculated for tool failures."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=1.0)

        # Inject failures with low probability but some failures
        injector = ToolFailureInjector(ToolFailureConfig(probability=0.3))
        wrapper.add_injector(injector, tools=["search_web"])

        tools = wrapper.get_wrapped_tools()

        # Make multiple calls to get some failures and recoveries
        for _ in range(10):
            try:
                tools["search_web"]({"query": "test"})
            except Exception:
                pass

        mttr_stats = wrapper.get_mttr_stats()

        # Should have metrics
        assert "aggregate" in mttr_stats
        assert isinstance(mttr_stats["aggregate"], dict)

    def test_metrics_per_tool(self):
        """Metrics are collected per tool."""
        wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=0.5)
        wrapper.configure_chaos(enable_tool_failures=True)

        tools = wrapper.get_wrapped_tools()

        # Use multiple tools
        for _ in range(3):
            try:
                tools["search_web"]({"query": "test"})
            except Exception:
                pass

        for _ in range(3):
            try:
                tools["summarize_text"]({"text": "test"})
            except Exception:
                pass

        metrics = wrapper.get_metrics()

        # Both tools should have metrics
        assert "search_web" in metrics["tools"]
        assert "summarize_text" in metrics["tools"]


# ---------------------------------------------------------------------------
# Parametrized Tests: Multiple Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "chaos_level,min_success_rate",
    [
        (0.0, 1.0),  # No chaos - should have 100% success
        (0.25, 0.5),  # Light chaos - should work >50%
        (0.5, 0.2),  # Medium chaos - should work >20%
        (1.0, 0.1),  # Heavy chaos - should work >10%
    ],
)
def test_chaos_levels(chaos_level: float, min_success_rate: float):
    """Test agent reliability at different chaos levels."""
    wrapper = ClaudeAgentSDKWrapper(tools=get_research_tools(mode="mock"), chaos_level=chaos_level)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    tools = wrapper.get_wrapped_tools()

    successes = 0
    total = 20

    for _ in range(total):
        try:
            tools["search_web"]({"query": "test"})
            successes += 1
        except Exception:
            pass

    success_rate = successes / total
    assert success_rate >= min_success_rate


# ---------------------------------------------------------------------------
# Edge Cases and Error Handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_save_report_creates_parent_directories(self):
        """save_report creates parent directories as needed."""
        tools = get_research_tools(mode="mock")
        save = next(t["func"] for t in tools if t["name"] == "save_report")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "nested", "dirs", "report.md")
            save({"content": "Test", "filename": filepath})

            assert os.path.exists(filepath)
            assert os.path.isfile(filepath)

    def test_tools_with_special_characters(self):
        """Tools handle special characters in input."""
        tools = get_research_tools(mode="mock")

        special_query = "AI & safety: 你好! 🤖"
        result = tools[0]["func"]({"query": special_query})

        assert "content" in result

    def test_large_text_summarization(self):
        """summarize_text handles large text input."""
        tools = get_research_tools(mode="mock")
        summarize = next(t["func"] for t in tools if t["name"] == "summarize_text")

        large_text = ". ".join([f"Sentence {i}" for i in range(100)])
        result = summarize({"text": large_text})

        assert "content" in result
        summary = result["content"][0]["text"]
        assert len(summary) < len(large_text)
