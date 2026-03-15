"""Tests for metrics collection."""

import time

from balaganagent.metrics import (
    MetricsCollector,
    MTTRCalculator,
    RecoveryQualityAnalyzer,
    ReliabilityScorer,
)
from balaganagent.metrics.recovery import RecoveryQuality
from balaganagent.metrics.reliability import ReliabilityGrade


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
        assert "balaganagent_test_counter 5" in output

    def test_record_edge_traversal(self):
        """Test recording edge traversal events."""
        collector = MetricsCollector()

        start = collector.record_edge_traversal_start("node_a", "node_b")
        time.sleep(0.05)
        collector.record_edge_traversal_end("node_a", "node_b", start)

        traversals = collector.get_edge_traversals()
        assert len(traversals) == 1
        assert traversals[0].source_node == "node_a"
        assert traversals[0].target_node == "node_b"
        assert traversals[0].delay_ms >= 50

    def test_edge_traversal_with_state_mutation(self):
        """Test recording state mutation size during edge traversal."""
        collector = MetricsCollector()

        start = collector.record_edge_traversal_start("node_a", "node_b")
        time.sleep(0.01)
        collector.record_edge_traversal_end("node_a", "node_b", start, state_mutation_size=256)

        traversals = collector.get_edge_traversals()
        assert len(traversals) == 1

        # Check mutation size metric was recorded
        series = collector.get_series("state_mutation_size_bytes")
        assert series is not None
        assert series.count == 1
        assert series.values[0] == 256

    def test_get_edge_metrics(self):
        """Test retrieving aggregated edge metrics."""
        collector = MetricsCollector()

        # Record multiple traversals on same edge
        for _ in range(3):
            start = collector.record_edge_traversal_start("node_a", "node_b")
            time.sleep(0.01)
            collector.record_edge_traversal_end("node_a", "node_b", start)

        # Record traversals on different edge
        for _ in range(2):
            start = collector.record_edge_traversal_start("node_b", "node_c")
            time.sleep(0.02)
            collector.record_edge_traversal_end("node_b", "node_c", start)

        metrics = collector.get_edge_metrics()
        assert metrics["total_edge_traversals"] == 5
        assert len(metrics["edges"]) == 2
        assert metrics["edges"]["node_a->node_b"]["traversal_count"] == 3
        assert metrics["edges"]["node_b->node_c"]["traversal_count"] == 2

    def test_get_edge_traversals_between(self):
        """Test filtering traversals between specific nodes."""
        collector = MetricsCollector()

        # Record multiple edges
        for _ in range(2):
            start = collector.record_edge_traversal_start("node_a", "node_b")
            collector.record_edge_traversal_end("node_a", "node_b", start)

        for _ in range(3):
            start = collector.record_edge_traversal_start("node_a", "node_c")
            collector.record_edge_traversal_end("node_a", "node_c", start)

        # Get only a->b traversals
        ab_traversals = collector.get_edge_traversals_between("node_a", "node_b")
        assert len(ab_traversals) == 2

        # Get only a->c traversals
        ac_traversals = collector.get_edge_traversals_between("node_a", "node_c")
        assert len(ac_traversals) == 3

    def test_edge_metrics_reset(self):
        """Test that reset clears edge traversals."""
        collector = MetricsCollector()

        start = collector.record_edge_traversal_start("node_a", "node_b")
        collector.record_edge_traversal_end("node_a", "node_b", start)

        assert len(collector.get_edge_traversals()) == 1

        collector.reset()
        assert len(collector.get_edge_traversals()) == 0

    def test_edge_id_property(self):
        """Test edge_id property formatting."""
        from balaganagent.metrics.collector import EdgeTraversalEvent

        event = EdgeTraversalEvent(
            source_node="start", target_node="end", traversal_start=time.time()
        )
        assert event.edge_id == "start->end"


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
        time.sleep(0.2)
        calc.record_recovery("op1", "tool_failure")

        # Slower recovery for timeout
        calc.record_failure("op2", "timeout")
        time.sleep(0.5)
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
        analyzer.assess_recovery("op1", "error", {"a": 1}, {"a": 1}, 100, 120, 1)

        # Poor recovery
        analyzer.assess_recovery("op2", "timeout", {"a": 1}, None, 100, 1000, 5)

        summary = analyzer.get_summary()
        assert summary["total_assessments"] == 2

    def test_weakest_areas(self):
        analyzer = RecoveryQualityAnalyzer()

        # Multiple assessments for same operation
        for _ in range(3):
            analyzer.assess_recovery(
                "flaky_op", "error", {"a": 1}, {"a": 2}, 100, 500, 3  # Wrong output
            )

        for _ in range(3):
            analyzer.assess_recovery(
                "stable_op", "error", {"a": 1}, {"a": 1}, 100, 100, 0  # Correct output
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
        # 80% availability is below 90%, so grade should be BELOW_90
        assert report.grade == ReliabilityGrade.BELOW_90

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

    def test_state_schema_validation_establishes_schema(self):
        """Test that state schema validation establishes a baseline schema."""
        collector = MetricsCollector()

        state = {"messages": [], "context": "initial"}
        collector.validate_state_schema("node_a", state)

        # No violations on first call
        assert collector.get_counter("consistency_violations") == 0

    def test_state_schema_validation_detects_new_fields(self):
        """Test that new unexpected fields are detected."""
        collector = MetricsCollector()

        # Establish schema
        collector.validate_state_schema("node_a", {"messages": [], "context": "initial"})

        # Add new field
        collector.validate_state_schema("node_a", {"messages": [], "context": "updated", "extra": "field"})

        violations = collector.get_consistency_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "unexpected_fields"
        assert "extra" in violations[0].details

    def test_state_schema_validation_detects_missing_fields(self):
        """Test that missing fields are detected."""
        collector = MetricsCollector()

        # Establish schema
        collector.validate_state_schema("node_a", {"messages": [], "context": "initial"})

        # Remove a field
        collector.validate_state_schema("node_a", {"messages": []})

        violations = collector.get_consistency_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "missing_fields"
        assert "context" in violations[0].details

    def test_state_mutation_reasonableness_detects_growth(self):
        """Test detection of explosive collection growth."""
        collector = MetricsCollector()

        state_before = {"items": [1, 2, 3]}
        state_after = {"items": list(range(50))}  # 3 -> 50 is >10x

        collector.check_state_mutation_reasonableness("node_a", state_before, state_after)

        violations = collector.get_consistency_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "explosive_growth"
        assert "items" in violations[0].details

    def test_state_mutation_reasonableness_allows_normal_growth(self):
        """Test that normal growth doesn't trigger violations."""
        collector = MetricsCollector()

        state_before = {"items": [1, 2, 3]}
        state_after = {"items": [1, 2, 3, 4, 5]}  # 3 -> 5 is normal

        collector.check_state_mutation_reasonableness("node_a", state_before, state_after)

        violations = collector.get_consistency_violations()
        assert len(violations) == 0

    def test_get_consistency_violations_for_node(self):
        """Test filtering violations by node."""
        collector = MetricsCollector()

        # Create violations on different nodes
        collector.validate_state_schema("node_a", {"x": 1})
        collector.validate_state_schema("node_b", {"y": 2})

        collector.validate_state_schema("node_a", {"x": 1, "z": 3})
        collector.validate_state_schema("node_b", {"y": 2})

        violations_a = collector.get_consistency_violations_for_node("node_a")
        violations_b = collector.get_consistency_violations_for_node("node_b")

        assert len(violations_a) == 1
        assert violations_a[0].violation_type == "unexpected_fields"
        assert len(violations_b) == 0

    def test_get_consistency_summary(self):
        """Test consistency summary generation."""
        collector = MetricsCollector()

        # Create various violations
        collector.validate_state_schema("node_a", {"x": 1})
        collector.validate_state_schema("node_a", {"x": 1, "new": 2})  # unexpected field
        collector.validate_state_schema("node_a", {"x": 1, "new": 2})  # missing field (x disappeared from previous)

        collector.validate_state_schema("node_b", {"items": [1, 2]})
        collector.check_state_mutation_reasonableness("node_b", {"items": [1]}, {"items": list(range(20))})

        summary = collector.get_consistency_summary()
        assert summary["total_violations"] >= 2  # At least 2 violations created
        assert "unexpected_fields" in summary["violations_by_type"]
        assert "explosive_growth" in summary["violations_by_type"]
        assert "node_a" in summary["violations_by_node"]
        assert "node_b" in summary["violations_by_node"]
        assert len(summary["recent_violations"]) > 0

    def test_consistency_violations_reset(self):
        """Test that consistency violations are reset."""
        collector = MetricsCollector()

        collector.validate_state_schema("node_a", {"x": 1})
        collector.validate_state_schema("node_a", {"x": 1, "new": 2})

        assert len(collector.get_consistency_violations()) == 1

        collector.reset()
        assert len(collector.get_consistency_violations()) == 0
