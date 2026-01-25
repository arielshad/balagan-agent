"""Tests for metrics collection."""

import pytest
import time

from agentchaos.metrics import (
    MetricsCollector,
    MTTRCalculator,
    RecoveryQualityAnalyzer,
    ReliabilityScorer,
)
from agentchaos.metrics.recovery import RecoveryQuality
from agentchaos.metrics.reliability import ReliabilityGrade


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_creation(self):
        collector = MetricsCollector()
        assert collector.get_counter("operations_total") == 0

    def test_record_metric(self):
        collector = MetricsCollector()
        collector.record("latency_ms", 100)
        collector.record("latency_ms", 150)
        collector.record("latency_ms", 200)

        series = collector.get_series("latency_ms")
        assert series.count == 3
        assert series.mean() == 150

    def test_increment_counter(self):
        collector = MetricsCollector()
        collector.increment("calls")
        collector.increment("calls")
        collector.increment("calls", 3)

        assert collector.get_counter("calls") == 5

    def test_record_operation(self):
        collector = MetricsCollector()

        collector.record_operation("search", latency_ms=100, success=True)
        collector.record_operation("search", latency_ms=150, success=True)
        collector.record_operation("search", latency_ms=200, success=False)

        assert collector.get_counter("operations_total") == 3
        assert collector.get_counter("operations_successful") == 2
        assert collector.get_counter("operations_failed") == 1

    def test_summary(self):
        collector = MetricsCollector()

        for i in range(10):
            collector.record_operation(
                "test",
                latency_ms=100 + i * 10,
                success=i < 8,  # 80% success rate
            )

        summary = collector.get_summary()
        assert summary["operations"]["total"] == 10
        assert summary["operations"]["success_rate"] == 0.8

    def test_export_prometheus(self):
        collector = MetricsCollector()
        collector.increment("test_counter", 5)

        output = collector.export_prometheus()
        assert "agentchaos_test_counter 5" in output


class TestMTTRCalculator:
    """Tests for MTTRCalculator."""

    def test_creation(self):
        calc = MTTRCalculator()
        assert calc.calculate_mttr() == 0.0

    def test_record_failure_and_recovery(self):
        calc = MTTRCalculator()

        calc.record_failure("search", "tool_failure")
        time.sleep(0.1)
        calc.record_recovery("search", "tool_failure", recovery_method="retry")

        mttr = calc.calculate_mttr()
        assert mttr >= 0.1

    def test_mttr_by_fault_type(self):
        calc = MTTRCalculator()

        # Fast recovery for tool_failure
        calc.record_failure("op1", "tool_failure")
        time.sleep(0.05)
        calc.record_recovery("op1", "tool_failure")

        # Slower recovery for timeout
        calc.record_failure("op2", "timeout")
        time.sleep(0.1)
        calc.record_recovery("op2", "timeout")

        by_type = calc.calculate_mttr_by_fault_type()
        assert "tool_failure" in by_type
        assert "timeout" in by_type
        assert by_type["timeout"] > by_type["tool_failure"]

    def test_recovery_stats(self):
        calc = MTTRCalculator()

        calc.record_failure("op1", "error")
        calc.record_recovery("op1", "error", retries=2, success=True)

        calc.record_failure("op2", "error")
        calc.record_recovery("op2", "error", retries=5, success=False)

        stats = calc.get_recovery_stats()
        assert stats["total_recoveries"] == 2
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 1
        assert stats["total_retries"] == 7


class TestRecoveryQualityAnalyzer:
    """Tests for RecoveryQualityAnalyzer."""

    def test_creation(self):
        analyzer = RecoveryQualityAnalyzer()
        summary = analyzer.get_summary()
        assert summary["total_assessments"] == 0

    def test_assess_perfect_recovery(self):
        analyzer = RecoveryQualityAnalyzer()

        assessment = analyzer.assess_recovery(
            operation_name="search",
            fault_type="tool_failure",
            expected_output={"result": "test"},
            actual_output={"result": "test"},
            baseline_latency_ms=100,
            actual_latency_ms=100,
            retries=0,
        )

        assert assessment.quality == RecoveryQuality.EXCELLENT
        assert assessment.score >= 0.9

    def test_assess_degraded_recovery(self):
        analyzer = RecoveryQualityAnalyzer()

        assessment = analyzer.assess_recovery(
            operation_name="search",
            fault_type="tool_failure",
            expected_output={"result": "test"},
            actual_output={"result": "wrong"},  # Wrong output
            baseline_latency_ms=100,
            actual_latency_ms=500,  # 5x slower
            retries=3,  # Multiple retries
        )

        assert assessment.quality in [RecoveryQuality.ACCEPTABLE, RecoveryQuality.POOR]
        assert assessment.score < 0.9

    def test_summary_with_multiple_assessments(self):
        analyzer = RecoveryQualityAnalyzer()

        # Good recovery
        analyzer.assess_recovery(
            "op1", "error",
            {"a": 1}, {"a": 1},
            100, 120, 1
        )

        # Poor recovery
        analyzer.assess_recovery(
            "op2", "timeout",
            {"a": 1}, None,
            100, 1000, 5
        )

        summary = analyzer.get_summary()
        assert summary["total_assessments"] == 2

    def test_weakest_areas(self):
        analyzer = RecoveryQualityAnalyzer()

        # Multiple assessments for same operation
        for _ in range(3):
            analyzer.assess_recovery(
                "flaky_op", "error",
                {"a": 1}, {"a": 2},  # Wrong output
                100, 500, 3
            )

        for _ in range(3):
            analyzer.assess_recovery(
                "stable_op", "error",
                {"a": 1}, {"a": 1},  # Correct output
                100, 100, 0
            )

        weak = analyzer.get_weakest_areas(top_n=1)
        assert len(weak) == 1
        assert "flaky_op" in weak[0]["key"]


class TestReliabilityScorer:
    """Tests for ReliabilityScorer."""

    def test_creation(self):
        scorer = ReliabilityScorer()
        report = scorer.calculate_score()
        assert report.overall_score >= 0

    def test_perfect_reliability(self):
        scorer = ReliabilityScorer()

        for _ in range(100):
            scorer.record_operation(success=True, latency_ms=50)

        report = scorer.calculate_score()
        assert report.availability == 1.0
        assert report.grade in [ReliabilityGrade.FIVE_NINES, ReliabilityGrade.FOUR_NINES]

    def test_degraded_reliability(self):
        scorer = ReliabilityScorer()

        for i in range(100):
            scorer.record_operation(
                success=i < 80,  # 80% success rate
                latency_ms=100 if i < 80 else 5000,
            )

        report = scorer.calculate_score()
        assert report.availability == 0.8
        assert report.grade == ReliabilityGrade.ONE_NINE

    def test_error_budget(self):
        scorer = ReliabilityScorer(slos={"availability": 0.99})

        # Exactly at SLO
        for i in range(100):
            scorer.record_operation(success=i < 99, latency_ms=50)

        report = scorer.calculate_score()
        budget = report.raw_metrics["error_budget"]

        # Should have consumed most of budget
        assert budget["consumed"] == 1
        assert budget["remaining_percent"] <= 0.1

    def test_recommendations(self):
        scorer = ReliabilityScorer()

        # Create scenario that should generate recommendations
        for i in range(100):
            scorer.record_operation(
                success=i < 70,  # 70% success rate - below SLO
                latency_ms=3000,  # High latency
            )

        report = scorer.calculate_score()
        assert len(report.recommendations) > 0

    def test_mttr_calculation(self):
        scorer = ReliabilityScorer()

        scorer.record_recovery(recovery_time_seconds=1.0)
        scorer.record_recovery(recovery_time_seconds=2.0)
        scorer.record_recovery(recovery_time_seconds=3.0)

        report = scorer.calculate_score()
        assert report.mttr_seconds == 2.0  # Mean of 1, 2, 3
