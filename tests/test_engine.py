"""Tests for the chaos engine."""

import pytest

from agentchaos import ChaosEngine
from agentchaos.experiment import ExperimentConfig, ExperimentStatus


class TestChaosEngine:
    """Tests for ChaosEngine."""

    def test_creation(self):
        engine = ChaosEngine()
        assert engine.chaos_level == 1.0

    def test_creation_with_config(self):
        engine = ChaosEngine(chaos_level=0.5, seed=42)
        assert engine.chaos_level == 0.5

    def test_wrap_tool(self):
        engine = ChaosEngine(chaos_level=0.0)  # No chaos

        def my_tool(x: int) -> int:
            return x * 2

        wrapped = engine.wrap_tool(my_tool)

        assert wrapped(5) == 10
        assert wrapped._chaos_wrapped is True

    def test_wrap_tool_with_name(self):
        engine = ChaosEngine()

        def my_func():
            pass

        wrapped = engine.wrap_tool(my_func, tool_name="custom_name")
        assert wrapped.__name__ == "custom_name"

    def test_experiment_context(self):
        engine = ChaosEngine(chaos_level=0.0)

        with engine.experiment("test-experiment") as exp:
            assert exp.status == ExperimentStatus.RUNNING

        results = engine.get_experiment_results()
        assert len(results) == 1
        assert results[0].config.name == "test-experiment"

    def test_experiment_operations(self):
        engine = ChaosEngine(chaos_level=0.0)

        with engine.experiment("test") as exp:
            with exp.operation("op1") as op:
                op.record_success()

            with exp.operation("op2") as op:
                op.record_failure("test error")

        result = engine.get_experiment_results()[-1]
        assert result.total_operations == 2
        assert result.successful_operations == 1
        assert result.failed_operations == 1

    def test_enable_disable_injector(self):
        engine = ChaosEngine()

        engine.disable_injector("tool_failure")
        injector = engine.get_injector("tool_failure")
        assert injector.config.enabled is False

        engine.enable_injector("tool_failure")
        assert injector.config.enabled is True

    def test_add_custom_injector(self):
        engine = ChaosEngine()

        from agentchaos.injectors import DelayInjector
        from agentchaos.injectors.delay import DelayConfig

        custom = DelayInjector(DelayConfig(probability=0.5))
        engine.add_injector("custom_delay", custom)

        assert engine.get_injector("custom_delay") is custom

    def test_remove_injector(self):
        engine = ChaosEngine()

        assert engine.get_injector("tool_failure") is not None
        engine.remove_injector("tool_failure")
        assert engine.get_injector("tool_failure") is None

    def test_injection_stats(self):
        engine = ChaosEngine(chaos_level=0.0)

        # Run some operations
        with engine.experiment("test"):
            pass

        stats = engine.get_injection_stats()
        assert "tool_failure" in stats
        assert "delay" in stats

    def test_reset(self):
        engine = ChaosEngine()

        with engine.experiment("test"):
            pass

        assert len(engine.get_experiment_results()) == 1

        engine.reset()
        assert len(engine.get_experiment_results()) == 0


class TestExperiment:
    """Tests for Experiment class."""

    def test_experiment_lifecycle(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test")
        exp = Experiment(config)

        assert exp.status == ExperimentStatus.PENDING

        exp.start()
        assert exp.status == ExperimentStatus.RUNNING

        result = exp.complete()
        assert exp.status == ExperimentStatus.COMPLETED
        assert result.config.name == "test"

    def test_experiment_abort(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test")
        exp = Experiment(config)
        exp.start()

        exp.abort("test abort reason")
        assert exp.status == ExperimentStatus.ABORTED

    def test_operation_context(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test")
        exp = Experiment(config)
        exp.start()

        with exp.operation("test_op") as op:
            op.record_success()

        result = exp.complete()
        assert result.total_operations == 1
        assert result.successful_operations == 1

    def test_operation_failure(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test")
        exp = Experiment(config)
        exp.start()

        with exp.operation("test_op") as op:
            op.record_failure("error message")

        result = exp.complete()
        assert result.failed_operations == 1

    def test_should_continue_duration(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test", duration_seconds=0.001)
        exp = Experiment(config)
        exp.start()

        import time
        time.sleep(0.01)

        assert exp.should_continue() is False

    def test_should_continue_iterations(self):
        from agentchaos.experiment import Experiment

        config = ExperimentConfig(name="test", max_iterations=2)
        exp = Experiment(config)
        exp.start()

        exp.record_operation("op1", success=True, duration=0.1)
        assert exp.should_continue() is True

        exp.record_operation("op2", success=True, duration=0.1)
        assert exp.should_continue() is False
