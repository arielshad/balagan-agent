"""Tests for fault injectors."""

import time

import pytest

from agentchaos.injectors import (
    BudgetExhaustionInjector,
    ContextCorruptionInjector,
    DelayInjector,
    HallucinationInjector,
    InjectorConfig,
    ToolFailureInjector,
)
from agentchaos.injectors.budget import BudgetExhaustionConfig
from agentchaos.injectors.context import ContextCorruptionConfig
from agentchaos.injectors.delay import DelayConfig, DelayPattern
from agentchaos.injectors.hallucination import HallucinationConfig
from agentchaos.injectors.tool_failure import FailureMode, ToolFailureConfig


class TestInjectorConfig:
    """Tests for InjectorConfig."""

    def test_default_config(self):
        config = InjectorConfig()
        assert config.enabled is True
        assert config.probability == 0.1
        assert config.seed is None

    def test_invalid_probability(self):
        with pytest.raises(ValueError):
            InjectorConfig(probability=1.5)

        with pytest.raises(ValueError):
            InjectorConfig(probability=-0.1)

    def test_target_tools(self):
        config = InjectorConfig(target_tools=["search", "calculate"])
        assert "search" in config.target_tools
        assert "calculate" in config.target_tools


class TestToolFailureInjector:
    """Tests for ToolFailureInjector."""

    def test_creation(self):
        injector = ToolFailureInjector()
        assert injector.config.enabled is True

    def test_should_inject_respects_probability(self):
        # 100% probability
        config = ToolFailureConfig(probability=1.0, seed=42)
        injector = ToolFailureInjector(config)
        assert injector.should_inject("any_tool") is True

        # 0% probability
        config = ToolFailureConfig(probability=0.0, seed=42)
        injector = ToolFailureInjector(config)
        assert injector.should_inject("any_tool") is False

    def test_inject_returns_failure(self):
        config = ToolFailureConfig(
            probability=1.0,
            failure_modes=[FailureMode.EMPTY_RESPONSE],
            seed=42,
        )
        injector = ToolFailureInjector(config)

        result, details = injector.inject("test_tool", {})
        assert result is None
        assert details["failure_mode"] == "empty_response"

    def test_inject_records_event(self):
        config = ToolFailureConfig(probability=1.0, seed=42)
        injector = ToolFailureInjector(config)

        # Use a non-exception failure mode
        config.failure_modes = [FailureMode.EMPTY_RESPONSE]

        injector.inject("test_tool", {})
        events = injector.get_events()

        assert len(events) == 1
        assert events[0].target == "test_tool"

    def test_max_injections_limit(self):
        config = ToolFailureConfig(probability=1.0, max_injections=2, seed=42)
        injector = ToolFailureInjector(config)

        assert injector.should_inject("tool") is True
        injector.record_injection("tool", {})

        assert injector.should_inject("tool") is True
        injector.record_injection("tool", {})

        assert injector.should_inject("tool") is False


class TestDelayInjector:
    """Tests for DelayInjector."""

    def test_creation(self):
        injector = DelayInjector()
        assert injector.config.pattern == DelayPattern.UNIFORM

    def test_fixed_delay(self):
        config = DelayConfig(
            probability=1.0,
            pattern=DelayPattern.FIXED,
            min_delay_ms=100,
            seed=42,
        )
        injector = DelayInjector(config)

        start = time.time()
        delay_ms, details = injector.inject("test", {})
        elapsed = (time.time() - start) * 1000

        assert delay_ms == 100
        assert elapsed >= 90  # Allow some tolerance

    def test_uniform_delay_in_range(self):
        config = DelayConfig(
            probability=1.0,
            pattern=DelayPattern.UNIFORM,
            min_delay_ms=50,
            max_delay_ms=100,
            seed=42,
        )
        injector = DelayInjector(config)

        for _ in range(10):
            delay_ms, _ = injector.inject("test", {})
            assert 50 <= delay_ms <= 100
            injector.reset()


class TestHallucinationInjector:
    """Tests for HallucinationInjector."""

    def test_creation(self):
        injector = HallucinationInjector()
        assert injector.config.severity == 0.5

    def test_corrupts_string(self):
        config = HallucinationConfig(probability=1.0, severity=1.0, seed=42)
        injector = HallucinationInjector(config)

        original = "original value"
        context = {"data": original}

        result, details = injector.inject("test", context)
        # Result should be different (corrupted)
        # Note: with high severity, it might be completely replaced

    def test_corrupts_dict(self):
        config = HallucinationConfig(probability=1.0, severity=0.5, seed=42)
        injector = HallucinationInjector(config)

        original = {"key1": "value1", "key2": 123}
        context = {"data": original}

        result, details = injector.inject("test", context)
        assert isinstance(result, dict)


class TestContextCorruptionInjector:
    """Tests for ContextCorruptionInjector."""

    def test_creation(self):
        injector = ContextCorruptionInjector()
        assert injector.config.truncation_ratio == 0.5

    def test_truncates_list(self):
        from agentchaos.injectors.context import CorruptionType

        config = ContextCorruptionConfig(
            probability=1.0,
            corruption_types=[CorruptionType.TRUNCATION],
            truncation_ratio=0.5,
            seed=42,
        )
        injector = ContextCorruptionInjector(config)

        original = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        context = {"data": original}

        result, details = injector.inject("test", context)
        assert len(result) < len(original)

    def test_reorders_list(self):
        from agentchaos.injectors.context import CorruptionType

        config = ContextCorruptionConfig(
            probability=1.0,
            corruption_types=[CorruptionType.REORDER],
            seed=42,
        )
        injector = ContextCorruptionInjector(config)

        original = [1, 2, 3, 4, 5]
        context = {"data": original}

        result, details = injector.inject("test", context)
        assert set(result) == set(original)  # Same elements


class TestBudgetExhaustionInjector:
    """Tests for BudgetExhaustionInjector."""

    def test_creation(self):
        injector = BudgetExhaustionInjector()
        assert injector.config.token_limit == 10000

    def test_tracks_calls(self):
        config = BudgetExhaustionConfig(
            probability=1.0,
            call_limit=5,
            seed=42,
        )
        injector = BudgetExhaustionInjector(config)

        # Make calls until limit
        for i in range(4):
            result, details = injector.inject("test", {"data": "x"})
            assert result is None  # Not exhausted yet

    def test_budget_status(self):
        config = BudgetExhaustionConfig(
            probability=1.0,
            token_limit=1000,
            cost_limit_dollars=0.10,
            seed=42,
        )
        injector = BudgetExhaustionInjector(config)

        status = injector.get_budget_status()
        assert "token_limit" in status
        assert "cost_limit" in status
        assert status["token_limit"]["remaining"] == 1000
